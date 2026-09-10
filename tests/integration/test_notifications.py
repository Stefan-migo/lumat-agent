"""NT-1/NT-2 integration tests for durable notification delivery."""

import os
from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, Customer, NotificationAttempt, NotificationOperation
from app.services import notifications
from app.services.customers import get_or_create_customer


ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)


@pytest.fixture(autouse=True)
def clean_notifications_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE notification_attempts, notification_operations, audit_log, "
            "cases, messages, conversations, customers RESTART IDENTITY CASCADE"
        )
    yield


def _operation(**overrides):
    values = {
        "recipient": "+56911111111",
        "channel": "whatsapp",
        "content": "Appointment reminder",
        "source_entity": "appointment",
        "source_id": "42",
        "idempotency_key": "appointment:42:reminder:24h",
    }
    values.update(overrides)
    with SessionLocal() as session:
        operation = notifications.create_operation(session, **values)
        session.commit()
        return operation.id


def test_operation_is_persisted_before_delivery_and_duplicate_is_safe(migrated_db, monkeypatch):
    calls = []
    monkeypatch.setattr(notifications, "send_whatsapp", lambda recipient, content: calls.append((recipient, content)) or "wamid-1")

    operation_id = _operation()
    with SessionLocal() as session:
        operation = session.get(NotificationOperation, operation_id)
        assert operation.status == "pending"
        assert operation.recipient == "+56911111111"
        assert operation.content == "Appointment reminder"
        assert operation.idempotency_key == "appointment:42:reminder:24h"
        duplicate = notifications.create_operation(
            session,
            recipient=operation.recipient,
            channel=operation.channel,
            content=operation.content,
            source_entity=operation.source_entity,
            source_id=operation.source_id,
            idempotency_key=operation.idempotency_key,
        )
        session.commit()
        assert duplicate.id == operation_id
        assert len(session.scalars(select(NotificationOperation)).all()) == 1
        assert notifications.process_operation(session, operation_id) is True
        session.commit()

    assert calls == [("+56911111111", "Appointment reminder")]
    with SessionLocal() as session:
        operation = session.get(NotificationOperation, operation_id)
        assert operation.status == "sent"
        assert operation.attempts == 1
        assert len(session.scalars(select(NotificationAttempt)).all()) == 1


def test_failed_operation_is_retryable_then_permanently_exhausted(migrated_db, monkeypatch):
    monkeypatch.setattr(notifications, "send_whatsapp", lambda recipient, content: (_ for _ in ()).throw(OSError("offline")))
    operation_id = _operation(max_attempts=2)

    with SessionLocal() as session:
        assert notifications.process_operation(session, operation_id) is False
        session.commit()
    with SessionLocal() as session:
        operation = session.get(NotificationOperation, operation_id)
        assert operation.status == "retryable"
        assert operation.attempts == 1
        assert operation.next_attempt_at is not None
        assert notifications.process_operation(session, operation_id, now=operation.next_attempt_at) is False
        session.commit()

    with SessionLocal() as session:
        operation = session.get(NotificationOperation, operation_id)
        assert operation.status == "permanently_failed"
        assert operation.attempts == 2
        assert notifications.process_operation(session, operation_id, now=datetime.now(timezone.utc) + timedelta(days=1)) is False
        assert len(session.scalars(select(NotificationAttempt)).all()) == 2
        assert session.scalar(
            select(AuditLog).where(AuditLog.action == "notification.exhausted")
        ) is not None


def test_due_reminder_is_idempotent_and_sweep_is_bounded(migrated_db, monkeypatch):
    calls = []
    monkeypatch.setattr(notifications, "send_whatsapp", lambda recipient, content: calls.append(recipient) or "wamid")
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56922222222")
        session.commit()
        operation_id = notifications.create_due_reminder(
            session, customer_id=customer.id, reminder_kind="24h", due_at=datetime.now(timezone.utc)
        ).id
        notifications.create_due_reminder(
            session, customer_id=customer.id, reminder_kind="48h", due_at=datetime.now(timezone.utc)
        )
        session.commit()

    assert notifications.sweep_due_operations(limit=1) == 1
    assert notifications.sweep_due_operations(limit=1) == 1
    assert notifications.sweep_due_operations(limit=1) == 0
    assert calls == ["+56922222222", "+56922222222"]
    with SessionLocal() as session:
        pending = session.scalar(
            select(NotificationOperation).where(NotificationOperation.id != operation_id)
        )
        assert pending.status == "sent"
