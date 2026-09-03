"""AR-1/2/3 integration coverage for deterministic automation fan-out."""

from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, AutomationExecution, AutomationRule, DomainEvent, MessageType, NotificationOperation
from app.webhook.ingest import NormalizedMessage, persist_message
from app.services.events import publish_event


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
