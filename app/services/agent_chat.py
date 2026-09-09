"""Persistence boundary for the panel assistant graph."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.assistant.graph import run_assistant
from app.chat.assistant.recovery import recover_events
from app.models import InternalChatMessage, InternalChatThread, User
from app.panel.api.serializers import to_internal_chat_message_dict, to_internal_chat_thread_dict
from app.services.audit import record_audit


def thread_dict(thread: InternalChatThread) -> dict:
    return to_internal_chat_thread_dict(thread)


def message_dict(message: InternalChatMessage) -> dict:
    return to_internal_chat_message_dict(message)


def create_thread(session: Session, user: User) -> InternalChatThread:
    thread = InternalChatThread(user_id=user.id)
    session.add(thread)
    session.flush()
    record_audit(session, actor=user.username, action="internal_chat.thread_created",
                 entity="internal_chat_thread", entity_id=str(thread.id))
    return thread


def submit_message(session: Session, thread: InternalChatThread, user: User, content: str) -> InternalChatMessage:
    run_id = uuid4().hex
    message = InternalChatMessage(
        thread_id=thread.id,
        author="admin",
        content=content.strip(),
        status="processing",
        assistant_metadata={"run_id": run_id},
    )
    session.add(message)
    session.flush()
    try:
        result = run_assistant(thread_id=thread.id, user_id=user.id, content=message.content, run_id=run_id)
        thread.active_run_id = run_id
        thread.current_plan = result.get("plan")
        thread.assistant_state = {
            "stage": result.get("status", "completed"),
            "recoverable": True,
            "events": _events_for(result, thread.id, run_id),
        }
        if result.get("status") == "approval_pending":
            message.status = "approval_pending"
        else:
            message.status = "processed"
            message.completed_at = datetime.now(timezone.utc)
            response_message = InternalChatMessage(
                thread_id=thread.id,
                author="agent",
                content=result.get("response") or "I could not produce an answer. Please try again.",
                status="processed",
                completed_at=datetime.now(timezone.utc),
                assistant_metadata={"run_id": run_id},
            )
            session.add(response_message)
            session.flush()
    except Exception as exc:
        message.status = "failed"
        message.error = "The agent could not process this message. Retry it."
        message.completed_at = datetime.now(timezone.utc)
        thread.assistant_state = {
            "stage": "failed",
            "recoverable": True,
            "events": [{"type": "error", "thread_id": thread.id, "run_id": run_id, "error": str(exc)}],
        }
        thread.active_run_id = run_id
    record_audit(session, actor=user.username, action="internal_chat.message_sent",
                 entity="internal_chat_message", entity_id=str(message.id),
                 after={"status": message.status})
    session.flush()
    return message


def _events_for(result: dict, thread_id: int, run_id: str) -> list[dict]:
    def event(kind: str, **data) -> dict:
        return {"type": kind, "thread_id": thread_id, "run_id": run_id, **data}

    events = [event("plan", plan=result.get("plan", {}))]
    events.append(event("approval", approval=result.get("approval"), status=result.get("status")))
    if result.get("status") != "approval_pending":
        events.extend(
            [
                event("tool", status="completed"),
                event("evidence", evidence=result.get("evidence", [])),
                event("status", status=result.get("status", "completed")),
                event("response", content=result.get("response", "")),
            ]
        )
    return events


def stream_events(session: Session, thread: InternalChatThread, run_id: str | None = None) -> list[dict]:
    return recover_events(thread, run_id)


def get_thread(session: Session, thread_id: int, user_id: int) -> tuple[InternalChatThread, list[InternalChatMessage]] | None:
    thread = session.scalar(select(InternalChatThread).where(InternalChatThread.id == thread_id, InternalChatThread.user_id == user_id))
    if thread is None:
        return None
    messages = list(session.scalars(select(InternalChatMessage).where(InternalChatMessage.thread_id == thread.id).order_by(InternalChatMessage.created_at, InternalChatMessage.id)))
    return thread, messages
