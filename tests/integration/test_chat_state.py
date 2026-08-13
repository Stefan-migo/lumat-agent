"""T3.2 integration tests — conversation state + graph scaffold + receive node.

Scenarios mapped 1:1 from openspec/specs/conversation-manager/spec.md:

- CM-1 "First contact": bot greets, identifies itself, presents the 8-category
  menu (Calefont, Caldera, Calefacción, Solicitar visita, Valores,
  Postventa/Garantía, Emergencia, Hablar con una persona)
- CM-1 "Repeat contact on same conversation": flow resumes from the stored
  conversation state (rebuilt from the DB per message — design D2, no
  LangGraph checkpointer), not from scratch

Plus design D2 state-rebuild specifics: window = last 10 messages, turn count,
closed conversation -> new conversation (CR-5). Runs against the migrated
pgvector test DB.
"""

import psycopg
import pytest
from sqlalchemy import func, select

from app.chat.state import MENU_CATEGORIES, WINDOW_SIZE, ConversationState, get_or_create_conversation  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Conversation,
    ConversationState as ConvState,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer  # noqa: E402

ADMIN_DB_URL = "postgresql://lumat:lumat@localhost:5432/lumat"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat-related tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


def _seed(message_texts: list[str]) -> int:
    """Seed a customer + open conversation + inbound received messages."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        for i, text in enumerate(message_texts):
            session.add(
                Message(
                    wamid=f"wamid.chat{i}",
                    conversation_id=conv.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text=text,
                    status=MessageStatus.RECEIVED,
                )
            )
        session.commit()
        return conv.id


def _outbound_texts(conversation_id: int) -> list[str]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.direction == MessageDirection.OUTBOUND,
            )
            .order_by(Message.id)
        ).all()
        return [r.text for r in rows]


def _inbound_count() -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count(Message.id)).where(
                Message.direction == MessageDirection.INBOUND
            )
        )


# ---------------------------------------------------------------------------
# CM-1 — first contact: greeting + 8-category menu
# ---------------------------------------------------------------------------


def test_cm1_first_contact_greeting_with_menu(mock_openai_chat):
    conv_id = _seed(["hola"])
    from app.chat.graph import run_conversation

    with SessionLocal() as session:
        message = session.scalars(
            select(Message).where(Message.conversation_id == conv_id)
        ).one()
        replies = run_conversation(session, message)
        session.commit()

    assert len(replies) >= 1
    greeting = replies[0]  # greeting is always the first reply on first contact
    assert "asistente virtual" in greeting.lower()  # identifies itself
    assert "Lumat" in greeting
    for category in MENU_CATEGORIES:  # all 8 categories present
        assert category in greeting


def test_cm1_menu_has_exactly_8_categories():
    assert MENU_CATEGORIES == [
        "Calefont",
        "Caldera",
        "Calefacción",
        "Solicitar visita",
        "Valores",
        "Postventa/Garantía",
        "Emergencia",
        "Hablar con una persona",
    ]


# ---------------------------------------------------------------------------
# CM-1 — repeat contact: resume from stored state, not from scratch
# ---------------------------------------------------------------------------


def test_cm1_repeat_contact_resumes_not_from_scratch(mock_openai_chat):
    conv_id = _seed(["hola"])
    from app.chat.graph import run_conversation

    with SessionLocal() as session:
        first = session.scalars(
            select(Message).where(Message.conversation_id == conv_id)
        ).one()
        run_conversation(session, first)
        # second inbound message arrives in the same conversation
        session.add(
            Message(
                wamid="wamid.chat2",
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="quiero agendar una visita",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        second = session.scalars(
            select(Message)
            .where(Message.conversation_id == conv_id, Message.wamid == "wamid.chat2")
        ).one()
        replies = run_conversation(session, second)
        session.commit()

    # resumed: the second reply is NOT a fresh greeting+menu (it's the first
    # capture question for the visita intent)
    assert len(replies) == 1
    assert "asistente virtual" not in replies[0].lower()
    assert MENU_CATEGORIES[0] not in replies[0]


# ---------------------------------------------------------------------------
# D2 — state rebuilt from the DB per message (no checkpointer)
# ---------------------------------------------------------------------------


def test_d2_state_rebuilt_from_db():
    conv_id = _seed(["primero", "segundo", "tercero"])
    with SessionLocal() as session:
        state = ConversationState.from_db(session, conv_id)

    assert state.conversation_id == conv_id
    assert state.phone == "+56912345678"
    assert state.turn == 3
    assert [m["text"] for m in state.window] == ["primero", "segundo", "tercero"]
    assert state.captured == {}
    assert state.intent is None
    assert state.emergency is False
    assert state.escalate is False


def test_d2_window_capped_at_10():
    conv_id = _seed([f"msg-{i}" for i in range(12)])
    with SessionLocal() as session:
        state = ConversationState.from_db(session, conv_id)

    assert len(state.window) == WINDOW_SIZE == 10
    # the LAST 10 messages survive (context window, not the whole history)
    assert state.window[0]["text"] == "msg-2"
    assert state.window[-1]["text"] == "msg-11"


def test_d2_run_conversation_persists_outbound_replies(mock_openai_chat):
    conv_id = _seed(["hola"])
    from app.chat.graph import run_conversation

    with SessionLocal() as session:
        message = session.scalars(
            select(Message).where(Message.conversation_id == conv_id)
        ).one()
        run_conversation(session, message)
        session.commit()

    assert _inbound_count() == 1  # original inbound untouched
    replies = _outbound_texts(conv_id)
    assert len(replies) == 1  # CM-1: greeting + menu only, no turn-1 clarification
    assert "asistente virtual" in replies[0].lower()


def test_d2_next_message_sees_previous_replies_in_window(mock_openai_chat):
    """The outbound reply from turn 1 is part of turn 2's context (D2)."""
    conv_id = _seed(["hola"])
    from app.chat.graph import run_conversation

    with SessionLocal() as session:
        first = session.scalars(
            select(Message).where(Message.conversation_id == conv_id)
        ).one()
        run_conversation(session, first)
        session.add(
            Message(
                wamid="wamid.chat3",
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="calefont",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        state = ConversationState.from_db(session, conv_id)

    assert state.turn == 2
    texts = [m["text"] for m in state.window]
    assert texts[0] == "hola"  # inbound
    assert "asistente virtual" in texts[1].lower()  # bot greeting reply in context
    # CM-1: turn 1 produces ONLY the greeting — no clarification after the menu
    assert "entend" not in texts[1].lower()
    assert texts[2] == "calefont"  # current inbound


# ---------------------------------------------------------------------------
# CR-5 — closed conversation opens a new one on next inbound
# ---------------------------------------------------------------------------


def test_cr5_closed_conversation_opens_new():
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        first = get_or_create_conversation(session, customer, "+56912345678")
        first.state = ConvState.CLOSED
        session.commit()
        second = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        assert second.id != first.id
        assert second.state == ConvState.BOT
