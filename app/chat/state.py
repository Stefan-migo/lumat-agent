"""Conversation state — rebuilt from the DB per message (design D2).

The conversation graph runs without a LangGraph checkpointer: every message
reconstructs the state from Postgres (messages table is the source of truth,
D2). `ConversationState` doubles as the LangGraph state schema (dataclass),
so nodes mutate/return field updates and `from_db` seeds the initial dict.

CM-1: on first contact the bot sends an open greeting; on repeat
the flow resumes from the stored state (window/turn/captured), never from
scratch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from operator import add
from typing import Annotated

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Conversation,
    ConversationEvent,
    ConversationState as ConvState,
    Customer,
    Message,
)
from app.services.customers import get_or_create_customer
from app.services.memory import load_customer_context, close_conversation
from app.services.realtime import stage_event
from app.services.settings import MESSAGE_DEFAULTS

# Context window: last N messages of the conversation (design Data Flow).
WINDOW_SIZE = 10

# Standard replies (SS-5 settings source).
GREETING_HEADER = MESSAGE_DEFAULTS["greeting"]


def greeting(header: str = GREETING_HEADER) -> str:
    """The CM-1 first-contact open greeting."""
    return header


def get_or_create_conversation(session: Session, customer: Customer, phone_e164: str) -> Conversation:
    """Return the open conversation for a customer; create it if none is open.

    Closed conversations are never reopened: a new inbound after close opens a
    new conversation on the same customer (CR-5), keeping history linked.
    """
    conversation = session.scalar(
        select(Conversation)
        .where(
            Conversation.customer_id == customer.id,
            Conversation.state != ConvState.CLOSED,
        )
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    if conversation is None:
        conversation = Conversation(customer_id=customer.id, wa_phone=phone_e164)
        session.add(conversation)
        session.flush()
    return conversation


def set_conversation_state(
    session: Session,
    conversation: Conversation,
    new_state: ConvState,
    *,
    cause: str,
    actor: str = "rule",
) -> Conversation:
    """Transition a conversation's bot/human/closed state (HH-1).

    Every transition writes one `state_change` row on `conversation_events`
    with timestamp + cause + actor (system | bot | rule) — the operador-
    visible transition log (audit_log stays admin-only, SH-5). A close also
    stamps `closed_at`. A no-op transition writes nothing.
    """
    if conversation.state == new_state:
        return conversation
    before = conversation.state.value
    conversation.state = new_state
    if new_state == ConvState.CLOSED:
        conversation.closed_at = datetime.now(timezone.utc)
        # MEM-4/CM-9: fire the close handler — upsert the customer_memo
        # (reusing conversation.summary VERBATIM) + persist observations.
        # The summary is consumed, never rewritten (CM-9 boundary).
        close_conversation(
            session,
            conversation,
            acta_text=conversation.summary or "",
        )
    session.add(
        ConversationEvent(
            conversation_id=conversation.id,
            event="state_change",
            cause=f"{before}->{new_state.value}: {cause}",
            actor=actor,
        )
    )
    session.flush()
    stage_event(
        session,
        type="conversation",
        conversation_id=conversation.id,
        data={
            "conversation_id": conversation.id,
            "from_state": before,
            "state": new_state.value,
            "cause": cause,
            "actor": actor,
        },
    )
    return conversation


@dataclass
class ConversationState:
    """Per-conversation state (design Data Model: state.py).

    `case` holds the case classification dict {service, priority, status};
    `captured` holds the progressive capture fields (CM-2); `window` is the
    last WINDOW_SIZE messages; `replies` accumulates bot replies produced by
    the graph run (persisted/sent by run_conversation).
    """

    customer_id: int
    conversation_id: int
    phone: str
    turn: int = 0
    intent: str | None = None
    case: dict = field(default_factory=dict)
    captured: dict = field(default_factory=dict)
    summary: str | None = None
    emergency: bool = False
    # set by the emergency_gate: "strong" | "weak" | None (EM-1/EM-5, T4.2)
    emergency_hit: str | None = None
    # set by the handoff_gate: deterministic pre-LLM trigger (HH-3, T4.4)
    handoff_reason: str | None = None
    # set by the cost_gate (SS-3, T4.5): "normal" | "conservative" | "blocked".
    # Computed fresh from the DB sums every run — never persisted (D2).
    cost_mode: str = "normal"
    escalate: bool = False
    escalate_reason: str | None = None
    unknown_count: int = 0
    next_step: str = "receive"
    # H2 orchestrator (design.md line 47): which sub-agent the orchestrator
    # dispatched to for this turn (None when no sub-graph runs).
    active_sub_agent: str | None = None
    # AO-8: bounded KB retry counter consumed by the research_triage sub-graph
    # (≤1 retry, then handoff) — never grows unbounded in a single turn.
    triage_retry: int = 0
    window: list[dict] = field(default_factory=list)
    # accumulator: nodes append their replies (reducer merges, last-write-wins off)
    replies: Annotated[list, add] = field(default_factory=list)
    # CM-7: the customer's persistent memory context, loaded from the DB for
    # this message (empty string on first contact -> reply never blocked).
    memory_context: str = ""

    @classmethod
    def from_db(cls, session: Session, conversation_id: int) -> "ConversationState":
        """Rebuild the state from the DB for one message (D2, no checkpointer)."""
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            raise ValueError(f"conversation {conversation_id} not found")

        last_messages = session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(WINDOW_SIZE)
        ).all()
        window = [
            {
                "id": m.id,
                "direction": m.direction.value,
                "msg_type": m.msg_type.value,
                "text": m.text,
                "created_at": m.created_at,
            }
            for m in reversed(last_messages)
        ]
        turn = session.scalar(
            select(func.count(Message.id)).where(
                Message.conversation_id == conversation_id,
                Message.direction == "inbound",
            )
        ) or 0
        # HH-3: unknown-intent attempts persist as conversation_events so the
        # counter survives the per-message state rebuild (D2).
        unknown_count = session.scalar(
            select(func.count(ConversationEvent.id)).where(
                ConversationEvent.conversation_id == conversation_id,
                ConversationEvent.event == "unknown_intent",
            )
        ) or 0
        return cls(
            customer_id=conversation.customer_id,
            conversation_id=conversation_id,
            phone=conversation.wa_phone,
            turn=int(turn),
            unknown_count=int(unknown_count),
            captured=dict(conversation.captured_data or {}),
            window=window,
            memory_context=load_customer_context(session, conversation.customer_id),
        )
