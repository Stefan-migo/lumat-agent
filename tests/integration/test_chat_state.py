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
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select

from app.chat.state import WINDOW_SIZE, ConversationState, get_or_create_conversation  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Appointment,
    AppointmentStatus,
    Case,
    Conversation,
    ConversationState as ConvState,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    User,
    UserRole,
)
from app.services.customers import get_or_create_customer  # noqa: E402
from app.services import memory as memory_service  # noqa: E402
from app.models import MemoryType  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat + memory tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE memories, memory_relations, memory_observations, "
            "audit_log, conversation_events, cases, messages, "
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
# CM-1 — first contact: open greeting
# ---------------------------------------------------------------------------


def test_cm1_first_contact_open_greeting_is_only_reply(mock_openai_chat):
    conv_id = _seed(["hola"])
    from app.chat.graph import run_conversation

    with SessionLocal() as session:
        message = session.scalars(
            select(Message).where(Message.conversation_id == conv_id)
        ).one()
        replies = run_conversation(session, message)
        session.commit()

    assert replies == ["Hola, soy el asistente virtual de Lumat. ¿Cómo estás?\n¿En qué te puedo ayudar?"]
    assert "Elige una opción" not in replies[0]
    assert "1." not in replies[0]


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

    # resumed: the second reply is NOT a fresh greeting (it's the first
    # capture question for the visita intent)
    assert len(replies) == 1
    assert "asistente virtual" not in replies[0].lower()
    assert "Elige una opción" not in replies[0]


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
    # S2 (CM-7): no stored memory on first contact -> empty context, flow unblocked
    assert state.memory_context == ""


def test_d2_state_carries_latest_booked_appointment():
    conv_id = _seed(["hola"])
    with SessionLocal() as session:
        conversation = session.get(Conversation, conv_id)
        case = Case(
            conversation_id=conv_id,
            customer_id=conversation.customer_id,
            service="Visita técnica",
        )
        technician = User(username=f"booking-state-tech-{uuid4().hex}", password_hash="test", role=UserRole.TECNICO)
        session.add_all([case, technician])
        session.flush()
        starts_at = datetime(2030, 5, 6, 15, 30, tzinfo=timezone.utc)
        appointment = Appointment(
            service="Visita técnica",
            customer_id=conversation.customer_id,
            case_id=case.id,
            technician_id=technician.id,
            local_start=datetime(2030, 5, 6, 15, 30),
            timezone="UTC",
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            duration_minutes=60,
            status=AppointmentStatus.BOOKED,
        )
        session.add(appointment)
        session.commit()
        state_with_booking = ConversationState.from_db(session, conv_id)

        appointment.status = AppointmentStatus.CANCELLED
        session.commit()
        state_without_booking = ConversationState.from_db(session, conv_id)

    assert state_with_booking.booking == {
        "service": "Visita técnica",
        "label": "06/05/2030 a las 15:30",
        "status": "booked",
    }
    assert state_without_booking.booking is None


def test_d2_window_capped_at_10():
    conv_id = _seed([f"msg-{i}" for i in range(12)])
    with SessionLocal() as session:
        state = ConversationState.from_db(session, conv_id)

    assert len(state.window) == WINDOW_SIZE == 10
    # the LAST 10 messages survive (context window, not the whole history)
    assert state.window[0]["text"] == "msg-2"
    assert state.window[-1]["text"] == "msg-11"


def test_d2_window_can_be_anchored_to_message_id():
    conv_id = _seed(["primero", "segundo", "tercero"])
    with SessionLocal() as session:
        through_message_id = session.scalar(
            select(Message.id)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.id)
            .offset(1)
            .limit(1)
        )
        state = ConversationState.from_db(
            session, conv_id, through_message_id=through_message_id
        )

    assert state.window[-1]["id"] == through_message_id
    assert [message["text"] for message in state.window] == ["primero", "segundo"]


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
    assert len(replies) == 1  # CM-1: greeting only, no turn-1 clarification
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
    # CM-1: turn 1 produces ONLY the greeting — no clarification
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


# ---------------------------------------------------------------------------
# S2 (CM-7) — memory context loaded into the rebuilt state
# ---------------------------------------------------------------------------


def test_s2_from_db_carries_memory_context(fake_embedder):
    """Returning customer: customer memories are loaded into memory_context.

    Scenario: Context injected (CM-7).
    """
    conv_id = _seed(["hola"])
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        memory_service.upsert(
            session,
            scope="customer",
            entity_id=str(conv.customer_id),
            topic_key="customer_memo",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="customer_memo",
            contenido="Cliente prefiere atencion en la tarde.",
        )
        session.commit()
        state = ConversationState.from_db(session, conv_id)

    assert state.memory_context
    assert "tarde" in state.memory_context


def test_s2_memory_context_marks_stale_snapshots_only(fake_embedder):
    conv_id = _seed(["hola"])
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        stale = memory_service.upsert(
            session,
            scope="customer",
            entity_id=str(conv.customer_id),
            topic_key="session",
            tipo=MemoryType.SESSION,
            titulo="session",
            contenido="stale session content",
        )
        memory_service.upsert(
            session,
            scope="customer",
            entity_id=str(conv.customer_id),
            topic_key="fresh_summary",
            tipo=MemoryType.SUMMARY,
            titulo="fresh summary",
            contenido="fresh summary content",
        )
        memory_service.upsert(
            session,
            scope="customer",
            entity_id=str(conv.customer_id),
            topic_key="customer_memo",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="customer memo",
            contenido="permanent customer content",
        )
        session.commit()
        stale.review_after = datetime.now(timezone.utc) - timedelta(days=1)
        session.commit()
        state = ConversationState.from_db(session, conv_id)

    assert "session (stale since " in state.memory_context
    assert "fresh summary (stale since" not in state.memory_context
    assert "customer memo (stale since" not in state.memory_context
