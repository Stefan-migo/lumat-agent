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
from app.services import settings as settings_service  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat + KB tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, technician_availability, technician_weekly_schedule, "
            "kb_chunks, kb_documents, audit_log, conversation_events, "
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

    # V4 §A3/A7: diagnose first (one question per turn); admin data last.
    replies = _turn(conv_id, "mi calefont falla", "wamid.cap1")
    assert any("qué pasa con el equipo" in r.lower() for r in replies)

    replies = _turn(conv_id, "no enciende", "wamid.cap2")
    assert any("qué equipo" in r.lower() for r in replies)

    replies = _turn(conv_id, "Calefont Bosch", "wamid.cap3")
    assert any("comuna" in r.lower() for r in replies)

    replies = _turn(conv_id, "Ñuñoa", "wamid.cap4")
    assert any("horario" in r.lower() for r in replies)

    replies = _turn(conv_id, "mañanas", "wamid.cap5")
    assert any("nombre" in r.lower() for r in replies)

    replies = _turn(conv_id, "Juan Perez", "wamid.cap6")
    assert any("correo" in r.lower() for r in replies)

    captured = _conversation_captured(conv_id)
    assert captured["failure"] == "no enciende"
    assert captured["equipment"] == "Calefont Bosch"
    assert captured["comuna"] == "Ñuñoa"
    assert captured["availability"] == "mañanas"
    assert captured["name"] == "Juan Perez"
    # S14: the configured max is 1 by default, so the booking data is asked one
    # field per message too (it used to ride a 2–3 field batch).
    assert captured["_pending"] == ["email"]


# ---------------------------------------------------------------------------
# S14 — one question per message, one reformulation, then a derivation
# ---------------------------------------------------------------------------


def _configure_conduct(**overrides) -> None:
    with session_scope() as session:
        settings_service.set_setting(
            session,
            settings_service.CHAT_CONDUCT_KEY,
            {**settings_service.CHAT_CONDUCT_DEFAULTS, **overrides},
            actor="test",
        )
        session.commit()


def test_s14_one_question_per_message_is_the_default(mock_openai_chat):
    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.s14a1")
    _turn(conv_id, "No enciende", "wamid.s14a2")
    _turn(conv_id, "Calefont Bosch", "wamid.s14a3")

    replies = _turn(conv_id, "Ñuñoa", "wamid.s14a4")

    assert any("días y horarios" in reply.lower() for reply in replies)
    assert all("nombre" not in reply.lower() for reply in replies)
    assert _conversation_captured(conv_id)["_pending"] == ["availability"]


def test_s14_max_two_asks_two_booking_fields(mock_openai_chat):
    _configure_conduct(max_preguntas_por_mensaje=2)
    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.s14b1")
    _turn(conv_id, "No enciende", "wamid.s14b2")
    _turn(conv_id, "Calefont Bosch", "wamid.s14b3")

    replies = _turn(conv_id, "Ñuñoa", "wamid.s14b4")

    assert _conversation_captured(conv_id)["_pending"] == ["availability", "name"]
    assert any("nombre" in reply.lower() for reply in replies)


def test_s14_a_field_asked_twice_without_an_answer_offers_a_derivation(
    mock_openai_chat, fake_embedder
):
    """Ask once, reformulate once (the KB deviation turn re-asks), then derive."""
    _seed_kb_doc("cuanto cuesta la revision anual de calefont: 15000 pesos", KbVisibility.CUSTOMER)
    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.s14c1")
    _turn(conv_id, "cuanto cuesta la revision anual", "wamid.s14c2")

    replies = _turn(conv_id, "cuanto cuesta la revision anual", "wamid.s14c3")

    # S14: the same question is never sent twice in one turn.
    assert len(replies) == len(set(replies))
    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state.value == "human"
        causes = session.scalars(
            select(ConversationEvent.cause).where(
                ConversationEvent.conversation_id == conv_id
            )
        ).all()
    assert "handoff:campo_sin_respuesta" in causes


def test_s14_two_questions_for_different_fields_do_not_derive(mock_openai_chat, fake_embedder):
    """The reformulation budget is per field: answering the field clears it."""
    _seed_kb_doc("cuanto cuesta la revision anual de calefont: 15000 pesos", KbVisibility.CUSTOMER)
    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.s14d1")
    _turn(conv_id, "cuanto cuesta la revision anual", "wamid.s14d2")
    _turn(conv_id, "No enciende", "wamid.s14d3")
    _turn(conv_id, "cuanto cuesta la revision anual", "wamid.s14d4")

    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state.value != "human"
    assert _conversation_captured(conv_id)["_pending"] == ["equipment"]



def test_media_during_capture_resumes_agenda(mock_openai_chat):
    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.media-start")
    pending_before = _conversation_captured(conv_id)["_pending"]

    replies = _media_turn(conv_id, "wamid.media-mid")

    captured = _conversation_captured(conv_id)
    assert any("Recibí tu archivo" in reply for reply in replies)
    assert any("Cuéntame qué pasa con el equipo" in reply for reply in replies)
    assert captured["_pending"] == pending_before
    assert all(value not in (None, "unknown") for key, value in captured.items() if key != "_pending")
    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state.value == "bot"


def test_configured_consent_question_is_used(mock_openai_chat):
    custom = "¿Nos autorizas a guardar tus datos?"
    with session_scope() as session:
        settings_service.set_setting(
            session,
            settings_service.REPLY_TEXTS_KEY,
            {**settings_service.REPLY_TEXT_DEFAULTS, "capture_consent": custom},
            actor="test",
        )
        session.commit()

    conv_id = _start_conversation()
    replies: list[str] = []
    for index, text in enumerate(
        ["quiero una visita", "No enciende", "Calefont", "Ñuñoa",
         "mañanas", "Juan", "juan@mail.cl", "Calle 1"],
        start=1,
    ):
        replies = _turn(conv_id, text, f"wamid.custom-consent{index}")

    assert replies == [custom]


def test_configured_capture_questions_are_the_fallback_text(mock_openai_chat):
    """S7: `capture.questions` replaces the built-in fallback, field by field."""
    from app.chat.nodes.capture import CAPTURE_FIELDS

    custom = "Cuéntame la falla con tus palabras."
    questions = {**dict(CAPTURE_FIELDS), "failure": custom}
    with session_scope() as session:
        settings_service.set_setting(
            session, settings_service.CAPTURE_QUESTIONS_KEY, questions, actor="test"
        )
        session.commit()

    conv_id = _start_conversation()
    replies = _turn(conv_id, "quiero una visita", "wamid.custom-question")

    assert any(custom in reply for reply in replies)
    assert all("Cuéntame qué pasa con el equipo" not in reply for reply in replies)


def test_optional_evidence_ask_is_not_mandatory(mock_openai_chat):
    from app.chat.nodes.capture import EVIDENCE_QUESTION
    conv_id = _start_conversation()
    all_replies = []
    for index, text in enumerate(
        ["quiero una visita", "No enciende", "Calefont", "Ñuñoa",
         "mañanas", "Juan", "juan@mail.cl", "Calle 1"],
        start=1,
    ):
        replies = _turn(conv_id, text, f"wamid.optional{index}")
        all_replies.extend(replies)

    # the optional evidence ask rides the last booking batch, never gates it
    assert any(EVIDENCE_QUESTION in reply for reply in all_replies)
    captured = _conversation_captured(conv_id)
    assert "evidence" not in captured
    assert captured["_pending"] == "consent"

    _turn(conv_id, "paso", "wamid.optional-skip")
    captured = _conversation_captured(conv_id)
    assert captured["consent"] == "unknown"
    assert "_pending" not in captured


def test_cm2_mid_capture_deviation_is_answered_and_agenda_resumes(mock_openai_chat, fake_embedder):
    _seed_kb_doc("cuanto cuesta la revision anual de calefont: 15000 pesos", KbVisibility.CUSTOMER)
    conv_id = _start_conversation()

    _turn(conv_id, "quiero una visita", "wamid.dev0")
    assert _conversation_captured(conv_id)["_pending"] == ["failure"]
    replies = _turn(conv_id, "cuanto cuesta la revision anual", "wamid.dev1")

    assert any("Segun el manual de Lumat" in reply for reply in replies)
    assert any("Cuéntame qué pasa con el equipo" in reply for reply in replies)
    captured = _conversation_captured(conv_id)
    assert captured.get("failure") != "cuanto cuesta la revision anual"
    assert captured["_pending"] == ["failure"]
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
    for index, text in enumerate(["quiero una visita", "Juan Perez", "Ñuñoa"]):
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
        ("No enciende y pierde agua", "wamid.comp2"),
        ("Calefont Bosch 10 anios", "wamid.comp3"),
        ("Ñuñoa", "wamid.comp4"),
        ("manana en la manana", "wamid.comp5"),
        ("Juan", "wamid.comp6"),
        ("juan@mail.cl", "wamid.comp7"),
        ("Av Siempre Viva 123", "wamid.comp8"),
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
    assert customer.comuna == "Ñuñoa"
    assert customer.address == "Av Siempre Viva 123"
    assert customer.consent_status is True
    assert customer.consent_at is not None

    with SessionLocal() as session:
        equipment = session.scalars(
            select(CustomerEquipment).where(CustomerEquipment.customer_id == customer.id)
        ).all()
        assert len(equipment) == 1
        assert equipment[0].details == "Calefont Bosch 10 anios"
        # V4 T07: the appliance in the message now sets the type.
        assert equipment[0].equipment_type == "calefont"


def test_capture_equipment_promotion_is_idempotent(mock_openai_chat):
    from app.services.customers import promote_captured_equipment

    conv_id = _start_conversation()
    _turn(conv_id, "calefont", "wamid.equipment0")
    for index, text in enumerate(
        ["No enciende", "Calefont Bosch 10L", "Ñuñoa", "mañana",
         "Juan", "juan@mail.cl", "Av Siempre Viva 123", "si"],
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
    replies = _turn(conv_id, "no se", "wamid.skip1")  # skip the failure field

    captured = _conversation_captured(conv_id)
    assert captured["failure"] == "unknown"
    assert captured["_pending"] == ["equipment"]  # continued, not blocked
    assert any("equipo" in r.lower() for r in replies)


def test_ci3_consent_is_a_separate_explicit_step(mock_openai_chat):
    """CI-3: consent is its own step, not a capture field (never extracted)."""
    from app.chat.nodes.capture import CAPTURE_FIELDS

    assert "consent" not in [field for field, _ in CAPTURE_FIELDS]
    assert "email" in [field for field, _ in CAPTURE_FIELDS]

    conv_id = _start_conversation()
    replies = []
    for index, text in enumerate(
        ["quiero una visita", "no enciende", "Calefont", "Ñuñoa",
         "manana", "Juan", "juan@mail.cl", "Calle 1"],
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

    def fake(text: str, message_id: int, conversation: str = "") -> dict:
        result = real(text, message_id, conversation)
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
    # First turn: the handoff reply travels fused with the CM-1 greeting.
    assert replies[-1].endswith("Un asesor revisará tu caso y te contactará a la brevedad.")

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
    # First turn: the handoff reply travels fused with the CM-1 greeting.
    assert replies[-1].endswith("Un asesor revisará tu caso y te contactará a la brevedad.")


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
        ("Ñuñoa", "wamid.sum3"),
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


# ---------------------------------------------------------------------------
# S11 — the effective capture order comes from `chat.conduct.orden`
# ---------------------------------------------------------------------------


def _configure_order(order: list[str]) -> None:
    with session_scope() as session:
        settings_service.set_setting(
            session,
            settings_service.CHAT_CONDUCT_KEY,
            {**settings_service.CHAT_CONDUCT_DEFAULTS, "orden": order},
            actor="test",
        )
        session.commit()


def test_s11_configured_order_is_the_sequence_that_gets_asked(mock_openai_chat):
    """The order is the source: comuna first asks comuna before the failure."""
    _configure_order(["comuna", "failure", "equipment", "availability", "name", "email", "address"])
    conv_id = _start_conversation()

    replies = _turn(conv_id, "quiero una visita", "wamid.order1")

    assert any("comuna" in reply.lower() for reply in replies)
    captured = _conversation_captured(conv_id)
    assert captured["_pending"][0] == "comuna"


def test_s11_a_field_dropped_from_the_order_is_never_asked(mock_openai_chat):
    """Address out of the order: the flow goes to consent without asking it."""
    _configure_order(["failure", "equipment", "comuna", "availability", "name", "email"])
    conv_id = _start_conversation()

    replies: list[str] = []
    for index, text in enumerate(
        ["quiero una visita", "No enciende", "Calefont", "Ñuñoa",
         "mañanas", "Juan", "juan@mail.cl"],
        start=1,
    ):
        replies = _turn(conv_id, text, f"wamid.drop-address{index}")

    assert not any("dirección" in reply.lower() for reply in replies)
    captured = _conversation_captured(conv_id)
    assert captured["_pending"] == "consent"


# ---------------------------------------------------------------------------
# S15 — a comuna outside coverage derives to an advisor, never a dead end
# ---------------------------------------------------------------------------


def _turn_causes(conv_id: int) -> list[str]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(ConversationEvent.cause).where(
                    ConversationEvent.conversation_id == conv_id
                )
            ).all()
        )


def _walk_to_comuna(conv_id: int) -> list[str]:
    _turn(conv_id, "quiero una visita", "wamid.cov0")
    _turn(conv_id, "No enciende", "wamid.cov1")
    _turn(conv_id, "Calefont Bosch", "wamid.cov2")
    return _turn(conv_id, "La Florida", "wamid.cov3")


def test_s15_a_comuna_outside_coverage_derives_without_promising_a_visit(mock_openai_chat):
    conv_id = _start_conversation()

    replies = _walk_to_comuna(conv_id)

    assert any("asesor" in reply.lower() for reply in replies)
    assert all("horarios disponibles" not in reply.lower() for reply in replies)
    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state.value == "human"
    assert "handoff:cobertura" in _turn_causes(conv_id)


def test_s15_a_covered_comuna_keeps_the_capture_going(mock_openai_chat):
    conv_id = _start_conversation()
    _turn(conv_id, "quiero una visita", "wamid.covc0")
    _turn(conv_id, "No enciende", "wamid.covc1")
    _turn(conv_id, "Calefont Bosch", "wamid.covc2")

    replies = _turn(conv_id, "Ñuñoa", "wamid.covc3")

    assert any("días y horarios" in reply.lower() for reply in replies)
    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state.value != "human"
    assert "handoff:cobertura" not in _turn_causes(conv_id)


def test_s15_the_coverage_rule_can_be_turned_off(mock_openai_chat):
    _configure_conduct(derivaciones=["garantia"])
    conv_id = _start_conversation()

    _walk_to_comuna(conv_id)

    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state.value != "human"
    assert _conversation_captured(conv_id)["_pending"] == ["availability"]
