"""Operational entry point for the follow-up detector sweep."""

from datetime import datetime, timezone

from app.db import SessionLocal
from app.services.followup import sweep_followup


def run(*, now: datetime | None = None) -> int:
    """Run one detector sweep and commit its event records."""
    with SessionLocal() as session:
        recorded = sweep_followup(session, now=now or datetime.now(timezone.utc))
        session.commit()
        return recorded
