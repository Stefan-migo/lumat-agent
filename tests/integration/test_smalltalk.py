"""S3: courtesy is a classified turn, not a comprehension failure."""

import psycopg
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.state import ConversationState, get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    ConversationEvent,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    Settings,
)
from app.services.customers import get_or_create_customer
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()
SMALLTALK_REPLY = "Con gusto. ¿En qué más te puedo ayudar?"


def _conversation() -> int:
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


def _events(conversation_id: int, event: str) -> list[ConversationEvent]:
    with SessionLocal() as session:
        return list(session.scalars(
            select(ConversationEvent)
            .where(ConversationEvent.conversation_id == conversation_id)
            .where(ConversationEvent.event == event)
        ))


def test_smalltalk_answers_courtesy_and_breaks_the_unknown_streak(migrated_db, monkeypatch):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    conversation_id = _conversation()
    with SessionLocal() as session:
        session.add(Settings(key="scope_rules", value={"smalltalk": "always_escalate"}))
        session.commit()

    def classify(text, **_kwargs):
        intent = "smalltalk" if text == "gracias, ¿cómo estás?" else "unknown"
        return {
            "intent": intent,
            "service": None,
            "priority": None,
            "status": None,
            "injection": False,
            "fields": {},
            "template_id": None,
        }

    from app.chat.nodes import classify_intent
    monkeypatch.setattr(classify_intent, "_llm_classify", classify)

    first = _turn(conversation_id, "no entiendo nada de esto", "wamid.smalltalk.unknown")
    assert first, "the original comprehension failure still receives its clarification"
    assert len(_events(conversation_id, "unknown_intent")) == 1

    replies = _turn(conversation_id, "gracias, ¿cómo estás?", "wamid.smalltalk.thanks")

    assert replies == [SMALLTALK_REPLY]
    with SessionLocal() as session:
        state = ConversationState.from_db(session, conversation_id)
        assert state.unknown_count == 0
        assert state.escalate is False
        assert session.get(Settings, "messages.smalltalk") is None
    assert len(_events(conversation_id, "unknown_intent")) == 1
    assert _events(conversation_id, "classified")[-1].cause == "intent:smalltalk"
    from app.chat.nodes.orchestrate import _dispatch
    assert _dispatch("smalltalk", mid_capture=True)["next_step"] == "respond"
    assert not any(
        event.cause == "handoff:unknown_intent_thrice"
        for event in _events(conversation_id, "escalation")
    )


def test_acknowledgements_reach_the_classifier_instead_of_the_farewell(
    migrated_db, monkeypatch
):
    """S3 (chatbot-experiencia), owner decision: the gate stops closing on thanks.

    A bare "gracias" or "ok" used to be answered with the goodbye by
    `closure_gate`, because reaching classification got it the menu
    clarification. Courtesy now has its own category and reply, so the gate must
    let these through instead of ending the conversation on an acknowledgement.
    """
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    conversation_id = _conversation()

    def classify(text, **_kwargs):
        return {
            "intent": "smalltalk",
            "service": None,
            "priority": None,
            "status": None,
            "injection": False,
            "fields": {},
            "template_id": None,
        }

    from app.chat.nodes import classify_intent
    monkeypatch.setattr(classify_intent, "_llm_classify", classify)

    from app.services.settings import MESSAGE_DEFAULTS

    # Turn 1 fuses the greeting with the answer (CM-1), so the courtesy arrives
    # as the tail of that single message; from turn 2 on it stands alone.
    first = _turn(conversation_id, "gracias", "wamid.ack.reaches.0")
    assert len(first) == 1
    assert first[0].endswith(SMALLTALK_REPLY)
    assert MESSAGE_DEFAULTS["farewell"] not in first[0]

    for index, text in enumerate(("ok", "muchas gracias", "perfecto"), start=1):
        replies = _turn(conversation_id, text, f"wamid.ack.reaches.{index}")

        assert replies == [SMALLTALK_REPLY], text
    with SessionLocal() as session:
        state = ConversationState.from_db(session, conversation_id)
        assert state.unknown_count == 0
        assert state.escalate is False
