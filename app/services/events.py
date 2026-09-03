"""Transactional domain event publication primitives."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DomainEvent


def publish_event(
    session: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str | int,
    payload: dict,
    dedupe_key: str,
    occurred_at: datetime | None = None,
) -> DomainEvent:
    """Add one event to the caller's transaction, reusing its stable identity."""
    existing = session.scalar(select(DomainEvent).where(DomainEvent.dedupe_key == dedupe_key))
    if existing is not None:
        return existing
    event = DomainEvent(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload=payload,
        dedupe_key=dedupe_key,
        occurred_at=occurred_at or datetime.now(timezone.utc),
    )
    session.add(event)
    session.flush()
    return event
