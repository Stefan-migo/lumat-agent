"""S1 of the chatbot backlog: a greeting is never a comprehension failure.

Measured on `main` before this slice (`odd/tasks/chatbot-backlog.md`, S1):
"Hola buenas tardes" reached `classify_intent` as `unknown`, and 3 of the 11
production greetings were a bare "Hola" sent mid-conversation (`_flow_start`
only short-circuited on the first turn).
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.state import get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    ConversationEvent,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer
from app.services.settings import MESSAGE_DEFAULTS
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()
GREETING = MESSAGE_DEFAULTS["greeting"]
FAREWELL = MESSAGE_DEFAULTS["farewell"]


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


def _start_conversation(name: str | None = None) -> int:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        customer.name = name
        conversation = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        return conversation.id


def _turn(conversation_id: int, text: str, wamid: str) -> list[str]:
    with SessionLocal() as session:
        message = Message(
            wamid=wamid,
            conversation_id=conversation_id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text=text,
            status=MessageStatus.RECEIVED,
        )
        session.add(message)
        session.commit()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _unknown_events() -> list[ConversationEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(ConversationEvent).where(ConversationEvent.event == "unknown_intent")
            ).all()
        )


@pytest.mark.parametrize(
    "text",
    ["Hola buenas tardes", "hola cómo va?", "Alo?", "holi", "buen día"],
)
def test_greeting_variant_answers_the_greeting_without_classifying(text, mock_openai_chat):
    replies = _turn(_start_conversation(), text, f"wamid.s1.first.{abs(hash(text))}")

    assert replies == [GREETING]
    assert mock_openai_chat == []
    assert _unknown_events() == []


def test_mid_conversation_greeting_answers_and_does_not_count(mock_openai_chat):
    conversation_id = _start_conversation()
    _turn(conversation_id, "tengo un calefont que no calienta", "wamid.s1.mid.1")
    calls_before = len(mock_openai_chat)
    unknowns_before = len(_unknown_events())

    replies = _turn(conversation_id, "Hola", "wamid.s1.mid.2")

    assert replies == [GREETING]
    assert len(mock_openai_chat) == calls_before
    assert len(_unknown_events()) == unknowns_before


def test_greeting_with_content_still_reaches_classification(mock_openai_chat):
    replies = _turn(
        _start_conversation(), "hola, tengo un calefont que no calienta", "wamid.s1.content.1"
    )

    assert replies != [GREETING]
    assert mock_openai_chat


def test_farewell_still_wins_before_the_greeting(mock_openai_chat):
    replies = _turn(_start_conversation(), "eso fue todo", "wamid.s1.farewell.1")

    assert replies == [FAREWELL]
    assert mock_openai_chat == []


def test_first_turn_greeting_uses_customer_name_and_keeps_single_message(mock_openai_chat):
    from app.services.settings import MESSAGE_DEFAULTS

    greeting = MESSAGE_DEFAULTS["greeting_name"]
    replies = _turn(_start_conversation("Ana"), "hola", "wamid.s2.named.first")

    assert replies == [greeting.replace("{{nombre}}", "Ana")]
    assert len(replies) == 1
    assert mock_openai_chat == []


def test_first_turn_content_uses_short_named_greeting(mock_openai_chat):
    from app.services.settings import MESSAGE_DEFAULTS

    greeting = MESSAGE_DEFAULTS["greeting_short_name"]
    replies = _turn(_start_conversation("Ana"), "tengo un calefont", "wamid.s2.named.short")

    assert len(replies) == 1
    assert replies[0].startswith(greeting.replace("{{nombre}}", "Ana"))
    assert len(replies[0]) > len(greeting)
    assert mock_openai_chat


@pytest.mark.parametrize("name", [None, "", "   "])
def test_first_turn_missing_or_blank_name_asks_for_name(name, mock_openai_chat):
    replies = _turn(_start_conversation(name), "hola", f"wamid.s2.ask.{name!r}")

    assert replies == [MESSAGE_DEFAULTS["greeting"]]
    assert "¿Con quién tengo el gusto?" in replies[0]
    assert mock_openai_chat == []


def test_first_turn_content_without_name_uses_short_name_question(mock_openai_chat):
    replies = _turn(_start_conversation(), "tengo un calefont", "wamid.s2.ask.short")

    assert len(replies) == 1
    assert replies[0].startswith(MESSAGE_DEFAULTS["greeting_short"])
    assert "¿Con quién tengo el gusto?" in replies[0]
    assert len(replies[0]) > len(MESSAGE_DEFAULTS["greeting_short"])
    assert mock_openai_chat


def test_later_bare_greeting_uses_named_variant(mock_openai_chat):
    from app.services.settings import MESSAGE_DEFAULTS

    conversation_id = _start_conversation("Ana")
    _turn(conversation_id, "tengo un calefont que no calienta", "wamid.s2.later.first")

    replies = _turn(conversation_id, "Hola", "wamid.s2.later.greeting")

    assert replies == [MESSAGE_DEFAULTS["greeting_name"].replace("{{nombre}}", "Ana")]
    assert len(replies) == 1
