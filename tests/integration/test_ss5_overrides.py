"""SS-5 chat-level proof that standard message overrides are consumed."""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.state import ConversationState, get_or_create_conversation
from app.chat.nodes.receive import receive
from app.chat.nodes.respond import respond
from app.db import SessionLocal
from app.models import (
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services import settings
from app.services.customers import get_or_create_customer
from _testdb import admin_database_url


ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


def _start_conversation() -> int:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
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


def test_kb_miss_offer_override_is_used_on_a_kb_miss(mock_openai_chat, monkeypatch):
    override = "No tengo ese dato; ¿visita o persona?"
    with SessionLocal() as session:
        settings.set_setting(session, "messages.kb_miss_offer", override, actor="test")
        session.commit()

    # Exercise the production respond node through the graph while keeping the
    # test focused on its KB-miss branch rather than research-triage handoff.
    from app.chat.nodes import orchestrate

    monkeypatch.setattr(orchestrate, "RETRIEVAL_INTENTS", set())
    conversation_id = _start_conversation()
    _turn(conversation_id, "hola", "wamid.ss5.1")
    replies = _turn(conversation_id, "cuanto cuesta la revision anual", "wamid.ss5.2")

    assert override in replies
    assert all("Lo siento, no puedo responder con seguridad" not in reply for reply in replies)


def test_kb_retrieval_failure_escalates_without_logging_unresolved(monkeypatch, migrated_db):
    from app.services.settings import MESSAGE_DEFAULTS

    unresolved_calls = []
    monkeypatch.setattr(
        "app.services.kb.retrieve",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    monkeypatch.setattr(
        "app.chat.nodes.respond.log_unresolved",
        lambda *args, **kwargs: unresolved_calls.append((args, kwargs)),
    )
    state = ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=2,
        intent="consulta",
        window=[{"id": 1, "text": "¿Cuánto cuesta la revisión anual?"}],
    )

    try:
        result = respond(state)
    except Exception as error:
        result = error

    assert isinstance(result, dict)
    assert result["replies"][0] != MESSAGE_DEFAULTS["cannot_answer"]
    assert result["escalate"] is True
    assert result["escalate_reason"] != "kb_miss"
    assert unresolved_calls == []


def test_greeting_and_clarification_overrides_keep_path_shape():
    with SessionLocal() as session:
        settings.set_setting(session, "messages.greeting", "Hola editado:\n", actor="test")
        settings.set_setting(session, "messages.clarification", "Aclara tu solicitud.", actor="test")
        session.commit()

    state = ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=1,
        window=[{"id": 1, "text": "hola"}],
    )
    greeting = receive(state)["first_turn_greeting"]
    assert greeting.startswith("Hola editado:\n")
    assert "8. Hablar con una persona" not in greeting  # menu removed (CI-1 open greeting)

    state.turn = 2
    state.intent = "unknown"
    state.window = [{"id": 2, "text": "???"}]
    assert respond(state) == {"replies": ["Aclara tu solicitud."]}
