"""QA del cerebro Max — T01..T12 (spec: `odd/tasks/chatbot-cerebro-max-v4.md`).

`CEREBRO_MAX_LUMAT_V4.pdf` §E1 defines these twelve cases as the mandatory smoke
suite before reloading the knowledge base. Each test encodes the REQUIRED
behavior, not today's behavior: a red test maps work that is still pending.

Known red set at the time of writing (maps step 5 — capture order and the
classifier's `persona` rule):

- T02/T04/T09: `app/chat/nodes/capture.py` still asks name → email → comuna
  before any technical question.
- T03/T05: `app/chat/nodes/orchestrate.py:72` sends intent `persona` to handoff,
  so a social greeting is treated as a human request.
- T07: the equipment type is only recorded on the first capture turn.

The classifier is mocked deterministically, but it reproduces the failures V4
documents: a social question classifies as `persona`, as the real model does.
"""

from __future__ import annotations

import json

import httpx
import psycopg
import pytest
import respx
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.nodes.handoff import HANDOFF_REPLY
from app.chat.state import get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    Case,
    Conversation,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer
from app.services.settings import REPLY_TEXT_DEFAULTS
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()
PHONE = "+56912345678"

COMMUNES = [
    "Las Condes",
    "Ñuñoa",
    "Lo Barnechea",
    "La Reina",
    "Peñalolén",
    "Colina",
    "Huechuraba",
]

# ---------------------------------------------------------------------------
# Deterministic provider mock (V4 §E1 behaviors, classifies like the real prompt)
# ---------------------------------------------------------------------------


def _fields(text: str) -> dict:
    """Fields a real classifier would extract from one message."""
    lowered = text.lower()
    fields: dict = {}
    for commune in COMMUNES:
        if commune.lower() in lowered:
            fields["comuna"] = commune
    for prefix in ("me llamo ", "soy "):
        if prefix in lowered:
            tail = lowered.split(prefix, 1)[1].split(",")[0].strip()
            if tail and " " not in tail:
                fields["name"] = tail.capitalize()
    return fields


def _classify(text: str) -> dict:
    """Mirror `agent/personas/classify.md`: price questions beat equipment reports."""
    lowered = text.lower()
    base = {
        "service": None,
        "priority": None,
        "status": None,
        "injection": False,
        "template_id": None,
        "fields": _fields(text) or None,
    }

    if any(word in lowered for word in ("cuanto", "cuánto", "cuesta", "precio", "valor")):
        return {**base, "intent": "valores", "service": "valores", "priority": "baja"}
    if "olores" in lowered or "olor a gas" in lowered:
        return {**base, "intent": "emergencia", "priority": "alta", "status": "escalado"}
    # V4 §A3: the real model classifies a social question as `persona`. The test
    # reproduces that failure on purpose so the routing rule is observable.
    if "como estas" in lowered or "cómo estás" in lowered:
        return {**base, "intent": "persona"}
    if "persona" in lowered or "humano" in lowered or "ejecutivo" in lowered:
        return {**base, "intent": "persona"}
    if "calefont" in lowered:
        return {**base, "intent": "calefont", "service": "calefont", "priority": "media"}
    if "caldera" in lowered:
        return {**base, "intent": "caldera", "service": "caldera", "priority": "media"}
    if "calefaccion" in lowered or "calefacción" in lowered:
        return {**base, "intent": "calefaccion", "service": "calefaccion", "priority": "media"}
    if "visita" in lowered or "mantención" in lowered or "mantencion" in lowered:
        return {**base, "intent": "solicitar_visita", "service": "visita", "priority": "alta"}
    return {**base, "intent": "unknown"}


@pytest.fixture
def chat():
    """Mock the provider: classify, or echo the KB chunk set to the model."""
    captured: list[dict] = []

    with respx.mock(base_url="https://api.deepseek.com", assert_all_called=False) as router:

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            captured.append(body)
            system = body["messages"][0]["content"]
            user = body["messages"][-1]["content"]

            if "resumen" in system.lower():
                content = "Resumen de prueba."
            elif "<kb>" in user:
                content = f"Segun los precios de Lumat: {user.split('<kb>')[1][:160]}"
            else:
                inner = (
                    user.split("<user_input>")[1].split("</user_input>")[0]
                    if "<user_input>" in user
                    else ""
                )
                content = json.dumps(_classify(inner), ensure_ascii=False)

            return httpx.Response(
                200,
                json={
                    "id": "cmpl-test",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "deepseek-chat",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 20,
                        "completion_tokens": 10,
                        "total_tokens": 30,
                    },
                },
            )

        router.post("/chat/completions").mock(side_effect=handler)
        yield captured


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat, KB and settings before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, technician_availability, technician_weekly_schedule, "
            "kb_chunks, kb_documents, audit_log, conversation_events, "
            "cases, messages, conversations, customer_notes, customers "
            "RESTART IDENTITY CASCADE"
        )
    yield


def _start() -> int:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, PHONE)
        conv = get_or_create_conversation(session, customer, PHONE)
        session.commit()
        return conv.id


def _turn(conv_id: int, text: str, wamid: str) -> list[str]:
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
            select(Message).where(Message.conversation_id == conv_id, Message.wamid == wamid)
        ).one()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _first_turn(text: str) -> list[str]:
    return _turn(_start(), text, "wamid.first")


def _captured(conv_id: int) -> dict:
    with SessionLocal() as session:
        return dict(session.get(Conversation, conv_id).captured_data or {})


def _asked_for_admin_data(reply: str) -> bool:
    lowered = reply.lower()
    return any(
        marker in lowered
        for marker in ("nombre", "correo", "dirección", "direccion", "comuna")
    )


# ---------------------------------------------------------------------------
# E1 — Smoke tests of the defective behavior
# ---------------------------------------------------------------------------


def test_t01_greeting_without_history_greets_and_asks_nothing(chat):
    replies = _first_turn("Hola")

    assert len(replies) == 1
    assert "asistente virtual de Lumat" in replies[0]
    assert "nombre" not in replies[0].lower()
    assert chat == []


def test_t02_caldera_problem_asks_a_technical_question_not_admin_data(chat):
    reply = _first_turn("Tengo problemas con mi caldera")[-1]

    assert "caldera" in reply.lower()
    assert not _asked_for_admin_data(reply)


def test_t03_greeting_with_a_pending_caldera_keeps_the_context(chat):
    conv = _start()
    _turn(conv, "Mi caldera no calienta", "w1")

    reply = _turn(conv, "Hola, ¿cómo estás?", "w2")[-1]

    assert _captured(conv).get("name") != "Hola, ¿cómo estás?"
    assert HANDOFF_REPLY not in reply


def test_t04_greeting_with_form_gaps_does_not_fire_missing_data(chat):
    conv = _start()
    _turn(conv, "mi caldera no calienta", "w1")

    reply = _turn(conv, "Holaaa", "w2")[-1]

    assert "correo" not in reply.lower()
    assert "comuna" not in reply.lower()
    assert "dirección" not in reply.lower()
    assert "direccion" not in reply.lower()


def test_t05_social_question_is_not_a_human_request(chat):
    reply = _first_turn("¿Cómo estás?")[-1]

    assert HANDOFF_REPLY not in reply


def test_t06_explicit_human_request_derives_with_a_real_case(chat):
    conv = _start()

    reply = _turn(conv, "Quiero hablar con una persona", "w1")[-1]

    assert REPLY_TEXT_DEFAULTS["handoff_persona"] in reply
    with SessionLocal() as session:
        case = session.scalars(
            select(Case).where(Case.conversation_id == conv)
        ).one()
        assert case.status == "escalado"


def test_t07_calefont_does_not_inherit_the_previous_caldera(chat):
    conv = _start()
    _turn(conv, "Mi caldera no calienta", "w1")

    _turn(conv, "Ahora el calefont no enciende", "w2")

    assert _captured(conv).get("equipment_type") == "calefont"


def test_t08_price_question_does_not_start_the_capture_form(chat):
    # Grounding quality is NOT asserted here: the deterministic trigram double
    # scores real Spanish text around 0.36 cosine, under the production 0.50
    # threshold, so a KB hit here would measure the double, not the product.
    # Retrieval fidelity is measured by `scripts/kb_fidelity.py` (step 6).
    # Prices reach the model through the <tarifario> block built from settings,
    # never through a customer KB document (S5), so nothing is seeded here.
    reply = _first_turn("¿Cuánto cuesta la mantención de caldera?")[-1]

    assert "correo" not in reply.lower()
    assert "¿cuál es tu nombre" not in reply.lower()


def test_t09_booking_request_checks_availability_before_admin_data(chat):
    reply = _first_turn(
        "Quiero mantención de caldera mañana a las 16:00 en Las Condes"
    )[-1]

    assert not _asked_for_admin_data(reply)


def test_t10_does_not_repeat_the_commune_already_given(chat):
    conv = _start()
    _turn(conv, "Mi caldera no calienta", "w1")
    _turn(conv, "Me llamo Ana, en Las Condes", "w2")

    reply = _turn(conv, "Te dije que es Las Condes", "w3")[-1]

    assert "¿en qué comuna" not in reply.lower()
    assert _captured(conv).get("comuna") == "Las Condes"


def test_t11_out_of_hours_preference_never_confirms_itself(chat):
    reply = _first_turn("El sábado puedo después de las 18")[-1]

    lowered = reply.lower()
    assert "quedó confirmada" not in lowered
    assert "quedó agendada" not in lowered
    assert "reservada" not in lowered


def test_t12_gas_smell_triggers_the_safety_protocol_first(chat):
    # V4 §E1 T12 uses this literal wording. Note: "olor FUERTE a gas" does not
    # match the default keyword list ("olor a gas") — see the closing report.
    replies = _first_turn("Hay olor a gas")
    answer = " ".join(replies).lower()

    assert "seguridad" in answer
    assert "bomberos" in answer or "132" in answer
    assert "nombre" not in answer
