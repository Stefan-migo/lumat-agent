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

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Conversation, DeliveryStatus, Message, MessageDirection, User
from app.panel.api.deps import require_user_json
from app.panel.api.serializers import to_conversation_dict, to_message_dict
from app.panel.deps import get_db
from app.services.conversations import assign, change_state, retry_operator_message, send_operator_message
from app.models import ConversationState

router = APIRouter(tags=["panel-api-conversations"])


class StateCommand(BaseModel):
    state: ConversationState
    expected_version: int = Field(ge=0)
    request_id: str = Field(min_length=1)


class AssignmentCommand(BaseModel):
    responsible_id: int | None
    expected_version: int = Field(ge=0)
    request_id: str = Field(min_length=1)


class MessageCommand(BaseModel):
    text: str
    request_id: str = Field(min_length=1)


class RetryCommand(BaseModel):
    request_id: str = Field(min_length=1)
    expected_status: str


def _conversation_or_404(session: Session, conversation_id: int) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conversation


def _conversation_payload(session: Session, conversation: Conversation) -> dict:
    latest_inbound_at = session.scalar(
        select(Message.created_at)
        .where(
            Message.conversation_id == conversation.id,
            Message.direction == MessageDirection.INBOUND,
        )
        .order_by(Message.created_at.desc(), Message.id.desc())
    )
    created = latest_inbound_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    open_window = created is not None and datetime.now(timezone.utc) - created < timedelta(hours=24)
    delivery_summary = {status.value: 0 for status in DeliveryStatus}
    for status in session.scalars(
        select(Message.delivery_status).where(
            Message.conversation_id == conversation.id,
            Message.direction == MessageDirection.OUTBOUND,
            Message.delivery_status.is_not(None),
        )
    ):
        delivery_summary[status.value] += 1
    return to_conversation_dict(
        conversation,
        latest_inbound_at=latest_inbound_at,
        reply_window_open=open_window,
        delivery_summary=delivery_summary,
    )


@router.get("/conversations")
def conversations_list(
    state: ConversationState | None = None,
    responsible_id: int | None = None,
    session: Session = Depends(get_db),
    current: User = Depends(require_user_json),
) -> dict:
    """List conversation metadata, most recently active first."""
    query = select(Conversation)
    if state is not None:
        query = query.where(Conversation.state == state)
    if responsible_id is not None:
        query = query.where(Conversation.responsible_id == responsible_id)
    rows = session.scalars(query.order_by(
            Conversation.last_message_at.desc().nulls_last(),
            Conversation.id.desc(),
        )
    ).all()
    return {"conversations": [_conversation_payload(session, row) for row in rows]}


@router.post("/conversations/{conversation_id}/state")
def state_command(conversation_id: int, body: StateCommand, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    conversation = change_state(session, conversation_id, current, body.state, body.expected_version, body.request_id)
    return {"ok": True, "conversation": _conversation_payload(session, conversation)}


@router.post("/conversations/{conversation_id}/assignment")
def assignment_command(conversation_id: int, body: AssignmentCommand, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    conversation = assign(session, conversation_id, current, body.responsible_id, body.expected_version, body.request_id)
    return {"ok": True, "conversation": _conversation_payload(session, conversation)}


@router.post("/conversations/{conversation_id}/messages")
def message_command(conversation_id: int, body: MessageCommand, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    if not body.text.strip():
        _conversation_or_404(session, conversation_id)
        from app.services.audit import record_audit
        record_audit(session, actor=current.username, action="message.send_rejected", entity="conversation", entity_id=str(conversation_id), after={"request_id": body.request_id, "detail": "message text must not be blank"})
        session.commit()
        raise HTTPException(status_code=422, detail="message text must not be blank")
    message = send_operator_message(session, conversation_id, current, body.text, body.request_id)
    if message.delivery_status != DeliveryStatus.SENT:
        raise HTTPException(status_code=502, detail="message delivery failed")
    return {"ok": True, "message": to_message_dict(message)}


@router.post("/conversations/{conversation_id}/messages/{message_id}/retry")
def retry_message(conversation_id: int, message_id: int, body: RetryCommand, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    message = retry_operator_message(session, conversation_id, message_id, current, body.request_id, body.expected_status)
    if message.delivery_status != DeliveryStatus.SENT:
        raise HTTPException(status_code=502, detail="message delivery failed")
    return {"ok": True, "message": to_message_dict(message)}


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
        "conversation": _conversation_payload(session, conversation),
        "messages": [to_message_dict(m) for m in messages],
    }
