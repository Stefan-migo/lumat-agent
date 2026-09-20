"""Concurrency regressions for the memory write identities."""

import threading

import pytest
from sqlalchemy import event, select

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
