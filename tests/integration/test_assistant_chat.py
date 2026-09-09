"""PR1 contract tests for the isolated assistant graph boundary."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.db import SessionLocal
from app.chat.assistant.approval import issue_approval, validate_approval
from app.models import InternalChatThread, User
from app.services.users import hash_password
@pytest.fixture(autouse=True)
def assistant_client(monkeypatch):
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: [
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="assistant response"))])
                ]
            )
        )
    )
    monkeypatch.setattr("app.services.llm.openai_client", lambda: client)


def _user(username: str, role: str) -> None:
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role=role))
        session.commit()


def _login(client, username: str) -> None:
    response = client.post("/panel/api/login", json={"username": username, "password": "pass"})
    assert response.status_code == 200
    assert client.get("/panel/api/me").status_code == 200


def test_operator_cannot_read_assistant_stream(client):
    _user("assistant-operator", "operador")
    _login(client, "assistant-operator")

    response = client.get("/panel/api/chat/threads/1/stream")

    assert response.status_code == 403
    assert "plan" not in response.text.lower()
    assert "evidence" not in response.text.lower()


def test_cross_thread_read_is_not_exposed(client):
    _user("assistant-owner", "admin")
    _user("assistant-other", "admin")
    _login(client, "assistant-owner")
    own_thread = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]

    client.post("/panel/api/logout")
    _login(client, "assistant-other")
    response = client.get(f"/panel/api/chat/threads/{own_thread}")

    assert response.status_code == 404
    assert "current_plan" not in response.text


def test_pending_plan_survives_thread_reload(client):
    _user("assistant-recovery", "admin")
    _login(client, "assistant-recovery")
    created = client.post("/panel/api/chat/threads", json={})
    assert created.status_code == 201, created.text
    thread_id = created.json()["thread"]["id"]

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        thread.current_plan = {
            "run_id": "run-recovery",
            "status": "approval_pending",
            "tool": "automation.create_rule",
            "arguments": {"name": "notify"},
        }
        thread.assistant_state = {"stage": "approval", "recoverable": True}
        session.commit()

    response = client.get(f"/panel/api/chat/threads/{thread_id}")

    assert response.status_code == 200
    payload = response.json()["thread"]
    assert payload["current_plan"]["status"] == "approval_pending"
    assert payload["assistant_state"]["recoverable"] is True


def test_stream_reconnect_returns_ordered_persisted_events(client):
    _user("assistant-stream", "admin")
    _login(client, "assistant-stream")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]

    response = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Summarize operations"}
    )
    assert response.status_code == 201
    run_id = response.json()["message"]["assistant_metadata"]["run_id"]

    stream = client.get(f"/panel/api/chat/threads/{thread_id}/stream?run_id={run_id}")

    assert stream.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in stream.text.splitlines()
        if line.startswith("data: ")
    ]
    assert [event["type"] for event in events] == [
        "plan", "approval", "tool", "evidence", "status", "response"
    ]
    assert all(event["thread_id"] == thread_id for event in events)
    assert all(event["run_id"] == run_id for event in events)
    assert [event["sequence"] for event in events] == list(range(len(events)))


def test_failed_run_does_not_persist_partial_response(client, monkeypatch):
    _user("assistant-failure", "admin")
    _login(client, "assistant-failure")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    monkeypatch.setattr(
        "app.services.agent_chat.run_assistant",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("planner failed")),
    )

    response = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Run this"}
    )

    assert response.status_code == 201
    assert response.json()["message"]["status"] == "failed"
    messages = client.get(f"/panel/api/chat/threads/{thread_id}").json()["messages"]
    assert not any(message["author"] == "agent" for message in messages)
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["events"][0]["type"] == "error"
        assert thread.assistant_state["events"][0]["sequence"] == 0


def test_approval_rejects_expired_token():
    plan = {"tool": "automation.create_rule", "arguments": {"name": "notify"}}
    approval = issue_approval(plan, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))

    assert validate_approval(plan, approval, approval["token"]) is False


def test_approval_rejects_changed_tool_or_arguments():
    plan = {"tool": "automation.create_rule", "arguments": {"name": "notify"}}
    approval = issue_approval(plan)

    assert validate_approval({**plan, "tool": "customers.list"}, approval, approval["token"]) is False
    assert validate_approval(
        {"tool": plan["tool"], "arguments": {"name": "changed"}}, approval, approval["token"]
    ) is False
