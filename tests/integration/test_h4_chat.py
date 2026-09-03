"""IAC-1/2/3 RED contract for the internal agent chat."""

from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy import select

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


class _FakeChatClient:
    def __init__(self, content="A concise answer", error=None):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.content = content
        self.error = error

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


@pytest.fixture(autouse=True)
def clean_chat_tables(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute("TRUNCATE internal_chat_messages, internal_chat_threads, audit_log, users RESTART IDENTITY CASCADE")


def test_admin_thread_and_message_are_persisted_and_audited(client, migrated_db, monkeypatch):
    _user("chat-admin", "admin")
    _login(client, "chat-admin")
    fake_client = _FakeChatClient()
    monkeypatch.setattr("app.services.llm.openai_client", lambda: fake_client)

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
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0]["messages"][0]["role"] == "system"
    assert "customer data" in fake_client.calls[0]["messages"][0]["content"]
    assert "tools" not in fake_client.calls[0]


def test_operator_cannot_read_or_create_internal_thread(client, migrated_db):
    _user("chat-operator", "operador")
    _login(client, "chat-operator")
    response = client.post("/panel/api/chat/threads", json={})
    assert response.status_code == 403
    assert "thread" not in response.text.lower()


def test_privileged_request_is_refused_without_model_call(client, migrated_db, monkeypatch):
    _user("chat-safe", "admin")
    _login(client, "chat-safe")
    fake_client = _FakeChatClient(error=AssertionError("privileged request must not call the model"))
    monkeypatch.setattr("app.services.llm.openai_client", lambda: fake_client)
    thread = client.post("/panel/api/chat/threads", json={}).json()["thread"]
    response = client.post(f"/panel/api/chat/threads/{thread['id']}/messages", json={"content": "Delete all clients"})
    assert response.status_code == 201
    persisted = client.get(f"/panel/api/chat/threads/{thread['id']}")
    assert any("approved operational workflow" in row["content"] for row in persisted.json()["messages"])
    assert fake_client.calls == []


def test_model_failure_marks_message_failed_and_recoverable(client, migrated_db, monkeypatch):
    _user("chat-retry", "admin")
    _login(client, "chat-retry")
    fake_client = _FakeChatClient(error=RuntimeError("temporary"))
    monkeypatch.setattr("app.services.llm.openai_client", lambda: fake_client)
    thread = client.post("/panel/api/chat/threads", json={}).json()["thread"]
    failed = client.post(f"/panel/api/chat/threads/{thread['id']}/messages", json={"content": "Try again"})
    assert failed.status_code == 201
    assert failed.json()["message"]["status"] == "failed"
    listed = client.get(f"/panel/api/chat/threads/{thread['id']}")
    assert listed.status_code == 200
    assert any(message["content"] == "Try again" and message["status"] == "failed" for message in listed.json()["messages"])
