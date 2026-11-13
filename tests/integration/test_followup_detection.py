from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    Commitment,
    Conversation,
    ConversationEvent,
    ConversationState,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.followup import detect_pending, sweep_followup


def _conversation(phone: str, *, state=ConversationState.HUMAN):
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone, name="Ana")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=phone, state=state)
        session.add(conversation)
        session.flush()
        conversation_id = conversation.id
        session.commit()
        return conversation_id


def _message(conversation_id: int, direction: MessageDirection, created_at: datetime):
    with SessionLocal() as session:
        session.add(Message(
            conversation_id=conversation_id,
            direction=direction,
            msg_type=MessageType.TEXT,
            status=MessageStatus.PROCESSED,
            text="Consulta",
            created_at=created_at,
        ))
        session.commit()


def test_detects_idle_inbound_but_not_replied_recent_or_closed():
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    idle = _conversation("+56970000011")
    replied = _conversation("+56970000012")
    recent = _conversation("+56970000013")
    closed = _conversation("+56970000014", state=ConversationState.CLOSED)
    for conversation_id in (idle, replied, closed):
        _message(conversation_id, MessageDirection.INBOUND, now - timedelta(hours=30))
    _message(replied, MessageDirection.OUTBOUND, now - timedelta(hours=1))
    _message(recent, MessageDirection.INBOUND, now - timedelta(hours=12))

    with SessionLocal() as session:
        detected = detect_pending(session, now=now)
        idle_ids = {item.conversation_id for item in detected if item.event == "idle_thread"}
        assert idle_ids == {idle}


def test_detects_overdue_but_not_future_commitment():
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    overdue_id = _conversation("+56970000015")
    future_id = _conversation("+56970000016")
    with SessionLocal() as session:
        for conversation_id, due_at in (
            (overdue_id, now - timedelta(days=3)),
            (future_id, now + timedelta(days=3)),
        ):
            conversation = session.get(Conversation, conversation_id)
            session.add(Commitment(
                conversation_id=conversation_id,
                customer_id=conversation.customer_id,
                promise_text="Le confirmo",
                actor="operador",
                due_at=due_at,
                status="pendiente",
            ))
        session.commit()

    with SessionLocal() as session:
        detected = detect_pending(session, now=now)
        overdue_ids = {
            item.conversation_id for item in detected if item.event == "commitment_overdue"
        }
        assert overdue_ids == {overdue_id}


def test_sweep_deduplicates_each_followup_fact():
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    conversation_id = _conversation("+56970000017")
    _message(conversation_id, MessageDirection.INBOUND, now - timedelta(hours=30))
    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        session.add(Commitment(
            conversation_id=conversation_id,
            customer_id=conversation.customer_id,
            promise_text="Le confirmo",
            actor="operador",
            due_at=now - timedelta(days=2),
            status="pendiente",
        ))
        session.commit()

    for _ in range(2):
        with SessionLocal() as session:
            sweep_followup(session, now=now)
            session.commit()

    with SessionLocal() as session:
        counts = dict(session.execute(
            select(ConversationEvent.event, func.count(ConversationEvent.id))
            .where(ConversationEvent.conversation_id == conversation_id)
            .group_by(ConversationEvent.event)
        ).all())
        assert counts == {"idle_thread": 1, "commitment_overdue": 1}
        events = session.scalars(select(ConversationEvent).where(
            ConversationEvent.conversation_id == conversation_id
        )).all()
        assert all(event.actor == "bot" and event.cause for event in events)


def test_two_overdue_commitments_on_one_conversation_are_two_facts():
    """Dedupe is per fact: the second overdue commitment is not swallowed."""
    conversation_id = _conversation(f"+5691{uuid4().int % 10_000_000:07d}")
    with SessionLocal() as session:
        customer_id = session.get(Conversation, conversation_id).customer_id
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        for days in (2, 5):
            session.add(Commitment(
                conversation_id=conversation_id,
                customer_id=customer_id,
                promise_text="Le confirmo el valor.",
                actor="operador",
                due_at=now - timedelta(days=days),
                status="pendiente",
            ))
        session.commit()

    with SessionLocal() as session:
        assert sweep_followup(session, now=now) == 2
        cause = session.scalars(
            select(ConversationEvent.cause).where(
                ConversationEvent.conversation_id == conversation_id,
                ConversationEvent.event == "commitment_overdue",
            )
        ).all()
        session.commit()

    assert len(cause) == 2


def test_a_second_silence_after_a_reply_is_a_new_fact():
    """Dedupe keyed by event type alone lost every silence after the first."""
    conversation_id = _conversation(f"+5691{uuid4().int % 10_000_000:07d}")
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add(Message(
            conversation_id=conversation_id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text="no calienta",
            status=MessageStatus.RECEIVED,
            created_at=now - timedelta(hours=48),
        ))
        session.commit()
    with SessionLocal() as session:
        assert sweep_followup(session, now=now) == 1
        session.commit()

    with SessionLocal() as session:
        session.add(Message(
            conversation_id=conversation_id,
            direction=MessageDirection.OUTBOUND,
            msg_type=MessageType.TEXT,
            text="Vamos a revisarlo.",
            status=MessageStatus.PROCESSED,
            created_at=now - timedelta(hours=40),
        ))
        session.add(Message(
            conversation_id=conversation_id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text="sigue igual",
            status=MessageStatus.RECEIVED,
            created_at=now - timedelta(hours=30),
        ))
        session.commit()

    with SessionLocal() as session:
        assert sweep_followup(session, now=now) == 1
        assert session.scalar(select(func.count(ConversationEvent.id)).where(
            ConversationEvent.conversation_id == conversation_id,
            ConversationEvent.event == "idle_thread",
        )) == 2
        session.commit()
