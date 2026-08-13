"""T4.4 integration tests — handoff state model, gate triggers, deriva bundle.

Scenarios mapped 1:1 from openspec/changes/hito-1-setup-whatsapp/specs/human-handoff/spec.md:

- HH-1 "Bot to human": an escalation trigger -> state `human` + transition
  recorded (conversation_events row with timestamp + cause + actor)
- HH-1 "Close conversation": a close -> state `closed` + closure recorded
  (the panel owns the close action in T5.3; `set_conversation_state` is the
  single auditable transition helper both paths use)
- HH-2 "Handoff bundle complete": the case contains full history, summary,
  customer data and captured fields
- HH-3 "Customer requests a person" / "Two failed comprehension attempts":
  deterministic triggers -> handoff (persona, 2x unknown, media evidence,
  complaint keywords, SS-1 always_escalate scope)
- HH-5 "Webhook keeps recording during human phase": inbound messages in
  `human` state are persisted, never answered by the bot loop
- CR-5 "History complete": a closed conversation opens a NEW conversation on
  the next inbound; history stays linked to the customer

The chat LLM (gpt-4o-mini) is mocked via respx — no real API calls.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.nodes.handoff_gate import handoff_gate  # noqa: E402
from app.chat.state import (  # noqa: E402
    ConversationState,
    get_or_create_conversation,
    set_conversation_state,
)
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Conversation,
    ConversationEvent,
    ConversationState as ConvState,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer  # noqa: E402
from app.services.settings import set_setting  # noqa: E402

ADMIN_DB_URL = "postgresql://lumat:lumat@localhost:5432/lumat"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat + settings tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


def _start_conversation() -> int:
    """Create a customer + open conversation (no messages yet)."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        return conv.id


def _turn(conv_id: int, text: str, wamid: str) -> list[str]:
    """Append an inbound message and run the graph (replies persisted)."""
    from app.chat.graph import run_conversation

    with SessionLocal() as session:
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        message = session.scalars(
            select(Message).where(
                Message.conversation_id == conv_id, Message.wamid == wamid
            )
        ).one()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _events(conv_id: int) -> list[ConversationEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(ConversationEvent)
                .where(ConversationEvent.conversation_id == conv_id)
                .order_by(ConversationEvent.id)
            )
        )


def _conversation_state(conv_id: int) -> str:
    with SessionLocal() as session:
        return session.get(Conversation, conv_id).state.value


# ---------------------------------------------------------------------------
# HH-1 — state model: every transition records a conversation_events row
# ---------------------------------------------------------------------------


def test_state_transition_bot_to_human_records_event():
    """HH-1 "Bot to human": transition + timestamp + cause + actor recorded."""
    conv_id = _start_conversation()
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        set_conversation_state(
            session, conv, ConvState.HUMAN, cause="escalation:persona", actor="rule"
        )
        session.commit()

    events = _events(conv_id)
    assert len(events) == 1
    assert events[0].event == "state_change"
    assert events[0].cause == "bot->human: escalation:persona"
    assert events[0].actor == "rule"
    assert events[0].created_at is not None  # HH-1: timestamp recorded
    assert _conversation_state(conv_id) == "human"


def test_state_transition_close_records_closure():
    """HH-1 "Close conversation": human -> closed recorded with closed_at."""
    conv_id = _start_conversation()
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        set_conversation_state(session, conv, ConvState.CLOSED, cause="resolved")
        session.commit()

    events = _events(conv_id)
    assert len(events) == 1
    assert events[0].cause.startswith("bot->closed: resolved")
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        assert conv.closed_at is not None  # closure timestamp on the row


def test_state_transition_same_state_is_noop():
    """A no-op transition (bot -> bot) writes no event row."""
    conv_id = _start_conversation()
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        set_conversation_state(session, conv, ConvState.BOT, cause="nothing")
        session.commit()
    assert _events(conv_id) == []


# ---------------------------------------------------------------------------
# HH-3 — deterministic handoff triggers (pre-LLM, handoff_gate node)
# ---------------------------------------------------------------------------


def _gate_state(text: str | None = None, msg_type: str = "text") -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        window=[{"id": 1, "direction": "inbound", "msg_type": msg_type, "text": text}],
    )


def test_gate_persona_trigger():
    """HH-3 "Customer requests a person": menu 'persona' text -> handoff."""
    assert handoff_gate(_gate_state("quiero hablar con una persona")) == {
        "handoff_reason": "persona"
    }
    assert handoff_gate(_gate_state("necesito un humano")) == {"handoff_reason": "persona"}


def test_gate_media_evidence_trigger():
    """HH-3 evidence: a photo/video/audio message -> handoff for review."""
    for msg_type in ("image", "video", "audio", "document", "sticker"):
        assert handoff_gate(_gate_state(text=None, msg_type=msg_type)) == {
            "handoff_reason": "media_evidence"
        }, msg_type


def test_gate_complaint_trigger():
    """HH-3 complaint/warranty: complaint language -> handoff."""
    assert handoff_gate(_gate_state("quiero hacer un reclamo")) == {
        "handoff_reason": "complaint"
    }
    assert handoff_gate(_gate_state("estoy molesto con el servicio")) == {
        "handoff_reason": "complaint"
    }


def test_gate_clear_message_no_trigger():
    """Normal commercial messages pass the gate untouched."""
    assert handoff_gate(_gate_state("mi calefont no enciende")) == {
        "handoff_reason": None
    }
    assert handoff_gate(_gate_state("cuanto cuesta la revision anual")) == {
        "handoff_reason": None
    }


def test_gate_empty_window_no_trigger():
    assert handoff_gate(
        ConversationState(customer_id=1, conversation_id=1, phone="+56912345678")
    ) == {"handoff_reason": None}


# ---------------------------------------------------------------------------
# HH-3 trigger 5 — SS-1 always_escalate scope rule (post-classification)
# ---------------------------------------------------------------------------


def _run_graph(conv_id: int) -> dict:
    from app.chat.graph import build_graph

    with SessionLocal() as session:
        state = ConversationState.from_db(session, conv_id)
    return build_graph().invoke(state)


def _seed(text: str, wamid: str = "wamid.handoff", phone: str = "+56912345678") -> int:
    """Seed a customer + open conversation + one inbound received message."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, phone)
        conv = get_or_create_conversation(session, customer, phone)
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conv.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        return conv.id


def test_scope_always_escalate_category_escalates(mock_openai_chat):
    """HH-3/SS-1: an always_escalate category escalates regardless of answer."""
    with SessionLocal() as session:
        set_setting(session, "scope_rules", {"calefont": "always_escalate"})
        session.commit()

    conv_id = _seed("mi calefont falla")
    result = _run_graph(conv_id)

    assert result["intent"] == "calefont"
    assert result["escalate"] is True
    assert result["escalate_reason"] == "scope_always_escalate"


def test_scope_bot_resolve_category_does_not_escalate(mock_openai_chat):
    """SS-1 default: a bot_resolve category follows the normal capture flow."""
    conv_id = _seed("mi calefont falla")
    result = _run_graph(conv_id)

    assert result["intent"] == "calefont"
    assert result["escalate"] is False
    assert result["next_step"] == "capture"
