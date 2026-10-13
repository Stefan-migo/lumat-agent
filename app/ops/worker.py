"""Bounded, lease-safe domain event worker entrypoint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import session_scope
from app.models import DomainEvent
from app.services.automation import evaluate_event
from app.services.time_triggers import evaluate_time_triggers

DEFAULT_BATCH_SIZE = 50
LEASE_SECONDS = 60
MAX_ATTEMPTS = 3


def handle_event(session: Session, event: DomainEvent) -> None:
    """Evaluate rules in the event's transaction."""
    evaluate_event(session, event)


def _claim(session: Session, limit: int, owner: str, now: datetime) -> list[int]:
    events = session.scalars(
        select(DomainEvent)
        .where(
            or_(
                DomainEvent.status == "pending",
                (DomainEvent.status == "failed") & (DomainEvent.available_at <= now),
                (DomainEvent.status == "processing") & (DomainEvent.leased_until <= now),
            )
        )
        .order_by(DomainEvent.id)
        .limit(max(0, limit))
        .with_for_update(skip_locked=True)
    ).all()
    for event in events:
        event.status = "processing"
        event.lease_owner = owner
        event.leased_until = now + timedelta(seconds=LEASE_SECONDS)
        event.attempts += 1
    session.flush()
    return [event.id for event in events]


def run_cycle(limit: int = DEFAULT_BATCH_SIZE, owner: str = "h4-worker") -> int:
    """Claim and process at most ``limit`` events, returning successful count."""
    now = datetime.now(timezone.utc)
    processed = 0
    with session_scope() as session:
        evaluate_time_triggers(session, now)
        session.flush()
        for event_id in _claim(session, limit, owner, now):
            event = session.get(DomainEvent, event_id)
            try:
                handle_event(session, event)
            except Exception as exc:
                event.status = "failed"
                event.error = str(exc)[:2000]
                event.leased_until = None
                event.lease_owner = None
                if event.attempts >= MAX_ATTEMPTS:
                    event.available_at = now + timedelta(days=36500)
                else:
                    event.available_at = now + timedelta(minutes=2 ** (event.attempts - 1))
                continue
            event.status = "completed"
            event.processed_at = now
            event.error = None
            event.leased_until = None
            event.lease_owner = None
            processed += 1
    return processed


def health_counts() -> dict[str, int]:
    with session_scope() as session:
        now = datetime.now(timezone.utc)
        return {
            "pending": session.scalar(select(func.count()).select_from(DomainEvent).where(DomainEvent.status == "pending")) or 0,
            "failed": session.scalar(select(func.count()).select_from(DomainEvent).where(DomainEvent.status == "failed")) or 0,
            "leased": session.scalar(select(func.count()).select_from(DomainEvent).where(DomainEvent.status == "processing", DomainEvent.leased_until > now)) or 0,
        }


def main() -> None:
    processed = run_cycle(
        limit=int(os.getenv("H4_WORKER_LIMIT", DEFAULT_BATCH_SIZE)),
        owner=os.getenv("H4_WORKER_OWNER", "h4-worker"),
    )
    counts = health_counts()
    print(
        f"worker cycle: processed={processed} "
        f"pending={counts['pending']} failed={counts['failed']} leased={counts['leased']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
