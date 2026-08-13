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
        wamid = send_template(owner_whatsapp, [customer.phone_e164, location, context])
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
# T4.3.2 — ack (reply keyword) + reminder escalation. Filled by the next
# TDD work unit; kept together here because they share the same case columns
# and the SMTP layer above.
# ---------------------------------------------------------------------------
