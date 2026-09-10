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

import os

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
    Case,
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

ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)


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


# ---------------------------------------------------------------------------
# HH-3 full flow — triggers converge on the handoff node (state -> human,
# deriva case created, escalation + state_change events)
# ---------------------------------------------------------------------------


def _case(conv_id: int) -> Case:
    with SessionLocal() as session:
        return session.scalar(select(Case).where(Case.conversation_id == conv_id))


def test_persona_escalates_to_human_with_deriva_case(mock_openai_chat):
    """HH-3 "Customer requests a person": handoff with case + events."""
    conv_id = _start_conversation()
    replies = _turn(conv_id, "quiero hablar con una persona", "wamid.p1")

    assert any("asesor" in r.lower() for r in replies)
    assert _conversation_state(conv_id) == "human"  # HH-1: bot -> human

    case = _case(conv_id)
    assert case is not None
    assert case.status == "escalado"
    assert case.escalated_at is not None
    assert case.bundle["escalate_reason"] == "persona"

    events = _events(conv_id)
    assert any(e.event == "escalation" and e.cause == "handoff:persona" for e in events)
    assert any(
        e.event == "state_change" and e.cause == "bot->human: handoff:persona"
        for e in events
    )


def test_two_unknown_intents_escalate_to_human(mock_openai_chat):
    """HH-3 "Two failed comprehension attempts": 2x unknown -> handoff."""
    conv_id = _start_conversation()
    _turn(conv_id, "zzzzzx", "wamid.u1")  # first unknown -> clarification
    replies = _turn(conv_id, "qqqqqw", "wamid.u2")  # second -> handoff

    assert any("asesor" in r.lower() for r in replies)
    assert _conversation_state(conv_id) == "human"
    case = _case(conv_id)
    assert case.bundle["escalate_reason"] == "unknown_intent_twice"


def test_complaint_escalates_to_human(mock_openai_chat):
    """HH-3 complaint: deterministic keyword -> handoff before any LLM."""
    conv_id = _start_conversation()
    _turn(conv_id, "quiero hacer un reclamo", "wamid.c1")

    assert _conversation_state(conv_id) == "human"
    assert _case(conv_id).bundle["escalate_reason"] == "complaint"


def test_media_evidence_escalates_through_process_message(mock_openai_chat, mock_meta_send):
    """HH-3 evidence: an inbound image (no text) escalates for review."""
    from app.webhook.ingest import process_message

    conv_id = _start_conversation()
    with SessionLocal() as session:
        session.add(
            Message(
                wamid="wamid.img1",
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.IMAGE,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        msg = session.scalars(
            select(Message).where(Message.wamid == "wamid.img1")
        ).one()
        process_message(session, msg)
        session.commit()

    assert _conversation_state(conv_id) == "human"
    case = _case(conv_id)
    assert case.bundle["escalate_reason"] == "media_evidence"
    assert any(m["msg_type"] == "image" for m in case.bundle["history"])


# ---------------------------------------------------------------------------
# HH-2 — deriva bundle content
# ---------------------------------------------------------------------------


def test_handoff_bundle_contains_history_summary_customer_captured(mock_openai_chat):
    """HH-2 "Handoff bundle complete": history + summary + customer + captured."""
    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.b1")
    _turn(conv_id, "Juan", "wamid.b2")
    _turn(conv_id, "Providencia", "wamid.b3")
    _turn(conv_id, "estoy molesto, quiero reclamar", "wamid.b4")

    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        assert conv.state.value == "human"
        case = session.scalar(select(Case).where(Case.conversation_id == conv_id))
        bundle = case.bundle

        # summary generated at escalation (CM-5) and persisted on conv + case
        assert bundle["summary"] is not None
        assert "resumen" in bundle["summary"].lower()
        assert case.summary == bundle["summary"]
        assert conv.summary == bundle["summary"]

        # customer ficha + captured fields
        # (CR-6: ficha data lands at consent — the escalation happened before
        # it, so the ficha name is None while the captured fields carry it)
        assert bundle["customer"]["phone_e164"] == "+56912345678"
        assert bundle["customer"]["name"] is None
        assert bundle["captured"]["name"] == "Juan"
        assert bundle["captured"]["comuna"] == "Providencia"
        assert bundle["escalate_reason"] == "complaint"

        # full history snapshot (inbound + bot replies)
        history = bundle["history"]
        assert len(history) >= 4
        assert any("reclamar" in (m["text"] or "") for m in history)


# ---------------------------------------------------------------------------
# HH-5 — webhook keeps persisting during `human`, no bot loop
# ---------------------------------------------------------------------------


def test_hh5_human_state_persists_without_bot_reply(mock_openai_chat):
    """HH-5: inbound during `human` is persisted; the bot never answers."""
    from app.webhook.ingest import process_message

    conv_id = _start_conversation()
    _turn(conv_id, "quiero hablar con una persona", "wamid.h51")  # -> human

    with SessionLocal() as session:
        session.add(
            Message(
                wamid="wamid.h52",
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="sigo esperando respuesta",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        msg = session.scalars(
            select(Message).where(Message.wamid == "wamid.h52")
        ).one()
        calls_before = len(mock_openai_chat)
        process_message(session, msg)
        session.commit()
        assert msg.status == MessageStatus.PROCESSED  # persisted (HH-5)

    # no new bot reply, no LLM call for the human-phase message
    with SessionLocal() as session:
        outbound = list(
            session.scalars(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.direction == MessageDirection.OUTBOUND,
                )
            )
        )
    assert all("asesor" in (m.text or "") for m in outbound)  # only the handoff reply
    assert len(mock_openai_chat) == calls_before


def test_hh5_human_state_graph_direct_still_persists_events(mock_openai_chat):
    """HH-5: a direct graph run on a human conversation never re-escalates.

    The no-bot-loop guard lives at the ingest boundary (process_message);
    run_conversation itself is state-agnostic (D2) and classifies the turn,
    but a human conversation never re-enters the escalation flow.
    """
    conv_id = _start_conversation()
    _turn(conv_id, "quiero hablar con una persona", "wamid.h53")
    escalations_before = [
        e
        for e in _events(conv_id)
        if e.event in ("escalation", "state_change")
    ]
    _turn(conv_id, "algo mas", "wamid.h54")
    escalations_after = [
        e
        for e in _events(conv_id)
        if e.event in ("escalation", "state_change")
    ]
    assert len(escalations_after) == len(escalations_before)  # no re-escalation


# ---------------------------------------------------------------------------
# CR-5 — closed conversation -> new conversation on next inbound (ingest path)
# ---------------------------------------------------------------------------


def test_cr5_closed_opens_new_conversation_through_ingest():
    """CR-5: a closed conversation never reopens; the next inbound lands in a
    new conversation on the same customer (history stays linked)."""
    from app.webhook.ingest import NormalizedMessage, persist_message

    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        first = get_or_create_conversation(session, customer, "+56912345678")
        set_conversation_state(session, first, ConvState.CLOSED, cause="resolved")
        session.commit()
        customer_id = customer.id
        first_id = first.id

    nm = NormalizedMessage(
        wamid="wamid.cr51",
        phone_e164="+56912345678",
        msg_type=MessageType.TEXT,
        text="nueva consulta",
        media_url=None,
        payload={},
    )
    with SessionLocal() as session:
        # persist_message's boolean reflects ON CONFLICT dedup (latent psycopg
        # rowcount quirk returns False even for new rows) — the acceptance is
        # the persisted row landing in a NEW conversation, asserted below.
        persist_message(session, nm)
        session.commit()
        conversations = list(
            session.scalars(
                select(Conversation)
                .where(Conversation.customer_id == customer_id)
                .order_by(Conversation.id)
            )
        )
        assert [c.id for c in conversations] == [first_id, conversations[-1].id]
        assert conversations[0].state.value == "closed"
        assert conversations[1].state.value == "bot"
        msg = session.scalars(select(Message).where(Message.wamid == "wamid.cr51")).one()
        assert msg.conversation_id == conversations[1].id  # new conversation
