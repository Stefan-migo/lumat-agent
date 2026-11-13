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


def _sweep(limit: int, *, now: datetime | None = None) -> tuple[int, bool]:
    now = now or datetime.now(timezone.utc)
    with session_scope() as session:
        if not get_transcription_enabled(session):
            logger.info("Audio transcription is disabled; no messages processed")
            return 0, False

        cutoff = now - timedelta(days=get_transcription_window_days(session))
        messages = session.scalars(
            select(Message)
            .where(
                Message.direction == MessageDirection.INBOUND,
                Message.msg_type == MessageType.AUDIO,
                Message.stored_path.is_not(None),
                Message.transcript.is_(None),
                Message.transcript_attempts < 3,
                Message.created_at >= cutoff,
            )
            .order_by(Message.created_at, Message.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()

        for message in messages:
            transcript = transcribe_message(session, message)
            logger.info(
                "Transcription sweep processed message %s (%s)",
                message.id,
                "transcribed" if transcript is not None else "no transcript returned",
            )
        return len(messages), True


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
