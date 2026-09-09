"""Persistence boundary for the panel assistant graph."""

from datetime import datetime, timezone
import json
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.chat.assistant.graph import run_assistant
from app.chat.assistant.approval import validate_approval
from app.chat.assistant.nodes import execute
from app.chat.assistant.recovery import claim_execution, recover_events
from app.models import AssistantAttachment, InternalChatMessage, InternalChatThread, User
from app.services.audit import record_audit
from app.services.realtime import stage_event


def thread_dict(thread: InternalChatThread) -> dict:
    from app.panel.api.serializers import to_internal_chat_thread_dict

    return to_internal_chat_thread_dict(thread)


def message_dict(message: InternalChatMessage) -> dict:
    from app.panel.api.serializers import to_internal_chat_message_dict

    return to_internal_chat_message_dict(message)


def create_thread(session: Session, user: User) -> InternalChatThread:
    thread = InternalChatThread(user_id=user.id)
    session.add(thread)
    session.flush()
    record_audit(session, actor=user.username, action="internal_chat.thread_created",
                 entity="internal_chat_thread", entity_id=str(thread.id))
    return thread


def submit_message(session: Session, thread: InternalChatThread, user: User, content: str, attachment_ids: list[int] | None = None) -> InternalChatMessage:
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
        def publish_token(token: str) -> None:
            stage_event(session, type="token", conversation_id=thread.id, data={"token": token})

        attachments = list(session.scalars(select(AssistantAttachment).where(AssistantAttachment.thread_id == thread.id, AssistantAttachment.id.in_(attachment_ids or []), AssistantAttachment.deleted_at.is_(None)))) if attachment_ids else []
        result = run_assistant(
            thread_id=thread.id,
            user_id=user.id,
            content=message.content,
            run_id=run_id,
            on_token=publish_token,
            session=session,
            actor=user.username,
            attachments=attachments,
        )
        thread.active_run_id = run_id
        thread.current_plan = result.get("plan")
        thread.assistant_state = {
            "stage": result.get("status", "completed"),
            "recoverable": True,
            "approval": result.get("approval"),
            "execution_status": "pending" if result.get("status") == "approval_pending" else "completed",
            "events": _events_for(result, thread.id, run_id),
        }
        message.assistant_metadata = {"run_id": run_id, "approval": result.get("approval"), "attachment_ids": [row.id for row in attachments]}
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
            stage_event(
                session,
                type="message",
                conversation_id=thread.id,
                data=message_dict(response_message),
            )
    except Exception as exc:
        message.status = "failed"
        message.error = "The agent could not process this message. Retry it."
        message.completed_at = datetime.now(timezone.utc)
        thread.assistant_state = {
            "stage": "failed",
            "recoverable": True,
            "events": [{
                "type": "error",
                "thread_id": thread.id,
                "run_id": run_id,
                "sequence": 0,
                "error": str(exc),
                "evidence": getattr(exc, "evidence", []),
            }],
        }
        thread.active_run_id = run_id
    record_audit(session, actor=user.username, action="internal_chat.message_sent",
                 entity="internal_chat_message", entity_id=str(message.id),
                 after={"status": message.status})
    session.flush()
    return message


def _events_for(result: dict, thread_id: int, run_id: str) -> list[dict]:
    events = [
        {"type": "plan", "thread_id": thread_id, "run_id": run_id, "sequence": 0, "plan": result.get("plan", {})},
        {"type": "approval", "thread_id": thread_id, "run_id": run_id, "sequence": 1, "approval": result.get("approval"), "status": result.get("status")},
    ]
    if result.get("status") != "approval_pending":
        events.extend(_execution_events(result, thread_id, run_id, len(events)))
    return events


def _execution_events(result: dict, thread_id: int, run_id: str, sequence: int) -> list[dict]:
    tool_result = result.get("tool_result") or {}
    return [
        {"type": "tool", "thread_id": thread_id, "run_id": run_id, "sequence": sequence, "tool": tool_result.get("tool"), "status": tool_result.get("status", result.get("status", "completed"))},
        {"type": "evidence", "thread_id": thread_id, "run_id": run_id, "sequence": sequence + 1, "evidence": result.get("evidence", [])},
        {"type": "status", "thread_id": thread_id, "run_id": run_id, "sequence": sequence + 2, "status": result.get("status", "completed")},
        {"type": "response", "thread_id": thread_id, "run_id": run_id, "sequence": sequence + 3, "content": result.get("response", "")},
    ]


def stream_events(session: Session, thread: InternalChatThread, run_id: str | None = None) -> list[dict]:
    return recover_events(thread, run_id)


def approve_plan(session: Session, thread: InternalChatThread, user: User, run_id: str, token: str, *, reject: bool = False) -> InternalChatMessage | None:
    """Atomically consume or reject the approval stored on the thread."""
    plan = thread.current_plan or {}
    state = thread.assistant_state or {}
    approval = state.get("approval") or {}
    if thread.active_run_id != run_id or not validate_approval(plan, approval, token):
        return None
    status = "rejected" if reject else "consumed"
    updated = session.execute(
        text("""
            UPDATE internal_chat_threads
            SET assistant_state = jsonb_set(assistant_state, '{approval,status}', CAST(:status AS jsonb))
            WHERE id = :thread_id
              AND active_run_id = :run_id
              AND assistant_state #>> '{approval,status}' = 'pending'
            RETURNING id
        """),
        {"status": json.dumps(status), "thread_id": thread.id, "run_id": run_id},
    ).scalar_one_or_none()
    if updated is None:
        return None
    session.refresh(thread)
    message = session.scalar(
        select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread.id,
            InternalChatMessage.assistant_metadata["run_id"].as_string() == run_id,
        ).order_by(InternalChatMessage.id.desc())
    )
    if message is None:
        return None
    if reject:
        message.status = "rejected"
        return message
    thread.assistant_state = {
        **thread.assistant_state,
        "stage": "executing",
        "execution_status": "pending",
    }
    session.flush()
    if not claim_execution(session, thread):
        return None
    result = execute({
        "thread_id": thread.id,
        "run_id": run_id,
        "content": message.content,
        "plan": plan,
        "approval": thread.assistant_state["approval"],
        "session": session,
        "actor": user.username,
    })
    message.status = "processed"
    message.completed_at = datetime.now(timezone.utc)
    thread.assistant_state = {**thread.assistant_state, "stage": "completed", "execution_status": "completed"}
    response_message = InternalChatMessage(
        thread_id=thread.id, author="agent", content=result["response"], status="processed",
        completed_at=datetime.now(timezone.utc), assistant_metadata={"run_id": run_id},
    )
    session.add(response_message)
    session.flush()
    thread.assistant_state = {
        **thread.assistant_state,
        "events": [
            *(thread.assistant_state.get("events") or []),
            *_execution_events(result, thread.id, run_id, len(thread.assistant_state.get("events") or [])),
        ],
    }
    session.flush()
    return message


def resume_thread(session: Session, thread: InternalChatThread, user: User) -> bool:
    """Resume a persisted execution after interruption, with an atomic claim."""
    state = thread.assistant_state or {}
    if state.get("stage") != "executing" or not claim_execution(session, thread):
        return False
    run_id = thread.active_run_id
    if not run_id:
        return False
    message = session.scalar(
        select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread.id,
            InternalChatMessage.assistant_metadata["run_id"].as_string() == run_id,
            InternalChatMessage.status == "processing",
        ).order_by(InternalChatMessage.id.desc())
    )
    if message is None:
        return False
    result = execute({
        "thread_id": thread.id,
        "run_id": run_id,
        "content": message.content,
        "plan": thread.current_plan or {},
        "approval": thread.assistant_state.get("approval"),
        "session": session,
        "actor": user.username,
    })
    message.status = "processed"
    message.completed_at = datetime.now(timezone.utc)
    thread.assistant_state = {**thread.assistant_state, "stage": "completed", "execution_status": "completed"}
    session.add(InternalChatMessage(
        thread_id=thread.id, author="agent", content=result["response"], status="processed",
        completed_at=datetime.now(timezone.utc), assistant_metadata={"run_id": run_id},
    ))
    thread.assistant_state = {
        **thread.assistant_state,
        "events": [
            *(thread.assistant_state.get("events") or []),
            *_execution_events(result, thread.id, run_id, len(thread.assistant_state.get("events") or [])),
        ],
    }
    session.flush()
    return True


def get_thread(session: Session, thread_id: int, user_id: int) -> tuple[InternalChatThread, list[InternalChatMessage]] | None:
    thread = session.scalar(select(InternalChatThread).where(InternalChatThread.id == thread_id, InternalChatThread.user_id == user_id))
    if thread is None:
        return None
    messages = list(session.scalars(select(InternalChatMessage).where(InternalChatMessage.thread_id == thread.id).order_by(InternalChatMessage.created_at, InternalChatMessage.id)))
    return thread, messages
