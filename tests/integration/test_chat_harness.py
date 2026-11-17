"""Integration coverage for the chat-harness core (ODD: chat-harness).

The harness is a manual QA surface over `run_conversation` — it adds no
production seam. These tests pin the contracts the REPL depends on, so the
surface cannot silently rot when the graph or the services move.

Only deterministic paths are asserted here:
- `ensure_conversation` is pure DB (customer + open conversation get-or-create).
- The emergency route is the one full path that reaches END with **zero LLM
  calls** (the gate runs before any model call — `app/chat/graph.py:194-199`).
- The first-contact greeting comes from `receive`, which is deterministic in
  content; substantive content still continues into `classify_intent`, while a
  greeting-only first turn ends before classification.
"""

import sys
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import func, select

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from chat_harness import ensure_conversation, inspect, run_turn  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.chat.nodes.receive import EVIDENCE_ACK  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    Conversation,
    ConversationEvent,
    ConversationState,
    Customer,
    Message,
    MessageDirection,
    MessageType,
)
from app.services.settings import (  # noqa: E402
    MESSAGE_DEFAULTS,
    REPLY_TEXT_DEFAULTS,
)
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()

PHONE = "+56912345678"
STRONG_EMERGENCY = "hay una fuga de gas en el calefont"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset the tables this unit reads, including `settings`.

    `settings` is in the list on purpose: the test database is shared by every
    worktree's pytest run, and emergency keyword overrides written by another
    suite leak into `emergency.keywords` and silently change gate outcomes
    (observed: a leaked `["caja de fusibles quemada"]` turned a strong hit into
    a weak one). Resetting it keeps these tests order- and neighbour-independent.
    """
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, memories, memory_relations, memory_observations, "
            "audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture
def no_emergency_notification(monkeypatch):
    """Stub the owner/technician notification, which reaches the network.

    The emergency node fires a WhatsApp template with an email fallback
    (`app/chat/nodes/emergency.py:107-113`). That behaviour is owned by
    `test_emergency_notify.py`, not by this unit, so the boundary is stubbed
    here to keep these tests offline and deterministic. The stub still proves
    the call happens — it records it.
    """
    from app.chat.nodes import emergency as emergency_node

    calls: list = []
    monkeypatch.setattr(
        emergency_node,
        "send_emergency_notification",
        lambda *args, **kwargs: calls.append(args),
    )
    return calls


# ---------------------------------------------------------------------------
# ensure_conversation — get-or-create, idempotent per phone
# ---------------------------------------------------------------------------


def test_ensure_conversation_is_idempotent_per_phone():
    with SessionLocal() as session:
        first = ensure_conversation(session, PHONE)
        session.commit()
        second = ensure_conversation(session, PHONE)
        session.commit()

    assert first == second
    with SessionLocal() as session:
        assert session.scalar(select(func.count(Customer.id))) == 1
        assert session.scalar(select(func.count(Conversation.id))) == 1


def test_ensure_conversation_never_reopens_a_closed_conversation():
    with SessionLocal() as session:
        first = ensure_conversation(session, PHONE)
        session.commit()
        closed = session.get(Conversation, first)
        closed.state = ConversationState.CLOSED
        session.commit()

        second = ensure_conversation(session, PHONE)
        session.commit()

    assert second != first
    with SessionLocal() as session:
        states = session.scalars(
            select(Conversation.state).order_by(Conversation.id)
        ).all()
    assert states == [ConversationState.CLOSED, ConversationState.BOT]


def test_inspect_reports_the_conversation_own_phone_not_the_caller_flag():
    """The REPL header must name the conversation's customer, not `--phone`.

    Reproduced live: `--conversation 5` printed `+56900000001` (the flag's
    default) while conversation #5 belonged to another customer entirely, so the
    operator could not tell whose thread they were writing into.
    """
    with SessionLocal() as session:
        first = ensure_conversation(session, PHONE)
        session.commit()
        second = ensure_conversation(session, "+56987654321")
        session.commit()

        assert inspect(session, first)["phone"] == PHONE
        assert inspect(session, second)["phone"] == "+56987654321"


# ---------------------------------------------------------------------------
# run_turn — drives the real entry point
# ---------------------------------------------------------------------------


def test_first_turn_greeting_only_does_not_classify(mock_openai_chat):
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        replies = run_turn(session, conversation_id, "hola")
        session.commit()

    assert replies == [MESSAGE_DEFAULTS["greeting"]]
    assert mock_openai_chat == []

    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        # The panel's active list filters on `last_message_at IS NOT NULL`
        # (`app/panel/api/routes/conversations.py:238-239`), so a turn that
        # leaves it unset produces a conversation nobody can see in the UI.
        assert conversation.last_message_at is not None


def _run_stubbed_model_answer(
    monkeypatch, text: str, answer: str, *, expect_model_call: bool = True
) -> tuple[int, list[str]]:
    """Drive a canned model completion through the production conversation graph."""
    from types import SimpleNamespace

    from app.chat.nodes import classify_intent, respond as respond_node

    model_calls = []

    def complete(**_kwargs):
        model_calls.append(True)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=answer))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )

    monkeypatch.setattr(
        respond_node,
        "openai_client",
        lambda: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=complete))
        ),
    )
    monkeypatch.setattr(
        classify_intent,
        "_llm_classify",
        lambda *_args, **_kwargs: {
            "intent": "consulta", "intents": ["consulta"], "service": None,
            "priority": "baja", "status": None, "injection": False,
            "fields": {},
        },
    )
    monkeypatch.setattr(
        respond_node, "retrieve_chunks", lambda *_args, **_kwargs: [{"content": "respuesta KB"}]
    )
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        run_turn(session, conversation_id, "hola")
        session.commit()
        replies = run_turn(session, conversation_id, text)
        session.commit()
    assert bool(model_calls) is expect_model_call
    return conversation_id, replies


@pytest.mark.parametrize(
    "unsafe",
    [
        "Revisa que la llave de gas esté abierta.",
        "Abre la válvula de gas.",
        "Cierra el suministro de gas.",
        "Prueba la línea de gas.",
    ],
)
def test_gas_hardware_instruction_from_model_is_replaced_and_recorded(monkeypatch, unsafe):
    conversation_id, replies = _run_stubbed_model_answer(
        monkeypatch, "Tengo una caldera y quiero saber qué hacer.", unsafe
    )

    assert unsafe not in replies, f"unsafe model answer escaped the response guard: {replies}"
    assert replies == [REPLY_TEXT_DEFAULTS["gas_instruction_guard"]]
    with SessionLocal() as session:
        event = session.scalar(
            select(ConversationEvent).where(
                ConversationEvent.conversation_id == conversation_id,
                ConversationEvent.event == "gas_instruction_guard",
            )
        )
    assert event is not None
    assert event.cause == "respond:gas_instruction_guard"
    assert event.actor == "bot"


def test_emergency_conditional_gas_advice_is_not_replaced(monkeypatch):
    advice = "Corta el suministro de gas solo si puedes hacerlo de forma segura."
    _, replies = _run_stubbed_model_answer(
        monkeypatch, "Tengo una caldera y quiero saber qué hacer.", advice
    )
    assert replies == [advice]


def test_general_gas_safety_advice_is_not_replaced(monkeypatch):
    advice = "Si sientes olor a gas, ventila y no enciendas artefactos ni luces."
    _, replies = _run_stubbed_model_answer(
        monkeypatch, "Tengo una caldera y quiero saber qué hacer.", advice
    )
    assert replies == [advice]


def test_descriptive_gas_line_answer_is_not_replaced(monkeypatch):
    answer = "La línea de gas se revisa durante la mantención del equipo."
    _, replies = _run_stubbed_model_answer(
        monkeypatch, "Tengo una caldera y quiero saber qué hacer.", answer
    )
    assert replies == [answer]


def test_named_out_of_area_place_gets_the_configured_policy(monkeypatch):
    from app.services.settings import COVERAGE_COMMUNES_KEY, set_setting

    with SessionLocal() as session:
        set_setting(session, COVERAGE_COMMUNES_KEY, ["Las Condes", "Ñuñoa"])
        session.commit()

    _, replies = _run_stubbed_model_answer(
        monkeypatch,
        "¿ustedes trabajan en Maipú?",
        "respuesta variable del modelo",
        expect_model_call=False,
    )

    assert replies == [
        "No tenemos cobertura habitual en Maipú, pero igual podemos ayudarte: "
        "un asesor coordina la visita según disponibilidad."
    ]


def test_named_covered_place_keeps_the_existing_confirmation(monkeypatch):
    from app.services.settings import COVERAGE_COMMUNES_KEY, set_setting

    with SessionLocal() as session:
        set_setting(session, COVERAGE_COMMUNES_KEY, ["Las Condes", "Ñuñoa"])
        session.commit()

    _, replies = _run_stubbed_model_answer(
        monkeypatch,
        "¿trabajan en Ñuñoa?",
        "respuesta variable del modelo",
        expect_model_call=False,
    )

    assert replies == ["Atendemos normalmente en Las Condes y Ñuñoa."]


def test_emergency_turn_escalates_without_any_llm_call(mock_openai_chat, no_emergency_notification):
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        replies = run_turn(session, conversation_id, STRONG_EMERGENCY)
        session.commit()

    # The gate runs before any model call; a fresh conversation adds none.
    assert mock_openai_chat == []
    assert any("Bomberos" in reply for reply in replies)

    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        assert conversation.state == ConversationState.HUMAN
        assert session.scalar(select(func.count(Case.id))) == 1


def test_preventive_capture_names_service_once_across_capture_turns(
    mock_openai_chat, monkeypatch
):
    from app.chat.nodes import classify_intent

    monkeypatch.setattr(
        classify_intent,
        "_llm_classify",
        lambda text, message_id, conversation="": {
            "intent": "caldera",
            "intents": ["caldera"],
            "service": "mantención de calefacción",
            "fields": {"equipment": "caldera"} if "Mantencion" in text else {},
        },
    )
    # The copy is settings-driven; assert against the default instead of a
    # second copy of the sentence, so a wording change does not fail here.
    maintenance_ack = REPLY_TEXT_DEFAULTS["capture_preventive_ack"].replace(
        "{{equipo}}", "caldera"
    ).strip()
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        first = run_turn(
            session,
            conversation_id,
            "Mantencion\nEsta funcionando bien la calefacción.\nQuiero mantencion",
        )
        session.commit()
        follow_up = run_turn(session, conversation_id, "no sé")
        session.commit()
        third = run_turn(session, conversation_id, "mañana")
        session.commit()

    assert any(maintenance_ack in reply for reply in first), first
    assert follow_up, follow_up
    assert third, third
    assert all(maintenance_ack not in reply for reply in follow_up), follow_up
    assert all(maintenance_ack not in reply for reply in third), third


def test_capture_pivot_to_fault_drops_preventive_ack(mock_openai_chat, monkeypatch):
    from app.chat.nodes import classify_intent

    def classify(text, message_id, conversation=""):
        fields = {}
        if "Mantencion" in text:
            fields["equipment"] = "caldera"
        elif "no calienta" in text:
            fields["failure"] = "no calienta"
        return {
            "intent": "caldera",
            "intents": ["caldera"],
            "service": "mantención de calefacción",
            "fields": fields,
        }

    monkeypatch.setattr(classify_intent, "_llm_classify", classify)
    # The copy is settings-driven; assert against the default instead of a
    # second copy of the sentence, so a wording change does not fail here.
    maintenance_ack = REPLY_TEXT_DEFAULTS["capture_preventive_ack"].replace(
        "{{equipo}}", "caldera"
    ).strip()
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        run_turn(
            session,
            conversation_id,
            "Mantencion\nEsta funcionando bien la calefacción.\nQuiero mantencion",
        )
        session.commit()
        pivot = run_turn(session, conversation_id, "la caldera no calienta")
        session.commit()

    assert all(maintenance_ack not in reply for reply in pivot), pivot


def test_reschedule_without_upcoming_visit_hands_off(mock_openai_chat, monkeypatch):
    from app.chat.nodes import classify_intent

    monkeypatch.setattr(
        classify_intent,
        "_llm_classify",
        lambda text, message_id, conversation="": {
            "intent": "reagendar_visita",
            "intents": ["reagendar_visita"],
            "service": None,
            "priority": None,
            "status": None,
            "injection": False,
            "fields": {},
        },
    )
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        run_turn(session, conversation_id, "hola")
        session.commit()
        replies = run_turn(session, conversation_id, "es factible que pases tipo 14 horas?")
        session.commit()
        result = inspect(session, conversation_id)

    assert all("No tienes visitas próximas" not in reply for reply in replies), replies
    assert any(
        event["cause"] == "intent:reagendar_visita" for event in result["events"]
    ), result["events"]
    assert result["state"] == "human", result
    assert any(
        event["cause"] == "handoff:booking_unavailable" for event in result["events"]
    ), result["events"]


# ---------------------------------------------------------------------------
# inspect — the observables the REPL prints
# ---------------------------------------------------------------------------


def test_inspect_surfaces_state_intent_events_and_memories(mock_openai_chat):
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        run_turn(session, conversation_id, "mi calefont falla")
        session.commit()
        result = inspect(session, conversation_id)

    assert result["conversation_id"] == conversation_id
    assert result["state"] == "bot"
    assert "captured_data" in result
    # The classified intent is persisted from inside the production path.
    assert any(
        event["event"] == "classified" and event["cause"] == "intent:calefont"
        for event in result["events"]
    ), result["events"]
    # The per-turn session memory is written by run_conversation itself.
    assert any(memory["topic_key"] == "session" for memory in result["memories"]), result["memories"]


def test_inspect_reports_the_emergency_case_and_human_state(mock_openai_chat, no_emergency_notification):
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        run_turn(session, conversation_id, STRONG_EMERGENCY)
        session.commit()
        result = inspect(session, conversation_id)

    assert result["state"] == "human"
    assert result["case"] is not None
    assert result["case"]["emergency"] is True


def test_a_media_turn_is_persisted_as_media(mock_openai_chat):
    """S4 (`odd/tasks/evals-gates-fallos.md`): a video is not a text message.

    The eval corpus writes `<video omitido>` as the placeholder for a video with
    no caption. While every turn was persisted as TEXT, that placeholder reached
    the classifier as unreadable text and recorded `unknown_intent`; production
    never does that, because media without text is evidence
    (`app/chat/nodes/handoff_gate.py:155-161`), never an utterance.
    """
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        replies = run_turn(session, conversation_id, "", media="video")
        session.commit()

        inbound = session.scalars(
            select(Message).where(Message.direction == MessageDirection.INBOUND)
        ).all()
        result = inspect(session, conversation_id)

    assert [message.msg_type for message in inbound] == [MessageType.VIDEO]
    assert inbound[0].text is None
    # The first turn also carries the greeting header; the evidence ack rides
    # along with it (`app/chat/nodes/receive.py:207-209`).
    assert any(EVIDENCE_ACK in reply for reply in replies), replies
    assert not [
        event for event in result["events"] if event["event"] == "unknown_intent"
    ], result["events"]
