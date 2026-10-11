from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import InternalChatThread, Project, User
from app.services.users import hash_password


def _user(username: str, role: str) -> int:
    with SessionLocal() as session:
        row = User(username=username, password_hash=hash_password("pass"), role=role)
        session.add(row)
        session.commit()
        return row.id


def _login(client, username: str):
    response = client.post("/panel/api/login", json={"username": username, "password": "pass"})
    assert response.status_code == 200


@pytest.fixture(autouse=True)
def clean_chat_tables(migrated_db):
    with SessionLocal() as session:
        session.query(InternalChatThread).delete()
        session.query(Project).delete()
        session.query(User).delete()
        session.commit()


def test_thread_creation_without_body_requires_explicit_project(client, migrated_db):
    _user("chat-no-body", "admin")
    _login(client, "chat-no-body")

    response = client.post("/panel/api/chat/threads")

    assert response.status_code == 422


def test_thread_creation_with_empty_object_requires_explicit_project(client, migrated_db):
    _user("chat-empty-body", "admin")
    _login(client, "chat-empty-body")

    response = client.post("/panel/api/chat/threads", json={})

    assert response.status_code == 422


def test_thread_creation_rejects_another_users_project_without_creating_thread(client, migrated_db):
    caller_id = _user("chat-caller", "admin")
    owner_id = _user("chat-other-owner", "admin")
    project_slug = f"other-{uuid4().hex[:8]}"
    with SessionLocal() as session:
        session.add(Project(
            slug=project_slug, name="Other project", purpose="A", purpose_embedding=[0.0] * 384,
            owner_id=owner_id,
        ))
        session.commit()
    _login(client, "chat-caller")

    response = client.post("/panel/api/chat/threads", json={"proyecto": project_slug})

    assert response.status_code == 400
    with SessionLocal() as session:
        assert session.scalar(select(InternalChatThread).where(InternalChatThread.user_id == caller_id)) is None


def test_thread_creation_accepts_callers_own_project(client, migrated_db):
    owner_id = _user("chat-project-owner", "admin")
    project_slug = f"owned-{uuid4().hex[:8]}"
    with SessionLocal() as session:
        session.add(Project(
            slug=project_slug, name="Owned project", purpose="A", purpose_embedding=[0.0] * 384,
            owner_id=owner_id,
        ))
        session.commit()
    _login(client, "chat-project-owner")

    response = client.post("/panel/api/chat/threads", json={"proyecto": project_slug})

    assert response.status_code == 201
    assert response.json()["thread"]["proyecto"] == project_slug


def test_thread_creation_accepts_explicit_default_project(client, migrated_db):
    _user("chat-explicit-default", "admin")
    _login(client, "chat-explicit-default")

    response = client.post("/panel/api/chat/threads", json={"proyecto": "default"})

    assert response.status_code == 201
    assert response.json()["thread"]["proyecto"] == "default"


def test_thread_patch_moves_thread_to_owned_project(client, migrated_db):
    owner_id = _user("chat-move-owner", "admin")
    project_slug = f"move-{uuid4().hex[:8]}"
    with SessionLocal() as session:
        session.add(Project(
            slug=project_slug, name="Move target", purpose="A", purpose_embedding=[0.0] * 384,
            owner_id=owner_id,
        ))
        session.commit()
    _login(client, "chat-move-owner")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

    response = client.patch(f"/panel/api/chat/threads/{thread_id}", json={"proyecto": project_slug})

    assert response.status_code == 200
    assert response.json()["thread"]["proyecto"] == project_slug


def test_thread_patch_rejects_invalid_project_and_default_for_non_business_role(client, migrated_db):
    owner_id = _user("chat-move-invalid", "tecnico")
    project_slug = f"tech-{uuid4().hex[:8]}"
    with SessionLocal() as session:
        session.add(Project(
            slug=project_slug, name="Tech project", purpose="A", purpose_embedding=[0.0] * 384,
            owner_id=owner_id,
        ))
        thread = InternalChatThread(user_id=owner_id, proyecto=project_slug)
        session.add(thread)
        session.commit()
        thread_id = thread.id
    _login(client, "chat-move-invalid")

    invalid = client.patch(f"/panel/api/chat/threads/{thread_id}", json={"proyecto": "missing-project"})
    default = client.patch(f"/panel/api/chat/threads/{thread_id}", json={"proyecto": "default"})

    assert invalid.status_code == 400
    assert default.status_code == 400


def test_thread_patch_requires_a_field_and_preserves_title_rename(client, migrated_db):
    _user("chat-patch-title", "admin")
    _login(client, "chat-patch-title")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

    empty = client.patch(f"/panel/api/chat/threads/{thread_id}", json={})
    renamed = client.patch(f"/panel/api/chat/threads/{thread_id}", json={"title": "Renamed thread"})

    assert empty.status_code == 422
    assert renamed.status_code == 200
    assert renamed.json()["thread"]["title"] == "Renamed thread"


def test_thread_patch_conflicts_while_run_is_active(client, migrated_db):
    owner_id = _user("chat-patch-running", "admin")
    with SessionLocal() as session:
        thread = InternalChatThread(user_id=owner_id, proyecto="default", assistant_state={"live": {"status": "running"}})
        session.add(thread)
        session.commit()
        thread_id = thread.id
    _login(client, "chat-patch-running")

    response = client.patch(f"/panel/api/chat/threads/{thread_id}", json={"title": "Blocked"})

    assert response.status_code == 409
