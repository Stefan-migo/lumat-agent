"""Bounded operational sweep for pending inbound audio transcription."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import session_scope
from app.models import Message, MessageDirection, MessageType
from app.services.settings import get_transcription_enabled, get_transcription_window_days
from app.services.transcription import transcribe_message

logger = logging.getLogger(__name__)
DEFAULT_BATCH_SIZE = 50


def _eligible_filters(now: datetime, window_days: int) -> tuple:
    cutoff = now - timedelta(days=window_days)
    return (
        Message.direction == MessageDirection.INBOUND,
        Message.msg_type == MessageType.AUDIO,
        Message.stored_path.is_not(None),
        Message.transcript.is_(None),
        Message.transcript_attempts < 3,
        Message.created_at >= cutoff,
    )


def _sweep(limit: int, *, now: datetime | None = None) -> tuple[int, bool]:
    now = now or datetime.now(timezone.utc)
    with session_scope() as session:
        if not get_transcription_enabled(session):
            logger.info("Audio transcription is disabled; no messages processed")
            return 0, False

        window_days = get_transcription_window_days(session)
        filters = _eligible_filters(now, window_days)
        message_ids = session.scalars(
            select(Message.id)
            .where(*filters)
            .order_by(Message.created_at, Message.id)
            .limit(limit)
        ).all()

    processed = 0
    for message_id in message_ids:
        try:
            with session_scope() as session:
                message = session.scalar(
                    select(Message)
                    .where(Message.id == message_id, *_eligible_filters(now, window_days))
                    .with_for_update(skip_locked=True)
                )
                if message is None:
                    continue
                transcript = transcribe_message(session, message)
                processed += 1
                logger.info(
                    "Transcription sweep processed message %s (%s)",
                    message.id,
                    "transcribed" if transcript is not None else "no transcript returned",
                )
        except Exception:
            logger.exception("Transcription sweep failed for message %s; continuing", message_id)

    return processed, True


def run(limit: int = DEFAULT_BATCH_SIZE, *, now: datetime | None = None) -> int:
    """Process at most ``limit`` eligible messages and return the row count."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    return _sweep(limit, now=now)[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transcribe recent inbound audio messages")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args(argv)
    if args.limit <= 0:
        parser.error("--limit must be positive")

    processed, enabled = _sweep(args.limit)
    if enabled:
        print(f"Processed {processed} audio message(s)")
    else:
        print("Transcription disabled; processed 0 audio message(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
