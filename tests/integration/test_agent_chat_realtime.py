"""IAC-6 / CRT-3 RED contract for internal chat token delivery."""

from types import SimpleNamespace

import psycopg
import pytest

from tests.integration.conftest import ADMIN_DB_URL

from app.db import SessionLocal
from app.models import InternalChatMessage, User
from app.services.users import hash_password


def _user(username: str, role: str) -> None:
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role=role))
        session.commit()


def _login(client, username: str) -> None:
    response = client.post("/panel/api/login", json={"username": username, "password": "pass"})
    assert response.status_code == 200


class _StreamingChatClient:
    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return [
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=chunk))])
            for chunk in self.chunks
        ]


@pytest.fixture(autouse=True)
def clean_chat_tables(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE internal_chat_messages, internal_chat_threads, audit_log, users RESTART IDENTITY CASCADE"
        )


def test_internal_chat_publishes_ordered_tokens_and_keeps_post_response(client, monkeypatch):
    _user("stream-admin", "admin")
    _login(client, "stream-admin")
    fake_client = _StreamingChatClient(["A ", "streamed", " answer"])
    monkeypatch.setattr("app.services.llm.openai_client", lambda: fake_client)
    published = []

    async def capture(envelope):
        published.append(envelope)

    monkeypatch.setattr("app.services.realtime.publisher.publish", capture)
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]

    response = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "What is pending?"}
    )

    assert response.status_code == 201
    assert response.json()["message"]["content"] == "What is pending?"
    token_events = [event for event in published if event.type == "token"]
    assert [event.data["token"] for event in token_events] == ["A ", "streamed", " answer"]
    assert all(event.conversation_id == thread_id for event in token_events)
    assert published[-1].type == "message"
    assert published[-1].conversation_id == thread_id
    assert published[-1].data["content"] == "A streamed answer"
    assert fake_client.calls[0]["stream"] is True

    with SessionLocal() as session:
        messages = session.query(InternalChatMessage).filter_by(thread_id=thread_id).all()
        assert [message.content for message in messages] == ["What is pending?", "A streamed answer"]


def test_token_delivery_failure_does_not_change_persisted_post_contract(client, monkeypatch):
    _user("failure-admin", "admin")
    _login(client, "failure-admin")
    monkeypatch.setattr("app.services.llm.openai_client", lambda: _StreamingChatClient(["complete"]))

    async def fail(_envelope):
        raise RuntimeError("subscriber disappeared")

    monkeypatch.setattr("app.services.realtime.publisher.publish", fail)
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]

    response = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Continue"}
    )

    assert response.status_code == 201
    assert response.json()["message"]["status"] == "processed"
    assert response.json()["message"]["content"] == "Continue"
    persisted = client.get(f"/panel/api/chat/threads/{thread_id}").json()["messages"]
    assert [message["content"] for message in persisted] == ["Continue", "complete"]


def test_operator_remains_denied_from_internal_chat(client):
    _user("stream-operator", "operador")
    _login(client, "stream-operator")

    response = client.post("/panel/api/chat/threads", json={})

    assert response.status_code == 403
    assert "thread" not in response.text.lower()
