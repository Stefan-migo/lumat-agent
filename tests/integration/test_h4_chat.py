"""IAC-1/2/3 RED contract for the internal agent chat."""

import json
from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy import select

from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()

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
    """Streaming-compatible fake for the assistant graph (IAC-6)."""

    def __init__(self, content="A concise answer", error=None):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.content = content
        self.error = error

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        if not kwargs.get("stream"):
            # The planner call needs a readable plan, or the turn degrades before any answer streams.
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
                "kind": "respond", "arguments": {}, "summary": "ok", "requires_approval": False,
            })))])
        parts = self.content.split(" ") if self.content else [""]
        return [
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=part + (" " if index < len(parts) - 1 else "")))])
            for index, part in enumerate(parts)
        ]


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
        messages = session.scalars(
            select(InternalChatMessage).where(InternalChatMessage.thread_id == thread_id).order_by(InternalChatMessage.id)
        ).all()
        assert [message.content for message in messages] == ["What is pending?", "A concise answer"]
        actions = session.scalars(select(AuditLog.action)).all()
        assert {action for action in actions} >= {"internal_chat.thread_created", "internal_chat.message_sent"}
        # One message, one audit row: `_run_agent_turn_session` already records
        # `message_sent` unconditionally with the final status, so the outer
        # callers must not record it a second time.
        assert actions.count("internal_chat.message_sent") == 1
    assert len(fake_client.calls) == 3
    assert fake_client.calls[1]["stream"] is True
    assert fake_client.calls[1]["messages"][0]["role"] == "system"
    assert "Lumat internal executive operator" in fake_client.calls[1]["messages"][0]["content"]
    assert "tools" not in fake_client.calls[1]
    assert "stream" not in fake_client.calls[2]


def test_operator_cannot_read_or_create_internal_thread(client, migrated_db):
    _user("chat-operator", "operador")
    _login(client, "chat-operator")
    response = client.post("/panel/api/chat/threads", json={})
    assert response.status_code == 403
    assert "thread" not in response.text.lower()


def test_privileged_request_requires_approval_without_model_call(client, migrated_db, monkeypatch):
    _user("chat-safe", "admin")
    _login(client, "chat-safe")
    fake_client = _FakeChatClient(error=AssertionError("privileged request must not call the model"))
    monkeypatch.setattr("app.services.llm.openai_client", lambda: fake_client)
    thread = client.post("/panel/api/chat/threads", json={}).json()["thread"]
    response = client.post(f"/panel/api/chat/threads/{thread['id']}/messages", json={"content": "Delete all clients"})
    assert response.status_code == 201
    persisted = client.get(f"/panel/api/chat/threads/{thread['id']}")
    assert persisted.status_code == 200
    assert persisted.json()["messages"][0]["status"] == "approval_pending"
    contents = [row["content"] for row in persisted.json()["messages"]]
    assert contents == ["Delete all clients"]
    assert len(fake_client.calls) == 1


def test_model_failure_marks_message_failed_and_recoverable(client, migrated_db, monkeypatch):
    _user("chat-retry", "admin")
    _login(client, "chat-retry")
    fake_client = _FakeChatClient(error=RuntimeError("temporary"))
    monkeypatch.setattr("app.services.llm.openai_client", lambda: fake_client)
    thread = client.post("/panel/api/chat/threads", json={}).json()["thread"]
    failed = client.post(f"/panel/api/chat/threads/{thread['id']}/messages", json={"content": "Try again"})
    assert failed.status_code == 201
    listed = client.get(f"/panel/api/chat/threads/{thread['id']}")
    assert listed.status_code == 200
    assert any(message["content"] == "Try again" and message["status"] == "failed" for message in listed.json()["messages"])
