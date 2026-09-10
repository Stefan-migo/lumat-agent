"""T3.5 integration tests — capture / respond / summary / unresolved nodes.

Scenarios mapped 1:1 from openspec/specs/conversation-manager/spec.md:

- CM-2 "Complete capture": progressive fields persisted (conversation +
  customer record); "Customer skips a field": skip -> unknown, non-blocking
- CM-4 "In-scope guidance": KB-grounded answer only (<kb> tags, no invented
  prices); "No reliable answer": KB miss -> cannot-answer + unresolved log
- CM-5 "Summary after flow": summary on completion/escalation stored on
  conversation + case
- CM-6 "Unresolved question logged": question + context + timestamp stored
- CR-6: consent answer updates the customer record

Runs the full graph per turn (multi-turn flows). OpenAI mocked via respx.
"""

import os

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation  # noqa: E402
from app.chat.nodes.respond import CANNOT_ANSWER_REPLY, list_unresolved_questions  # noqa: E402
from app.chat.state import get_or_create_conversation  # noqa: E402
from app.db import SessionLocal, session_scope  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    Conversation,
    Customer,
    DocumentFormat,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services import kb as kb_service  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402

ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat + KB tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, kb_chunks, kb_documents, audit_log, conversation_events, "
            "cases, messages, conversations, customer_notes, customers "
            "RESTART IDENTITY CASCADE"
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


def _conversation_captured(conv_id: int) -> dict:
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        return conv.captured_data or {}


def _customer() -> Customer:
    with SessionLocal() as session:
        return session.scalar(select(Customer).where(Customer.phone_e164 == "+56912345678"))


# ---------------------------------------------------------------------------
# CM-2 — progressive capture (one field per turn) + persistence
# ---------------------------------------------------------------------------


def test_cm2_progressive_capture_asks_fields_in_order(mock_openai_chat):
    conv_id = _start_conversation()

    replies = _turn(conv_id, "mi calefont falla", "wamid.cap1")
    # turn 1: greeting menu + first capture question
    assert any("nombre" in r.lower() for r in replies)

    replies = _turn(conv_id, "Juan Perez", "wamid.cap2")
    assert any("comuna" in r.lower() for r in replies)

    replies = _turn(conv_id, "Providencia", "wamid.cap3")
    assert any("direcci" in r.lower() for r in replies)

    replies = _turn(conv_id, "Av Siempre Viva 123", "wamid.cap4")
    assert any("equipo" in r.lower() for r in replies)

    captured = _conversation_captured(conv_id)
    assert captured["name"] == "Juan Perez"
    assert captured["comuna"] == "Providencia"
    assert captured["address"] == "Av Siempre Viva 123"
    assert captured["_pending"] == "equipment"


def test_cm2_complete_capture_persists_and_confirms(mock_openai_chat):
    conv_id = _start_conversation()
    turns = [
        ("quiero una visita", "wamid.comp1"),
        ("Juan", "wamid.comp2"),
        ("Providencia", "wamid.comp3"),
        ("Av Siempre Viva 123", "wamid.comp4"),
        ("Calefont Bosch 10 anios", "wamid.comp5"),
        ("No enciende y pierde agua", "wamid.comp6"),
        ("no tengo", "wamid.comp7"),  # evidence skipped -> unknown, non-blocking
        ("manana en la manana", "wamid.comp8"),
        ("si", "wamid.comp9"),  # consent
    ]
    last_replies = []
    for text, wamid in turns:
        last_replies = _turn(conv_id, text, wamid)

    captured = _conversation_captured(conv_id)
    assert captured["name"] == "Juan"
    assert captured["evidence"] == "unknown"  # skip non-blocking (CM-2)
    assert captured["consent"] == "si"
    assert "_pending" not in captured  # capture finished
    # completion confirmation reply
    assert any("registrada" in r.lower() for r in last_replies)

    # CR-6: consent + captured data stored on the customer ficha
    customer = _customer()
    assert customer.name == "Juan"
    assert customer.comuna == "Providencia"
    assert customer.address == "Av Siempre Viva 123"
    assert customer.consent_status is True
    assert customer.consent_at is not None


def test_cm2_skip_is_unknown_and_non_blocking(mock_openai_chat):
    conv_id = _start_conversation()
    _turn(conv_id, "caldera", "wamid.skip0")
    replies = _turn(conv_id, "no se", "wamid.skip1")  # skip the name field

    captured = _conversation_captured(conv_id)
    assert captured["name"] == "unknown"
    assert captured["_pending"] == "comuna"  # flow continued, not blocked
    assert any("comuna" in r.lower() for r in replies)


# ---------------------------------------------------------------------------
# CM-4 / CM-6 — KB-grounded answers + unresolved logging
# ---------------------------------------------------------------------------


def _seed_kb_doc(text: str) -> None:
    # H2 (PR 2, AO-7): KB retail (valores) queries are answered by the scoped
    # research_triage sub-graph, which only retrieves chunks whose
    # source_meta.category is in its kb_scope. Seed the manual with the
    # matching category so the scoped retrieval can find it (same semantic
    # hit the pre-H2 unscoped path produced).
    with SessionLocal() as session:
        kb_service.ingest_document(
            session,
            title="Manual",
            fmt=DocumentFormat.MD,
            content=text.encode(),
            source_meta={"category": "valores"},
        )
        session.commit()


def test_cm4_kb_grounded_answer_with_kb_tags(mock_openai_chat, fake_embedder):
    # the customer question is a prefix of the chunk -> semantic hit (mocked)
    _seed_kb_doc("cuanto cuesta la revision anual de calefont: 15000 pesos")
    conv_id = _start_conversation()
    replies = _turn(conv_id, "cuanto cuesta la revision anual", "wamid.kb0")

    # the LAST reply is the KB-grounded answer (turn 1 also carries the greeting)
    grounded = replies[-1]
    assert "Segun el manual de Lumat" in grounded
    assert "15000" in grounded

    # SH-4/CM-4 structure: user text in <user_input>, KB content in <kb>
    assert len(mock_openai_chat) == 2  # classify + respond
    respond_call = mock_openai_chat[1]
    user = respond_call["messages"][-1]["content"]
    assert "<kb>" in user and "</kb>" in user
    assert "<user_input>cuanto cuesta la revision anual</user_input>" in user
    system = respond_call["messages"][0]["content"]
    assert "15000" not in system  # KB content never in the system prompt


def test_cm4_kb_miss_cannot_answer_and_logs_unresolved(mock_openai_chat, fake_embedder):
    _seed_kb_doc("revision anual 15000")
    conv_id = _start_conversation()
    replies = _turn(conv_id, "cuanto cuesta un grifo de cocina marca x", "wamid.miss0")

    # H2 (PR 2, AO-8): the scoped research_triage miss hands off directly
    # (it does NOT reach respond's canned CANNOT_ANSWER_REPLY); the last reply
    # is the handoff message announcing human takeover.
    assert CANNOT_ANSWER_REPLY not in replies
    assert replies[-1] == "Un asesor revisará tu caso y te contactará a la brevedad."

    # CM-6: question + context + timestamp logged (payload flag, no view); the
    # research sub-graph preserves the unresolved log before handing off.
    with session_scope() as session:
        unresolved = list_unresolved_questions(session)
    assert len(unresolved) == 1
    assert "grifo de cocina" in unresolved[0].text
    assert unresolved[0].payload["unresolved"] is True
    assert unresolved[0].payload["unresolved_context"] == "intent=valores"
    assert unresolved[0].created_at is not None

    # KB miss escalates by default; summary generated at escalation (CM-5)
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        assert conv.summary is not None
        assert "resumen" in conv.summary.lower()


def test_cm6_no_unresolved_when_kb_hits(mock_openai_chat, fake_embedder):
    _seed_kb_doc("cuanto cuesta la revision anual de calefont: 15000 pesos")
    conv_id = _start_conversation()
    _turn(conv_id, "cuanto cuesta la revision anual", "wamid.hit0")

    with session_scope() as session:
        unresolved = list_unresolved_questions(session)
    assert unresolved == []  # answered from KB -> nothing logged


# ---------------------------------------------------------------------------
# CM-5 — summary generated at completion / escalation
# ---------------------------------------------------------------------------


def test_cm5_summary_stored_on_conversation_and_case(mock_openai_chat):
    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.sum0")
    for text, wamid in [
        ("Juan", "wamid.sum1"),
        ("Providencia", "wamid.sum2"),
        ("Av Siempre Viva 123", "wamid.sum3"),
        ("calefont", "wamid.sum4"),
        ("no enciende", "wamid.sum5"),
        ("no tengo", "wamid.sum6"),
        ("manana", "wamid.sum7"),
        ("si", "wamid.sum8"),
    ]:
        _turn(conv_id, text, wamid)

    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        case = session.scalar(select(Case).where(Case.conversation_id == conv_id))
        assert conv.summary is not None and "resumen" in conv.summary.lower()
        assert case is not None
        assert case.summary == conv.summary
        # LLM cost recorded on the inbound message (T3.6 rate basis)
        msg = session.scalars(
            select(Message).where(
                Message.conversation_id == conv_id, Message.wamid == "wamid.sum8"
            )
        ).one()
        assert msg.cost_llm is not None and float(msg.cost_llm) > 0
