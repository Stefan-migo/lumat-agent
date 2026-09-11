"""Persistence boundary for the panel assistant graph."""

from datetime import datetime, timezone
import json
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.chat.assistant.graph import run_assistant
from app.chat.assistant.approval import validate_approval
from app.chat.assistant.nodes import execute
from app.chat.assistant import nodes as assistant_nodes
from app.chat.assistant.attachments import prepare_attachment_context
from app.chat.assistant.state import COMPACTION_RETENTION_TOKENS, COMPACTION_THRESHOLD_TOKENS, INJECTION_TOKEN_BUDGET, estimate_tokens
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


def load_panel_context(session, thread_id: int) -> dict:
    """Delegate the read-only Tukulpan panel context seam."""
    return assistant_nodes.load_panel_context(session, thread_id)


def flush_panel_session(session, thread_id: int, *, source_message_ids: list[int], recap: str,
                        source_tokens: int, truncated: bool) -> dict:
    """Delegate the meaningful Tukulpan recap seam."""
    return assistant_nodes.flush_panel_session(
        session, thread_id, source_message_ids=source_message_ids, recap=recap,
        source_tokens=source_tokens, truncated=truncated,
    )


def compact_session(session, thread_id: int, messages: list, *, before_tokens: int) -> dict:
    """Flush and retain the newest bounded history when the session threshold is met."""
    retention = COMPACTION_RETENTION_TOKENS
    retained = []
    used = 0
    for message in reversed(messages):
        cost = estimate_tokens(str(message.content))
        if used + cost > retention:
            continue
        retained.append(message)
        used += cost
    retained.reverse()
    truncated = len(retained) != len(messages)
    if before_tokens < COMPACTION_THRESHOLD_TOKENS:
        return {
            "window_tokens": 8_000,
            "threshold_tokens": COMPACTION_THRESHOLD_TOKENS,
            "before_tokens": before_tokens,
            "after_tokens": used,
            "flushed": False,
            "failed": False,
            "rotated": False,
            "retained_message_ids": [message.id for message in retained],
        }
    recap = "\n".join(f"{getattr(message, 'author', 'message')}: {message.content}" for message in retained)
    write = flush_panel_session(
        session, thread_id, source_message_ids=[message.id for message in retained],
        recap=recap, source_tokens=used, truncated=truncated,
    )
    written = bool(write.get("written"))
    if not written:
        return {
            "window_tokens": 8_000, "threshold_tokens": COMPACTION_THRESHOLD_TOKENS,
            "before_tokens": before_tokens, "after_tokens": used,
            "flushed": False, "rotated": False, "failed": True,
            "retained_message_ids": [message.id for message in retained], "write": write,
        }
    rotated_at = datetime.now(timezone.utc).isoformat()
    return {
        "window_tokens": 8_000,
        "threshold_tokens": COMPACTION_THRESHOLD_TOKENS,
        "before_tokens": before_tokens,
        "after_tokens": used,
        "flushed": True,
        "failed": False,
        "rotated": True,
        "retained_message_ids": [message.id for message in retained],
        "rotation": {
            "thread_id": thread_id,
            "retention_tokens": retention,
            "rotated_at": rotated_at,
        },
        "write": write,
    }


def assemble_context(session, thread_id: int, *, messages=None, attachments=None, budget: int = INJECTION_TOKEN_BUDGET) -> dict:
    """Build bounded panel context in stable source order.

    The default is the fixed 4,000-token harness budget; callers may pass a
    smaller ceiling for focused tests and bounded adapters.
    """
    if messages is None:
        messages = list(session.scalars(
            select(InternalChatMessage)
            .where(InternalChatMessage.thread_id == thread_id)
            .order_by(InternalChatMessage.created_at, InternalChatMessage.id)
        ))
    attachments = attachments or []
    tukulpan = load_panel_context(session, thread_id)
    items: list[dict] = []
    message_ids: list[int] = []
    attachment_ids: list[int] = []
    tukulpan_ids: list[str] = []
    used = 0
    truncated = False

    for source in (tukulpan.get("pinned", []), tukulpan.get("panel", [])):
        for entry in source:
            content = str(entry.get("content", ""))
            cost = estimate_tokens(content)
            if used + cost > budget:
                truncated = True
                continue
            items.append({"source": "tukulpan", "content": content, "id": entry.get("id")})
            tukulpan_ids.append(str(entry.get("id")))
            used += cost

    messages = sorted(
        messages,
        key=lambda row: (
            getattr(row, "created_at", None).timestamp()
            if hasattr(getattr(row, "created_at", None), "timestamp")
            else 0,
            row.id,
        ),
    )
    retained_messages: list[dict] = []
    retained_ids: list[int] = []
    for message in reversed(messages):
        content = str(message.content)
        cost = estimate_tokens(content)
        if used + cost > budget:
            truncated = True
            continue
        retained_messages.append({"source": "history", "author": message.author, "content": content, "id": message.id})
        retained_ids.append(message.id)
        used += cost

    items.extend(reversed(retained_messages))
    message_ids.extend(reversed(retained_ids))

    for attachment in attachments:
        content = str(attachment.get("content", "") if isinstance(attachment, dict) else getattr(attachment, "content", ""))
        remaining = max(0, (budget - used) * 4)
        if not remaining:
            truncated = True
            continue
        encoded = content.encode("utf-8")
        if len(encoded) > remaining:
            content = encoded[:remaining].decode("utf-8", errors="ignore")
            truncated = True
        if content:
            attachment_id = attachment.get("id") if isinstance(attachment, dict) else getattr(attachment, "id", None)
            items.append({"source": "attachment", "content": content, "id": attachment_id})
            attachment_ids.append(attachment_id)
            used += estimate_tokens(content)

    return {
        "items": items,
        "meta": {
            "scope": "panel",
            "entity_id": f"thread:{thread_id}",
            "message_ids": message_ids,
            "attachment_ids": attachment_ids,
            "tukulpan_ids": tukulpan_ids,
            "estimated_tokens": used,
            "truncated": truncated,
        },
    }


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
        context_attachments = prepare_attachment_context(attachments) if attachments else []
        context = assemble_context(session, thread.id, attachments=context_attachments)
        compaction = compact_session(
            session, thread.id, list(session.scalars(
                select(InternalChatMessage)
                .where(InternalChatMessage.thread_id == thread.id)
                .order_by(InternalChatMessage.created_at, InternalChatMessage.id)
            )), before_tokens=context["meta"]["estimated_tokens"]
        )
        result = run_assistant(
            thread_id=thread.id,
            user_id=user.id,
            content=message.content,
            run_id=run_id,
            on_token=publish_token,
            session=session,
            actor=user.username,
            attachments=attachments,
            context=context,
            compaction=compaction,
        )
        thread.active_run_id = run_id
        thread.current_plan = result.get("plan")
        thread.assistant_state = {
            "stage": result.get("status", "completed"),
            "recoverable": True,
            "approval": result.get("approval"),
            "execution_status": "pending" if result.get("status") == "approval_pending" else "completed",
            "events": _events_for(result, thread.id, run_id),
            "context_meta": context["meta"],
            "planner": result.get("planner", {}),
            "guardrails": result.get("guardrails", {}),
            "compaction": compaction,
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
