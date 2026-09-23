"""Concurrency regressions for the memory write identities."""

import threading
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import Memory, MemoryType
from app.services import tukulpan as memory


def _run_conflict(*, loser_topic_key: str, winner_topic_key: str) -> None:
    reached_insert = threading.Event()
    winner_committed = threading.Event()
    errors: list[BaseException] = []

    def lose():
        with SessionLocal() as session:
            parked = False

            def park_before_insert(session, flush_context, instances):
                nonlocal parked
                if parked:
                    return
                parked = True
                reached_insert.set()
                if not winner_committed.wait(timeout=10):
                    raise RuntimeError("winner did not commit before loser timeout")

            event.listen(session, "before_flush", park_before_insert)
            try:
                memory.upsert(
                    session,
                    scope="customer",
                    entity_id="42",
                    topic_key=loser_topic_key,
                    tipo=MemoryType.DECISION,
                    titulo="Fact",
                    contenido="The customer prefers afternoon visits.",
                )
                session.commit()
            except BaseException as error:
                errors.append(error)
            finally:
                event.remove(session, "before_flush", park_before_insert)

    loser = threading.Thread(target=lose)
    loser.start()
    assert reached_insert.wait(timeout=10), "loser did not reach its INSERT"

    with SessionLocal() as session:
        memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key=winner_topic_key,
            tipo=MemoryType.DECISION,
            titulo="Fact",
            contenido="The customer prefers afternoon visits.",
        )
        session.commit()

    winner_committed.set()
    loser.join(timeout=10)
    assert not loser.is_alive(), "loser did not finish after winner committed"
    assert not errors


def test_concurrent_identical_content_different_keys_folds_duplicate(
    fake_embedder, migrated_db
):
    _run_conflict(loser_topic_key="loser", winner_topic_key="winner")

    with SessionLocal() as session:
        rows = session.scalars(select(Memory).where(Memory.entity_id == "42")).all()
        assert len(rows) == 1
        assert rows[0].duplicate_count == 2


def test_concurrent_identical_content_same_key_revises_one_row(fake_embedder, migrated_db):
    _run_conflict(loser_topic_key="fact", winner_topic_key="fact")

    with SessionLocal() as session:
        assert session.query(Memory).filter_by(entity_id="42").count() == 1


def test_third_writer_re_raises_when_it_loses_both_bounded_attempts(
    fake_embedder, migrated_db
):
    entity_id = f"third-writer-{uuid4().hex}"
    content = "The customer prefers afternoon visits."
    writer_a_ready = threading.Event()
    allow_writer_a = threading.Event()
    writer_a_committed = threading.Event()
    writer_c_first_ready = threading.Event()
    allow_writer_c_first = threading.Event()
    writer_c_first_failed = threading.Event()
    release_writer_c_retry = threading.Event()
    writer_c_retry_ready = threading.Event()
    writer_b_ready = threading.Event()
    allow_writer_b = threading.Event()
    writer_b_committed = threading.Event()
    errors: dict[str, BaseException] = {}

    def wait_for(signal: threading.Event, description: str) -> None:
        if not signal.wait(timeout=10):
            raise RuntimeError(f"timed out waiting for {description}")

    def write(name: str, topic_key: str) -> None:
        with SessionLocal() as session:
            retry_phase = False
            flushes = 0

            def before_flush(_session, _flush_context, _instances):
                nonlocal flushes
                flushes += 1
                if name == "a" and flushes == 1:
                    writer_a_ready.set()
                    wait_for(allow_writer_a, "writer A release")
                elif name == "c" and flushes == 1:
                    writer_c_first_ready.set()
                    wait_for(allow_writer_c_first, "writer C first release")
                elif name == "c" and retry_phase and flushes == 2:
                    writer_c_retry_ready.set()
                    wait_for(writer_b_committed, "writer B commit")
                elif name == "b" and flushes == 1:
                    writer_b_ready.set()
                    wait_for(allow_writer_b, "writer B release")

            def after_soft_rollback(_session, _previous_transaction):
                nonlocal retry_phase
                if name != "c" or retry_phase:
                    return
                retry_phase = True
                writer_c_first_failed.set()
                wait_for(release_writer_c_retry, "writer C retry release")

            event.listen(session, "before_flush", before_flush)
            event.listen(session, "after_soft_rollback", after_soft_rollback)
            try:
                memory.upsert(
                    session,
                    scope="customer",
                    entity_id=entity_id,
                    topic_key=topic_key,
                    tipo=MemoryType.DECISION,
                    titulo="Fact",
                    contenido=content,
                )
                session.commit()
                if name == "a":
                    writer_a_committed.set()
                elif name == "b":
                    writer_b_committed.set()
            except BaseException as error:
                errors[name] = error
            finally:
                event.remove(session, "before_flush", before_flush)
                event.remove(session, "after_soft_rollback", after_soft_rollback)

    writer_a = threading.Thread(target=write, args=("a", "writer-a"))
    writer_b = threading.Thread(target=write, args=("b", "writer-b"))
    writer_c = threading.Thread(target=write, args=("c", "writer-c"))
    writer_a.start()
    assert writer_a_ready.wait(timeout=10), "writer A did not reach its INSERT"
    writer_c.start()
    assert writer_c_first_ready.wait(timeout=10), "writer C did not reach its first INSERT"
    allow_writer_a.set()
    assert writer_a_committed.wait(timeout=10), "writer A did not commit"
    allow_writer_c_first.set()
    assert writer_c_first_failed.wait(timeout=10), "writer C did not lose its first attempt"
    with SessionLocal() as session:
        winner = session.scalar(
            select(Memory).where(
                Memory.entity_id == entity_id,
                Memory.topic_key == "writer-a",
            )
        )
        assert winner is not None
        session.delete(winner)
        session.commit()
    release_writer_c_retry.set()
    assert writer_c_retry_ready.wait(timeout=10), "writer C did not reach its retry INSERT"
    writer_b.start()
    assert writer_b_ready.wait(timeout=10), "writer B did not reach its INSERT"
    allow_writer_b.set()
    assert writer_b_committed.wait(timeout=10), "writer B did not commit its retry"

    writer_a.join(timeout=10)
    writer_b.join(timeout=10)
    writer_c.join(timeout=10)
    assert not writer_a.is_alive() and not writer_b.is_alive() and not writer_c.is_alive()
    assert "a" not in errors
    assert "b" not in errors
    assert isinstance(errors.get("c"), IntegrityError)

    with SessionLocal() as session:
        rows = session.scalars(select(Memory).where(Memory.entity_id == entity_id)).all()
        assert [row.topic_key for row in rows] == ["writer-b"]
