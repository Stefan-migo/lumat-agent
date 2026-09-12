"""Integration coverage for native SDB typed artifacts and durable state."""

import os

import psycopg
import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import InternalChatThread, Memory, MemoryType, User
from app.services import agent_chat, tukulpan


ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE memories, internal_chat_messages, internal_chat_threads, users "
            "RESTART IDENTITY CASCADE"
        )
    yield


def _thread_id() -> int:
    with SessionLocal() as session:
        user = User(username="sdb-admin", password_hash="test", role="admin")
        session.add(user)
        session.flush()
        thread = InternalChatThread(user_id=user.id)
        session.add(thread)
        session.commit()
        return thread.id


def _rows(thread_id: int) -> list[Memory]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(Memory)
                .where(Memory.scope == "panel", Memory.entity_id == f"thread:{thread_id}")
                .order_by(Memory.topic_key)
            )
        )


def test_sdb_artifacts_use_typed_memory_keys_and_default_project():
    thread_id = _thread_id()
    with SessionLocal() as session:
        tukulpan.persist_sdb_artifact(
            session,
            thread_id=thread_id,
            run_id="run-1",
            kind="spec",
            payload={"scope": {"entities": ["service history"]}},
        )
        tukulpan.persist_sdb_artifact(
            session,
            thread_id=thread_id,
            run_id="run-1",
            kind="state",
            sequence=1,
            payload={"phase": "EXECUTE"},
        )
        tukulpan.persist_sdb_artifact(
            session,
            thread_id=thread_id,
            run_id="run-1",
            kind="result",
            task_id="task-1",
            payload={"status": "completed"},
        )
        session.commit()

    rows = _rows(thread_id)
    assert [(row.topic_key, row.tipo) for row in rows] == [
        ("sdb:run-1:result:task-1", MemoryType.DISCOVERY),
        ("sdb:run-1:spec", MemoryType.PATTERN),
        ("sdb:run-1:state:1", MemoryType.SESSION),
    ]
    assert all(row.proyecto == "default" for row in rows)
    assert all(row.scope == "panel" and row.entity_id == f"thread:{thread_id}" for row in rows)


def test_sdb_artifact_explicit_project_reaches_guard_before_write():
    thread_id = _thread_id()
    with SessionLocal() as session:
        with pytest.raises(ValueError, match="proyecto='default'"):
            tukulpan.persist_sdb_artifact(
                session,
                thread_id=thread_id,
                run_id="run-2",
                kind="spec",
                payload={"scope": {}},
                proyecto="other",
            )
        assert session.scalar(select(func.count()).select_from(Memory)) == 0


def test_existing_panel_seams_propagate_explicit_default_project():
    thread_id = _thread_id()
    with SessionLocal() as session:
        milestone = tukulpan.record_milestone(
            session,
            thread_id=thread_id,
            topic_key="milestone",
            title="Milestone",
            content="SDB started",
            proyecto="default",
        )
        decision = tukulpan.record_decision(
            session,
            thread_id=thread_id,
            topic_key="decision",
            title="Decision",
            content="Use bounded persistence",
            proyecto="default",
        )
        session.commit()
    assert milestone.proyecto == decision.proyecto == "default"


def test_sdb_artifacts_bound_spec_and_checkpoint_result_payloads():
    thread_id = _thread_id()
    with SessionLocal() as session:
        spec = tukulpan.persist_sdb_artifact(
            session,
            thread_id=thread_id,
            run_id="run-3",
            kind="spec",
            payload={"text": "x" * 20_000},
        )
        state = tukulpan.persist_sdb_artifact(
            session,
            thread_id=thread_id,
            run_id="run-3",
            kind="state",
            sequence=2,
            payload={"text": "x" * 20_000},
        )
        result = tukulpan.persist_sdb_artifact(
            session,
            thread_id=thread_id,
            run_id="run-3",
            kind="result",
            task_id="task-3",
            payload={"text": "x" * 20_000},
        )
        assert len(spec.contenido.encode()) <= 8 * 1024
        assert len(state.contenido.encode()) <= 4 * 1024
        assert len(result.contenido.encode()) <= 4 * 1024


def test_sdb_state_persists_phase_checkpoints_and_ordered_events():
    thread_id = _thread_id()
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        agent_chat.persist_sdb_state(
            session,
            thread,
            run_id="run-4",
            phase="EXECUTE",
            checkpoint={"sequence": 1, "task_id": "task-1", "status": "completed"},
            events=[{"type": "phase", "sequence": 0}, {"type": "checkpoint", "sequence": 1}],
        )
        session.commit()

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        state = thread.assistant_state
        assert state["sdb"]["phase"] == "EXECUTE"
        assert state["sdb"]["checkpoints"] == [
            {"sequence": 1, "task_id": "task-1", "status": "completed"}
        ]
        assert [event["sequence"] for event in state["events"]] == [0, 1]


def test_sdb_state_writes_one_checkpoint_row_per_task_sequence():
    thread_id = _thread_id()
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        for sequence, task_id in ((1, "task-1"), (2, "task-2")):
            agent_chat.persist_sdb_state(
                session,
                thread,
                run_id="run-5",
                phase="EXECUTE",
                checkpoint={"sequence": sequence, "task_id": task_id, "status": "completed"},
                events=[{"type": "checkpoint", "sequence": sequence}],
            )
        session.commit()

    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(Memory).where(
                    Memory.entity_id == f"thread:{thread_id}",
                    Memory.topic_key.like("sdb:run-5:state:%"),
                )
            )
        )
    assert {row.topic_key for row in rows} == {
        "sdb:run-5:state:1", "sdb:run-5:state:2"
    }
