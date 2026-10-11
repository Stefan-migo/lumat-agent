"""Internal agent chat JSON API for every authenticated panel role (IAC-1/2/3)."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import AssistantArtifact, AssistantAttachment, InternalChatMessage, InternalChatThread, Memory, User
from app.config import get_settings
from app.agent_registry import get_registry
from app.chat.assistant.tools.registry import get_tool, is_tool_allowed_for_role
from app.panel.api.deps import require_agent_surface_json
from app.panel.deps import get_db
from app.services.agent_chat import approve_plan, close_cortex_session, create_run_message, create_thread, get_thread, message_dict, read_owned_thread_run, reap_stale_run, resume_thread, run_agent_turn, stream_events_async, thread_dict
from app.chat.assistant.state import merge_assistant_state
from app.db import SessionLocal
from app.chat.assistant.attachments import cleanup_expired, store_attachment
from app.panel.api.serializers import (
    to_assistant_attachment_dict,
    to_assistant_artifact_dict,
    to_active_chat_run_dict,
    to_cortex_report_dict,
    to_cortex_session_dict,
    to_internal_chat_thread_summary_dict,
)
from app.services.audit import record_audit
from sqlalchemy import func, select
from app.services import projects, tukulpan
from app.services import assistant_artifacts
from app.services.project_config import (
    reset_thread_tool_policy,
    set_thread_tool_policy,
    thread_tool_policy,
)

router = APIRouter(tags=["panel-api-chat"])


class ChatMessageBody(BaseModel):
    content: str = Field(min_length=1)
    attachment_ids: list[int] = Field(default_factory=list)
    sdb_requested: bool | None = None


class ApprovalBody(BaseModel):
    run_id: str = Field(min_length=1)
    token: str = Field(min_length=1)
    reject: bool = False


class StopBody(BaseModel):
    run_id: str | None = Field(default=None, min_length=1)


class PlanningSessionBody(BaseModel):
    topic: str
    thread_id: int | None = None
    proyecto: str | None = Field(default=None, max_length=100)


class ChatThreadTitleBody(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChatThreadBody(BaseModel):
    proyecto: str = Field(min_length=1, max_length=100)


class ChatThreadToolPolicyBody(BaseModel):
    opt_in_enabled: list[str]


def _tool_policy_thread(session: Session, thread_id: int, current: User) -> InternalChatThread:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    return result[0]


def _require_no_active_run(thread: InternalChatThread) -> None:
    # `active_run_id` remains populated after terminal outcomes; only `running`
    # represents a live, non-terminal run (completed/failed/approval_pending are terminal).
    # Reads stay available; only writes are locked while a run is in flight.
    if ((thread.assistant_state or {}).get("live") or {}).get("status") == "running":
        raise HTTPException(status_code=409, detail="tool policy cannot change while a run is active")


def _thread_tool_policy_response(session: Session, thread: InternalChatThread, current: User) -> dict:
    return thread_tool_policy(session, thread, current.role)


@router.get("/chat/threads/{thread_id}/tool-policy")
def read_thread_tool_policy(
    thread_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    thread = _tool_policy_thread(session, thread_id, current)
    return _thread_tool_policy_response(session, thread, current)


@router.put("/chat/threads/{thread_id}/tool-policy")
def update_thread_tool_policy(
    thread_id: int,
    body: ChatThreadToolPolicyBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    thread = _tool_policy_thread(session, thread_id, current)
    _require_no_active_run(thread)
    try:
        set_thread_tool_policy(thread, body.opt_in_enabled, current.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.flush()
    return _thread_tool_policy_response(session, thread, current)


@router.delete("/chat/threads/{thread_id}/tool-policy")
def delete_thread_tool_policy(
    thread_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    thread = _tool_policy_thread(session, thread_id, current)
    _require_no_active_run(thread)
    reset_thread_tool_policy(thread)
    session.flush()
    return _thread_tool_policy_response(session, thread, current)


def _planning_thread(session: Session, slug: str, user_id: int) -> InternalChatThread | None:
    threads = session.scalars(select(InternalChatThread).where(InternalChatThread.user_id == user_id)).all()
    return next((thread for thread in threads if ((thread.assistant_state or {}).get("cortex_session") or {}).get("slug") == slug), None)


def _planning_report(session: Session, thread: InternalChatThread) -> Memory | None:
    cortex = (thread.assistant_state or {}).get("cortex_session") or {}
    if not cortex.get("report_key"):
        return None
    proyecto = thread.proyecto or "default"
    authorization = None if proyecto == "default" else projects.agent_context(session, proyecto, owner_id=thread.user_id)
    return tukulpan.get_by_key(
        session, scope=tukulpan.AGENT_SCOPE, entity_id=tukulpan.agent_memory_entity(proyecto),
        topic_key=cortex["report_key"], proyecto=proyecto,
        owner_id=authorization.owner_id if authorization else None,
    )


@router.post("/chat/threads", status_code=201)
def new_thread(
    body: ChatThreadBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    try:
        thread = create_thread(session, current, proyecto=body.proyecto)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"thread": thread_dict(thread), "messages": []}


@router.get("/chat/threads")
def list_chat_threads(
    limit: int = Query(..., ge=1, le=50),
    proyecto: str | None = Query(default=None, max_length=100),
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    latest_created_at = (
        select(func.max(InternalChatMessage.created_at))
        .where(InternalChatMessage.thread_id == InternalChatThread.id)
        .scalar_subquery()
    )
    where = [
        InternalChatThread.user_id == current.id,
        InternalChatThread.assistant_state["cortex_session"].as_string().is_(None),
        select(InternalChatMessage.id)
        .where(InternalChatMessage.thread_id == InternalChatThread.id)
        .exists(),
    ]
    if proyecto is not None:
        where.append(InternalChatThread.proyecto == proyecto)
    rows = session.scalars(
        select(InternalChatThread)
        .where(*where)
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


@router.get("/chat/active-runs")
def list_active_chat_runs(
    limit: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    rows = session.scalars(
        select(InternalChatThread)
        .where(
            InternalChatThread.user_id == current.id,
            InternalChatThread.assistant_state["live"]["status"].as_string() == "running",
            InternalChatThread.assistant_state["cortex_session"].as_string().is_(None),
        )
        .order_by(InternalChatThread.updated_at.desc())
        .limit(limit)
    ).all()
    return {"active_runs": [to_active_chat_run_dict(thread) for thread in rows]}


@router.patch("/chat/threads/{thread_id}")
def rename_chat_thread(
    thread_id: int,
    body: ChatThreadTitleBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
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
    current: User = Depends(require_agent_surface_json),
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
    current: User = Depends(require_agent_surface_json),
) -> dict:
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic must not be blank")
    thread = session.get(InternalChatThread, body.thread_id) if body.thread_id is not None else None
    if body.thread_id is not None and (thread is None or thread.user_id != current.id):
        raise HTTPException(status_code=404, detail="chat thread not found")
    if thread is None:
        try:
            thread = create_thread(session, current, proyecto=body.proyecto or "default")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    cortex = (thread.assistant_state or {}).get("cortex_session") or {}
    if cortex.get("status") == "active":
        raise HTTPException(status_code=409, detail="planning session is already active")
    slug = f"{topic.lower().replace(' ', '-')}-{thread.id}"
    thread.assistant_state = {
        **(thread.assistant_state or {}),
        "cortex_session": {
            "slug": slug, "topic": topic, "status": "active",
            "opened_at": datetime.now(timezone.utc).isoformat(), "closed_at": None,
            "report_key": None,
        },
    }
    session.flush()
    return {"session": to_cortex_session_dict(thread), "thread_id": thread.id}


@router.get("/planning/sessions")
def list_planning_sessions(session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)) -> dict:
    threads = session.scalars(select(InternalChatThread).where(InternalChatThread.user_id == current.id).order_by(InternalChatThread.updated_at.desc())).all()
    return {"sessions": [to_cortex_session_dict(thread) for thread in threads if (thread.assistant_state or {}).get("cortex_session")]}


@router.get("/planning/sessions/{slug}")
def planning_session_detail(slug: str, session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)) -> dict:
    thread = _planning_thread(session, slug, current.id)
    if thread is None:
        raise HTTPException(status_code=404, detail="planning session not found")
    return {"session": to_cortex_session_dict(thread), "thread": thread_dict(thread),
            "report": to_cortex_report_dict(_planning_report(session, thread))}


@router.post("/planning/sessions/{slug}/close")
def close_planning_session(slug: str, session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)) -> dict:
    thread = _planning_thread(session, slug, current.id)
    if thread is None:
        raise HTTPException(status_code=404, detail="planning session not found")
    cortex = (thread.assistant_state or {}).get("cortex_session") or {}
    if cortex.get("status") != "active":
        raise HTTPException(status_code=409, detail="planning session is not active")
    report = json.dumps({"topic": cortex.get("topic", "")}, ensure_ascii=False)
    close_cortex_session(session, thread, report=report)
    session.flush()
    return {"session": to_cortex_session_dict(thread), "report": to_cortex_report_dict(_planning_report(session, thread))}


@router.post("/planning/sessions/{slug}/reopen")
def reopen_planning_session(slug: str, session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)) -> dict:
    thread = _planning_thread(session, slug, current.id)
    if thread is None:
        raise HTTPException(status_code=404, detail="planning session not found")
    cortex = (thread.assistant_state or {}).get("cortex_session") or {}
    if cortex.get("status") == "active":
        raise HTTPException(status_code=409, detail="planning session is already active")
    thread.assistant_state = {**(thread.assistant_state or {}), "cortex_session": {
        **cortex, "status": "active", "closed_at": None,
    }}
    session.flush()
    return {"session": to_cortex_session_dict(thread), "thread_id": thread.id}


@router.get("/chat/threads/{thread_id}")
def read_thread(thread_id: int, session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)) -> dict:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    thread, messages = result
    reap_stale_run(session, thread)
    resume_thread(session, thread, current)
    messages = get_thread(session, thread_id, current.id)[1]
    attachments = session.scalars(select(AssistantAttachment).where(AssistantAttachment.thread_id == thread_id, AssistantAttachment.deleted_at.is_(None)).order_by(AssistantAttachment.id)).all()
    artifacts = session.scalars(select(AssistantArtifact).where(AssistantArtifact.thread_id == thread_id).order_by(AssistantArtifact.id)).all()
    return {"thread": thread_dict(thread), "messages": [message_dict(row) for row in messages], "attachments": [to_assistant_attachment_dict(row) for row in attachments], "artifacts": [to_assistant_artifact_dict(row) for row in artifacts]}


@router.post("/chat/threads/{thread_id}/stop")
def stop_thread_run(
    thread_id: int,
    body: StopBody | None = None,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    # Lock the owner-scoped row so competing stop requests and terminal writes
    # cannot both make a decision from an outdated JSONB snapshot.
    thread = session.scalar(select(InternalChatThread).where(
        InternalChatThread.id == thread_id, InternalChatThread.user_id == current.id,
    ).with_for_update())
    if thread is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    state = thread.assistant_state or {}
    live = state.get("live") or {}
    run_id = live.get("run_id")
    stop = state.get("stop_request") or {}
    # `approval_pending` is a persisted terminal graph outcome with no runner
    # left, but the owner decision explicitly allows cancelling that pending
    # approval rather than leaving an executable plan available.
    if live.get("status") not in {"running", "approval_pending"}:
        raise HTTPException(status_code=409, detail="assistant run is not active")
    if body and body.run_id and body.run_id != run_id:
        raise HTTPException(status_code=409, detail="assistant run has changed")
    if stop.get("run_id") != run_id:
        thread.assistant_state = merge_assistant_state(state, {"stop_request": {"run_id": run_id}})
    if live.get("status") == "approval_pending" or live.get("stage") == "approval_pending":
        # The graph has already returned at this safe boundary; there is no
        # background runner left to consume the intent, so settle it here.
        settled = dict(thread.assistant_state or {})
        settled.pop("stop_request", None)
        approval = settled.get("approval")
        if isinstance(approval, dict) and approval.get("status") == "pending":
            approval["status"] = "revoked"
        thread.assistant_state = merge_assistant_state(settled, {
            "stage": "cancelled", "execution_status": "cancelled",
            "live": {"run_id": run_id, "stage": "cancelled", "status": "cancelled"},
            "events": [*(settled.get("events") or []), {
                "type": "status", "thread_id": thread_id, "run_id": run_id,
                "sequence": len(settled.get("events") or []), "status": "cancelled",
            }],
        })
        message = session.scalar(select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread_id,
            InternalChatMessage.assistant_metadata["run_id"].as_string() == run_id,
        ).order_by(InternalChatMessage.id.desc()))
        if message is not None:
            message.status = "cancelled"
            message.error = "This assistant run was cancelled by the user."
            message.completed_at = datetime.now(timezone.utc)
            message.assistant_metadata = {
                **(message.assistant_metadata or {}),
                "cancellation": {"status": "cancelled", "requested_by": "owner"},
            }
        session.flush()
        return {"status": "cancelled", "run_id": run_id}
    session.flush()
    return {"status": "stopping", "run_id": run_id}


@router.get("/chat/threads/{thread_id}/artifacts/{artifact_id}/download")
def download_artifact(thread_id: int, artifact_id: int, session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)) -> FileResponse:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    row = assistant_artifacts.get_artifact(session, thread_id, artifact_id)
    if row is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(row.stored_path, filename=row.filename, media_type=row.content_type)


@router.get("/assistant/capabilities")
def assistant_capabilities(current: User = Depends(require_agent_surface_json)) -> dict:
    """Return the validated assistant configuration without mutation controls."""
    registry = get_registry()
    assistant = registry.assistant
    # R3-001: the catalog must describe only what this role may execute, so the
    # panel count and the KB/memory flags never advertise a tool the role's map
    # denies. Intersect with the runtime whitelist; never replace it.
    allowed = [
        name for name in assistant.tools_whitelist if is_tool_allowed_for_role(name, current.role.value)
    ]
    tools = [
        {
            "name": name,
            "description": get_tool(name).description,
            "read_only": get_tool(name).read_only,
            "write": get_tool(name).write,
        }
        for name in allowed
    ]
    return {
        "tools": tools,
        "personas": [assistant.persona],
        "prompts": list(assistant.prompts.values()),
        "kb_available": "kb.retrieve" in allowed,
        "memory_available": any(name.startswith("memory.") for name in allowed),
    }


@router.post("/chat/threads/{thread_id}/messages", status_code=201)
def send_message(thread_id: int, body: ChatMessageBody, background_tasks: BackgroundTasks, session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)) -> dict:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    if body.sdb_requested and current.role.value != "admin":
        raise HTTPException(status_code=403, detail="admin role required for sdb_requested")
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
        attachment_ids=[row.id for row in owned],
        sdb_requested=body.sdb_requested,
    )
    return {"message": message_dict(message)}


@router.get("/chat/threads/{thread_id}/stream")
async def stream_thread(
    thread_id: int,
    run_id: str | None = None,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
):
    # Release the request-scoped connection first: FastAPI keeps the request
    # dependency open until the response is fully sent, so an open stream would
    # hold a pooled connection for up to 300 s (pool_size 5 + overflow 10). Auth
    # shares this session and has already read everything it needs from it, and
    # the read-only route has nothing to commit.
    user_id = current.id
    session.close()
    # The read must not block the loop, and it must not hand that session to a
    # worker thread (a `Session` is not thread-safe): it opens its own, the same
    # shape #213 gave the polling below. Only the thread row is read —
    # `get_thread` would also load every message of the thread, and this route
    # discards that list.
    owned = await asyncio.to_thread(read_owned_thread_run, SessionLocal, thread_id, user_id)
    if owned is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    (active_run_id,) = owned
    run = run_id or active_run_id
    events = stream_events_async(SessionLocal, thread_id, run)

    async def body():
        async for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(body(), media_type="text/event-stream")


@router.post("/chat/threads/{thread_id}/approval")
def approve_thread_plan(
    thread_id: int,
    body: ApprovalBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
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
    current: User = Depends(require_agent_surface_json),
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
