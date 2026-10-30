from __future__ import annotations

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, Memory, MemoryProducer, MemoryStatus, MemoryType, MemoryVisibility, User, UserRole
from app.services import tukulpan
from app.services.users import hash_password


@pytest.fixture(autouse=True)
def _fake_memory_embedding(monkeypatch):
    monkeypatch.setattr(tukulpan, "_embed", lambda texts: [[0.0] * 384 for _ in texts])


@pytest.fixture
def panel_users():
    created_ids: list[int] = []

    def create(username: str, role: str = "operador") -> tuple[int, str, str]:
        username = f"{username}-{uuid4().hex}"
        password = "test-password"
        with SessionLocal() as session:
            user = User(
                username=username,
                password_hash=hash_password(password),
                role=UserRole(role),
                active=True,
            )
            session.add(user)
            session.flush()
            user_id = user.id
            session.commit()
        created_ids.append(user_id)
        return user_id, password, username

    yield create

    with SessionLocal() as session:
        session.execute(Memory.__table__.delete().where(Memory.owner_id.in_(created_ids)))
        session.execute(User.__table__.delete().where(User.id.in_(created_ids)))
        session.commit()


def _upsert_user_memory(owner_id: int, topic_key: str, content: str) -> Memory:
    with SessionLocal() as session:
        row = tukulpan.upsert(
            session,
            scope="user",
            entity_id=f"user:{owner_id}",
            owner_id=owner_id,
            proyecto="default",
            topic_key=topic_key,
            tipo=MemoryType.PREFERENCE,
            titulo=topic_key,
            contenido=content,
            visibility=MemoryVisibility.GLOBAL,
            producer=MemoryProducer.SYSTEM,
        )
        session.commit()
        return row


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post("/panel/api/login", json={"username": username, "password": password})
    assert response.status_code == 200


def test_list_returns_only_callers_user_axis_rows_and_excludes_archived(client, panel_users):
    owner_id, password, username = panel_users("mem-owner")
    other_id, _, _ = panel_users("mem-other")
    own_old = _upsert_user_memory(owner_id, "own-old", "old personal fact")
    own_new = _upsert_user_memory(owner_id, "own-new", "new personal fact")
    archived = _upsert_user_memory(owner_id, "own-archived", "archived personal fact")
    other = _upsert_user_memory(other_id, "other", "another user's fact")
    with SessionLocal() as session:
        archived_row = session.get(Memory, archived.id)
        archived_row.status = MemoryStatus.ARCHIVED
        session.commit()

    _login(client, username, password)
    response = client.get("/panel/api/assistant/memories")

    assert response.status_code == 200
    payload = response.json()
    assert list(payload) == ["memories"]
    rows = payload["memories"]
    assert [row["id"] for row in rows] == [own_new.id, own_old.id]
    assert all(row["id"] != other.id for row in rows)
    assert all(set(row) == {"id", "titulo", "contenido", "tipo", "topic_key", "created_at", "updated_at", "review_after"} for row in rows)
    assert [row["topic_key"] for row in rows] == ["own-new", "own-old"]


def test_list_requires_authentication(client):
    response = client.get("/panel/api/assistant/memories")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_outside_business_memory_roles_are_denied(client, panel_users):
    _, password, username = panel_users("mem-technician", role="tecnico")
    _login(client, username, password)

    response = client.get("/panel/api/assistant/memories")

    assert response.status_code == 403
    assert response.json() == {"detail": "panel role required"}


def test_delete_own_memory_returns_204_and_removes_row(client, panel_users):
    owner_id, password, username = panel_users("mem-delete-owner")
    row = _upsert_user_memory(owner_id, "delete-own", "delete this personal fact")
    _login(client, username, password)

    response = client.delete(f"/panel/api/assistant/memories/{row.id}")

    assert response.status_code == 204
    assert response.content == b""
    with SessionLocal() as session:
        assert session.get(Memory, row.id) is None
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "memory.deleted", AuditLog.entity_id == str(row.id)))
        assert audit is not None
        assert audit.actor == username


def test_delete_another_users_memory_is_not_found_and_preserves_row(client, panel_users):
    owner_id, password, username = panel_users("mem-delete-caller")
    other_id, _, _ = panel_users("mem-delete-other")
    row = _upsert_user_memory(other_id, "not-yours", "keep another user's fact")
    _login(client, username, password)

    response = client.delete(f"/panel/api/assistant/memories/{row.id}")

    assert response.status_code == 404
    with SessionLocal() as session:
        assert session.get(Memory, row.id) is not None

