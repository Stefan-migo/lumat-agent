"""The human boundary lives in the brain, not only in the webhook.

Why this exists
---------------
`app/webhook/ingest.py:660` already refuses to answer a conversation a human or a
closure owns (HH-5). That guard protects exactly one caller: the webhook. The
brain itself — `run_conversation` — stayed state-agnostic, so every other caller
(`scripts/chat_harness.py:120`, `scripts/conv_eval.py`, `scripts/kb_fidelity.py`)
kept running turns production never executes. The conversation evaluation
measured «¿Qué equipo es? Si sabes la marca y el modelo, mejor» on a turn that the
WhatsApp channel discards, and reported it as a bot behaviour.

The owner decided (L4/L5 in `odd/tasks/emergencia-turno-siguiente.md`) that the
rule belongs to the brain, and that a strong emergency beats it: the safety
protocol is delivered even in a human-owned conversation, because the alternative
is a customer reporting a gas leak and reading nothing.

These tests pin both halves over the real seam: `run_conversation`.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.state import get_or_create_conversation, set_conversation_state
from app.db import SessionLocal
from app.models import (
    Case,
    Conversation,
    ConversationEvent,
    ConversationState as ConvState,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture
def no_emergency_notification(monkeypatch):
    """Keep the emergency notification offline; it is owned by its own suite."""
    from app.chat.nodes import emergency as emergency_node

    calls: list = []
    monkeypatch.setattr(
        emergency_node,
        "send_emergency_notification",
        lambda *args, **kwargs: calls.append(args),
    )
    return calls


def _conversation(state: ConvState | None = None) -> int:
    """Create a customer and one conversation, optionally already owned."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conversation = get_or_create_conversation(session, customer, "+56912345678")
        if state is not None:
            set_conversation_state(
                session, conversation, state, cause="test_setup", actor="rule"
            )
        session.commit()
        return conversation.id


def _turn(conv_id: int, text: str, wamid: str) -> list[str]:
    """Persist one inbound message and run the brain over it."""
    with SessionLocal() as session:
        message = Message(
            wamid=wamid,
            conversation_id=conv_id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text=text,
            status=MessageStatus.RECEIVED,
        )
        session.add(message)
        session.commit()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _outbound(conv_id: int) -> list[str]:
    with SessionLocal() as session:
        return [
            message.text
            for message in session.scalars(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.direction == MessageDirection.OUTBOUND,
                )
            )
        ]


def _turn_count(conv_id: int) -> int:
    with SessionLocal() as session:
        return session.get(Conversation, conv_id).turn_count


def _events(conv_id: int) -> list[ConversationEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(ConversationEvent).where(
                    ConversationEvent.conversation_id == conv_id
                )
            )
        )


# S7 — a turn the human owns produces no answer at all.
def test_human_conversation_is_not_answered(mock_openai_chat):
    conv_id = _conversation(ConvState.HUMAN)
    calls_before = len(mock_openai_chat)

    replies = _turn(conv_id, "sigo esperando respuesta", "wamid.own1")

    assert replies == []
    assert _outbound(conv_id) == []
    # An unanswered turn is not a turn: `state.turn` means "turns so far".
    assert _turn_count(conv_id) == 0
    # No LLM ran, and no node wrote an event describing a conversation that did
    # not happen (the setup transition is the only one).
    assert len(mock_openai_chat) == calls_before
    assert [event.event for event in _events(conv_id)] == ["state_change"]


# S7 — a closed conversation is silent too.
def test_closed_conversation_is_not_answered(mock_openai_chat):
    conv_id = _conversation(ConvState.CLOSED)
    calls_before = len(mock_openai_chat)

    replies = _turn(conv_id, "hola de nuevo", "wamid.own2")

    assert replies == []
    assert _outbound(conv_id) == []
    assert _turn_count(conv_id) == 0
    assert len(mock_openai_chat) == calls_before


# S8 — the safety protocol still goes out: the emergency wins over the boundary.
def test_strong_emergency_answers_inside_a_human_conversation(
    mock_openai_chat, no_emergency_notification
):
    conv_id = _conversation(ConvState.HUMAN)
    calls_before = len(mock_openai_chat)

    replies = _turn(
        conv_id, "Fuga de gas en las cañerías que van hacia los hornos", "wamid.own3"
    )

    assert len(replies) == 3  # safety instructions + contacts + notified
    assert "INSTRUCCIONES DE SEGURIDAD" in replies[0]
    assert "Bomberos 132" in replies[1]
    assert "técnico" in replies[2].lower()
    # Only the protocol: no capture question, and no LLM on the emergency path.
    assert not any("¿Qué equipo es?" in reply for reply in replies)
    assert len(mock_openai_chat) == calls_before
    assert len(no_emergency_notification) == 1
    with SessionLocal() as session:
        case = session.scalars(
            select(Case).where(Case.conversation_id == conv_id)
        ).one()
        conversation = session.get(Conversation, conv_id)
    assert case.emergency is True
    assert conversation.state == ConvState.HUMAN
