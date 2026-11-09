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
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import httpx
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.chat.graph import run_conversation
from app.chat.nodes.handoff_gate import MEDIA_EVIDENCE_TYPES
from app.chat.state import get_or_create_conversation
from app.config import get_settings
from app.db import session_scope
from app.models import (
    Conversation,
    ConversationState,
    DeliveryStatus,
    ConversationEvent,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    User,
)
from app.services.customers import (
    get_or_create_customer,
    normalize_phone_e164,
    restart_cycle_if_closed,
)
from app.services.events import publish_event
from app.services.notify import acknowledge_emergency_if_ack, send_pending_emergency_reminders
from app.services.audit import record_audit
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


def _delivery_error(status: dict) -> tuple[str, str | None]:
    """Format Meta's status errors into the operator-facing one-line reason.

    `error_data.details` is the only field that says what actually went wrong.
    Meta fills `title` and `message` with the same useless pair -- measured on
    131053, both read "Media upload error" -- while the detail carries the real
    verdict, for example "Audio file uploaded with mimetype as audio/ogg, however
    on processing it is of type application/octet-stream". Preferring `message`
    threw that away on every audio failure and left the operator with a code and
    no cause.
    """
    errors = status.get("errors") or []
    parts: list[str] = []
    codes: list[str] = []
    for error in errors:
        if not isinstance(error, dict):
            continue
        code = error.get("code")
        title = error.get("title")
        error_data = error.get("error_data") or {}
        detail_text = error_data.get("details") if isinstance(error_data, dict) else None
        reason = detail_text or error.get("message")
        if code is not None:
            codes.append(str(code))
        head = ": ".join(str(part) for part in (code, title) if part is not None)
        if reason:
            head = f"{head} — {reason}" if head else str(reason)
        if head:
            parts.append(head)
    return ("; ".join(parts) or "Meta no informó el motivo")[:2000], ",".join(codes) or None


def apply_delivery_statuses(statuses: list[dict]) -> None:
    """Apply Meta delivery callbacks without allowing stale statuses to regress."""
    for status in statuses:
        wamid = status.get("id") if isinstance(status, dict) else None
        state = status.get("status") if isinstance(status, dict) else None
        if not wamid or not state:
            logger.warning("Meta delivery status ignored: missing id or status")
            continue
        with session_scope() as session:
            row = session.scalar(
                select(Message).where(
                    Message.wamid == wamid,
                    Message.direction == MessageDirection.OUTBOUND,
                ).with_for_update()
            )
            if row is None:
                logger.warning("Meta delivery status ignored for unknown wamid=%s", wamid)
                continue
            if state == "failed":
                if row.delivery_status == DeliveryStatus.FAILED:
                    continue
                error, code = _delivery_error(status)
                row.delivery_status = DeliveryStatus.FAILED
                row.delivery_error = error
                # The real 131053 arrives here, not as a rejected send: Meta answers
                # the send with a wamid and fails the media afterwards. Dropping the
                # cached id is what lets `Reintentar entrega` upload the file again
                # instead of re-sending an id Meta will never process.
                row.meta_media_id = None
                actor = session.scalar(select(User.username).where(User.id == row.author_id))
                record_audit(
                    session,
                    actor=actor or "system",
                    action="message.delivery_failed",
                    entity="message",
                    entity_id=str(row.id),
                    after={
                        "conversation_id": row.conversation_id,
                        "request_id": row.request_id,
                        "status": "failed",
                        "error": row.delivery_error,
                        "cause": "Meta rejected delivery",
                        "wamid": wamid,
                        "code": code,
                        # The formatted line can only carry 2000 chars; the raw
                        # array is what makes a wrong formatter recoverable.
                        "meta_errors": str(status.get("errors"))[:2000],
                    },
                )
            elif state in {"delivered", "read"}:
                if row.delivery_status != DeliveryStatus.SENT:
                    continue
                timestamp = status.get("timestamp")
                try:
                    delivered_at = datetime.fromtimestamp(int(timestamp), timezone.utc)
                except (TypeError, ValueError, OverflowError):
                    logger.warning("Meta delivery status ignored: invalid timestamp for wamid=%s", wamid)
                    continue
                if row.delivered_at is None or delivered_at > row.delivered_at:
                    row.delivered_at = delivered_at
            # `sent` and anything else Meta may add later need no transition:
            # `sent` is already written when Meta accepts the message (the wamid
            # comes from that same response), and S2 forbids letting a late
            # `sent` walk a `failed` row back.


def iter_delivery_statuses(payload: dict) -> Iterable[dict]:
    """Yield Meta delivery status objects from a webhook payload.

    Kept separate from `iter_inbound_messages` on purpose: this one drives writes,
    and a generator that writes as a side effect of being consumed silently skips
    its work for any caller that stops iterating early. The ingestion path calls
    it explicitly; readers of inbound messages stay pure.
    """
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            for status in value.get("statuses") or []:
                if isinstance(status, dict):
                    yield status


def iter_inbound_messages(payload: dict) -> Iterable[NormalizedMessage]:
    """Yield normalized inbound messages from a Meta webhook payload.

    Filters (WH-6): non-`messages` events and error-131051 objects are
    acknowledged by the router (200) but never yielded — debug log only.
    """
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if (change.get("value") or {}).get("statuses"):
                # Handled by `iter_delivery_statuses`; not an ignored change.
                continue
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
# Per-conversation turn lock (chat-rafagas S4)
# ---------------------------------------------------------------------------

# conversation_id -> lock. In-process, like `RateLimiter`: the design runs a
# single worker (D1), so a process-local lock is the whole coordination surface.
# The upgrade path when a second worker appears is a Postgres advisory lock
# keyed by conversation. A row lock is NOT an option: the graph persists the
# conversation in separate sessions, so holding FOR UPDATE across the turn
# deadlocks against its own writes.
#
# Measured in production (Engram `chat/burst-de-mensajes`): two webhook POSTs
# enqueue two background sweeps, and without this lock each one runs its own
# `run_conversation` for the same conversation. The second turn then rebuilds
# state before the first reply is persisted and answers two consecutive user
# messages with no bot turn in between.
_turn_locks: dict[int, threading.Lock] = {}
_turn_locks_guard = threading.Lock()


def _turn_lock(conversation_id: int) -> threading.Lock:
    """The turn lock for one conversation, created on first use.

    Never pruned: each entry is a bare lock and the project's volume is tens of
    conversations a day — the same tradeoff `RateLimiter` already accepts.
    """
    with _turn_locks_guard:
        return _turn_locks.setdefault(conversation_id, threading.Lock())


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
    # Delivery callbacks are applied before the inbound insert, in their own
    # transaction: they update already-persisted outbound rows and must not be
    # nested inside the inbound session.
    apply_delivery_statuses(list(iter_delivery_statuses(payload)))
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


# How long the pipeline waits for the customer to stop typing before it answers.
# Chat-rafagas S1: people send "Hola" and the real question as two messages a few
# hundred milliseconds apart, and answering the first one immediately is what
# broke production on 2026-11-06. Read from settings on every call so ops can
# change it without a deploy, and so tests can zero it.
def _burst_idle_seconds() -> float:
    return float(get_settings().burst_idle_seconds)


# Messages to skip while draining one conversation: a failed media download goes
# back to `received` on purpose, and re-processing it in the same pass would spin.
def _received_ids(conversation_id: int) -> list[int]:
    with session_scope() as session:
        return list(
            session.scalars(
                select(Message.id)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.status == MessageStatus.RECEIVED,
                )
                .order_by(Message.id)
            )
        )


def _conversations_with_received(limit: int) -> list[int]:
    """Conversations that own at least one `received` message, oldest first."""
    with session_scope() as session:
        return list(
            session.scalars(
                select(Message.conversation_id)
                .where(Message.status == MessageStatus.RECEIVED)
                .group_by(Message.conversation_id)
                .order_by(func.min(Message.id))
                .limit(limit)
            )
        )


def _wait_for_burst_to_settle(conversation_id: int) -> None:
    """Sleep until the customer has been quiet for `_burst_idle_seconds()`.

    The clock is the newest `received` row's `created_at`, not the process clock:
    a row persisted by another sweep still measures when the customer wrote it.
    """
    idle = _burst_idle_seconds()
    if idle <= 0:
        return
    with session_scope() as session:
        newest = session.scalar(
            select(func.max(Message.created_at)).where(
                Message.conversation_id == conversation_id,
                Message.status == MessageStatus.RECEIVED,
            )
        )
    if newest is None:
        return
    remaining = idle - (datetime.now(timezone.utc) - newest).total_seconds()
    if remaining > 0:
        logger.debug(
            "waiting %.2fs for conversation %s to finish its burst", remaining, conversation_id
        )
        time.sleep(remaining)


def _prepare_media(session, message: Message) -> bool:
    """Download the media of one burst message.

    True when the message takes part in the turn; False when it does not: a
    failed download either goes back to `received` for the next sweep (WH-4) or,
    after five attempts, is consumed with a `media_unavailable` event so a broken
    file cannot pin the conversation.
    """
    if not message.media_url:
        return True
    settings = get_settings()
    try:
        media = download_media(
            message.media_url, message.wamid, settings.meta_access_token, settings.media_dir
        )
    except MediaDownloadError:
        message.media_attempts += 1
        if message.media_attempts >= 5:
            message.status = MessageStatus.PROCESSED
            message.stored_path = None
            session.add(ConversationEvent(
                conversation_id=message.conversation_id,
                event="media_unavailable",
                cause=f"Media download failed after 5 attempts for message {message.id}",
                actor="system",
            ))
            logger.error(
                "media download failed for message %s after %s attempts; media unavailable",
                message.id, message.media_attempts,
            )
            return False
        message.status = MessageStatus.RECEIVED
        logger.warning(
            "media download failed for message %s; will retry on next sweep", message.id
        )
        return False
    message.stored_path = str(media.path)
    message.content_type = media.content_type
    message.filename = media.filename
    message.size_bytes = media.size_bytes
    session.commit()
    return True


def process_turn(session, messages: list[Message]) -> None:
    """Process one conversational turn: the customer's burst, then the reply.

    Chat-rafagas S1: every inbound message the customer sent before the bot
    answered is one turn, so the graph runs ONCE through the last message of the
    burst and `ConversationState.from_db` collapses the trailing inbound run into
    a single utterance. N messages still produce one WhatsApp reply.

    Media is resolved per message first; a message whose download failed does not
    take part in the turn (it stays `received` for the sweep, or is consumed after
    five attempts). The status transition received -> processed happens after a
    successful run.

    HH-5 (T4.4): during `human` state the webhook keeps persisting every message
    (complete history retained) but the bot never runs again — the human owns the
    channel in H1 (replies from the WhatsApp app on the same number, no panel
    reply). Ack handling still runs per message (a customer "ok" acks an unacked
    emergency); no LLM call, no outbound delivery.

    CI-4: media-only inbound (photo/video/audio/document) runs the graph too, so
    it is acknowledged as case evidence, not escalated by itself.
    """
    if not messages:
        return
    participants = [message for message in messages if _prepare_media(session, message)]
    conversation_id = messages[-1].conversation_id
    conversation = session.get(Conversation, conversation_id)
    if conversation is not None and conversation.state in {
        ConversationState.HUMAN,
        ConversationState.CLOSED,
    }:
        for message in messages:
            message.status = MessageStatus.PROCESSED  # HH-5: persisted, never retried
        return
    for message in participants:
        if message.text:
            # EM-4 ack (T4.3.2): a reply-keyword ack is recorded on the emergency
            # case BEFORE the graph runs — deterministic, audited, no-op otherwise.
            acknowledge_emergency_if_ack(session, message.conversation_id, message.text)
    # Meta onboarding text entered as customer content produced unknown_intent in production.
    runnable = [
        message
        for message in participants
        if message.msg_type is not MessageType.OTHER
        and (message.text or message.msg_type in MEDIA_EVIDENCE_TYPES)
    ]
    if runnable:
        run_conversation(session, runnable[-1])
        deliver_outbound(session, conversation_id)
    # Only the messages that took part are consumed: one whose download failed is
    # back in `received` on purpose (WH-4), and the sweep retries it.
    for message in participants:
        message.status = MessageStatus.PROCESSED


def process_message(session, message: Message) -> None:
    """One inbound message through the pipeline (a turn of one message).

    Kept as the single-message entry point: the emergency ack, handoff and
    platform-message suites call it directly. `sweep_received` uses
    `process_turn` because a webhook burst is one turn.
    """
    process_turn(session, [message])


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


def _run_burst(conversation_id: int, message_ids: list[int]) -> int:
    """Run ONE turn for a whole burst; returns how many messages were consumed.

    `processing` is the operator-visible in-flight marker, and the row
    `reset_stale_processing` recovers after a hard crash. Called with the
    conversation's turn lock held — see `_turn_lock`.
    """
    consumed = 0
    failed = False
    # The claim is its own short transaction on purpose: holding it open across
    # the graph run deadlocks against the graph's own writes in separate sessions
    # (case, captured, cost_llm touch these rows).
    with session_scope() as session:
        session.execute(
            update(Message)
            .where(Message.id.in_(message_ids))
            .values(status=MessageStatus.PROCESSING)
        )
    with session_scope() as session:
        messages = list(
            session.scalars(
                select(Message).where(Message.id.in_(message_ids)).order_by(Message.id)
            )
        )
        try:
            process_turn(session, messages)
        except Exception:
            logger.exception("processing failed for messages %s; marking failed", message_ids)
            failed = True
        consumed = sum(
            1 for message in messages if message.status is MessageStatus.PROCESSED
        )
    if failed:
        with session_scope() as session:
            session.execute(
                update(Message)
                .where(Message.id.in_(message_ids))
                .values(status=MessageStatus.FAILED)
            )
        return 0
    return consumed


def _drain_conversation(conversation_id: int) -> int:
    """Answer every pending message of one conversation, one burst at a time.

    Loops because a new message can land while the turn is running: a customer
    who writes again right after the reply opens a new burst, not a lost message.
    `attempted` keeps a failed media download (back in `received` on purpose)
    from spinning in the same pass — the next sweep retries it.
    """
    processed = 0
    attempted: set[int] = set()
    while True:
        if not [mid for mid in _received_ids(conversation_id) if mid not in attempted]:
            return processed
        _wait_for_burst_to_settle(conversation_id)
        burst = [mid for mid in _received_ids(conversation_id) if mid not in attempted]
        if not burst:
            return processed
        attempted.update(burst)
        processed += _run_burst(conversation_id, burst)


def sweep_received(limit: int = 50) -> int:
    """Process conversations holding `received` messages (background + boot).

    Claim pattern (WH-7: no duplicate side effects): the exclusivity unit is the
    CONVERSATION, not the message (chat-rafagas S4). Two webhook POSTs enqueue two
    sweeps, and a per-message claim let both open a turn on the same conversation.
    Each conversation now takes its turn lock, waits for the burst to settle
    (S1: `_burst_idle_seconds()`), marks the whole burst `processing`, and runs a
    single turn through its last message, so N messages produce one reply.

    Holding a row lock across the graph run would deadlock — the graph nodes
    persist in separate sessions (case, captured, cost_llm) — which is why the
    lock is process-local and the rows carry only the `processing` marker.

    Failures: media download -> back to `received` (retry); anything else ->
    `failed` (raw payload still stored). Hard-crash rows stay `processing` until
    the next boot's `reset_stale_processing`.
    """
    processed = 0
    for conversation_id in _conversations_with_received(limit):
        with _turn_lock(conversation_id):
            processed += _drain_conversation(conversation_id)

    # EM-4 escalation (T4.3.2): reminder emails for unacked emergencies — a
    # lightweight call in the same sweep (startup + webhook BackgroundTask),
    # no separate scheduler (ponytail: tens of cases/day; a cron/dedicated
    # worker is the upgrade path when volume grows).
    with session_scope() as session:
        send_pending_emergency_reminders(session)
    return processed
