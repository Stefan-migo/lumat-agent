"""EO-1/2 and DW-1/2/3 integration coverage for the H4 outbox worker."""

from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import DomainEvent, NotificationOperation
from app.ops import worker
from app.services.events import publish_event
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_h4_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute("TRUNCATE domain_events, notification_operations RESTART IDENTITY CASCADE")
    yield


def test_publish_is_transactional_and_deduplicated(migrated_db):
    with SessionLocal() as session:
        event = publish_event(
            session, event_type="case.opened", entity_type="case", entity_id="42",
            payload={"priority": "high"}, dedupe_key="case:42:opened",
        )
        session.commit()
        event_id = event.id

    with SessionLocal() as session:
        duplicate = publish_event(
            session, event_type="case.opened", entity_type="case", entity_id="42",
            payload={"priority": "high"}, dedupe_key="case:42:opened",
        )
        session.commit()
        assert duplicate.id == event_id
        assert session.scalar(select(DomainEvent).where(DomainEvent.id == event_id)).status == "pending"

    with SessionLocal() as session:
        publish_event(
            session, event_type="message.received", entity_type="message", entity_id="99",
            payload={}, dedupe_key="message:99:received",
        )
        session.rollback()
    with SessionLocal() as session:
        assert session.scalar(select(DomainEvent).where(DomainEvent.dedupe_key == "message:99:received")) is None


def test_worker_batches_and_reclaims_expired_leases(migrated_db, monkeypatch):
    with SessionLocal() as session:
        for number in range(3):
            publish_event(session, event_type="test", entity_type="case", entity_id=str(number), payload={}, dedupe_key=f"test:{number}")
        session.commit()

    handled = []
    monkeypatch.setattr(worker, "handle_event", lambda session, event: handled.append(event.dedupe_key))
    assert worker.run_cycle(limit=2, owner="worker-a") == 2
    assert len(handled) == 2

    with SessionLocal() as session:
        event = session.scalar(select(DomainEvent).where(DomainEvent.dedupe_key == "test:2"))
        event.status = "processing"
        event.lease_owner = "dead-worker"
        event.leased_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
    assert worker.run_cycle(limit=1, owner="worker-b") == 1
    assert handled[-1] == "test:2"


def test_worker_is_repeat_safe_and_records_retry_exhaustion(migrated_db, monkeypatch):
    with SessionLocal() as session:
        success = publish_event(session, event_type="notify", entity_type="case", entity_id="1", payload={}, dedupe_key="notify:1")
        failure = publish_event(session, event_type="broken", entity_type="case", entity_id="2", payload={}, dedupe_key="broken:2")
        session.commit()
        success_id, failure_id = success.id, failure.id

    side_effects = []
    monkeypatch.setattr(worker, "handle_event", lambda session, event: side_effects.append(event.id) if event.id == success_id else (_ for _ in ()).throw(RuntimeError("broken")))
    assert worker.run_cycle(limit=2, owner="worker") == 1
    assert worker.run_cycle(limit=2, owner="worker") == 0
    with SessionLocal() as session:
        event = session.get(DomainEvent, failure_id)
        event.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
    assert worker.run_cycle(limit=1, owner="worker") == 0
    with SessionLocal() as session:
        event = session.get(DomainEvent, failure_id)
        event.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
    assert worker.run_cycle(limit=1, owner="worker") == 0
    with SessionLocal() as session:
        event = session.get(DomainEvent, failure_id)
        assert event.status == "failed"
        assert event.attempts == 3
        assert event.error == "broken"
        assert side_effects == [success_id]


def test_event_operation_linkage_and_health_counts(migrated_db):
    with SessionLocal() as session:
        event = publish_event(session, event_type="notify", entity_type="case", entity_id="8", payload={}, dedupe_key="notify:8")
        operation = NotificationOperation(
            recipient="+56911111111", channel="whatsapp", content="hello", source_entity="case",
            source_id="8", idempotency_key="event:notify:8", event_id=event.id,
        )
        session.add(operation)
        session.commit()
        assert operation.event_id == event.id

    counts = worker.health_counts()
    assert counts["pending"] == 1
    assert counts["failed"] == 0
    assert counts["leased"] == 0


def test_worker_main_invokes_bounded_entrypoint(monkeypatch):
    calls = []
    monkeypatch.setenv("H4_WORKER_LIMIT", "7")
    monkeypatch.setenv("H4_WORKER_OWNER", "cli-worker")
    monkeypatch.setattr(worker, "run_cycle", lambda *, limit, owner: calls.append((limit, owner)) or 0)
    worker.main()
    assert calls == [(7, "cli-worker")]
