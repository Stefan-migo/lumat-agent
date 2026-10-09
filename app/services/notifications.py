"""Durable, idempotent notification operations and bounded delivery."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import smtplib
from email.message import EmailMessage

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import session_scope
from app.models import Appointment, AutomationExecution, AutomationRule, Customer, NotificationAttempt, NotificationOperation, NotificationTemplateVersion, PanelNotification, User, UserRole
from app.services.audit import record_audit
from app.services.send import send_text
from app.services.push import send_push
from app.services.realtime import stage_event

SWEEP_LOCK_KEY = 832731
DEFAULT_BATCH_SIZE = 50


class MissingReminderEmail(Exception):
    pass


def _send_appointment_reminder(session: Session, operation: NotificationOperation) -> str:
    from app.services import notify
    from app.services.settings import get_setting
    from app.services.templates import TemplatePolicyError, validate_channel_policy

    appointment = session.get(Appointment, int(operation.source_id))
    customer = session.get(Customer, appointment.customer_id) if appointment else None
    if appointment is None or customer is None or appointment.status.value != "booked":
        raise RuntimeError("appointment reminder no longer references a booked visit")
    template_name = get_setting(session, "notify.reminder_template_name", default="appointment_reminder_24h")
    template = session.scalar(select(NotificationTemplateVersion).where(
        NotificationTemplateVersion.event == "appointment.reminder.24h",
        NotificationTemplateVersion.channel == "whatsapp",
        NotificationTemplateVersion.locale == "es",
    ).order_by(NotificationTemplateVersion.version.desc()).limit(1))
    if template is None:
        raise TemplatePolicyError("appointment reminder WhatsApp template is not published")
    validate_channel_policy(channel="whatsapp", approved=template.approved, business_initiated=True)
    params = [appointment.local_start.strftime("%d/%m/%Y"), appointment.local_start.strftime("%H:%M")]
    try:
        return notify.send_template(operation.recipient, params, template_name=template_name)
    except Exception as whatsapp_error:
        if not customer.email:
            raise MissingReminderEmail("customer has no email for appointment reminder fallback") from whatsapp_error
        try:
            notify.send_email(session, customer.email, "Recordatorio de visita Lumat",
                              f"Te recordamos tu visita el {params[0]} a las {params[1]}.")
        except Exception:
            raise
        record_audit(session, actor="system", action="notification.reminder_email_fallback",
                     entity="notification_operation", entity_id=str(operation.id),
                     after={"recipient": customer.email})
        return f"email:{customer.email}"


def _send_appointment_followup(
    session: Session, operation: NotificationOperation, outcome: str
) -> str:
    from app.services import notify
    from app.services.settings import get_setting
    from app.services.templates import TemplatePolicyError, validate_channel_policy

    appointment = session.get(Appointment, int(operation.source_id))
    if appointment is None or appointment.status.value != outcome:
        raise RuntimeError("appointment follow-up no longer references the expected outcome")
    customer = session.get(Customer, appointment.customer_id)
    if customer is None:
        raise RuntimeError("appointment follow-up customer no longer exists")
    settings_key = (
        "notify.followup_template_name" if outcome == "completed"
        else "notify.followup_no_show_template_name"
    )
    event = f"appointment.followup.{outcome}"
    template_name = get_setting(session, settings_key)
    template = session.scalar(select(NotificationTemplateVersion).where(
        NotificationTemplateVersion.event == event,
        NotificationTemplateVersion.channel == "whatsapp",
        NotificationTemplateVersion.locale == "es",
    ).order_by(NotificationTemplateVersion.version.desc()).limit(1))
    if template is None:
        raise TemplatePolicyError(f"{event} WhatsApp template is not published")
    validate_channel_policy(channel="whatsapp", approved=template.approved, business_initiated=True)
    params = [
        customer.name,
        appointment.local_start.strftime("%d/%m/%Y"),
        appointment.local_start.strftime("%H:%M"),
    ]
    try:
        return notify.send_template(operation.recipient, params, template_name=template_name)
    except Exception as whatsapp_error:
        address = get_setting(session, "notify.owner_email")
        subject = "Seguimiento de visita Lumat"
        body = (
            f"La visita de {customer.name} del {params[1]} a las {params[2]} quedó cerrada como completada. "
            "Contacta al cliente para hacer el seguimiento."
            if outcome == "completed"
            else f"La visita de {customer.name} del {params[1]} a las {params[2]} quedó marcada como no asistida. "
            "Contacta al cliente para reagendar."
        )
        try:
            notify.send_email(session, address, subject, body)
        except Exception:
            raise
        record_audit(session, actor="system", action="notification.followup_email_fallback",
                     entity="notification_operation", entity_id=str(operation.id),
                     after={"recipient": address, "whatsapp_error": str(whatsapp_error)[:2000]})
        return f"email:{address}"


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
    if operation.user_id is not None:
        session.add(PanelNotification(user_id=operation.user_id, operation_id=operation.id, title=operation.source_entity, content=operation.content, source=operation.source_entity, status=operation.status))
        session.flush()
    return operation


def create_panel_notification(session: Session, *, user_id: int, operation_id: int, title: str, content: str, source: str) -> PanelNotification:
    existing = session.scalar(select(PanelNotification).where(PanelNotification.user_id == user_id, PanelNotification.operation_id == operation_id))
    if existing is not None:
        return existing
    operation = session.get(NotificationOperation, operation_id)
    row = PanelNotification(user_id=user_id, operation_id=operation_id, title=title, content=content, source=source, status=operation.status if operation else "pending")
    session.add(row)
    session.flush()
    return row


def notify_admins(
    session: Session,
    *,
    title: str,
    content: str,
    source: str,
    source_id: str | int,
    dedupe_key: str,
) -> None:
    now = datetime.now(timezone.utc)
    operation = create_operation(
        session,
        recipient="panel",
        channel="panel",
        content=content,
        source_entity=source,
        source_id=str(source_id),
        idempotency_key=f"panel:{dedupe_key}",
        status="sent",
        delivered_at=now,
    )
    admins = session.scalars(select(User).where(User.role == UserRole.ADMIN)).all()
    for admin in admins:
        create_panel_notification(
            session,
            user_id=admin.id,
            operation_id=operation.id,
            title=title,
            content=content,
            source=source,
        )
    stage_event(
        session,
        type="notification",
        data={"source": source, "source_id": str(source_id), "dedupe_key": dedupe_key},
    )


def list_panel_notifications(session: Session, *, user_id: int, unread: bool | None = None, status: str | None = None, source: str | None = None) -> list[PanelNotification]:
    query = select(PanelNotification).where(PanelNotification.user_id == user_id)
    if unread is True:
        query = query.where(PanelNotification.read_at.is_(None))
    if status:
        query = query.where(PanelNotification.status == status)
    if source:
        query = query.where(PanelNotification.source == source)
    return session.scalars(query.order_by(PanelNotification.created_at.desc(), PanelNotification.id.desc())).all()


def mark_notification_read(session: Session, notification_id: int, *, user_id: int, now: datetime | None = None) -> PanelNotification:
    row = session.scalar(select(PanelNotification).where(PanelNotification.id == notification_id, PanelNotification.user_id == user_id).with_for_update())
    if row is None:
        raise PermissionError("notification not found")
    row.read_at = row.read_at or (now or datetime.now(timezone.utc))
    session.flush()
    return row


def mark_all_notifications_read(session: Session, *, user_id: int, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    rows = session.scalars(select(PanelNotification).where(PanelNotification.user_id == user_id, PanelNotification.read_at.is_(None)).with_for_update()).all()
    for row in rows:
        row.read_at = now
    session.flush()
    return len(rows)


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


def _fallback_channel(session: Session, operation: NotificationOperation) -> str | None:
    """Return the first enabled fallback channel allowed by the operation's rule."""
    if operation.event_id is None:
        return None
    return session.scalar(
        select(AutomationRule.channel)
        .join(AutomationExecution, AutomationExecution.rule_id == AutomationRule.id)
        .where(
            AutomationExecution.event_id == operation.event_id,
            AutomationExecution.operation_id == operation.id,
            AutomationRule.enabled.is_(True),
            AutomationRule.channel.in_(("whatsapp", "email")),
        )
        .order_by(AutomationExecution.id)
    )


def _process_push_fallback(session: Session, operation: NotificationOperation) -> None:
    channel = _fallback_channel(session, operation)
    if channel is None:
        return
    fallback = create_operation(
        session,
        recipient=operation.recipient,
        channel=channel,
        content=operation.content,
        source_entity=operation.source_entity,
        source_id=operation.source_id,
        idempotency_key=f"{operation.idempotency_key}:fallback:{channel}",
        event_id=operation.event_id,
        user_id=operation.user_id,
    )
    record_audit(
        session,
        actor="system",
        action="notification.fallback_attempt",
        entity="notification_operation",
        entity_id=str(fallback.id),
        after={"from_operation_id": operation.id, "channel": channel},
    )
    process_operation(session, fallback.id)


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
        if (operation.idempotency_key.endswith(":reminder:24h") and operation.source_entity == "appointment"
                and session.get(Appointment, int(operation.source_id)) is not None):
            external_id = _send_appointment_reminder(session, operation)
        elif operation.source_entity == "appointment" and operation.idempotency_key in {
            f"appointment:{operation.source_id}:followup:completed",
            f"appointment:{operation.source_id}:followup:no_show",
        }:
            outcome = operation.idempotency_key.rsplit(":", 1)[1]
            external_id = _send_appointment_followup(session, operation, outcome)
        elif operation.channel == "push":
            external_id = (deliver or send_push)(operation.recipient, operation.content)
        else:
            external_id = (deliver or (send_whatsapp if operation.channel == "whatsapp" else send_email))(operation.recipient, operation.content)
    except Exception as exc:
        error = str(exc)[:2000]
        if isinstance(exc, MissingReminderEmail):
            attempt.status = "failed"
            attempt.error = error
            operation.error = error
            operation.status = "permanently_failed"
            record_audit(session, actor="system", action="notification.reminder_no_email",
                         entity="notification_operation", entity_id=str(operation.id),
                         after={"appointment_id": operation.source_id, "error": error})
            record_audit(session, actor="system", action="notification.attempt_failed",
                         entity="notification_operation", entity_id=str(operation.id),
                         after={"attempt": operation.attempts, "error": error, "status": operation.status})
            session.flush()
            return False
        if operation.channel == "push":
            record_audit(session, actor="system", action="notification.push_failed", entity="notification_operation", entity_id=str(operation.id), after={"error": error, "fallback": "whatsapp_or_email"})
            _process_push_fallback(session, operation)
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
        for panel_row in session.scalars(select(PanelNotification).where(PanelNotification.operation_id == operation.id)):
            panel_row.status = operation.status
        return False
    attempt.status = "sent"
    attempt.external_id = external_id
    operation.status = "sent"
    operation.error = None
    operation.delivered_at = now
    for panel_row in session.scalars(select(PanelNotification).where(PanelNotification.operation_id == operation.id)):
        panel_row.status = operation.status
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
