"""Database-backed isolation and cross-project proof for the assistant user axis."""

from sqlalchemy import select

from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.db import SessionLocal
from app.models import Memory, Project, User, UserRole
from app.services.tukulpan import MemoryVisibility


def _user(session, username: str) -> User:
    row = User(username=username, password_hash="test-hash", role=UserRole.ADMIN)
    session.add(row)
    session.flush()
    return row


def _project(session, owner_id: int, slug: str) -> None:
    session.add(Project(
        owner_id=owner_id, slug=slug, name=slug, purpose="A test project",
        purpose_embedding=[0.0] * 384,
    ))
    session.flush()


def _write(session, owner_id: int, proyecto: str = "default"):
    return execute_tool(
        session,
        "memory.write",
        {
            "titulo": "Personal preference",
            "contenido": "Prefers concise explanations.",
            "topic_key": "agent:communication-preference",
            "tipo": "preference",
            "visibility": "user",
        },
        trusted_thread_id=91,
        owner_id=owner_id,
        proyecto=proyecto,
        role="admin",
    )


def _read(session, owner_id: int, proyecto: str):
    result = execute_tool(
        session,
        "memory.read",
        {"scope": "own", "limit": 10},
        trusted_thread_id=91,
        owner_id=owner_id,
        proyecto=proyecto,
        role="admin",
    )
    assert result["status"] == "completed"
    return result["result"]


def test_user_axis_row_is_persisted_with_global_visibility_and_isolated_cross_project(fake_embedder, migrated_db):
    with SessionLocal() as session:
        user_a = _user(session, "memory-user-a")
        user_b = _user(session, "memory-user-b")
        _project(session, user_a.id, "user-a-project")
        _project(session, user_b.id, "user-b-project")
        session.commit()
        owner_a, owner_b = user_a.id, user_b.id

    with SessionLocal() as session:
        written = _write(session, owner_a, "user-a-project")
        assert written["status"] == "completed"
        assert written["result"]["written"] is True
        session.commit()
        row = session.scalar(select(Memory).where(Memory.topic_key == "agent:communication-preference"))
        assert row is not None
        assert row.visibility == MemoryVisibility.GLOBAL
        assert row.scope == "user"
        assert row.entity_id == f"user:{owner_a}"
        assert row.proyecto == "default"
        assert row.owner_id == owner_a

    with SessionLocal() as session:
        assert any(row["scope"] == "user" for row in _read(session, owner_a, "default"))
    with SessionLocal() as session:
        assert any(row["scope"] == "user" for row in _read(session, owner_a, "user-a-project"))
    for proyecto in ("default", "user-b-project"):
        with SessionLocal() as session:
            assert all(row["scope"] != "user" for row in _read(session, owner_b, proyecto))


def test_user_visibility_without_authenticated_owner_fails_without_writing(fake_embedder, migrated_db):
    with SessionLocal() as session:
        user = _user(session, "memory-user-no-auth")
        session.commit()
        owner_id = user.id

    with SessionLocal() as session:
        try:
            execute_tool(
                session,
                "memory.write",
                {
                    "titulo": "Personal preference",
                    "contenido": "Must not persist.",
                    "topic_key": "agent:unauthenticated",
                    "tipo": "preference",
                    "visibility": "user",
                },
                trusted_thread_id=92,
                role="admin",
            )
        except ToolValidationError:
            pass
        else:
            raise AssertionError("user-axis write unexpectedly accepted a missing authenticated owner")
        assert session.scalar(select(Memory.id).where(Memory.topic_key == "agent:unauthenticated")) is None

    with SessionLocal() as session:
        assert session.scalar(select(Memory.id).where(Memory.topic_key == "agent:unauthenticated")) is None
        assert owner_id > 0
