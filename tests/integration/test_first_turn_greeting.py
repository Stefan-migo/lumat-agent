"""Contract: the first-turn greeting is ONE message and never re-asks a stated need.

Spec: `odd/tasks/chatbot-first-turn-greeting.md` (S1–S3).

- S1: a bare greeting keeps the full greeting (CM-1: identifies itself and asks how
  it can help) and does not classify.
- S2: a first message that already states the need gets the short greeting — which
  identifies itself but drops the redundant "¿En qué te puedo ayudar?" — fused with
  the answer.
- S3: either way, the first turn yields exactly one outbound message (today the
  greeting and the answer go out as two separate WhatsApp messages).
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.state import get_or_create_conversation
from app.db import SessionLocal
from app.models import Message, MessageDirection, MessageStatus, MessageType
from app.services.customers import get_or_create_customer
from app.services.settings import MESSAGE_DEFAULTS
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()
PHONE = "+56912345678"
FULL_GREETING = MESSAGE_DEFAULTS["greeting"]
SHORT_GREETING = MESSAGE_DEFAULTS["greeting_short"]
ASK = "¿En qué te puedo ayudar?"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


def _first_turn(text: str) -> list[str]:
    """Seed one fresh conversation, run its first inbound message, return replies."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, PHONE)
        conv = get_or_create_conversation(session, customer, PHONE)
        session.add(
            Message(
                wamid="wamid.first",
                conversation_id=conv.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        message = session.scalars(
            select(Message).where(
                Message.conversation_id == conv.id, Message.wamid == "wamid.first"
            )
        ).one()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def test_s1_bare_greeting_is_one_full_greeting_and_does_not_classify(mock_openai_chat):
    replies = _first_turn("hola")

    assert replies == [FULL_GREETING]
    assert mock_openai_chat == []


def test_s2_greeting_with_content_is_one_short_greeting_and_does_not_ask_again(
    mock_openai_chat,
):
    replies = _first_turn("hola, tengo un calefont que no calienta")

    assert len(replies) == 1
    assert replies[0].startswith(SHORT_GREETING + "\n\n")
    assert "soy el asistente virtual de Lumat" in replies[0]
    assert ASK not in replies[0]
    assert "Cuéntame qué pasa con el equipo" in replies[0]


def test_s2_content_without_a_greeting_is_one_short_greeting_and_does_not_ask_again(
    mock_openai_chat,
):
    replies = _first_turn("necesito reagendar una visita")

    assert len(replies) == 1
    assert replies[0].startswith(SHORT_GREETING + "\n\n")
    assert ASK not in replies[0]
