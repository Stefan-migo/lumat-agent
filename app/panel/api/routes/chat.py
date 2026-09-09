"""Owner/admin internal agent chat JSON API (IAC-1/2/3)."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_admin_json
from app.panel.deps import get_db
from app.services.agent_chat import create_thread, get_thread, message_dict, stream_events, submit_message, thread_dict

router = APIRouter(tags=["panel-api-chat"])


class ChatMessageBody(BaseModel):
    content: str = Field(min_length=1)


@router.post("/chat/threads", status_code=201)
def new_thread(session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    return {"thread": thread_dict(create_thread(session, current)), "messages": []}


@router.get("/chat/threads/{thread_id}")
def read_thread(thread_id: int, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    result = get_thread(session, thread_id, current.id)
    if result is None:
        raise HTTPException(status_code=404, detail="chat thread not found")
    thread, messages = result
    return {"thread": thread_dict(thread), "messages": [message_dict(row) for row in messages]}


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
