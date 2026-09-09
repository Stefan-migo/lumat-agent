"""Recovery helpers for persisted assistant runs."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import InternalChatThread


def recover_events(thread: InternalChatThread, run_id: str | None = None) -> list[dict]:
    events = (thread.assistant_state or {}).get("events", [])
    if run_id is None:
        return events
    return [event for event in events if event.get("run_id") == run_id]


def is_recoverable(thread: InternalChatThread) -> bool:
    return bool((thread.assistant_state or {}).get("recoverable"))


def claim_execution(session: Session, thread: InternalChatThread) -> bool:
    """Claim a persisted pending execution exactly once for recovery."""
    claimed = session.execute(
        text("""
            UPDATE internal_chat_threads
            SET assistant_state = jsonb_set(assistant_state, '{execution_status}', '"running"'::jsonb)
            WHERE id = :thread_id
              AND assistant_state #>> '{execution_status}' = 'pending'
            RETURNING id
        """),
        {"thread_id": thread.id},
    ).scalar_one_or_none()
    if claimed is None:
        return False
    session.refresh(thread)
    return True
