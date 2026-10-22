"""S2d of the chatbot backlog: a platform message is stored, never classified.

Measured in production (audit 2026-10-22): Meta's own onboarding text
("Continue setting up your account…") entered as if it were a customer message
and produced an `unknown_intent`. A message the customer did not write is never
evidence that the bot failed to understand the customer.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    ConversationEvent,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.webhook.ingest import (
    normalize_message,
    persist_message,
    process_message,
)
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()
CUSTOMER_PHONE = "56912345678"
PLATFORM_TEXT = "Continue setting up your account or contact support"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


def _value(raw: dict) -> dict:
    return {"contacts": [{"wa_id": CUSTOMER_PHONE}], "messages": [raw]}


def _normalize(raw: dict):
    return normalize_message(raw, _value(raw))


def _process(raw: dict) -> None:
    normalized = _normalize(raw)
    with SessionLocal() as session:
        persist_message(session, normalized)
        session.commit()
    with SessionLocal() as session:
        message = session.scalars(
            select(Message).where(Message.wamid == raw["id"])
        ).one()
        process_message(session, message)
        session.commit()


def _events(name: str) -> list[ConversationEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(ConversationEvent).where(ConversationEvent.event == name)
            ).all()
        )


def _outbound(conversation_phone: str = CUSTOMER_PHONE) -> list[Message]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(Message).where(Message.direction == MessageDirection.OUTBOUND)
            ).all()
        )


@pytest.mark.parametrize("raw_type", ["system", "unsupported", "ephemeral", "request_welcome"])
def test_platform_message_types_are_not_customer_text(raw_type):
    body = {"body": PLATFORM_TEXT} if raw_type == "system" else {}
    normalized = _normalize(
        {"id": f"wamid.platform.{raw_type}", "from": CUSTOMER_PHONE, "type": raw_type, raw_type: body}
    )

    assert normalized.msg_type is MessageType.OTHER


def test_platform_message_keeps_its_text_for_the_record():
    normalized = _normalize(
        {
            "id": "wamid.platform.record",
            "from": CUSTOMER_PHONE,
            "type": "system",
            "system": {"body": PLATFORM_TEXT},
        }
    )

    assert normalized.text == PLATFORM_TEXT


def test_platform_message_is_stored_but_never_classified(mock_openai_chat, monkeypatch):
    from app.webhook import ingest

    monkeypatch.setattr(ingest, "deliver_outbound", lambda *args, **kwargs: None)
    _process(
        {
            "id": "wamid.platform.onboarding",
            "from": CUSTOMER_PHONE,
            "type": "system",
            "system": {"body": PLATFORM_TEXT},
        }
    )

    with SessionLocal() as session:
        stored = session.scalars(
            select(Message).where(Message.wamid == "wamid.platform.onboarding")
        ).one()
    assert stored.status is MessageStatus.PROCESSED
    assert _outbound() == []
    assert _events("unknown_intent") == []
    assert mock_openai_chat == []


def test_customer_text_still_reaches_the_graph(mock_openai_chat, monkeypatch):
    from app.webhook import ingest

    monkeypatch.setattr(ingest, "deliver_outbound", lambda *args, **kwargs: None)
    _process(
        {
            "id": "wamid.platform.customer",
            "from": CUSTOMER_PHONE,
            "type": "text",
            "text": {"body": "hola, tengo un calefont que no calienta"},
        }
    )

    assert _outbound(), "the customer is answered"
    assert mock_openai_chat, "the customer turn is classified and answered"
