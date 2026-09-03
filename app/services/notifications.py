"""Durable, idempotent notification operations and bounded delivery."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import smtplib
from email.message import EmailMessage

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import session_scope
from app.models import Customer, NotificationAttempt, NotificationOperation
from app.services.audit import record_audit
from app.services.send import send_text

SWEEP_LOCK_KEY = 832731
DEFAULT_BATCH_SIZE = 50


def send_whatsapp(recipient: str, content: str) -> str:
    return send_text(recipient, content)


def send_email(recipient: str, content: str) -> None:
    message = EmailMessage()
    message["From"] = "notificaciones@lumat.cl"
    message["To"] = recipient
    message["Subject"] = "Notificación Lumat"
    message.set_content(content)
    with smtplib.SMTP("localhost") as server:
        server.send_message(message)


def create_operation(session: Session, **values) -> NotificationOperation:
    existing = session.scalar(
        select(NotificationOperation).where(
            NotificationOperation.idempotency_key == values["idempotency_key"]
        )
    )
    if existing is not None:
        return existing
    operation = NotificationOperation(**values)
    session.add(operation)
    session.flush()
    return operation


def create_due_reminder(
    session: Session, *, customer_id: int, reminder_kind: str, due_at: datetime,
    recipient: str | None = None, content: str | None = None,
) -> NotificationOperation:
    customer = session.get(Customer, customer_id)
    return create_operation(
        session,
        recipient=recipient or (customer.phone_e164 if customer is not None else str(customer_id)),
        channel="whatsapp",
        content=content or f"Reminder: {reminder_kind}",
        source_entity="customer",
        source_id=str(customer_id),
        idempotency_key=f"customer:{customer_id}:reminder:{reminder_kind}",
        next_attempt_at=due_at,
    )


def process_operation(
    session: Session, operation_id: int, *, now: datetime | None = None, deliver=None
) -> bool:
    now = now or datetime.now(timezone.utc)
    operation = session.scalar(
        select(NotificationOperation).where(NotificationOperation.id == operation_id).with_for_update()
    )
    if operation is None or operation.status in {"sent", "permanently_failed"}:
        return False
    if operation.next_attempt_at and operation.next_attempt_at > now:
        return False
    operation.status = "sending"
    operation.attempts += 1
    operation.last_attempt_at = now
    attempt = NotificationAttempt(operation_id=operation.id, attempt_number=operation.attempts, status="sending")
    session.add(attempt)
    session.flush()
    try:
        external_id = (deliver or (send_whatsapp if operation.channel == "whatsapp" else send_email))(
            operation.recipient, operation.content
        )
    except Exception as exc:
        error = str(exc)[:2000]
        attempt.status = "failed"
        attempt.error = error
        operation.error = error
        if operation.attempts >= operation.max_attempts:
            operation.status = "permanently_failed"
            record_audit(session, actor="system", action="notification.exhausted", entity="notification_operation", entity_id=str(operation.id), after={"attempts": operation.attempts, "error": error})
        else:
            operation.status = "retryable"
            operation.next_attempt_at = now + timedelta(minutes=2 ** (operation.attempts - 1))
        record_audit(session, actor="system", action="notification.attempt_failed", entity="notification_operation", entity_id=str(operation.id), after={"attempt": operation.attempts, "error": error, "status": operation.status})
        return False
    attempt.status = "sent"
    attempt.external_id = external_id
    operation.status = "sent"
    operation.error = None
    operation.delivered_at = now
    record_audit(session, actor="system", action="notification.operation_sent", entity="notification_operation", entity_id=str(operation.id), after={"channel": operation.channel, "recipient": operation.recipient, "attempt": operation.attempts})
    return True


def sweep_due_operations(limit: int = DEFAULT_BATCH_SIZE, *, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    with session_scope() as session:
        if not session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": SWEEP_LOCK_KEY}):
            return 0
        ids = session.scalars(
            select(NotificationOperation.id)
            .where(NotificationOperation.status.in_(("pending", "retryable")), NotificationOperation.next_attempt_at <= now)
            .order_by(NotificationOperation.id).limit(limit).with_for_update(skip_locked=True)
        ).all()
        return sum(process_operation(session, operation_id, now=now) for operation_id in ids)
