"""Owner/admin internal agent chat JSON API (IAC-1/2/3)."""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import AssistantAttachment, InternalChatMessage, InternalChatThread, Memory, User
from app.config import get_settings
from app.agent_registry import get_registry
from app.chat.assistant.tools.registry import get_tool
from app.panel.api.deps import require_admin_json
from app.panel.deps import get_db
from app.services.agent_chat import approve_plan, close_cortex_session, create_run_message, create_thread, get_thread, message_dict, reap_stale_run, resume_thread, run_agent_turn, stream_events, thread_dict
from app.db import SessionLocal
from app.chat.assistant.attachments import cleanup_expired, store_attachment
from app.panel.api.serializers import (
    to_assistant_attachment_dict,
    to_cortex_report_dict,
    to_cortex_session_dict,
    to_internal_chat_thread_summary_dict,
)
from app.services.audit import record_audit
from sqlalchemy import func, select
from app.services import tukulpan

router = APIRouter(tags=["panel-api-chat"])


class ChatMessageBody(BaseModel):
    content: str = Field(min_length=1)
    attachment_ids: list[int] = Field(default_factory=list)
    sdb_requested: bool | None = None


class ApprovalBody(BaseModel):
    run_id: str = Field(min_length=1)
    token: str = Field(min_length=1)
    reject: bool = False


class PlanningSessionBody(BaseModel):
    topic: str
    thread_id: int | None = None


class ChatThreadTitleBody(BaseModel):
    title: str = Field(min_length=1, max_length=255)


def _planning_thread(session: Session, slug: str, user_id: int) -> InternalChatThread | None:
    threads = session.scalars(select(InternalChatThread).where(InternalChatThread.user_id == user_id)).all()
    return next((thread for thread in threads if ((thread.assistant_state or {}).get("cortex_session") or {}).get("slug") == slug), None)


def _planning_report(session: Session, thread: InternalChatThread) -> Memory | None:
    cortex = (thread.assistant_state or {}).get("cortex_session") or {}
    return tukulpan.get_by_key(session, scope="panel", entity_id=f"thread:{thread.id}", topic_key=cortex.get("report_key", "")) if cortex.get("report_key") else None


@router.post("/chat/threads", status_code=201)
def new_thread(session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    return {"thread": thread_dict(create_thread(session, current)), "messages": []}


@router.get("/chat/threads")
def list_chat_threads(
    limit: int = Query(..., ge=1, le=50),
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    latest_created_at = (
        select(func.max(InternalChatMessage.created_at))
        .where(InternalChatMessage.thread_id == InternalChatThread.id)
        .scalar_subquery()
    )
    rows = session.scalars(
        select(InternalChatThread)
        .where(
            InternalChatThread.user_id == current.id,
            InternalChatThread.assistant_state["cortex_session"].as_string().is_(None),
            select(InternalChatMessage.id)
            .where(InternalChatMessage.thread_id == InternalChatThread.id)
            .exists(),
        )
        .order_by(latest_created_at.desc(), InternalChatThread.id.desc())
        .limit(limit)
    ).all()
    # Cortex sessions have their own lifecycle/list endpoint; they are not chat threads.
    threads = list(rows)
    if not threads:
        return {"threads": []}
    latest_messages = session.scalars(
        select(InternalChatMessage)
        .where(InternalChatMessage.thread_id.in_([row.id for row in threads]))
        .order_by(InternalChatMessage.created_at.desc(), InternalChatMessage.id.desc())
    ).all()
    latest_by_thread = {}
    for message in latest_messages:
        latest_by_thread.setdefault(message.thread_id, message)
    return {
        "threads": [
            to_internal_chat_thread_summary_dict(row, latest_by_thread.get(row.id))
            for row in threads
        ]
    }


@router.patch("/chat/threads/{thread_id}")
def rename_chat_thread(
    thread_id: int,
    body: ChatThreadTitleBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    thread = session.get(InternalChatThread, thread_id)
    if thread is None or thread.user_id != current.id:
        raise HTTPException(status_code=404, detail="chat thread not found")
    thread.title = body.title.strip()
    if not thread.title:
        raise HTTPException(status_code=422, detail="title must not be blank")
    session.flush()
    return {"thread": to_internal_chat_thread_summary_dict(thread)}


@router.delete("/chat/threads/{thread_id}")
def delete_chat_thread(
    thread_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    thread = session.get(InternalChatThread, thread_id)
    if thread is None or thread.user_id != current.id:
        raise HTTPException(status_code=404, detail="chat thread not found")
    session.delete(thread)
    return {"ok": True}


@router.post("/planning/sessions", status_code=201)
def open_planning_session(
    body: PlanningSessionBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic must not be blank")
    thread = session.get(InternalChatThread, body.thread_id) if body.thread_id is not None else None
    if body.thread_id is not None and (thread is None or thread.user_id != current.id):
        raise HTTPException(status_code=404, detail="chat thread not found")
    if thread is None:
        thread = create_thread(session, current)
    cortex = (thread.assistant_state or {}).get("cortex_session") or {}
    if cortex.get("status") == "active":
        raise HTTPException(status_code=409, detail="planning session is already active")
    slug = f"{topic.lower().replace(' ', '-')}-{thread.id}"
    thread.assistant_state = {
        **(thread.assistant_state or {}),
        "cortex_session": {
            "slug": slug, "topic": topic, "status": "active",
            "opened_at": datetime.now(timezone.utc).isoformat(), "closed_at": None,
            "turn_index": 0, "next_decision": None, "last_class": None,
            "decision_keys": [], "report_key": None,
            "handoff": {"status": "none", "sdb_phase": None},
        },
    }
    session.flush()
    return {"session": to_cortex_session_dict(thread), "thread_id": thread.id}


@router.get("/planning/sessions")
def list_planning_sessions(session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    threads = session.scalars(select(InternalChatThread).where(InternalChatThread.user_id == current.id).order_by(InternalChatThread.updated_at.desc())).all()
    return {"sessions": [to_cortex_session_dict(thread) for thread in threads if (thread.assistant_state or {}).get("cortex_session")]}


@router.get("/planning/sessions/{slug}")
def planning_session_detail(slug: str, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    thread = _planning_thread(session, slug, current.id)
    if thread is None:
        raise HTTPException(status_code=404, detail="planning session not found")
    memories = tukulpan.list_for_entity(session, scope="panel", entity_id=f"thread:{thread.id}")
    decisions = [row for row in memories if ":decision:" in row.topic_key]
    return {"session": to_cortex_session_dict(thread), "thread": thread_dict(thread),
            "decisions": [to_cortex_report_dict(row) for row in decisions],
            "report": to_cortex_report_dict(_planning_report(session, thread))}


@router.post("/planning/sessions/{slug}/close")
def close_planning_session(slug: str, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    thread = _planning_thread(session, slug, current.id)
    if thread is None:
        raise HTTPException(status_code=404, detail="planning session not found")
    cortex = (thread.assistant_state or {}).get("cortex_session") or {}
    if cortex.get("status") != "active":
        raise HTTPException(status_code=409, detail="planning session is not active")
    decisions = tukulpan.list_for_entity(session, scope="panel", entity_id=f"thread:{thread.id}")
    report = json.dumps({"topic": cortex.get("topic", ""), "decisions": [row.contenido for row in decisions if ":decision:" in row.topic_key]}, ensure_ascii=False)
    result = close_cortex_session(session, thread, report=report)
    approval = (thread.assistant_state or {}).get("approval") or {}
    session.add(InternalChatMessage(thread_id=thread.id, author="admin", content=report,
                                    status="approval_pending", assistant_metadata={"run_id": result["run_id"], "approval": approval}))
    session.flush()
    return {"session": to_cortex_session_dict(thread), "report": to_cortex_report_dict(_planning_report(session, thread)),
            "handoff": {"status": "pending", "sdb_phase": "SPEC", "run_id": result["run_id"], "approval": approval}}


@router.post("/planning/sessions/{slug}/reopen")
def reopen_planning_session(slug: str, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    thread = _planning_thread(session, slug, current.id)
    if thread is None:
        raise HTTPException(status_code=404, detail="planning session not found")
    cortex = (thread.assistant_state or {}).get("cortex_session") or {}
    if cortex.get("status") == "active":
        raise HTTPException(status_code=409, detail="planning session is already active")
    thread.assistant_state = {**(thread.assistant_state or {}), "cortex_session": {
        **cortex, "status": "active", "closed_at": None,
        "handoff": {"status": "none", "sdb_phase": None},
    }}
    session.flush()
    return {"session": to_cortex_session_dict(thread), "thread_id": thread.id}


@router.get("/chat/threads/{thread_id}")
def read_thread(thread_id: int, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    thread, messages = result
    reap_stale_run(session, thread)
    resume_thread(session, thread, current)
    messages = get_thread(session, thread_id, current.id)[1]
    attachments = session.scalars(select(AssistantAttachment).where(AssistantAttachment.thread_id == thread_id, AssistantAttachment.deleted_at.is_(None)).order_by(AssistantAttachment.id)).all()
    return {"thread": thread_dict(thread), "messages": [message_dict(row) for row in messages], "attachments": [to_assistant_attachment_dict(row) for row in attachments]}


@router.get("/assistant/capabilities")
def assistant_capabilities(current: User = Depends(require_admin_json)) -> dict:
    """Return the validated assistant configuration without mutation controls."""
    registry = get_registry()
    assistant = registry.assistant
    tools = [
        {
            "name": name,
            "description": get_tool(name).description,
            "read_only": get_tool(name).read_only,
            "write": get_tool(name).write,
        }
        for name in assistant.tools_whitelist
    ]
    return {
        "tools": tools,
        "personas": [assistant.persona],
        "prompts": list(assistant.prompts.values()),
        "kb_available": "kb.retrieve" in assistant.tools_whitelist,
        "memory_available": any(name.startswith("memory.") for name in assistant.tools_whitelist),
    }


@router.post("/chat/threads/{thread_id}/messages", status_code=201)
def send_message(thread_id: int, body: ChatMessageBody, background_tasks: BackgroundTasks, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    if len(body.attachment_ids) > get_settings().assistant_attachment_max_count:
        raise HTTPException(status_code=400, detail="attachment count limit reached")
    owned = list(session.scalars(select(AssistantAttachment).where(AssistantAttachment.thread_id == thread_id, AssistantAttachment.id.in_(body.attachment_ids), AssistantAttachment.deleted_at.is_(None)))) if body.attachment_ids else []
    if len(owned) != len(set(body.attachment_ids)):
        raise HTTPException(status_code=404, detail="attachment not found")
    message = create_run_message(
        session, result[0], current, body.content, [row.id for row in owned],
        sdb_requested=body.sdb_requested,
    )
    # Commit before scheduling: FastAPI may run background tasks before the
    # request dependency's teardown, and the runner must see this row without
    # waiting on the request transaction.
    session.commit()
    background_tasks.add_task(
        run_agent_turn,
        thread_id=thread_id,
        run_id=message.assistant_metadata["run_id"],
        user_id=current.id,
        username=current.username,
        actor_role=current.role.value,
        attachment_ids=[row.id for row in owned],
        sdb_requested=body.sdb_requested,
    )
    return {"message": message_dict(message)}


@router.get("/chat/threads/{thread_id}/stream")
def stream_thread(
    thread_id: int,
    run_id: str | None = None,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
):
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    events = stream_events(SessionLocal, thread_id, run_id or result[0].active_run_id)

    def body():
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(body(), media_type="text/event-stream")


@router.post("/chat/threads/{thread_id}/approval")
def approve_thread_plan(
    thread_id: int,
    body: ApprovalBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    message = approve_plan(session, result[0], current, body.run_id, body.token, reject=body.reject)
    if message is None:
        raise HTTPException(status_code=409, detail="approval is invalid, expired, or already consumed")
    return {"status": message.status, "message": message_dict(message)}


@router.post("/chat/threads/{thread_id}/attachments", status_code=201)
def upload_attachment(
    thread_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    cleanup_expired(session, datetime.now(timezone.utc) - timedelta(days=get_settings().assistant_attachment_expiry_days), {thread_id})
    count = session.scalar(select(func.count(AssistantAttachment.id)).where(AssistantAttachment.thread_id == thread_id, AssistantAttachment.deleted_at.is_(None))) or 0
    if count >= get_settings().assistant_attachment_max_count:
        raise HTTPException(status_code=400, detail="attachment count limit reached")
    content = file.file.read(get_settings().assistant_attachment_max_bytes + 1)
    try:
        kind, path, digest = store_attachment(thread_id, file.filename or "attachment", file.content_type, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = AssistantAttachment(thread_id=thread_id, filename=file.filename or "attachment", kind=kind,
                              content_type=file.content_type or "application/octet-stream", size=len(content),
                              sha256=digest, stored_path=str(path))
    session.add(row)
    session.flush()
    record_audit(session, actor=current.username, action="internal_chat.attachment_uploaded",
                 entity="assistant_attachment", entity_id=str(row.id), after={"thread_id": thread_id, "kind": kind, "size": len(content)})
    session.commit()
    return {"attachment": to_assistant_attachment_dict(row)}
