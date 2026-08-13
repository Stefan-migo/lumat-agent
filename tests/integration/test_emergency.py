"""T4.2 integration tests — emergency engine (service) + emergency nodes.

Scenarios mapped 1:1 from openspec/changes/hito-1-setup-whatsapp/specs/emergency-detection/spec.md:

- EM-1 "Emergency keyword detected": every SS-2 default keyword + accented
  variants -> strong hit (deterministic, before any LLM)
- EM-1 "Keyword configured": a settings change is picked up per run
- EM-2 "Interrupt mid-capture": strong hit abandons the capture sub-flow
- EM-3 "Safety guidance delivered": safety instructions + contacts +
  technician-notified reply; case flagged, conversation state -> human
- EM-5 "Ambiguous risk": weak hit escalates to a human, never ignored;
  benign text (e.g. "fuga de agua") is NOT a hit

Part 1 (service): pure deterministic classification — no DB, no mocks.
Part 2 (graph): full-graph runs against the migrated pgvector test DB with
the OpenAI chat mocked via respx (emergency paths must NOT call it).
"""

import re

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    Conversation,
    ConversationEvent,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.emergency import classify_emergency, compile_keywords, fold_accents  # noqa: E402
from app.services.settings import DEFAULT_EMERGENCY_KEYWORDS, set_setting  # noqa: E402
from app.chat.graph import run_conversation  # noqa: E402
from app.chat.state import get_or_create_conversation  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402

ADMIN_DB_URL = "postgresql://lumat:lumat@localhost:5432/lumat"


# ---------------------------------------------------------------------------
# Part 1 — service: deterministic strong / weak / no-hit classification
# ---------------------------------------------------------------------------


def _pattern():
    return compile_keywords(DEFAULT_EMERGENCY_KEYWORDS)


# EM-1: every default keyword produces a strong hit in a realistic sentence.
# "fuga" is tested via "fuga de gas" — the phrase keyword wins over the bare
# stem, and a bare stem followed by a benign qualifier ("de agua") is NOT a
# hit (Lumat is a plumbing company; water leaks are normal service work).
EMERGENCY_SENTENCES = [
    ("olor a gas", "siento olor a gas en la cocina"),
    ("huele a gas", "huele a gas en el calefont"),
    ("fuga", "hay una fuga de gas en el calefont"),
    ("fuga de gas", "hay una fuga de gas en el calefont"),
    ("humo", "sale humo del calefont"),
    ("incendio", "hay un incendio en la casa"),
    ("chispa", "veo chispas cerca del medidor"),
    ("chispas", "veo chispas cerca del medidor"),
    ("explosión", "escuché una explosión en el patio"),
    ("monóxido", "creo que hay monóxido en el ambiente"),
    ("intoxicación", "parece intoxicación por gas"),
    ("riesgo eléctrico", "hay riesgo eléctrico en el panel"),
    ("filtración severa", "tengo una filtración severa en el techo"),
]


@pytest.mark.parametrize("keyword,sentence", EMERGENCY_SENTENCES)
def test_strong_hit_each_default_keyword(keyword, sentence):
    # each configured keyword is a direct emergency phrase (EM-1)
    assert classify_emergency(sentence, _pattern()) == "strong", keyword


@pytest.mark.parametrize(
    "sentence",
    [
        "hay una explosion en el patio",  # explosión -> explosion (T4.1.2 gotcha)
        "huele a monoxido",  # monóxido -> monoxido
        "parece intoxicacion por gas",  # intoxicación -> intoxicacion
        "hay riesgo electrico en el panel",  # eléctrico -> electrico
        "tengo una filtracion severa en el techo",  # severa stays
    ],
)
def test_accent_folded_variants_are_strong(sentence):
    assert classify_emergency(sentence, _pattern()) == "strong"


# EM-5: ambiguous/risk-adjacent language -> weak (escalate to human), never
# silently ignored; it is NOT the full emergency protocol.
@pytest.mark.parametrize(
    "sentence",
    [
        "huele raro el calefont",
        "no me llega gas al calefont",
        "hay un olor a quemado en el patio",
    ],
)
def test_weak_hit_escalates_not_ignored(sentence):
    assert classify_emergency(sentence, _pattern()) == "weak"


# No false positive on benign text: a water leak is Lumat's normal service
# work (gasfitería), not a gas emergency; plain commercial messages pass.
@pytest.mark.parametrize(
    "sentence",
    [
        "tengo una fuga de agua en el baño",
        "quiero cotizar un calefont de 10 litros",
        "¿en qué horario atienden?",
    ],
)
def test_benign_text_no_hit(sentence):
    assert classify_emergency(sentence, _pattern()) is None


def test_fuga_de_gas_strong_but_fuga_de_agua_benign():
    # the exact pair from the task: phrase hit vs benign qualifier exclusion
    pattern = _pattern()
    assert classify_emergency("hay una fuga de gas en el calefont", pattern) == "strong"
    assert classify_emergency("hay una fuga de agua en el baño", pattern) is None


def test_compile_deterministic_and_read_only_defaults():
    # same input -> identical pattern (deterministic compile)
    assert compile_keywords(DEFAULT_EMERGENCY_KEYWORDS).pattern == compile_keywords(
        DEFAULT_EMERGENCY_KEYWORDS
    ).pattern
    # case-insensitive over the folded keywords
    assert compile_keywords(DEFAULT_EMERGENCY_KEYWORDS).flags & re.IGNORECASE
    # the default list is a shared mutable object (T4.1.2) — never mutated
    snapshot = list(DEFAULT_EMERGENCY_KEYWORDS)
    compile_keywords(DEFAULT_EMERGENCY_KEYWORDS)
    assert DEFAULT_EMERGENCY_KEYWORDS == snapshot


def test_empty_text_no_hit():
    assert classify_emergency("", _pattern()) is None


def test_fold_accents_drops_combining_marks():
    assert fold_accents("Explosión MONÓXIDO") == "explosion monoxido"


# ---------------------------------------------------------------------------
# Part 2 — graph: emergency gate before any LLM + emergency node
# ---------------------------------------------------------------------------


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


def test_strong_hit_mid_capture_interrupts(mock_openai_chat, mock_meta_send):
    """EM-2: a strong hit abandons the capture flow and runs the protocol."""
    conv_id = _start_conversation()
    _turn(conv_id, "mi calefont falla", "wamid.ema1")  # capture starts
    calls_before = len(mock_openai_chat)

    replies = _turn(conv_id, "hay una fuga de gas en el calefont", "wamid.ema2")

    # EM-3: safety instructions + contacts + technician-notified
    assert any("INSTRUCCIONES DE SEGURIDAD" in r for r in replies)
    assert any("Bomberos" in r for r in replies)
    assert any("notificado" in r for r in replies)
    # the gate runs BEFORE any LLM — the emergency turn added zero LLM calls
    assert len(mock_openai_chat) == calls_before

    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        assert conv.state.value == "human"  # state -> human
        # EM-2: capture abandoned (the pending field is not advanced)
        assert "_pending" in (conv.captured_data or {})
        case = session.scalar(select(Case).where(Case.conversation_id == conv_id))
        assert case is not None
        assert case.emergency is True  # emergency flag on the case row
        assert case.status == "escalado"
        events = session.scalars(
            select(ConversationEvent).where(ConversationEvent.conversation_id == conv_id)
        ).all()
        assert any(e.event == "emergency" for e in events)


def test_weak_hit_escalates_to_human(mock_openai_chat):
    """EM-5: ambiguous risk escalates to a human, never ignored.

    T4.4: the weak path converges on the handoff node — the deriva case is
    created (HH-2) but WITHOUT the emergency protocol flags (EM-3 is strong
    only). Deterministic gate: no classify/respond call ever carries the
    customer text (D4); the only LLM call is the internal escalation summary.
    """
    conv_id = _start_conversation()
    replies = _turn(conv_id, "huele raro el calefont", "wamid.emw1")

    assert any("asesor" in r.lower() for r in replies)
    assert not any("INSTRUCCIONES DE SEGURIDAD" in r for r in replies)
    # only the internal summary call runs — never a classification of the text
    assert len(mock_openai_chat) == 1
    assert not any(
        "<user_input>" in c["messages"][-1]["content"] for c in mock_openai_chat
    )

    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        assert conv.state.value == "human"  # escalated to a human
        case = session.scalar(select(Case).where(Case.conversation_id == conv_id))
        assert case is not None  # handoff deriva case (HH-2)
        assert case.emergency is False  # weak hit is a handoff, not the protocol
        assert case.bundle["escalate_reason"] == "emergency_weak_hit"


def test_benign_text_passes_through_normal_flow(mock_openai_chat):
    conv_id = _start_conversation()
    replies = _turn(conv_id, "mi calefont no enciende", "wamid.emn1")

    # normal first-contact flow: greeting menu + first capture question
    assert any("nombre" in r.lower() for r in replies)
    assert not any("INSTRUCCIONES DE SEGURIDAD" in r for r in replies)
    assert len(mock_openai_chat) == 1  # only the intent classification ran

    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        assert conv.state.value == "bot"  # untouched by the gate


def test_custom_keyword_from_settings_detected(mock_openai_chat, mock_meta_send):
    """EM-1 'Keyword configured': a settings change applies on the next message."""
    conv_id = _start_conversation()
    with SessionLocal() as session:
        set_setting(session, "emergency.keywords", ["caja de fusibles quemada"])
        session.commit()

    replies = _turn(conv_id, "revisa la caja de fusibles quemada", "wamid.emc1")
    assert any("INSTRUCCIONES DE SEGURIDAD" in r for r in replies)
    assert len(mock_openai_chat) == 0
