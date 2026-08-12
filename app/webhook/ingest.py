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
from pathlib import Path
from typing import Iterable, Optional

import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import get_settings
from app.db import session_scope
from app.models import (
    Conversation,
    ConversationState,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer, normalize_phone_e164

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


class MediaDownloadError(RuntimeError):
    """Raised when a media file cannot be downloaded; the sweep will retry."""


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
    if raw_type == "text":
        text = (raw.get("text") or {}).get("body")
    elif raw_type in _MEDIA_TYPES:
        media_url = (raw.get(raw_type) or {}).get("url")

    return NormalizedMessage(
        wamid=wamid,
        phone_e164=normalize_phone_e164(phone_raw or ""),
        msg_type=_META_TYPE_TO_ENUM.get(raw_type, MessageType.OTHER),
        text=text,
        media_url=media_url,
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


def _get_or_create_customer_and_conversation(session, phone_e164: str) -> Conversation:
    """Get-or-create customer + open conversation for the messages FK.

    Customer creation is delegated to the formal T3.1 customers service
    (auto-ficha + E.164 dedup, CR-1/CR-2). Conversation handling here is a
    lightweight bridge until T3.2's chat state owns conversations: one open
    conversation per customer (closed conversations are not reopened — a new
    inbound after close opens a new conversation, CR-5).
    """
    customer = get_or_create_customer(session, phone_e164)

    conversation = session.scalar(
        select(Conversation)
        .where(
            Conversation.customer_id == customer.id,
            Conversation.state != ConversationState.CLOSED,
        )
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    if conversation is None:
        conversation = Conversation(
            customer_id=customer.id, wa_phone=phone_e164, state=ConversationState.BOT
        )
        session.add(conversation)
        session.flush()
    return conversation


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
        status=MessageStatus.RECEIVED,
        payload=normalized.payload,
    )
    stmt = stmt.on_conflict_do_nothing(
        index_elements=[Message.wamid],
        index_where=text("direction = 'inbound' AND wamid IS NOT NULL"),
    )
    result = session.execute(stmt)
    session.flush()
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


def download_media(media_url: str, wamid: str, token: str, media_dir: str) -> Path:
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
    return dest


def process_message(session, message: Message) -> None:
    """Process one inbound message: media download, then status processed.

    The LangGraph conversation run lands in T3.2+; this is the Batch 2
    placeholder that owns the status transition (received -> processed) and
    the media download. Download failure keeps the message `received` so the
    sweep retries it — the raw payload is never lost (WH-4).
    """
    if message.media_url:
        settings = get_settings()
        download_media(
            message.media_url, message.wamid, settings.meta_access_token, settings.media_dir
        )
    message.status = MessageStatus.PROCESSED


def sweep_received(limit: int = 50) -> int:
    """Process messages stuck in `received` (BackgroundTask + startup sweep).

    FOR UPDATE SKIP LOCKED so concurrent sweeps (background + startup) never
    process the same row twice (WH-7: no duplicate side effects). Unexpected
    failures mark the row `failed` (retried never; raw payload still stored).
    """
    processed = 0
    with session_scope() as session:
        rows = session.scalars(
            select(Message)
            .where(Message.status == MessageStatus.RECEIVED)
            .order_by(Message.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        for message in rows:
            try:
                process_message(session, message)
                processed += 1
            except MediaDownloadError:
                # keep status='received' -> next sweep retries the download
                logger.warning(
                    "media download failed for %s; will retry on next sweep", message.wamid
                )
            except Exception:
                logger.exception("processing failed for wamid=%s; marking failed", message.wamid)
                message.status = MessageStatus.FAILED
    return processed
