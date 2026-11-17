"""S8: the production webhook delivers a strong emergency through ownership."""

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    Case,
    Conversation,
    ConversationState,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer
from app.chat.state import get_or_create_conversation, set_conversation_state
from app.webhook import ingest
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture
def no_emergency_notification(monkeypatch):
    from app.chat.nodes import emergency as emergency_node

    calls = []
    monkeypatch.setattr(
        emergency_node,
        "send_emergency_notification",
        lambda *args, **kwargs: calls.append(args),
    )
    return calls


def _human_conversation() -> int:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conversation = get_or_create_conversation(session, customer, "+56912345678")
        set_conversation_state(
            session, conversation, ConversationState.HUMAN, cause="test_setup", actor="rule"
        )
        session.commit()
        return conversation.id


def _process(
    conv_id: int,
    text: str | None,
    wamid: str,
    *,
    msg_type: MessageType = MessageType.TEXT,
    transcript: str | None = None,
) -> list[str]:
    with SessionLocal() as session:
        message = Message(
            wamid=wamid,
            conversation_id=conv_id,
            direction=MessageDirection.INBOUND,
            msg_type=msg_type,
            text=text,
            transcript=transcript,
            status=MessageStatus.RECEIVED,
        )
        session.add(message)
        session.commit()
        ingest.process_turn(session, [message])
        session.commit()
        return [
            row.text
            for row in session.scalars(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.direction == MessageDirection.OUTBOUND,
                ).order_by(Message.id)
            )
        ]


def test_strong_emergency_in_human_conversation_is_delivered_by_webhook(
    monkeypatch, mock_openai_chat, no_emergency_notification
):
    monkeypatch.setattr(ingest, "deliver_outbound", lambda *args: None)
    conv_id = _human_conversation()

    replies = _process(
        conv_id,
        "Fuga de gas en las cañerías que van hacia los hornos",
        "wamid.webhook-emergency",
    )

    assert len(replies) == 3
    assert "INSTRUCCIONES DE SEGURIDAD" in replies[0]
    assert not any("¿Qué equipo es?" in reply for reply in replies)
    with SessionLocal() as session:
        case = session.scalars(select(Case).where(Case.conversation_id == conv_id)).one()
        conversation = session.get(Conversation, conv_id)
    assert case.emergency is True
    assert conversation.state == ConversationState.HUMAN
    assert len(no_emergency_notification) == 1
    assert not mock_openai_chat


def test_ordinary_message_in_human_conversation_stays_silent(monkeypatch, mock_openai_chat):
    monkeypatch.setattr(ingest, "deliver_outbound", lambda *args: None)
    conv_id = _human_conversation()

    assert _process(conv_id, "sigo esperando respuesta", "wamid.webhook-ordinary") == []

    with SessionLocal() as session:
        assert session.scalar(select(Case.id).where(Case.conversation_id == conv_id)) is None
        assert session.get(Conversation, conv_id).state == ConversationState.HUMAN
    assert not mock_openai_chat

def test_audio_reporting_a_strong_emergency_is_delivered(
    monkeypatch, mock_openai_chat, no_emergency_notification
):
    """A voice note is the same words as a text message, and the brain reads it that way.

    `ConversationState.from_db` classifies the transcript of an AUDIO message, not its
    text column, so a boundary that reads only `text` drops exactly the message the
    brain would have caught. Measured: without this, a voice note saying there is a gas
    leak in a handed-off conversation produced nothing at all.
    """
    monkeypatch.setattr(ingest, "deliver_outbound", lambda *args: None)
    conv_id = _human_conversation()

    replies = _process(
        conv_id,
        None,
        "wamid.webhook-audio-emergency",
        msg_type=MessageType.AUDIO,
        transcript="hay olor a gas en la cocina, se siente fuerte",
    )

    assert len(replies) == 3
    assert "INSTRUCCIONES DE SEGURIDAD" in replies[0]
    assert not any("¿Qué equipo es?" in reply for reply in replies)
    assert not mock_openai_chat
    with SessionLocal() as session:
        case = session.scalars(select(Case).where(Case.conversation_id == conv_id)).one()
    assert case.emergency is True
