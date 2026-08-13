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

import httpx
from sqlalchemy import select

from app.config import get_settings
from app.db import session_scope
from app.models import Conversation, Message, MessageDirection, MessageStatus, Settings

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


def meta_message_cost(session) -> float:
    """Service-message unit cost from settings (SS-4), default reference."""
    row = session.get(Settings, "meta_pricing")
    if row is not None and isinstance(row.value, dict):
        unit = row.value.get("service_message_cost")
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
