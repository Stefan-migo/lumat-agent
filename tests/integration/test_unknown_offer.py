"""S3a of the chatbot backlog: rephrase, then offer two paths, then derive (D17).

Measured on `main` before this slice: the second consecutive failure derived the
conversation, so the customer never got the offer of D17 ("take my data for a
visit" or "a person answers you"), and the transcript died at failure two.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.state import get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    Conversation,
    ConversationEvent,
    ConversationState as ConvState,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services import settings
from app.services.customers import get_or_create_customer
from app.services.settings import MESSAGE_DEFAULTS
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()
CLARIFICATION = MESSAGE_DEFAULTS["clarification"]
OFFER = MESSAGE_DEFAULTS["cannot_understand_offer"]
# The deterministic test double classifies these as unknown: no keyword of its
# table matches, so each one is a comprehension failure.
FAILURE = "zzz qqq"
FAILURE_2 = "qqq zzz"
FAILURE_3 = "www yyy"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
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
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conversation_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        message = session.scalars(select(Message).where(Message.wamid == wamid)).one()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _state(conversation_id: int) -> ConvState:
    with SessionLocal() as session:
        return session.get(Conversation, conversation_id).state


def _causes() -> list[str | None]:
    with SessionLocal() as session:
        return [
            row.cause
            for row in session.scalars(
                select(ConversationEvent).where(ConversationEvent.event == "escalation")
            ).all()
        ]


def test_first_failure_asks_the_customer_to_rephrase(mock_openai_chat):
    conversation_id = _start_conversation()
    _turn(conversation_id, "hola", "wamid.offer.0")
    replies = _turn(conversation_id, FAILURE, "wamid.offer.1")

    assert replies == [CLARIFICATION]
    assert _state(conversation_id) == ConvState.BOT


def test_second_failure_offers_the_two_paths_and_keeps_the_bot(mock_openai_chat):
    conversation_id = _start_conversation()
    _turn(conversation_id, "hola", "wamid.offer.10")
    _turn(conversation_id, FAILURE, "wamid.offer.11")
    replies = _turn(conversation_id, FAILURE_2, "wamid.offer.12")

    assert replies == [OFFER]
    assert _state(conversation_id) == ConvState.BOT
    assert not any(cause and "unknown_intent" in cause for cause in _causes())


def test_third_failure_derives_the_conversation(mock_openai_chat):
    conversation_id = _start_conversation()
    _turn(conversation_id, "hola", "wamid.offer.20")
    _turn(conversation_id, FAILURE, "wamid.offer.21")
    _turn(conversation_id, FAILURE_2, "wamid.offer.22")
    _turn(conversation_id, FAILURE_3, "wamid.offer.23")

    assert _state(conversation_id) == ConvState.HUMAN
    assert "handoff:unknown_intent_thrice" in _causes()


def test_the_offer_text_is_configurable(mock_openai_chat):
    marker = "Oferta configurada por el negocio."
    with SessionLocal() as session:
        settings.set_setting(
            session, "messages.cannot_understand_offer", marker, actor="test"
        )
        session.commit()

    conversation_id = _start_conversation()
    _turn(conversation_id, "hola", "wamid.offer.30")
    _turn(conversation_id, FAILURE, "wamid.offer.31")
    replies = _turn(conversation_id, FAILURE_2, "wamid.offer.32")

    assert replies == [marker]
