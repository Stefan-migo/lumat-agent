"""Emergency owner/technician notification (EM-4; T4.3).

`send_emergency_notification` pushes the WhatsApp utility template
`emergency_alert` to the configured owner/technician number — the customer's
phone, location when known and the detected context — and falls back to a
plain-text email (stdlib `smtplib`, no new dependency) when Meta fails
(API error, missing template approval, network). Every attempt is audited
(SH-5); the function NEVER raises, so the emergency node's safety reply is
never blocked by a notification failure (EM-3 "reply regardless").

The WhatsApp template is the only business-initiated channel Meta allows
outside a 24h customer-service window — the owner is exactly that case
(design D9). The ack + reminder escalation live here too (T4.3.2):
`acknowledge_emergency_if_ack` records the customer reply-keyword ack from
the webhook ingest flow, and `send_pending_emergency_reminders` is the
sweep that escalates unacked emergencies after 15 minutes (max 2 reminders).
"""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Case, Conversation, Customer
from app.services.audit import record_audit
from app.services.send import (
    META_API_VERSION,
    META_SEND_URL,
    SEND_TIMEOUT_SECONDS,
    meta_message_cost,
)
from app.services.settings import (
    DEFAULT_OWNER_EMAIL,
    DEFAULT_OWNER_WHATSAPP,
    DEFAULT_SMTP_FROM,
    DEFAULT_SMTP_HOST,
    get_setting,
)
from app.services.notifications import create_operation, process_operation

logger = logging.getLogger(__name__)

# EM-4 / design D9: utility template name + language for the owner notification.
EMERGENCY_TEMPLATE_NAME = "emergency_alert"
TEMPLATE_LANGUAGE = "es"

# T4.3.2: reminder escalation window and cap.
REMINDER_DELAY_MINUTES = 15
MAX_REMINDERS = 2

# T4.3.2: customer reply-keyword ack after an emergency (EM-4 ack). The panel
# ack button lands in T5.3 on the same case columns.
ACK_WORDS = frozenset({"ok", "listo", "recibido", "gracias"})
_ACK_PUNCTUATION = " .,!?¿¡;:"


def send_template(phone_e164: str, body_params: list[str]) -> str:
    """Send the `emergency_alert` utility template; returns the Meta wamid.

    Same pattern as `send.send_text` (Bearer token, raise_for_status) but with
    type=template — the only business-initiated channel Meta allows (D9).
    """
    settings = get_settings()
    response = httpx.post(
        META_SEND_URL.format(
            version=META_API_VERSION, phone_number_id=settings.meta_phone_number_id
        ),
        headers={"Authorization": f"Bearer {settings.meta_access_token}"},
        json={
            "messaging_product": "whatsapp",
            "to": phone_e164,
            "type": "template",
            "template": {
                "name": EMERGENCY_TEMPLATE_NAME,
                "language": {"code": TEMPLATE_LANGUAGE},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": p} for p in body_params],
                    }
                ],
            },
        },
        timeout=SEND_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["messages"][0]["id"]


def send_email(session: Session, to: str, subject: str, body: str) -> None:
    """Send one plain-text email via the configured SMTP host (stdlib only).

    Thin `smtplib` wrapper (tasks.md ponytail guard: no SMTP dependency) so
    tests patch `app.services.notify.smtplib.SMTP` — never a real server.
    Raises on SMTP failure; callers decide the fallback/audit.
    """
    host = get_setting(session, "notify.smtp_host", default=DEFAULT_SMTP_HOST)
    mail_from = get_setting(session, "notify.smtp_from", default=DEFAULT_SMTP_FROM)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("Lumat Emergencias", mail_from))
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP(host) as server:
        server.sendmail(mail_from, [to], msg.as_string())


def _customer_location(conversation: Conversation) -> str | None:
    """Best-known location from the captured-data map (address, else comuna)."""
    captured = conversation.captured_data or {}
    return captured.get("address") or captured.get("comuna")


def _notification_body(
    customer: Customer, conversation: Conversation, context: str
) -> tuple[str, list[str]]:
    """Compose (subject, body) for the email fallback (EN-neutral Spanish).

    Carries the same information as the WhatsApp template: customer phone,
    location when known, and the detected emergency context.
    """
    location = _customer_location(conversation) or "sin ubicación"
    body = (
        "EMERGENCIA detectada por el asistente Lumat.\n\n"
        f"Cliente: {customer.phone_e164}\n"
        f"Ubicación: {location}\n"
        f"Contexto: {context}\n"
        f"Conversación: #{conversation.id}"
    )
    return f"EMERGENCIA Lumat - caso #{conversation.id}", body


def _audit_notification(
    session: Session,
    case: Case,
    *,
    action: str,
    channel: str,
    recipient: str,
    result: dict,
) -> None:
    """One SH-5 audit row per notification attempt (channel + recipient + result)."""
    record_audit(
        session,
        actor="system",
        action=action,
        entity="case",
        entity_id=str(case.id),
        after={"channel": channel, "recipient": recipient, **result},
    )
    session.flush()


def send_emergency_notification(
    session: Session,
    case: Case,
    customer: Customer,
    conversation: Conversation,
    *,
    context: str,
) -> dict:
    """EM-4: notify the owner/technician of an emergency; never raises.

    Primary channel: the `emergency_alert` WhatsApp template to
    `notify.owner_whatsapp` (customer phone + location when known + context).
    Fallback: email to `notify.owner_email` when Meta fails. `case.notified_at`
    is set when a channel delivers (drives the reminder sweep); every attempt
    is audited (SH-5). Returns {"channel": "whatsapp"|"email"|"none",
    "wamid": str|None}.
    """
    owner_whatsapp = get_setting(
        session, "notify.owner_whatsapp", default=DEFAULT_OWNER_WHATSAPP
    )
    location = _customer_location(conversation) or "sin ubicación"
    unit_cost = meta_message_cost(session)

    try:
        operation = create_operation(
            session,
            recipient=owner_whatsapp,
            channel="whatsapp",
            content=f"{customer.phone_e164}|{location}|{context}",
            source_entity="case",
            source_id=str(case.id),
            idempotency_key=f"case:{case.id}:emergency",
        )
        wamid_holder = {}
        delivered = process_operation(
            session,
            operation.id,
            deliver=lambda recipient, content: wamid_holder.setdefault(
                "wamid", send_template(recipient, content.split("|"))
            ),
        )
        if not delivered:
            raise RuntimeError(operation.error or "emergency notification failed")
        wamid = wamid_holder["wamid"]
    except Exception as exc:  # Meta error / template not approved -> email
        logger.warning(
            "emergency WhatsApp notification failed (email fallback): %s", exc
        )
        _audit_notification(
            session,
            case,
            action="notification.failed",
            channel="whatsapp",
            recipient=owner_whatsapp,
            result={"error": str(exc), "cost_meta": 0},
        )
        return _send_email_fallback(session, case, customer, conversation, context)

    case.notified_at = datetime.now(timezone.utc)
    _audit_notification(
        session,
        case,
        action="notification.sent",
        channel="whatsapp",
        recipient=owner_whatsapp,
        result={"template": EMERGENCY_TEMPLATE_NAME, "wamid": wamid, "cost_meta": unit_cost},
    )
    return {"channel": "whatsapp", "wamid": wamid}


def _send_email_fallback(
    session: Session,
    case: Case,
    customer: Customer,
    conversation: Conversation,
    context: str,
) -> dict:
    """Email fallback after a WhatsApp failure; audits and never raises."""
    owner_email = get_setting(session, "notify.owner_email", default=DEFAULT_OWNER_EMAIL)
    subject, body = _notification_body(customer, conversation, context)
    try:
        send_email(session, owner_email, subject, body)
    except Exception as exc:
        logger.exception("emergency email notification failed for case %s: %s", case.id, exc)
        _audit_notification(
            session,
            case,
            action="notification.failed",
            channel="email",
            recipient=owner_email,
            result={"error": str(exc)},
        )
        return {"channel": "none", "wamid": None}

    case.notified_at = datetime.now(timezone.utc)
    _audit_notification(
        session,
        case,
        action="notification.sent",
        channel="email",
        recipient=owner_email,
        result={"subject": subject},
    )
    return {"channel": "email", "wamid": None}


# ---------------------------------------------------------------------------
# T4.3.2 — ack (reply keyword) + reminder escalation.
# ---------------------------------------------------------------------------


def is_ack_message(text: str) -> bool:
    """True when the customer's reply is a pure ack-keyword message.

    "ok" / "listo" / "recibido" / "gracias" — case- and punctuation-
    insensitive, combinations count ("ok gracias"). A reply carrying any other
    word ("ok pero no funciona") is NOT an ack: the emergency conversation
    continues. Only combined with an unacked emergency case does it record an
    ack (see acknowledge_emergency_if_ack).
    """
    words = [w.strip(_ACK_PUNCTUATION) for w in text.lower().split()]
    return bool(words) and all(w in ACK_WORDS for w in words)


def acknowledge_emergency_if_ack(session: Session, conversation_id: int, text: str) -> bool:
    """Record the customer reply-keyword ack on the emergency case (T4.3.2).

    Deterministic hook called from the webhook ingest flow BEFORE the graph
    runs (minimal hook; the panel ack button lands in T5.3 on the same case
    columns). No-op unless the message is a pure ack keyword AND the
    conversation has an unacknowledged emergency case. Audited (SH-5).
    Returns True when an ack was recorded.
    """
    if not is_ack_message(text):
        return False
    case = session.scalar(
        select(Case)
        .where(
            Case.conversation_id == conversation_id,
            Case.emergency.is_(True),
            Case.acknowledged_at.is_(None),
        )
        .order_by(Case.id.desc())
        .limit(1)
    )
    if case is None:
        return False
    case.acknowledged_at = datetime.now(timezone.utc)
    case.ack_by = "customer_reply"
    record_audit(
        session,
        actor="system",
        action="case.acknowledged",
        entity="case",
        entity_id=str(case.id),
        before={"acknowledged_at": None},
        after={
            "acknowledged_at": case.acknowledged_at.isoformat(),
            "ack_by": case.ack_by,
            "keyword": text,
        },
    )
    session.flush()
    return True


def acknowledge_case(session: Session, case: Case, actor: str) -> bool:
    """EM-4: record the ack on an emergency case (panel button, T5.3).

    Same mechanism as the reply-keyword ack (`acknowledge_emergency_if_ack`):
    acknowledged_at + ack_by on the case, audited with action
    `case.acknowledged`. No-op (False) when the case is not an unacknowledged
    emergency. The caller commits.
    """
    if not case.emergency or case.acknowledged_at is not None:
        return False
    case.acknowledged_at = datetime.now(timezone.utc)
    case.ack_by = actor
    record_audit(
        session,
        actor=actor,
        action="case.acknowledged",
        entity="case",
        entity_id=str(case.id),
        before={"acknowledged_at": None},
        after={
            "acknowledged_at": case.acknowledged_at.isoformat(),
            "ack_by": case.ack_by,
            "channel": "panel",
        },
    )
    session.flush()
    return True


def send_pending_emergency_reminders(session: Session) -> int:
    """Reminder emails for unacked emergencies: notified >15 min, max 2 (T4.3.2).

    Finds cases with a delivered notification (notified_at set), not
    acknowledged, older than REMINDER_DELAY_MINUTES, with fewer than
    MAX_REMINDERS reminders already sent; sends one reminder email each and
    increments reminder_count. Every reminder is audited (SH-5). Returns the
    number of reminders sent. Deterministic with seeded timestamps (UTC).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=REMINDER_DELAY_MINUTES)
    cases = session.scalars(
        select(Case).where(
            Case.emergency.is_(True),
            Case.notified_at.is_not(None),
            Case.acknowledged_at.is_(None),
            Case.notified_at <= cutoff,
            Case.reminder_count < MAX_REMINDERS,
        )
    ).all()
    owner_email = get_setting(session, "notify.owner_email", default=DEFAULT_OWNER_EMAIL)
    sent = 0
    for case in cases:
        customer = session.get(Customer, case.customer_id)
        conversation = session.get(Conversation, case.conversation_id)
        location = _customer_location(conversation) if conversation is not None else None
        subject = f"Recordatorio: emergencia sin confirmar - caso #{case.id}"
        body = (
            f"El caso #{case.id} (emergencia) aún no ha sido confirmado.\n\n"
            f"Cliente: {customer.phone_e164 if customer is not None else 'desconocido'}\n"
            f"Ubicación: {location or 'sin ubicación'}\n"
            f"Caso: #{case.id}\n"
            "Confirma el caso para detener estos recordatorios."
        )
        try:
            send_email(session, owner_email, subject, body)
        except Exception as exc:
            logger.exception("emergency reminder email failed for case %s: %s", case.id, exc)
            _audit_notification(
                session,
                case,
                action="notification.reminder_failed",
                channel="email",
                recipient=owner_email,
                result={"error": str(exc)},
            )
            continue
        case.reminder_count += 1
        _audit_notification(
            session,
            case,
            action="notification.reminder_sent",
            channel="email",
            recipient=owner_email,
            result={"reminder": case.reminder_count, "subject": subject},
        )
        sent += 1
    return sent
