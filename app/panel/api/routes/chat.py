"""Owner/admin internal agent chat JSON API (IAC-1/2/3)."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import User
from app.agent_registry import get_registry
from app.chat.assistant.tools.registry import get_tool
from app.panel.api.deps import require_admin_json
from app.panel.deps import get_db
from app.services.agent_chat import approve_plan, create_thread, get_thread, message_dict, resume_thread, stream_events, submit_message, thread_dict

router = APIRouter(tags=["panel-api-chat"])


class ChatMessageBody(BaseModel):
    content: str = Field(min_length=1)


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
    return {"thread": thread_dict(thread), "messages": [message_dict(row) for row in messages]}


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
    message = submit_message(session, result[0], current, body.content)
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
