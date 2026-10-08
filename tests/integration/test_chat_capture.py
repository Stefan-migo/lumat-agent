"""T3.5 integration tests — capture / respond / summary / unresolved nodes.

Scenarios mapped 1:1 from openspec/specs/conversation-manager/spec.md:

- CM-2 "Complete capture": progressive fields persisted (conversation +
  customer record); "Customer skips a field": skip -> unknown, non-blocking
- CM-4 "In-scope guidance": KB-grounded answer only (<kb> tags, no invented prices).
  "No reliable answer" is a GUARD, not a reachable path: every intent the classifier
  declares is routed away from the linear retrieval, so the refusal branch only runs
  on an undeclared intent. Covered by the two `guard`/`never_reaches` tests below.
- CM-5 "Summary after flow": summary on completion/escalation stored on
  conversation + case
- CM-6 "Unresolved question logged": question + context + timestamp stored
- CR-6: consent answer updates the customer record

Runs the full graph per turn (multi-turn flows). OpenAI mocked via respx.
"""

from dataclasses import replace

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation  # noqa: E402
from app.chat.nodes.respond import (  # noqa: E402
    CANNOT_ANSWER_REPLY,
    list_unresolved_questions,
    respond as respond_node,
)
from app.chat.state import ConversationState, get_or_create_conversation  # noqa: E402
from app.db import SessionLocal, session_scope  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    Conversation,
    ConversationEvent,
    Customer,
    CustomerEquipment,
    DocumentFormat,
    KbVisibility,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services import kb as kb_service  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()


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


def _media_turn(conv_id: int, wamid: str) -> list[str]:
    """Append a media-only inbound message and run the graph."""
    with SessionLocal() as session:
        message = Message(
            wamid=wamid,
            conversation_id=conv_id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.IMAGE,
            status=MessageStatus.RECEIVED,
        )
        session.add(message)
        session.commit()
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
    # turn 1: greeting + first capture question
    assert any("nombre" in r.lower() for r in replies)

    replies = _turn(conv_id, "Juan Perez", "wamid.cap2")
    assert any("correo" in r.lower() for r in replies)

    replies = _turn(conv_id, "juan@mail.cl", "wamid.cap3")
    assert any("comuna" in r.lower() for r in replies)

    replies = _turn(conv_id, "Providencia", "wamid.cap4")
    assert any("direcci" in r.lower() for r in replies)

    replies = _turn(conv_id, "Av Siempre Viva 123", "wamid.cap5")
    assert any("equipo" in r.lower() for r in replies)

    captured = _conversation_captured(conv_id)
    assert captured["name"] == "Juan Perez"
    assert captured["email"] == "juan@mail.cl"
    assert captured["comuna"] == "Providencia"
    assert captured["address"] == "Av Siempre Viva 123"
    # CI-3b: the ask is grouped (leading missing fields), not one per turn.
    assert captured["_pending"] == ["equipment", "failure", "availability"]


def test_media_during_capture_resumes_agenda(mock_openai_chat):
    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.media-start")
    pending_before = _conversation_captured(conv_id)["_pending"]

    replies = _media_turn(conv_id, "wamid.media-mid")

    captured = _conversation_captured(conv_id)
    assert any("Recibí tu archivo" in reply for reply in replies)
    assert any("¿Cuál es tu nombre?" in reply for reply in replies)
    assert captured["_pending"] == pending_before
    assert all(value not in (None, "unknown") for key, value in captured.items() if key != "_pending")
    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state.value == "bot"


def test_optional_evidence_ask_is_not_mandatory(mock_openai_chat):
    from app.chat.nodes.capture import EVIDENCE_QUESTION

    conv_id = _start_conversation()
    all_replies = []
    for index, text in enumerate(
        ["quiero una visita", "Juan", "juan@mail.cl", "Providencia", "Calle 1",
         "Calefont", "no enciende"],
        start=1,
    ):
        replies = _turn(conv_id, text, f"wamid.optional{index}")
        all_replies.extend(replies)

    assert any(EVIDENCE_QUESTION in reply for reply in all_replies)
    captured = _conversation_captured(conv_id)
    assert "evidence" not in captured
    assert "availability" in captured["_pending"]

    replies = _turn(conv_id, "paso", "wamid.optional-skip")
    assert any("¿Autorizas" in reply for reply in replies)
    captured = _conversation_captured(conv_id)
    assert captured["_pending"] == "consent"
    assert "evidence" not in captured


def test_cm2_mid_capture_deviation_is_answered_and_agenda_resumes(mock_openai_chat, fake_embedder):
    _seed_kb_doc("cuanto cuesta la revision anual de calefont: 15000 pesos", KbVisibility.CUSTOMER)
    conv_id = _start_conversation()

    _turn(conv_id, "quiero una visita", "wamid.dev0")
    assert _conversation_captured(conv_id)["_pending"] == ["name", "email", "comuna"]
    replies = _turn(conv_id, "cuanto cuesta la revision anual", "wamid.dev1")

    assert any("Segun el manual de Lumat" in reply for reply in replies)
    assert any("¿Cuál es tu nombre?" in reply for reply in replies)
    captured = _conversation_captured(conv_id)
    assert captured.get("name") != "cuanto cuesta la revision anual"
    assert captured["_pending"] == ["name", "email", "comuna"]
    with SessionLocal() as session:
        unknown_count = session.scalar(
            select(ConversationEvent.id).where(
                ConversationEvent.conversation_id == conv_id,
                ConversationEvent.event == "unknown_intent",
            )
        )
        assert unknown_count is None
        assert session.get(Conversation, conv_id).state.value != "human"


def test_cm2_field_answers_do_not_burn_unknown_attempts(mock_openai_chat):
    conv_id = _start_conversation()
    for index, text in enumerate(["quiero una visita", "Juan Perez", "Providencia"]):
        _turn(conv_id, text, f"wamid.unknown-field{index}")

    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state.value != "human"
        assert session.scalar(
            select(ConversationEvent.id).where(
                ConversationEvent.conversation_id == conv_id,
                ConversationEvent.event == "unknown_intent",
            )
        ) is None


def test_cm2_complete_capture_persists_and_confirms(mock_openai_chat):
    conv_id = _start_conversation()
    turns = [
        ("quiero una visita", "wamid.comp1"),
        ("Juan", "wamid.comp2"),
        ("juan@mail.cl", "wamid.comp3"),
        ("Providencia", "wamid.comp4"),
        ("Av Siempre Viva 123", "wamid.comp5"),
        ("Calefont Bosch 10 anios", "wamid.comp6"),
        ("No enciende y pierde agua", "wamid.comp7"),
        ("manana en la manana", "wamid.comp8"),
        ("si", "wamid.comp9"),  # consent
    ]
    last_replies = []
    for text, wamid in turns:
        last_replies = _turn(conv_id, text, wamid)

    captured = _conversation_captured(conv_id)
    assert captured["name"] == "Juan"
    assert captured["email"] == "juan@mail.cl"
    assert "evidence" not in captured
    assert captured["consent"] == "si"
    assert "_pending" not in captured  # capture finished
    # No technician schedule is configured: the completed request is handed off.
    assert last_replies[-1] == "Un asesor revisará tu caso y te contactará a la brevedad."

    # CR-6: consent + captured data stored on the customer ficha
    customer = _customer()
    assert customer.name == "Juan"
    assert customer.email == "juan@mail.cl"
    assert customer.comuna == "Providencia"
    assert customer.address == "Av Siempre Viva 123"
    assert customer.consent_status is True
    assert customer.consent_at is not None

    with SessionLocal() as session:
        equipment = session.scalars(
            select(CustomerEquipment).where(CustomerEquipment.customer_id == customer.id)
        ).all()
        assert len(equipment) == 1
        assert equipment[0].details == "Calefont Bosch 10 anios"
        assert equipment[0].equipment_type is None


def test_capture_equipment_promotion_is_idempotent(mock_openai_chat):
    from app.services.customers import promote_captured_equipment

    conv_id = _start_conversation()
    _turn(conv_id, "calefont", "wamid.equipment0")
    for index, text in enumerate(
        ["Juan", "juan@mail.cl", "Providencia", "Av Siempre Viva 123",
         "Calefont Bosch 10L", "No enciende", "mañana", "si"],
        start=1,
    ):
        _turn(conv_id, text, f"wamid.equipment{index}")

    with SessionLocal() as session:
        customer = session.scalar(select(Customer).where(Customer.phone_e164 == "+56912345678"))
        captured = _conversation_captured(conv_id)
        first = promote_captured_equipment(session, customer, conv_id, captured)
        session.commit()
        second = promote_captured_equipment(session, customer, conv_id, captured)
        session.commit()
        rows = session.scalars(
            select(CustomerEquipment).where(CustomerEquipment.source_conversation_id == conv_id)
        ).all()

    assert first is not None and second is not None
    assert first.id == second.id
    assert len(rows) == 1
    assert rows[0].details == "Calefont Bosch 10L"
    assert rows[0].equipment_type == "calefont"


def test_equipment_repromotion_preserves_operator_type_when_capture_omits_it():
    from app.services.customers import (
        promote_captured_equipment,
        update_customer_equipment,
    )

    conv_id = _start_conversation()
    captured = {"equipment": "Calefont Bosch 10L"}
    with SessionLocal() as session:
        customer = session.scalar(
            select(Customer).where(Customer.phone_e164 == "+56912345678")
        )
        equipment = promote_captured_equipment(session, customer, conv_id, captured)
        session.commit()
        assert equipment is not None
        assert equipment.equipment_type is None

        update_customer_equipment(
            session, equipment, actor="oper", equipment_type="caldera"
        )
        session.commit()
        original_details = equipment.details

        promoted_again = promote_captured_equipment(
            session, customer, conv_id, captured
        )
        session.commit()
        rows = session.scalars(
            select(CustomerEquipment).where(
                CustomerEquipment.source_conversation_id == conv_id
            )
        ).all()
        from app.models import AuditLog

        promotion_audits = session.scalars(
            select(AuditLog).where(
                AuditLog.action == "customer.equipment_promoted",
                AuditLog.entity_id == str(equipment.id),
            )
        ).all()

    assert promoted_again is not None
    assert promoted_again.equipment_type == "caldera"
    assert promoted_again.details == original_details == "Calefont Bosch 10L"
    assert len(rows) == 1
    assert len(promotion_audits) == 1


def test_cm2_skip_is_unknown_and_non_blocking(mock_openai_chat):
    conv_id = _start_conversation()
    _turn(conv_id, "caldera", "wamid.skip0")
    replies = _turn(conv_id, "no se", "wamid.skip1")  # skip the name field

    captured = _conversation_captured(conv_id)
    assert captured["name"] == "unknown"
    assert captured["_pending"] == ["email", "comuna", "address"]  # continued, not blocked
    assert any("correo" in r.lower() for r in replies)


def test_ci3_consent_is_a_separate_explicit_step(mock_openai_chat):
    """CI-3: consent is its own step, not a capture field (never extracted)."""
    from app.chat.nodes.capture import CAPTURE_FIELDS

    assert "consent" not in [field for field, _ in CAPTURE_FIELDS]
    assert "email" in [field for field, _ in CAPTURE_FIELDS]

    conv_id = _start_conversation()
    replies = []
    for index, text in enumerate(
        ["quiero una visita", "Juan", "juan@mail.cl", "Providencia", "Calle 1",
         "Calefont", "no enciende", "manana"],
        start=1,
    ):
        replies = _turn(conv_id, text, f"wamid.consent{index}")

    # availability was the last data field; the bot now asks consent explicitly.
    assert any("autori" in r.lower() for r in replies)
    assert _conversation_captured(conv_id)["_pending"] == "consent"

    _turn(conv_id, "si", "wamid.consent10")
    captured = _conversation_captured(conv_id)
    assert captured["consent"] == "si"
    assert "_pending" not in captured


def test_cm3_extracts_multiple_fields_from_one_message(mock_openai_chat, monkeypatch):
    """CI-3b: one free-text message fills several fields; the ask skips them."""
    from app.chat.nodes import classify_intent as ci

    real = ci._llm_classify

    def fake(text: str, message_id: int) -> dict:
        result = real(text, message_id)
        if "Los Leones" in text:
            result["fields"] = {
                "name": "Juan Pérez",
                "email": "juan@mail.cl",
                "address": "Los Leones 1234",
            }
        return result

    monkeypatch.setattr(ci, "_llm_classify", fake)

    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.ext1")
    replies = _turn(conv_id, "Juan Pérez, juan@mail.cl, Los Leones 1234", "wamid.ext2")

    captured = _conversation_captured(conv_id)
    assert captured["name"] == "Juan Pérez"
    assert captured["email"] == "juan@mail.cl"
    assert captured["address"] == "Los Leones 1234"

    # the grouped ask skipped the fields the same message already supplied
    asked = " ".join(replies)
    assert "¿Cuál es tu nombre?" not in asked
    assert "¿Cuál es tu correo" not in asked
    assert "¿Cuál es tu dirección?" not in asked


# ---------------------------------------------------------------------------
# CM-4 / CM-6 — KB-grounded answers + unresolved logging
# ---------------------------------------------------------------------------


def _seed_kb_doc(text: str, visibility: KbVisibility) -> None:
    # Ingested the way the panel upload does: no `source_meta`. This used to seed
    # `{"category": "valores"}` to satisfy the research_triage scope, which made the
    # test pass while the production path could never satisfy that filter. The scope
    # is gone (odd/tasks/kb-triage-scope.md), so the seed is gone with it.
    with SessionLocal() as session:
        kb_service.ingest_document(
            session,
            title="Manual",
            fmt=DocumentFormat.MD,
            content=text.encode(),
            visibility=visibility,
        )
        session.commit()


def test_cm4_kb_grounded_answer_with_kb_tags(mock_openai_chat, fake_embedder):
    # the customer question is a prefix of the chunk -> semantic hit (mocked)
    _seed_kb_doc(
        "cuanto cuesta la revision anual de calefont: 15000 pesos",
        KbVisibility.CUSTOMER,
    )
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


def test_triage_kb_miss_hands_off_without_the_cm4_refusal(mock_openai_chat, fake_embedder):
    """A KB-intent miss escalates through handoff (AO-8), not through CM-4's refusal.

    Renamed from ``test_cm4_kb_miss_cannot_answer_and_logs_unresolved``, which named the
    requirement whose text it asserts is ABSENT. That name is what made the traceability
    map claim a CM-4 coverage this test cannot provide, and what led a previous handoff
    to file the real finding as a defect. See ``odd/tasks/cm4-linear-path-scope.md``.
    """
    _seed_kb_doc("revision anual 15000", KbVisibility.CUSTOMER)
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


def test_cm4_guard_refuses_an_undeclared_intent_with_no_kb(mock_openai_chat, fake_embedder):
    """CM-4's refusal is a guard: unreachable for declared intents, still load-bearing.

    Every intent in the classifier's vocabulary is routed away from the linear
    retrieval (see the companion test below and ``orchestrate._dispatch``). The branch
    is kept because an intent the vocabulary does NOT declare falls through to it, and
    without it a KB miss would call ``_answer_from_kb(text, "")`` with an EMPTY ``<kb>``
    block — the model answering from nothing. That is the hallucination CM-4 exists to
    prevent, so the guard is not dead code.

    See ``odd/tasks/cm4-linear-path-scope.md``.
    """
    conv_id = _start_conversation()
    with SessionLocal() as session:
        session.add(
            Message(
                wamid="wamid.cm4guard0",
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="una consulta que el vocabulario del clasificador no declara",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        # An intent outside the declared vocabulary: no routing rule claims it, so
        # `_dispatch` falls through to the linear `respond` path.
        state = replace(ConversationState.from_db(session, conv_id), intent="garantia_heredada")
        # No KB document is seeded, so the retrieval misses.
        result = respond_node(state)

    assert result["replies"] == [CANNOT_ANSWER_REPLY]
    assert result["escalate"] is True
    assert result["escalate_reason"] == "kb_miss"


def test_unknown_intent_never_reaches_the_cm4_refusal(mock_openai_chat, fake_embedder):
    """The negative half: no declared intent reaches CM-4's refusal.

    ``unknown`` is the only intent that lands on the linear ``respond`` node, and it
    returns before the retrieval (``respond.py:121-128``): the CM-1 greeting answers the
    first turn, and the second attempt escalates through handoff (HH-3). This is why the
    refusal never fired in production, and why the misnamed triage test below could not
    be read as evidence that it did.
    """
    conv_id = _start_conversation()

    # Turn 1 — no capture/retrieval keyword and no handoff-gate trigger -> `unknown`.
    # The greeting + menu already answered the turn, so respond adds nothing.
    replies = _turn(conv_id, "me gustaria saber sobre pintura de interiores", "wamid.cm4lin1")
    assert CANNOT_ANSWER_REPLY not in replies
    assert len(replies) == 1

    # Turn 2 — the second unknown attempt escalates (HH-3), still not through CM-4.
    replies = _turn(conv_id, "sigo sin encontrar lo que busco", "wamid.cm4lin2")
    assert CANNOT_ANSWER_REPLY not in replies
    assert replies[-1] == "Un asesor revisará tu caso y te contactará a la brevedad."

    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state.value == "human"


def test_cm6_no_unresolved_when_kb_hits(mock_openai_chat, fake_embedder):
    _seed_kb_doc(
        "cuanto cuesta la revision anual de calefont: 15000 pesos",
        KbVisibility.CUSTOMER,
    )
    conv_id = _start_conversation()
    _turn(conv_id, "cuanto cuesta la revision anual", "wamid.hit0")

    with session_scope() as session:
        unresolved = list_unresolved_questions(session)
    assert unresolved == []  # answered from KB -> nothing logged


def test_customer_chat_cannot_ground_on_internal_kb_document(
    mock_openai_chat, fake_embedder, monkeypatch
):
    internal_text = "cuanto cuesta la revision anual de calefont: precio interno 15000"
    _seed_kb_doc(internal_text, KbVisibility.INTERNAL)
    retrieve_calls = []
    original_retrieve = kb_service.retrieve

    def capture_retrieve(*args, **kwargs):
        retrieve_calls.append(kwargs)
        return original_retrieve(*args, **kwargs)

    monkeypatch.setattr(kb_service, "retrieve", capture_retrieve)
    conv_id = _start_conversation()
    replies = _turn(conv_id, "cuanto cuesta la revision anual", "wamid.internal-customer")

    assert retrieve_calls
    assert all(call["audience"] is KbVisibility.CUSTOMER for call in retrieve_calls)
    assert all("<kb>" not in request["messages"][-1]["content"] for request in mock_openai_chat)
    assert replies[-1] == "Un asesor revisará tu caso y te contactará a la brevedad."


def test_lumat_assistant_can_retrieve_internal_kb_document(fake_embedder):
    from app.chat.assistant.tools.registry import KbArgs, _retrieve_kb

    internal_text = "manual interno para configurar el tablero de operaciones"
    with SessionLocal() as session:
        kb_service.ingest_document(
            session,
            title="Internal assistant manual",
            fmt=DocumentFormat.MD,
            content=internal_text.encode(),
            visibility=KbVisibility.INTERNAL,
        )
        session.commit()

    with SessionLocal() as session:
        chunks = _retrieve_kb(session, KbArgs(query=internal_text))

    assert chunks
    assert chunks[0]["content"] == internal_text


# ---------------------------------------------------------------------------
# CM-5 — summary generated at completion / escalation
# ---------------------------------------------------------------------------


def test_cm5_summary_stored_on_conversation_and_case(mock_openai_chat):
    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.sum0")
    for text, wamid in [
        ("Juan", "wamid.sum1"),
        ("juan@mail.cl", "wamid.sum2"),
        ("Providencia", "wamid.sum3"),
        ("Av Siempre Viva 123", "wamid.sum4"),
        ("calefont", "wamid.sum5"),
        ("no enciende", "wamid.sum6"),
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
