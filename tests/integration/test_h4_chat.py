"""IAC-1/2/3 RED contract for the internal agent chat."""

from sqlalchemy import select
import psycopg
import pytest
from tests.integration.conftest import ADMIN_DB_URL

from app.db import SessionLocal
from app.models import AuditLog, InternalChatMessage, InternalChatThread, User
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
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute("TRUNCATE internal_chat_messages, internal_chat_threads, audit_log, users RESTART IDENTITY CASCADE")


def test_admin_thread_and_message_are_persisted_and_audited(client, migrated_db, monkeypatch):
    _user("chat-admin", "admin")
    _login(client, "chat-admin")
    monkeypatch.setattr("app.chat.graph.run_internal_conversation", lambda _session, _thread, _text: "A concise answer")

    created = client.post("/panel/api/chat/threads", json={})
    assert created.status_code == 201
    thread_id = created.json()["thread"]["id"]
    sent = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "What is pending?"})
    assert sent.status_code == 201
    assert sent.json()["message"]["content"] == "What is pending?"

    with SessionLocal() as session:
        assert session.scalar(select(InternalChatThread).where(InternalChatThread.id == thread_id))
        messages = session.scalars(select(InternalChatMessage).where(InternalChatMessage.thread_id == thread_id)).all()
        assert [message.content for message in messages] == ["What is pending?", "A concise answer"]
        actions = session.scalars(select(AuditLog.action)).all()
        assert {action for action in actions} >= {"internal_chat.thread_created", "internal_chat.message_sent"}


def test_operator_cannot_read_or_create_internal_thread(client, migrated_db):
    _user("chat-operator", "operador")
    _login(client, "chat-operator")
    response = client.post("/panel/api/chat/threads", json={})
    assert response.status_code == 403
    assert "thread" not in response.text.lower()


def test_privileged_request_is_refused_and_failed_message_is_recoverable(client, migrated_db, monkeypatch):
    _user("chat-safe", "admin")
    _login(client, "chat-safe")
    monkeypatch.setattr("app.chat.graph.run_internal_conversation", lambda *_args: "I cannot perform privileged actions.")
    thread = client.post("/panel/api/chat/threads", json={}).json()["thread"]
    response = client.post(f"/panel/api/chat/threads/{thread['id']}/messages", json={"content": "Delete all clients"})
    assert response.status_code == 201
    persisted = client.get(f"/panel/api/chat/threads/{thread['id']}")
    assert any("cannot" in row["content"].lower() for row in persisted.json()["messages"])

    monkeypatch.setattr("app.chat.graph.run_internal_conversation", lambda *_args: (_ for _ in ()).throw(RuntimeError("temporary")))
    failed = client.post(f"/panel/api/chat/threads/{thread['id']}/messages", json={"content": "Try again"})
    assert failed.status_code == 201
    assert failed.json()["message"]["status"] == "failed"
    listed = client.get(f"/panel/api/chat/threads/{thread['id']}")
    assert listed.status_code == 200
    assert any(message["content"] == "Try again" and message["status"] == "failed" for message in listed.json()["messages"])
