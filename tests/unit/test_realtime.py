import asyncio

import pytest

from app.services.realtime import (
    ACTIVITY_EVENTS,
    RealtimeEnvelope,
    RealtimePublisher,
    validate_activity_event,
    dispatch_staged_events,
    stage_event,
)


def test_activity_validator_accepts_only_activity_vocabulary():
    assert ACTIVITY_EVENTS == {"classified", "kb_retrieved", "kb_miss", "escalation"}
    for event in ("classified", "kb_retrieved", "kb_miss", "escalation"):
        assert validate_activity_event(event) == event
    with pytest.raises(ValueError, match="unsupported activity event"):
        validate_activity_event("state_change")


def test_envelope_serializes_the_shared_contract_and_rejects_unknown_type():
    envelope = RealtimeEnvelope(
        type="activity", conversation_id=42, data={"event": "classified"}
    )
    assert envelope.model_dump() == {
        "type": "activity",
        "conversation_id": 42,
        "data": {"event": "classified"},
    }
    with pytest.raises(ValueError):
        RealtimeEnvelope(type="unknown", data={})

    assert RealtimeEnvelope(type="snapshot", data=[{"id": 1}]).conversation_id is None


def test_publisher_filters_by_conversation_and_preserves_order():
    async def scenario():
        publisher = RealtimePublisher(queue_size=4)
        matching = await publisher.subscribe(conversation_id=42)
        global_subscriber = await publisher.subscribe()

        await publisher.publish(RealtimeEnvelope(type="message", conversation_id=42, data={"n": 1}))
        await publisher.publish(RealtimeEnvelope(type="activity", conversation_id=7, data={"n": 2}))

        assert (await matching.queue.get()).data == {"n": 1}
        assert (await global_subscriber.queue.get()).data == {"n": 1}
        assert (await global_subscriber.queue.get()).data == {"n": 2}
        await matching.close()
        await global_subscriber.close()
        assert publisher.subscriber_count == 0

    asyncio.run(scenario())


def test_publisher_drops_full_subscribers_and_cleans_them_up():
    async def scenario():
        publisher = RealtimePublisher(queue_size=1)
        subscriber = await publisher.subscribe(conversation_id=42)
        event = RealtimeEnvelope(type="conversation", conversation_id=42, data={})

        await publisher.publish(event)
        await publisher.publish(event)

        assert publisher.subscriber_count == 0
        assert subscriber.closed

    asyncio.run(scenario())


def test_publication_failure_does_not_escape_the_commit_boundary(monkeypatch):
    class Session:
        info = {}

    async def fail(_envelope):
        raise RuntimeError("subscriber disappeared")

    monkeypatch.setattr("app.services.realtime.publisher.publish", fail)
    session = Session()
    stage_event(session, type="message", conversation_id=9, data={"id": 1})

    dispatch_staged_events(session)
    assert "realtime_events" not in session.info
