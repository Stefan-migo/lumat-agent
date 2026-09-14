"""Recovery helpers for persisted assistant runs."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.chat.assistant.approval import arguments_digest, canonical_sdb_digest, canonical_sdb_payload
from app.models import InternalChatThread


def recover_events(thread: InternalChatThread, run_id: str | None = None) -> list[dict]:
    events = (thread.assistant_state or {}).get("events", [])
    if run_id is not None:
        events = [event for event in events if event.get("run_id") == run_id]
    unique = {}
    for event in events:
        key = (
            event.get("run_id"), event.get("sequence"), event.get("type"),
            event.get("task_id"), event.get("tool"),
        )
        unique.setdefault(key, event)
    return sorted(
        unique.values(),
        key=lambda event: (
            event.get("sequence", 0),
            # A rejected task emits order=None; coerce it so a mixed stream sorts
            # instead of raising TypeError. None ranks before any integer order.
            event.get("order") if isinstance(event.get("order"), int) else -1,
            event.get("type", ""),
            event.get("task_id", ""),
        ),
    )


def revalidate_sdb_resume(
    thread: InternalChatThread,
    plan: dict,
    approval: dict,
    task: dict,
    order: int,
) -> bool:
    """Fail closed unless a resumed task still belongs to the frozen plan."""
    sdb = plan.get("sdb") if isinstance(plan, dict) else None
    if not isinstance(sdb, dict) or not isinstance(approval, dict) or not isinstance(task, dict):
        return False
    if (thread.current_plan or {}).get("sdb") != sdb:
        return False
    if approval.get("status") != "consumed":
        return False
    expected_plan = canonical_sdb_payload(sdb)
    bindings = approval.get("sdb_bindings")
    if bindings != expected_plan["sdb_bindings"]:
        return False
    if approval.get("sdb_sha256") != canonical_sdb_digest(sdb):
        return False
    selected = next((binding for binding in bindings if binding.get("order") == order), None)
    if selected is None:
        return False
    return (
        selected.get("task_id") == task.get("id")
        and selected.get("tool") == task.get("tool")
        and selected.get("arguments") == task.get("arguments")
        and selected.get("arguments_sha256") == arguments_digest(
            task.get("tool"), task.get("arguments") or {}, order=order, task_id=task.get("id")
        )
    )


def is_recoverable(thread: InternalChatThread) -> bool:
    return bool((thread.assistant_state or {}).get("recoverable"))


def claim_execution(
    session: Session, thread: InternalChatThread, *, active_run_id: str | None = None
) -> bool:
    """Claim a persisted pending execution exactly once for recovery."""
    claimed = session.execute(
        text("""
            UPDATE internal_chat_threads
            SET assistant_state = jsonb_set(assistant_state, '{execution_status}', '"running"'::jsonb)
            WHERE id = :thread_id
              AND (CAST(:active_run_id AS VARCHAR) IS NULL OR active_run_id = :active_run_id)
              AND assistant_state #>> '{execution_status}' = 'pending'
            RETURNING id
        """),
        {"thread_id": thread.id, "active_run_id": active_run_id or thread.active_run_id},
    ).scalar_one_or_none()
    if claimed is None:
        return False
    session.refresh(thread)
    return True


def resumable_sdb_tasks(tasks: list[dict], checkpoints: list[dict]) -> list[dict]:
    """Return only tasks without a successful persisted checkpoint."""
    completed = {
        checkpoint.get("task_id")
        for checkpoint in checkpoints
        if checkpoint.get("status") == "completed" and checkpoint.get("task_id")
    }
    return [task for task in tasks if task.get("id") not in completed]
