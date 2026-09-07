"""Authenticated panel WebSocket stream (CRT-1, CRT-2, CRT-3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Conversation, ConversationEvent, User
from app.panel.api.deps import get_current_user_json
from app.panel.api.routes.conversations import _conversation_payload
from app.panel.deps import get_db
from app.services.realtime import ACTIVITY_EVENTS, publisher

router = APIRouter(tags=["panel-realtime"])


def realtime_user(current: User = Depends(get_current_user_json)) -> User:
    """Allow only roles that are authorized to use the panel stream."""
    if current.role.value not in {"admin", "operador"}:
        raise HTTPException(status_code=403, detail="panel role required")
    return current


def _snapshot(session: Session) -> dict:
    conversations = session.scalars(
        select(Conversation).order_by(
            Conversation.last_message_at.desc().nulls_last(), Conversation.id.desc()
        )
    ).all()
    events = session.scalars(
        select(ConversationEvent)
        .where(ConversationEvent.event.in_(ACTIVITY_EVENTS))
        .order_by(ConversationEvent.created_at, ConversationEvent.id)
    ).all()
    return {
        "conversations": [_conversation_payload(session, row) for row in conversations],
        "activity": [
            {
                "id": event.id,
                "conversation_id": event.conversation_id,
                "event": event.event,
                "cause": event.cause,
                "actor": event.actor,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }


@router.websocket("/ws")
async def panel_websocket(
    websocket: WebSocket,
    session: Session = Depends(get_db),
    current: User = Depends(realtime_user),
) -> None:
    """Send a current snapshot, then stream best-effort process-local events."""
    await websocket.accept()
    subscriber = None
    try:
        await websocket.send_json(
            {"type": "snapshot", "conversation_id": None, "data": _snapshot(session)}
        )
        subscriber = await publisher.subscribe()
        async for envelope in subscriber:
            await websocket.send_json(envelope.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
    finally:
        if subscriber is not None:
            await subscriber.close()
