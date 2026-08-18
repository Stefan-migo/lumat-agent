"""Panel JSON API conversations (B3/T3.1; PDW-API, PDW-API-3, D4).

Thin JSON wrapper over the read-only conversation thread (same data the
Jinja route renders — AP-4/HH-1): one conversation + its messages in
chronological order (`created_at`, then `id` for same-timestamp ties), with
`media_url` files exposed as plain URLs so the SPA renders them as links
(PDW-TST-3 pattern). Read-only by design (H1: no reply-from-panel, HH-5).

Errors are JSON {"detail": ...} (PDW-API-3): 401 from the JSON-401 dep (D4,
PDW-AUTH-1), 404 for a missing conversation. No redirects, no CORS (D1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Conversation, Message, User
from app.panel.api.deps import require_user_json
from app.panel.api.serializers import to_conversation_dict, to_message_dict
from app.panel.deps import get_db

router = APIRouter(tags=["panel-api-conversations"])


def _conversation_or_404(session: Session, conversation_id: int) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conversation


@router.get("/conversations/{conversation_id}")
def conversation_thread(
    conversation_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_user_json),
) -> dict:
    """Conversation metadata + chronological messages (media as URL links)."""
    conversation = _conversation_or_404(session, conversation_id)
    messages = list(
        session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)
        )
    )
    return {
        "conversation": to_conversation_dict(conversation),
        "messages": [to_message_dict(m) for m in messages],
    }
