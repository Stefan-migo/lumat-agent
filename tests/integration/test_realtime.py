from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal, session_scope
from app.models import Conversation, ConversationEvent, Customer
from app.services.realtime import (
    activity_events,
    dispatch_staged_events,
    record_activity,
    stage_event,
)


def test_activity_history_query_excludes_non_activity_events(migrated_db):
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56900000001")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        record_activity(session, conversation.id, "classified", cause="intent")
        session.add(ConversationEvent(conversation_id=conversation.id, event="state_change"))
        session.commit()

        rows = session.scalars(activity_events(conversation.id)).all()
        assert [row.event for row in rows] == ["classified"]


def test_activity_writer_rejects_unknown_event_without_inserting(migrated_db):
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56900000002")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()

        try:
            record_activity(session, conversation.id, "state_change")
        except ValueError:
            pass
        assert session.scalars(select(ConversationEvent)).all() == []


def test_staged_event_is_dispatched_only_after_commit(migrated_db, monkeypatch):
    published = []

    async def capture(envelope):
        published.append(envelope)

    monkeypatch.setattr("app.services.realtime.publisher.publish", capture)
    with session_scope() as session:
        stage_event(
            session,
            type="conversation",
            conversation_id=12,
            data={"state": "human"},
        )
        assert published == []

    assert published[0].type == "conversation"
    assert published[0].conversation_id == 12


def test_rollback_discards_staged_event(migrated_db, monkeypatch):
    published = []

    async def capture(envelope):
        published.append(envelope)

    monkeypatch.setattr("app.services.realtime.publisher.publish", capture)
    try:
        with session_scope() as session:
            stage_event(session, type="message", conversation_id=12, data={"id": 1})
            raise RuntimeError("abort")
    except RuntimeError:
        pass

    assert published == []
