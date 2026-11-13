"""D8/S2: un trabajo fuera del tarifario abre el paso de cotización."""

import re
from uuid import uuid4

import psycopg
import pytest

from app.chat.nodes.respond import QUOTE_REQUIRED_REPLY, respond
from app.chat.state import ConversationState
from app.db import SessionLocal
from app.services import settings
from app.services.settings import TARIFA_PRECIOS_KEY
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute("TRUNCATE settings RESTART IDENTITY CASCADE")
    yield


def _state(text: str) -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone=f"+569{uuid4().int % 100_000_000:08d}",
        turn=2,
        intent="valores",
        window=[{"id": 1, "text": text}],
        retrieval=[],
    )


def test_an_unlisted_boiler_change_offers_a_quote_instead_of_a_kb_miss():
    reply = respond(_state("cuanto cuesta cambiar la caldera"))["replies"][0]

    assert "cotiz" in reply.casefold()
    assert "equipo" in reply.casefold() and "necesitas" in reply.casefold()
    assert "No tengo ese dato" not in reply


def test_a_published_maintenance_tariff_still_answers_the_price():
    with SessionLocal() as session:
        settings.set_setting(
            session,
            TARIFA_PRECIOS_KEY,
            {
                "visita_tecnica": [{"desde_mes": 1, "hasta_mes": 12, "valor": 30000}],
                "mantencion_calefont": [{"desde_mes": 1, "hasta_mes": 12, "valor": 50000}],
                "mantencion_caldera": [{"desde_mes": 1, "hasta_mes": 12, "valor": 80000}],
                "lavado_red": [{"desde_mes": 1, "hasta_mes": 12, "valor": 140000}],
            },
        )
        session.commit()

    reply = respond(_state("cuanto cuesta la mantencion de caldera"))["replies"][0]

    assert "Mantención de caldera" in reply
    assert "$80.000" in reply
    assert "cotiz" not in reply.casefold()


def test_an_unrelated_kb_miss_keeps_the_existing_offer():
    reply = respond(_state("cuanto cuesta el lavado de estanque solar?"))["replies"][0]

    assert "No tengo ese dato" in reply


def test_quote_predicate_matches_measured_works_with_word_boundaries():
    from app.chat.nodes.respond import quotes_required

    assert quotes_required("cambio de caldera")
    assert quotes_required("conversión a gas natural")
    assert quotes_required("filtro de agua")
    assert not quotes_required("no calienta la casa")
    assert not quotes_required("necesito un prefiltro nuevo")


def test_quote_reply_has_no_peso_amount():
    assert not re.search(r"\$\s*\d|\b\d[\d.]*(?:\s*pesos)?\b", QUOTE_REQUIRED_REPLY, re.IGNORECASE)


# --------------------------------------------------------------------------
# S2/D8 end to end: the turn runs through the real graph, not a forced state.
# --------------------------------------------------------------------------


def test_the_quote_step_answers_a_real_turn_through_the_graph(mock_openai_chat):
    """The classifier returns `caldera` here; the price question still gets answered.

    Without the routing flag this turn went to capture and the customer read
    "cuéntame qué pasa con el equipo", so the quote step was unreachable for the
    eight works the defect measures.
    """
    from uuid import uuid4

    from sqlalchemy import select

    from app.chat.graph import run_conversation
    from app.chat.state import get_or_create_conversation
    from app.db import SessionLocal
    from app.models import Message, MessageDirection, MessageStatus, MessageType
    from app.services.customers import get_or_create_customer

    phone = f"+569{uuid4().int % 100_000_000:08d}"
    with SessionLocal() as session:
        customer = get_or_create_customer(session, phone)
        conversation = get_or_create_conversation(session, customer, phone)
        session.commit()
        conversation_id = conversation.id

    wamid = f"wamid.{uuid4().hex}"
    with SessionLocal() as session:
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conversation_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="cuanto cuesta cambiar la caldera",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        message = session.scalars(
            select(Message).where(Message.conversation_id == conversation_id, Message.wamid == wamid)
        ).one()
        replies = run_conversation(session, message)
        session.commit()

    joined = "\n".join(replies)
    assert "se cotiza según cada caso" in joined
    assert "No tengo ese dato" not in joined
    assert "qué pasa con el equipo" not in joined
