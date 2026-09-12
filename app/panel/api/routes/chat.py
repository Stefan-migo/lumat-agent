"""Owner/admin internal agent chat JSON API (IAC-1/2/3)."""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import AssistantAttachment, User
from app.config import get_settings
from app.agent_registry import get_registry
from app.chat.assistant.tools.registry import get_tool
from app.panel.api.deps import require_admin_json
from app.panel.deps import get_db
from app.services.agent_chat import approve_plan, create_thread, get_thread, message_dict, resume_thread, stream_events, submit_message, thread_dict
from app.chat.assistant.attachments import cleanup_expired, store_attachment
from app.panel.api.serializers import to_assistant_attachment_dict
from app.services.audit import record_audit
from sqlalchemy import select, func

router = APIRouter(tags=["panel-api-chat"])


class ChatMessageBody(BaseModel):
    content: str = Field(min_length=1)
    attachment_ids: list[int] = Field(default_factory=list)
    sdb_requested: bool | None = None


class ApprovalBody(BaseModel):
    run_id: str = Field(min_length=1)
    token: str = Field(min_length=1)
    reject: bool = False


@router.post("/chat/threads", status_code=201)
def new_thread(session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    return {"thread": thread_dict(create_thread(session, current)), "messages": []}


@router.get("/chat/threads/{thread_id}")
def read_thread(thread_id: int, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    thread, messages = result
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
def send_message(thread_id: int, body: ChatMessageBody, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    if len(body.attachment_ids) > get_settings().assistant_attachment_max_count:
        raise HTTPException(status_code=400, detail="attachment count limit reached")
    owned = list(session.scalars(select(AssistantAttachment).where(AssistantAttachment.thread_id == thread_id, AssistantAttachment.id.in_(body.attachment_ids), AssistantAttachment.deleted_at.is_(None)))) if body.attachment_ids else []
    if len(owned) != len(set(body.attachment_ids)):
        raise HTTPException(status_code=404, detail="attachment not found")
    message = submit_message(
        session, result[0], current, body.content, [row.id for row in owned],
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
    events = stream_events(session, result[0], run_id)

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
