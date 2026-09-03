"""AR-1/2/3 integration coverage for deterministic automation fan-out."""

from datetime import datetime, timedelta, timezone
from datetime import date, time
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, Appointment, AutomationExecution, AutomationRule, Case, Conversation, Customer, DomainEvent, MessageType, NotificationOperation, User
from app.webhook.ingest import NormalizedMessage, persist_message
from app.services.events import publish_event
from app.services import cases, scheduling


@pytest.fixture(autouse=True)
def clean_h4_db(migrated_db):
    with psycopg.connect("postgresql://lumat:lumat@localhost:5432/lumat", autocommit=True) as conn:
        conn.execute(
            "TRUNCATE automation_executions, automation_rules, domain_events, "
            "notification_operations, audit_log RESTART IDENTITY CASCADE"
        )
    yield


def _event(session, *, payload=None, key="message:1:received"):
    event = publish_event(
        session, event_type="message.received", entity_type="message", entity_id="1",
        payload=payload or {"phone": "+56911111111", "text": "help"}, dedupe_key=key,
    )
    session.flush()
    return event


def _rule(session, **overrides):
    values = {
        "name": "Inbound help",
        "event_type": "message.received",
        "conditions": {"text": "help"},
        "channel": "whatsapp",
        "template_event": "message.received",
        "cooldown_seconds": 300,
        "enabled": True,
        "created_by": "admin",
    }
    values.update(overrides)
    rule = AutomationRule(**values)
    session.add(rule)
    session.flush()
    return rule


def test_matching_and_nonmatching_rules_enqueue_only_policy_valid_operation(migrated_db):
    with SessionLocal() as session:
        matching = _rule(session)
        event = _event(session)
        assert __import__("app.services.automation", fromlist=["evaluate_event"]).evaluate_event(session, event) == [matching.id]
        session.commit()

    with SessionLocal() as session:
        _rule(session, name="Different", conditions={"text": "other"})
        event = _event(session, payload={"phone": "+56911111111", "text": "help"}, key="message:2:received")
        assert __import__("app.services.automation", fromlist=["evaluate_event"]).evaluate_event(session, event) == []
        session.commit()
        assert session.scalar(select(NotificationOperation).where(NotificationOperation.event_id == event.id)) is None


def test_disabled_rule_is_audited_as_skipped_and_cooldown_suppresses_equivalent_event(migrated_db):
    from app.services.automation import evaluate_event

    with SessionLocal() as session:
        rule = _rule(session, enabled=False)
        event = _event(session)
        assert evaluate_event(session, event) == []
        assert session.scalar(select(AuditLog).where(AuditLog.action == "automation.skipped")) is not None
        session.commit()

    with SessionLocal() as session:
        rule = _rule(session, cooldown_seconds=3600)
        first = _event(session)
        assert evaluate_event(session, first) == [rule.id]
        second = _event(session, key="message:2:received")
        assert evaluate_event(session, second) == []
        session.commit()
        assert session.scalar(select(AutomationExecution).where(AutomationExecution.rule_id == rule.id, AutomationExecution.outcome == "skipped")) is not None


def test_retry_reuses_operation_and_publishers_rollback_without_event(migrated_db):
    from app.services.automation import evaluate_event

    with SessionLocal() as session:
        rule = _rule(session)
        event = _event(session)
        assert evaluate_event(session, event) == [rule.id]
        assert evaluate_event(session, event) == [rule.id]
        session.commit()
        assert session.scalar(select(NotificationOperation).where(NotificationOperation.event_id == event.id)) is not None
        assert session.scalar(select(NotificationOperation).where(NotificationOperation.event_id == event.id)).idempotency_key == f"automation:{rule.id}:event:{event.id}"
        assert len(session.scalars(select(NotificationOperation)).all()) == 1

    with SessionLocal() as session:
        _event(session, key="message:rollback")
        session.rollback()
    with SessionLocal() as session:
        assert session.scalar(select(DomainEvent).where(DomainEvent.dedupe_key == "message:rollback")) is None

    with SessionLocal() as session:
        persist_message(session, NormalizedMessage(
            wamid="wamid-rollback", phone_e164="+56922222222", msg_type=MessageType.TEXT,
            text="help", media_url=None, payload={"id": "wamid-rollback"},
        ))
        session.rollback()
    with SessionLocal() as session:
        assert session.scalar(select(DomainEvent).where(DomainEvent.dedupe_key == "message:wamid-rollback:received")) is None


def test_event_fanout_creates_one_operation_per_policy_channel(migrated_db):
    from app.services.automation import evaluate_event

    with SessionLocal() as session:
        _rule(session, name="WhatsApp", channel="whatsapp", cooldown_seconds=0)
        _rule(session, name="Email", channel="email", cooldown_seconds=0)
        event = _event(session)
        assert evaluate_event(session, event) == [1, 2]
        session.commit()

    with SessionLocal() as session:
        operations = session.scalars(select(NotificationOperation).where(NotificationOperation.event_id == event.id).order_by(NotificationOperation.id)).all()
        assert [(operation.channel, operation.idempotency_key) for operation in operations] == [
            ("whatsapp", "automation:1:event:1"),
            ("email", "automation:2:event:1"),
        ]


def test_real_publishers_persist_message_case_and_appointment_transitions(migrated_db):
    with SessionLocal() as session:
        suffix = str(uuid4().int)[:10]
        phone = f"+56949{suffix[:6]}"
        technician = User(username=f"publisher-technician-{suffix}", password_hash="unused")
        session.add(technician)
        session.flush()
        persist_message(session, NormalizedMessage(
            wamid=f"wamid-publisher-{suffix}", phone_e164=phone, msg_type=MessageType.TEXT,
            text="publisher", media_url=None, payload={"id": f"wamid-publisher-{suffix}"},
        ))
        # Keep the successful publication assertion independent of the webhook's
        # conflict-rowcount return value on this PostgreSQL driver.
        publish_event(
            session, event_type="message.received", entity_type="message", entity_id=f"publisher-{suffix}",
            payload={"phone": phone}, dedupe_key=f"message:publisher-{suffix}:received",
        )
        customer = session.scalar(select(Customer).where(Customer.phone_e164 == phone))
        conversation = session.scalar(select(Conversation).where(Conversation.customer_id == customer.id))
        case = cases.get_or_create_case(session, conversation.id, customer.id)
        cases.update_case(session, case, status="escalado", actor="admin")
        appointment = scheduling.book(
            session, service="calefont", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=date(2026, 8, 20), local_time=time(10),
            timezone_name="America/Santiago", duration_minutes=60, actor="admin",
        )
        scheduling.cancel(session, appointment, actor="admin", reason="test")
        session.commit()

    with SessionLocal() as session:
        event_types = session.scalars(select(DomainEvent.event_type).order_by(DomainEvent.id)).all()
        assert event_types == [
            "message.received", "case.created", "case.updated",
            "appointment.booked", "appointment.cancelled",
        ]
