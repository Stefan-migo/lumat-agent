"""Webhook ingest pipeline (specs WH-3..WH-7; design "Webhook Pipeline").

Flow per accepted POST (called from the router after the HMAC gate):

    filter (non-messages events, error 131051)  [WH-6]
    -> normalize (E.164 phone, wamid, type, text/media)
    -> rate limit per phone (in-memory, 15 msg/min)
    -> INSERT messages(status='received') ON CONFLICT (wamid) DO NOTHING  [WH-5]
    -> 200 first (router)  [WH-3]
    -> BackgroundTask: sweep_received()  [WH-4: persist-before-process]
    -> startup sweep: status='received' FOR UPDATE SKIP LOCKED  [crash recovery]

Media messages keep their Meta `media_url`; the download to the `media/`
volume happens during processing (sweep), and a failed download leaves the
message `received` so the next sweep retries it (design: "retry via sweep").
"""

from __future__ import annotations

import logging
import re
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import httpx
from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.chat.graph import run_conversation
from app.chat.nodes.handoff_gate import MEDIA_EVIDENCE_TYPES
from app.chat.state import get_or_create_conversation
from app.config import get_settings
from app.db import session_scope
from app.models import (
    Conversation,
    ConversationState,
    ConversationEvent,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import (
    get_or_create_customer,
    normalize_phone_e164,
    restart_cycle_if_closed,
)
from app.services.events import publish_event
from app.services.notify import acknowledge_emergency_if_ack, send_pending_emergency_reminders
from app.services.send import deliver_outbound

logger = logging.getLogger(__name__)

# Per-phone inbound rate limit (design: in-memory sliding window, 15 msg/min).
RATE_LIMIT_PER_MINUTE = 15
RATE_LIMIT_WINDOW_SECONDS = 60.0

# Meta error code for unsupported/undeliverable messages (WH-6).
ERROR_CODE_131051 = 131051

# HTTP timeout for media downloads (Meta lookaside URLs).
MEDIA_DOWNLOAD_TIMEOUT = 30.0

_MEDIA_MIME_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/amr": ".amr",
    "application/pdf": ".pdf",
}
_DEFAULT_MEDIA_EXT = ".bin"


@dataclass(frozen=True)
class NormalizedMessage:
    """The normalized inbound message record persisted before processing."""

    wamid: str
    phone_e164: str
    msg_type: MessageType
    text: Optional[str]
    media_url: Optional[str]
    payload: dict  # raw Meta message object (WH-4: raw payload survives)
    caption: Optional[str] = None  # optional Meta caption; last so callers stay source-compatible


class MediaDownloadError(RuntimeError):
    """Raised when a media file cannot be downloaded."""


@dataclass(frozen=True)
class DownloadedMedia:
    path: Path
    content_type: str
    filename: str
    size_bytes: int


# ---------------------------------------------------------------------------
# Normalization (pure functions)
# ---------------------------------------------------------------------------

_META_TYPE_TO_ENUM = {
    "text": MessageType.TEXT,
    "image": MessageType.IMAGE,
    "video": MessageType.VIDEO,
    "audio": MessageType.AUDIO,
    "document": MessageType.DOCUMENT,
    "sticker": MessageType.STICKER,
    "location": MessageType.LOCATION,
    "contacts": MessageType.CONTACTS,
}
_MEDIA_TYPES = {"image", "video", "audio", "document", "sticker"}


def normalize_message(raw: dict, value: dict) -> Optional[NormalizedMessage]:
    """Extract a normalized inbound message from a Meta message object.

    Returns None when the message cannot be processed (no wamid to dedup on —
    WH-5 requires the id). `value` supplies the contact wa_id fallback.
    """
    wamid = raw.get("id")
    if not wamid:
        logger.debug("webhook message without id skipped (no wamid to dedup)")
        return None

    phone_raw = raw.get("from") or (value.get("contacts") or [{}])[0].get("wa_id")
    raw_type = raw.get("type") or "text"

    text: Optional[str] = None
    media_url: Optional[str] = None
    caption: Optional[str] = None
    if raw_type == "text":
        text = (raw.get("text") or {}).get("body")
    elif raw_type in {"system", "unsupported", "ephemeral", "request_welcome"}:
        text = (raw.get(raw_type) or {}).get("body")
    elif raw_type in _MEDIA_TYPES:
        media_data = raw.get(raw_type) or {}
        media_url = media_data.get("url")
        caption = media_data.get("caption")

    return NormalizedMessage(
        wamid=wamid,
        phone_e164=normalize_phone_e164(phone_raw or ""),
        msg_type=_META_TYPE_TO_ENUM.get(raw_type, MessageType.OTHER),
        text=text,
        media_url=media_url,
        caption=caption,
        payload=raw,
    )


def _change_is_message_event(change: dict) -> bool:
    """True when a webhook change carries a `messages` payload (WH-6)."""
    if change.get("field") != "messages":
        return False
    value = change.get("value") or {}
    return "messages" in value and not _value_error_131051(value)


def _value_error_131051(value: dict) -> bool:
    """True when the change value carries Meta error 131051 (WH-6)."""
    error = (value.get("error") or {}).get("code")
    return error == ERROR_CODE_131051


def _message_error_131051(raw: dict) -> bool:
    """True when a message object carries error 131051 (WH-6, message-level)."""
    return any(
        (err or {}).get("code") == ERROR_CODE_131051 for err in raw.get("errors") or []
    )


def iter_inbound_messages(payload: dict) -> Iterable[NormalizedMessage]:
    """Yield normalized inbound messages from a Meta webhook payload.

    Filters (WH-6): non-`messages` events and error-131051 objects are
    acknowledged by the router (200) but never yielded — debug log only.
    """
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if not _change_is_message_event(change):
                logger.debug(
                    "webhook change ignored: field=%s error=%s (WH-6)",
                    change.get("field"),
                    (change.get("value") or {}).get("error"),
                )
                continue
            value = change.get("value", {})
            for raw in value.get("messages", []):
                if _message_error_131051(raw):
                    logger.debug("message error 131051 skipped (WH-6): %s", raw.get("id"))
                    continue
                normalized = normalize_message(raw, value)
                if normalized is not None:
                    yield normalized


# ---------------------------------------------------------------------------
# Rate limit (in-memory, per phone)
# ---------------------------------------------------------------------------


class RateLimiter:
    """Per-phone sliding window.

    ponytail: in-memory only — resets on restart. Acceptable: single worker
    (design D1), tens of conversations/day; a restart clears counts, never
    data (messages are already persisted by then).
    """

    def __init__(
        self, limit: int = RATE_LIMIT_PER_MINUTE, window_seconds: float = RATE_LIMIT_WINDOW_SECONDS
    ) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = {}

    def allow(self, phone: str) -> bool:
        """Record a message from `phone`; False when the window is saturated."""
        now = time.monotonic()
        window_start = now - self.window
        hits = self._hits.setdefault(phone, deque())
        while hits and hits[0] <= window_start:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


rate_limiter = RateLimiter()


# ---------------------------------------------------------------------------
# Persistence (WH-4 persist-before-process, WH-5 dedup by wamid)
# ---------------------------------------------------------------------------


def _get_or_create_customer_and_conversation(session, phone_e164: str):
    """Get-or-create customer + open conversation for the messages FK.

    Customer creation delegates to the T3.1 customers service (auto-ficha +
    E.164 dedup, CR-1/CR-2); conversation get-or-create lives in the chat
    state (CR-5: closed conversations are never reopened — a new inbound after
    close opens a new conversation).
    """
    customer = get_or_create_customer(session, phone_e164)
    restart_cycle_if_closed(session, customer)
    return get_or_create_conversation(session, customer, phone_e164)


def persist_message(session, normalized: NormalizedMessage) -> bool:
    """INSERT the normalized message as `received`; True when newly inserted.

    ON CONFLICT (wamid) DO NOTHING against the partial unique index
    (direction='inbound' AND wamid IS NOT NULL) makes duplicate Meta
    deliveries a no-op (WH-5): the duplicate is acknowledged but skipped.
    """
    conversation = _get_or_create_customer_and_conversation(session, normalized.phone_e164)
    stmt = pg_insert(Message).values(
        wamid=normalized.wamid,
        conversation_id=conversation.id,
        direction=MessageDirection.INBOUND,
        msg_type=normalized.msg_type,
        text=normalized.text,
        media_url=normalized.media_url,
        caption=normalized.caption,
        status=MessageStatus.RECEIVED,
        payload=normalized.payload,
    )
    stmt = stmt.on_conflict_do_nothing(
        index_elements=[Message.wamid],
        index_where=text("direction = 'inbound' AND wamid IS NOT NULL"),
    )
    result = session.execute(stmt)
    session.flush()
    message = session.scalar(select(Message).where(Message.wamid == normalized.wamid))
    if message is not None and (
        conversation.last_message_at is None
        or message.created_at > conversation.last_message_at
    ):
        conversation.last_message_at = message.created_at or datetime.now(timezone.utc)
    if result.rowcount == 1:
        publish_event(
            session, event_type="message.received", entity_type="message", entity_id=str(normalized.wamid),
            payload={"phone": normalized.phone_e164, "phone_e164": normalized.phone_e164, "text": normalized.text, "msg_type": normalized.msg_type.value},
            dedupe_key=f"message:{normalized.wamid}:received",
        )
    return result.rowcount == 1


def ingest_payload(payload: dict) -> int:
    """Persist every accepted inbound message; returns rows newly inserted.

    The 200 is returned AFTER this (router) — persistence is the acceptance
    boundary (WH-4); processing happens later in the background sweep.
    """
    inserted = 0
    with session_scope() as session:
        for normalized in iter_inbound_messages(payload):
            if not normalized.phone_e164:
                logger.debug("message without phone skipped: %s", normalized.wamid)
                continue
            if not rate_limiter.allow(normalized.phone_e164):
                logger.debug(
                    "rate limited (%d/min) phone %s: %s dropped",
                    RATE_LIMIT_PER_MINUTE,
                    normalized.phone_e164,
                    normalized.wamid,
                )
                continue
            if persist_message(session, normalized):
                inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Processing: media download + status transitions (sweep / BackgroundTask)
# ---------------------------------------------------------------------------


def _safe_filename(wamid: str) -> str:
    """Filesystem-safe filename stem derived from the wamid."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", wamid)


def download_media(media_url: str, wamid: str, token: str, media_dir: str) -> DownloadedMedia:
    """Download a Meta media URL to the media volume; raise on failure.

    Meta lookaside URLs require the access token as a Bearer header. A failed
    download raises MediaDownloadError so the message stays `received` and the
    next sweep retries (design: "retry via sweep").
    """
    try:
        resp = httpx.get(
            media_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=MEDIA_DOWNLOAD_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise MediaDownloadError(f"media download failed for {wamid}: {exc}") from exc

    mime = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    ext = _MEDIA_MIME_EXT.get(mime, _DEFAULT_MEDIA_EXT)
    dest = Path(media_dir) / f"{_safe_filename(wamid)}{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return DownloadedMedia(dest, mime or "application/octet-stream", dest.name, len(resp.content))


def process_message(session, message: Message) -> None:
    """Process one inbound message: media download, conversation run, delivery.

    The LangGraph conversation run (T3.2+) answers the customer, persists the
    outbound replies (T3.5) and delivers them via Meta (T3.6). The status
    transition received -> processed happens after a successful run; a failed
    download keeps the message `received` so the sweep retries it (WH-4).

    HH-5 (T4.4): during `human` state the webhook keeps persisting every
    message (complete history retained) but the bot never runs again — the
    human owns the channel in H1 (replies from the WhatsApp app on the same
    number, no panel reply). Ack handling still runs (a customer "ok" acks an
    unacked emergency); no LLM call, no outbound delivery.

    CI-4: media-only inbound (photo/video/audio/document) runs the graph too,
    so it is acknowledged as case evidence, not escalated by itself.
    """
    if message.media_url:
        settings = get_settings()
        media = download_media(
            message.media_url, message.wamid, settings.meta_access_token, settings.media_dir
        )
        message.stored_path = str(media.path)
        message.content_type = media.content_type
        message.filename = media.filename
        message.size_bytes = media.size_bytes
        session.commit()
    if message.direction == MessageDirection.INBOUND:
        if message.text:
            # EM-4 ack (T4.3.2): a reply-keyword ack is recorded on the emergency
            # case BEFORE the graph runs — deterministic, audited, no-op otherwise.
            acknowledge_emergency_if_ack(session, message.conversation_id, message.text)
        conversation = session.get(Conversation, message.conversation_id)
        if conversation is not None and conversation.state in {
            ConversationState.HUMAN,
            ConversationState.CLOSED,
        }:
            message.status = MessageStatus.PROCESSED  # HH-5: persisted, never retried
            return
        # Meta onboarding text entered as customer content produced unknown_intent in production.
        if message.msg_type is not MessageType.OTHER and (
            message.text or message.msg_type in MEDIA_EVIDENCE_TYPES
        ):
            run_conversation(session, message)
            deliver_outbound(session, message.conversation_id)
    message.status = MessageStatus.PROCESSED


def reset_stale_processing() -> int:
    """Crash recovery: reset `processing` rows back to `received` at startup.

    The claim pattern below sets `processing` in a short transaction; a hard
    crash mid-processing would leave a row stuck there. Single worker + boot
    sweep means no processing is active at startup, so a blanket reset is safe.
    """
    with session_scope() as session:
        result = session.execute(
            update(Message)
            .where(Message.status == MessageStatus.PROCESSING)
            .values(status=MessageStatus.RECEIVED)
        )
        return result.rowcount


def sweep_received(limit: int = 50) -> int:
    """Process messages stuck in `received` (BackgroundTask + startup sweep).

    Claim pattern (WH-7: no duplicate side effects): a short transaction
    SELECTs received ids FOR UPDATE SKIP LOCKED and flips them to `processing`
    (releasing the locks), then each message is processed in its OWN session.
    Holding the FOR UPDATE lock across the graph run would deadlock — the
    graph nodes persist in separate sessions (case, captured, cost_llm on the
    very row the sweep would be locking).

    Failures: media download -> back to `received` (retry); anything else ->
    `failed` (raw payload still stored). Hard-crash rows stay `processing`
    until the next boot's `reset_stale_processing`.
    """
    with session_scope() as session:
        claimed_ids = session.scalars(
            select(Message.id)
            .where(Message.status == MessageStatus.RECEIVED)
            .order_by(Message.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        if claimed_ids:
            session.execute(
                update(Message)
                .where(Message.id.in_(claimed_ids))
                .values(status=MessageStatus.PROCESSING)
            )

    processed = 0
    for message_id in claimed_ids:
        try:
            with session_scope() as session:
                message = session.get(Message, message_id)
                process_message(session, message)
            processed += 1
        except MediaDownloadError:
            with session_scope() as session:
                message = session.get(Message, message_id)
                message.media_attempts += 1
                if message.media_attempts >= 5:
                    message.status = MessageStatus.PROCESSED
                    message.stored_path = None
                    session.add(ConversationEvent(
                        conversation_id=message.conversation_id,
                        event="media_unavailable",
                        cause=f"Media download failed after 5 attempts for message {message_id}",
                        actor="system",
                    ))
                else:
                    message.status = MessageStatus.RECEIVED
            if message.media_attempts >= 5:
                logger.error("media download failed for message %s after %s attempts; media unavailable", message_id, message.media_attempts)
                processed += 1
            else:
                logger.warning("media download failed for message %s; will retry on next sweep", message_id)
        except Exception:
            logger.exception("processing failed for message %s; marking failed", message_id)
            with session_scope() as session:
                message = session.get(Message, message_id)
                message.status = MessageStatus.FAILED

    # EM-4 escalation (T4.3.2): reminder emails for unacked emergencies — a
    # lightweight call in the same sweep (startup + webhook BackgroundTask),
    # no separate scheduler (ponytail: tens of cases/day; a cron/dedicated
    # worker is the upgrade path when volume grows).
    with session_scope() as session:
        send_pending_emergency_reminders(session)
    return processed
