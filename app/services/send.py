"""Meta Cloud API outbound send (design: app/services/send.py; SS-4 basis).

`send_text` POSTs one WhatsApp text message and returns the Meta wamid.
`deliver_outbound` sends the pending outbound message rows of a conversation
and records `cost_meta` on each row using the service-message unit cost from
settings (`meta_pricing.service_message_cost` — SS-4: Meta service-message
pricing effective 2026-10-01; the default is a reference placeholder verified
at activation).

All requests go through httpx; tests intercept them with respx (no real Meta
calls — the token comes from env, SH-2).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.config import get_settings
from app.db import session_scope
from app.models import Conversation, DeliveryStatus, Message, MessageDirection, MessageStatus, User
from app.services.audit import record_audit
from app.services.settings import get_setting

logger = logging.getLogger(__name__)

META_API_VERSION = "v20.0"
META_SEND_URL = "https://graph.facebook.com/{version}/{phone_number_id}/messages"
SEND_TIMEOUT_SECONDS = 30.0

# SS-4 reference unit cost per service message (USD), used when settings do
# not define `meta_pricing.service_message_cost`. Verify at activation.
DEFAULT_META_COST = 0.01


def send_text(phone_e164: str, text: str) -> str:
    """Send one WhatsApp text message; returns the Meta wamid.

    Raises httpx.HTTPStatusError on a Meta error (caller decides retry).
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
            "type": "text",
            "text": {"body": text},
        },
        timeout=SEND_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["messages"][0]["id"]


def deliver_message(message_id: int) -> Message:
    """Claim one operator message, call Meta, and durably finalize its outcome."""
    with session_scope() as session:
        message = session.scalar(select(Message).where(Message.id == message_id).with_for_update())
        if message is None:
            raise ValueError("message not found")
        if message.delivery_status == DeliveryStatus.SENT:
            return message
        if message.delivery_status in (DeliveryStatus.SENDING, DeliveryStatus.UNKNOWN):
            return message
        message.delivery_status = DeliveryStatus.SENDING
        message.delivery_attempts += 1
        message.last_attempt_at = datetime.now(timezone.utc)
        phone = session.scalar(
            select(Conversation.wa_phone).where(Conversation.id == message.conversation_id)
        )

    try:
        wamid = send_text(phone, message.text or "")
    except httpx.HTTPStatusError as exc:
        _finalize_delivery(message_id, DeliveryStatus.FAILED, str(exc))
    except httpx.HTTPError as exc:
        _finalize_delivery(message_id, DeliveryStatus.UNKNOWN, "Meta transport outcome is unknown")
        logger.warning("Meta transport outcome is unknown for outbound message %s", message_id)
    except Exception:
        _finalize_delivery(message_id, DeliveryStatus.UNKNOWN, "Meta response outcome is unknown")
        logger.exception("Meta response outcome is unknown for outbound message %s", message_id)
    else:
        with session_scope() as session:
            row = session.get(Message, message_id)
            row.delivery_status = DeliveryStatus.SENT
            row.wamid = wamid
            row.delivery_error = None
            row.delivered_at = datetime.now(timezone.utc)
            actor = session.scalar(select(User.username).where(User.id == row.author_id))
            record_audit(session, actor=actor or "system", action="message.delivery_sent", entity="message", entity_id=str(message_id), after={"request_id": row.request_id, "status": "sent", "wamid": wamid})
    with session_scope() as session:
        return session.get(Message, message_id)


def _finalize_delivery(message_id: int, status: DeliveryStatus, error: str) -> None:
    with session_scope() as session:
        row = session.get(Message, message_id)
        row.delivery_status = status
        row.delivery_error = error[:2000]
        actor = session.scalar(select(User.username).where(User.id == row.author_id))
        record_audit(session, actor=actor or "system", action=f"message.delivery_{status.value}", entity="message", entity_id=str(message_id), after={"request_id": row.request_id, "status": status.value, "error": row.delivery_error})


def meta_message_cost(session) -> float:
    """Service-message unit cost from settings (SS-4), default reference.

    T4.5 consolidation (T4.1.1 ponytail debt): reads through the settings
    service (`get_setting`) instead of touching the `settings` row directly
    — one settings read path for the whole codebase. A stored pricing dict
    without `service_message_cost` (or any non-dict value) falls back to the
    reference default; the effective-2026-10-01 price is verified at
    activation.
    """
    pricing = get_setting(
        session, "meta_pricing", default={"service_message_cost": DEFAULT_META_COST}
    )
    if isinstance(pricing, dict):
        unit = pricing.get("service_message_cost")
        if unit is not None:
            return float(unit)
    return DEFAULT_META_COST


def deliver_outbound(session, conversation_id: int) -> int:
    """Send pending outbound rows of a conversation; record wamid + cost_meta.

    Only rows without a wamid are sent (already-delivered rows are skipped, so
    a retry never double-sends). The recipient is the conversation wa_phone.
    """
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        return 0
    rows = session.scalars(
        select(Message).where(
            Message.conversation_id == conversation_id,
            Message.direction == MessageDirection.OUTBOUND,
            Message.wamid.is_(None),
            Message.status == MessageStatus.PROCESSED,
        )
    ).all()
    unit = meta_message_cost(session)
    sent = 0
    for row in rows:
        wamid = send_text(conversation.wa_phone, row.text or "")
        row.wamid = wamid
        row.cost_meta = unit
        sent += 1
    return sent


def deliver_all_pending() -> int:
    """Send every pending outbound message across conversations (sweep path)."""
    sent = 0
    with session_scope() as session:
        conversation_ids = session.scalars(
            select(Message.conversation_id)
            .where(
                Message.direction == MessageDirection.OUTBOUND,
                Message.wamid.is_(None),
                Message.status == MessageStatus.PROCESSED,
            )
            .distinct()
        ).all()
        for conversation_id in conversation_ids:
            sent += deliver_outbound(session, conversation_id)
    return sent
