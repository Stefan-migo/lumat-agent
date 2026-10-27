"""Best-effort realtime publication and conversation activity persistence."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import ConversationEvent

logger = logging.getLogger(__name__)
ACTIVITY_EVENTS = {"classified", "kb_retrieved", "kb_miss", "escalation"}
_STAGED_EVENTS_KEY = "realtime_events"


class RealtimeEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["message", "conversation", "activity", "snapshot", "notification"]
    conversation_id: int | None = None
    data: Any


def validate_activity_event(event: str) -> str:
    """Validate activity vocabulary without restricting other event writers."""
    if event not in ACTIVITY_EVENTS:
        raise ValueError(f"unsupported activity event: {event}")
    return event


def record_activity(
    session: Session,
    conversation_id: int,
    event: str,
    *,
    cause: str | None = None,
    actor: str | None = None,
) -> ConversationEvent:
    validate_activity_event(event)
    row = ConversationEvent(
        conversation_id=conversation_id, event=event, cause=cause, actor=actor
    )
    session.add(row)
    session.flush()
    stage_event(
        session,
        type="activity",
        conversation_id=conversation_id,
        data={"event": row.event, "cause": row.cause, "actor": row.actor},
    )
    return row


def activity_events(conversation_id: int) -> Select:
    """Return only activity rows used in the reconnect-safe ficha history."""
    return (
        select(ConversationEvent)
        .where(
            ConversationEvent.conversation_id == conversation_id,
            ConversationEvent.event.in_(ACTIVITY_EVENTS),
        )
        .order_by(ConversationEvent.created_at, ConversationEvent.id)
    )


def stage_event(
    session: Session,
    *,
    type: str,
    data: Any,
    conversation_id: int | None = None,
) -> RealtimeEnvelope:
    envelope = RealtimeEnvelope(type=type, conversation_id=conversation_id, data=data)
    session.info.setdefault(_STAGED_EVENTS_KEY, []).append(envelope)
    return envelope


async def _publish_all(events: list[RealtimeEnvelope]) -> None:
    for event in events:
        await publisher.publish(event)


def dispatch_staged_events(session: Session) -> None:
    """Publish events staged by a successfully committed transaction."""
    events = session.info.pop(_STAGED_EVENTS_KEY, [])
    if events:
        try:
            asyncio.run(_publish_all(events))
        except Exception:
            logger.exception("realtime publication failed after commit")


@dataclass
class Subscriber:
    queue: asyncio.Queue[RealtimeEnvelope]
    conversation_id: int | None
    _publisher: "RealtimePublisher"
    closed: bool = False

    async def close(self) -> None:
        self._publisher._remove(self)

    def __aiter__(self):
        return self

    async def __anext__(self) -> RealtimeEnvelope:
        if self.closed:
            raise StopAsyncIteration
        return await self.queue.get()


class RealtimePublisher:
    """A bounded, process-local fan-out publisher for one API process."""

    def __init__(self, *, queue_size: int = 100) -> None:
        self.queue_size = queue_size
        self._subscribers: list[Subscriber] = []

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    async def subscribe(self, *, conversation_id: int | None = None) -> Subscriber:
        subscriber = Subscriber(
            asyncio.Queue(maxsize=self.queue_size), conversation_id, self
        )
        self._subscribers.append(subscriber)
        return subscriber

    def _remove(self, subscriber: Subscriber) -> None:
        subscriber.closed = True
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)

    async def publish(self, envelope: RealtimeEnvelope) -> None:
        for subscriber in tuple(self._subscribers):
            if (
                subscriber.conversation_id is not None
                and subscriber.conversation_id != envelope.conversation_id
            ):
                continue
            try:
                subscriber.queue.put_nowait(envelope)
            except asyncio.QueueFull:
                self._remove(subscriber)


publisher = RealtimePublisher()
