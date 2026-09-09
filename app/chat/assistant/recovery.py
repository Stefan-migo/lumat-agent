"""Recovery helpers for persisted assistant runs."""

from __future__ import annotations

from app.models import InternalChatThread


def recover_events(thread: InternalChatThread, run_id: str | None = None) -> list[dict]:
    events = (thread.assistant_state or {}).get("events", [])
    if run_id is None:
        return events
    return [event for event in events if event.get("run_id") == run_id]


def is_recoverable(thread: InternalChatThread) -> bool:
    return bool((thread.assistant_state or {}).get("recoverable"))
