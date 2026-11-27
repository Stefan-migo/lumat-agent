"""Run the production conversation brain without making a customer-visible thread.

Simulation conversations use one reserved synthetic customer, are flagged at
creation, and deliberately never stamp ``last_message_at``. Operational panel and
case reads exclude flagged rows, while the missing activity timestamp remains an
additional guard for the active inbox. The graph nodes open their own sessions and
commit, so transaction rollback cannot isolate a run.

The synthetic *customer* is deliberately shared by every run while the conversation
is fresh each time. A per-run customer would leave one fake row in the panel's
customer list per simulation; one shared row bounds that litter to a single row
whose phone identifies it. The conversation is new per run because the brain reads
its own prior turns, and a reused one would answer the second simulation with the
first one's context. Leaving the name empty is deliberate too: a name here would
feed the ``{{nombre}}`` greeting and distort what the simulation measures.

The real brain persists outbound reply rows for subsequent-turn context, but this
service never invokes channel delivery, creates a delivery/outbox request, or sets
a Meta identifier. Replies are returned only as simulation observations.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Conversation,
    ConversationEvent,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer

# Reserved: no real customer ever uses this number, so the one row a simulation
# leaves in the customer list is identifiable on sight.
RESERVED_SIMULATION_PHONE = "+56900000000"


def _event_data(event: ConversationEvent) -> dict:
    return {
        "event": event.event,
        "cause": event.cause,
        "actor": event.actor,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def _intent_of(events: list[dict]) -> str | None:
    for event in reversed(events):
        if event["event"] == "classified" and event["cause"]:
            return event["cause"].removeprefix("intent:")
        if event["event"] == "unknown_intent":
            return "unknown"
    return None


def simulate(session: Session, messages: list[str]) -> dict:
    """Run each supplied customer message through ``run_conversation`` in isolation."""
    # The simulation can run the production graph for minutes. Its own session
    # prevents its per-turn commits from committing the assistant turn's work.
    from app.db import SessionLocal

    with SessionLocal() as simulation_session:
        # The simulation is its own unit of work now: the replies it writes must be durable
        # before it returns, because closing this session would otherwise discard them.
        result = _simulate_in_session(simulation_session, messages)
        simulation_session.commit()
        return result


def _simulate_in_session(session: Session, messages: list[str]) -> dict:
    # Import lazily: registry.py is loaded while graph node imports are still
    # in progress, and importing chat.graph at module scope would form a cycle.
    from app.chat.graph import run_conversation

    phone = RESERVED_SIMULATION_PHONE
    customer = get_or_create_customer(session, phone)
    conversation = Conversation(customer_id=customer.id, wa_phone=phone, simulated=True)
    session.add(conversation)
    session.flush()
    session.commit()

    turns = []
    for text in messages:
        message = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text=text,
            status=MessageStatus.RECEIVED,
            # Deliberately no wamid: simulations have no Meta identifier.
        )
        session.add(message)
        session.commit()

        previous_event_id = session.scalar(
            select(ConversationEvent.id)
            .where(ConversationEvent.conversation_id == conversation.id)
            .order_by(ConversationEvent.id.desc())
            .limit(1)
        ) or 0
        replies = run_conversation(session, message)
        events = session.scalars(
            select(ConversationEvent)
            .where(
                ConversationEvent.conversation_id == conversation.id,
                ConversationEvent.id > previous_event_id,
            )
            .order_by(ConversationEvent.created_at, ConversationEvent.id)
        ).all()
        event_data = [_event_data(event) for event in events]
        turns.append(
            {
                "text": text,
                "replies": replies,
                "intent": _intent_of(event_data),
                "events": event_data,
            }
        )

    return {"turns": turns, "conversation_id": conversation.id, "delivered": False}
