from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    Commitment,
    Conversation,
    ConversationState,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.commitments import record_from_message


def _message(text: str):
    customer = Customer(phone_e164="+56970000001", name="Ana")
    with SessionLocal() as session:
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id,
            wa_phone=customer.phone_e164,
            state=ConversationState.HUMAN,
        )
        session.add(conversation)
        session.flush()
        message = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            msg_type=MessageType.TEXT,
            text=text,
            status=MessageStatus.PROCESSED,
            created_at=datetime.now(timezone.utc),
        )
        session.add(message)
        session.flush()
        ids = customer.id, conversation.id, message.id
        session.commit()
        return ids


def test_record_from_message_persists_promise_verbatim_with_context_and_due_date():
    customer_id, conversation_id, message_id = _message("Mañana le envío el detalle tal cual.")
    with SessionLocal() as session:
        message = session.get(Message, message_id)
        commitment = record_from_message(session, message, actor="operador")
        session.commit()
        assert commitment.promise_text == message.text
        assert commitment.actor == "operador"
        assert commitment.conversation_id == conversation_id
        assert commitment.customer_id == customer_id
        assert commitment.source_message_id == message_id
        assert commitment.due_at is not None


def test_same_source_message_is_recorded_once():
    _, _, message_id = _message("Le confirmo mañana.")
    with SessionLocal() as session:
        message = session.get(Message, message_id)
        first = record_from_message(session, message, actor="operador")
        second = record_from_message(session, message, actor="operador")
        session.commit()
        assert first is not None
        assert second is first
        assert session.scalar(select(func.count(Commitment.id))) == 1


def test_non_promise_creates_no_commitment():
    _, _, message_id = _message("No calienta la casa.")
    with SessionLocal() as session:
        message = session.get(Message, message_id)
        assert record_from_message(session, message, actor="operador") is None
        session.commit()
        assert session.scalar(select(func.count(Commitment.id))) == 0


def test_vague_date_keeps_due_at_null():
    _, _, message_id = _message("Te aviso a la brevedad.")
    with SessionLocal() as session:
        message = session.get(Message, message_id)
        commitment = record_from_message(session, message, actor="operador")
        session.commit()
        assert commitment is not None
        assert commitment.due_at is None
