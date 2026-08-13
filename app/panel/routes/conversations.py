"""Conversations panel views (T5.2; AP-4).

GET /panel/conversations/{id} — read-only thread: the conversation metadata
plus its messages in chronological order, with linked files (media_url)
rendered as links. Read-only by design (H1: no reply-from-panel, HH-5 — the
human answers via the WhatsApp app). Media URLs are stored by the webhook
ingest pipeline (B2) — no upload endpoints here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.models import Conversation, Message
from app.panel.deps import get_db, require_user, templates

router = APIRouter(tags=["panel-conversations"])


@router.get("/conversations/{conversation_id}")
def conversation_thread(
    request: Request,
    conversation_id: int,
    session=Depends(get_db),
    current=Depends(require_user),
):
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    messages = list(
        session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)
        )
    )
    return templates.TemplateResponse(
        request,
        "conversations/thread.html",
        {
            "current_user": current,
            "conversation": conversation,
            "messages": messages,
        },
    )
