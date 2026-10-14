from datetime import datetime, timedelta, timezone

import pytest

from app.db import SessionLocal
from app.models import (
    Conversation,
    ConversationEvent,
    ConversationState,
    Message,
    MessageDirection,
)
from app.services.conversations import conversation_transcript


def _seed_thread(session, customer_id, now):
    conversation = Conversation(
        customer_id=customer_id,
        wa_phone="+56922220001",
        state=ConversationState.HUMAN,
        summary="gas leak reported",
        last_message_at=now - timedelta(minutes=5),
    )
    session.add(conversation)
    session.flush()
    session.add_all([
        Message(conversation_id=conversation.id, direction=MessageDirection.INBOUND,
                text="hola", created_at=now - timedelta(minutes=30)),
        Message(conversation_id=conversation.id, direction=MessageDirection.OUTBOUND,
                text="buenas", created_at=now - timedelta(minutes=20)),
        Message(conversation_id=conversation.id, direction=MessageDirection.INBOUND,
                text="se rompe", created_at=now - timedelta(minutes=5)),
    ])
    session.add_all([
        ConversationEvent(conversation_id=conversation.id, event="unknown_intent",
                          created_at=now - timedelta(minutes=25)),
        ConversationEvent(conversation_id=conversation.id, event="escalation",
                          cause="handoff:emergency", created_at=now - timedelta(minutes=4)),
    ])
    session.flush()
    return conversation.id


def test_transcript_returns_metadata_bounded_messages_and_events(seed_customer):
    now = datetime.now(timezone.utc)
    customer_id = seed_customer("+56922220001")

    with SessionLocal() as session:
        conversation_id = _seed_thread(session, customer_id, now)
        result = conversation_transcript(session, conversation_id, limit=2)

    conversation = result["conversation"]
    assert set(conversation) == {
        "id", "customer_id", "wa_phone", "state", "summary", "last_message_at", "closed_at"
    }
    assert conversation["id"] == conversation_id
    assert conversation["customer_id"] == customer_id
    assert conversation["wa_phone"] == "+56922220001"
    assert conversation["state"] == "human"
    assert conversation["summary"] == "gas leak reported"
    assert conversation["closed_at"] is None
    assert conversation["last_message_at"] is not None
    assert result["messages_total"] == 3
    assert [m["text"] for m in result["messages"]] == ["buenas", "se rompe"]
    assert [m["direction"] for m in result["messages"]] == ["outbound", "inbound"]
    assert result["messages"][0]["msg_type"] == "text"
    assert [e["event"] for e in result["events"]] == ["unknown_intent", "escalation"]
    assert result["events"][1]["cause"] == "handoff:emergency"


def test_transcript_full_when_limit_exceeds_messages(seed_customer):
    now = datetime.now(timezone.utc)
    customer_id = seed_customer("+56922220002")

    with SessionLocal() as session:
        conversation_id = _seed_thread(session, customer_id, now)
        result = conversation_transcript(session, conversation_id, limit=20)

    assert [m["text"] for m in result["messages"]] == ["hola", "buenas", "se rompe"]


def test_transcript_empty_conversation_has_no_messages(seed_customer):
    customer_id = seed_customer("+56922220003")

    with SessionLocal() as session:
        conversation = Conversation(customer_id=customer_id, wa_phone="+56922220003")
        session.add(conversation)
        session.flush()
        result = conversation_transcript(session, conversation.id, limit=20)

    assert result["messages"] == [] and result["events"] == [] and result["messages_total"] == 0


def test_transcript_unknown_conversation_raises(seed_customer):
    seed_customer("+56922220004")

    with SessionLocal() as session:
        with pytest.raises(ValueError, match="conversation not found"):
            conversation_transcript(session, 999999, limit=20)
