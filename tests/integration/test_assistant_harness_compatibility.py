"""Compatibility contracts for the shipped admin assistant boundary."""

import json
from types import SimpleNamespace

import pytest

from app.chat.assistant.state import AssistantState
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.services.agent_chat import _events_for, stream_events
from app.db import SessionLocal
from app.models import User
from app.services.users import hash_password


def _user(username: str, role: str = "admin") -> None:
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role=role))
        session.commit()


def _login(client, username: str) -> None:
    assert client.post("/panel/api/login", json={"username": username, "password": "pass"}).status_code == 200


def test_stream_events_preserves_compatible_event_serialization():
    thread = SimpleNamespace(
        assistant_state={
            "events": _events_for(
                {"plan": {"kind": "respond"}, "status": "completed", "response": "done"},
                3,
                "run-1",
            )
        }
    )

    events = stream_events(None, thread, "run-1")

    assert [event["type"] for event in events] == [
        "plan", "approval", "tool", "evidence", "status", "response"
    ]
    assert json.loads(json.dumps(events))[0]["thread_id"] == 3


def test_failed_stream_keeps_recoverable_error_without_partial_completion():
    from app.chat.assistant.nodes import collect_evidence

    state: AssistantState = {"status": "failed", "error": "stream disconnected", "evidence": []}
    assert collect_evidence(state)["status"] == "failed"


def test_admin_sse_replays_only_the_requested_run(client, monkeypatch):
    _user("compat-sse-admin")
    _login(client, "compat-sse-admin")
    monkeypatch.setattr(
        "app.services.agent_chat.run_assistant",
        lambda **kwargs: {"status": "completed", "plan": {"kind": "respond"}, "response": "ok"},
    )
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    sent = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "hello"})
    run_id = sent.json()["message"]["assistant_metadata"]["run_id"]

    response = client.get(f"/panel/api/chat/threads/{thread_id}/stream?run_id={run_id}")

    assert response.status_code == 200
    assert all(json.loads(line[6:])["run_id"] == run_id for line in response.text.splitlines() if line.startswith("data: "))


def test_operator_cannot_open_compatibility_sse(client):
    _user("compat-sse-operator", "operador")
    _login(client, "compat-sse-operator")

    response = client.get("/panel/api/chat/threads/1/stream")

    assert response.status_code == 403
    assert "evidence" not in response.text.lower()


def test_exact_approval_replay_is_rejected_after_first_consumption(client, monkeypatch):
    _user("compat-replay-admin")
    _login(client, "compat-replay-admin")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    pending = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "create a rule"})
    metadata = client.get(f"/panel/api/chat/threads/{thread_id}").json()["messages"][0]["assistant_metadata"]
    monkeypatch.setattr(
        "app.services.agent_chat.execute",
        lambda state: {"status": "completed", "response": "created", "evidence": []},
    )
    payload = {"run_id": metadata["run_id"], "token": metadata["approval"]["token"]}

    assert client.post(f"/panel/api/chat/threads/{thread_id}/approval", json=payload).status_code == 200
    assert client.post(f"/panel/api/chat/threads/{thread_id}/approval", json=payload).status_code == 409


def test_streaming_failure_is_persisted_as_recoverable_error(client, monkeypatch):
    _user("compat-failure-admin")
    _login(client, "compat-failure-admin")
    monkeypatch.setattr(
        "app.services.agent_chat.run_assistant",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("stream disconnected")),
    )
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]

    sent = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "continue"})
    loaded = client.get(f"/panel/api/chat/threads/{thread_id}")

    assert loaded.json()["messages"][0]["status"] == "failed"
    assert loaded.json()["thread"]["assistant_state"]["recoverable"] is True
    assert not any(message["author"] == "agent" for message in loaded.json()["messages"])


def test_panel_turn_does_not_receive_whatsapp_state(client, monkeypatch):
    _user("compat-isolation-admin")
    _login(client, "compat-isolation-admin")
    seen = {}

    def fake_run(**kwargs):
        seen.update(kwargs)
        return {"status": "completed", "plan": {"kind": "respond"}, "response": "ok"}

    monkeypatch.setattr("app.services.agent_chat.run_assistant", fake_run)
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    response = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "hello"})

    assert response.status_code == 201
    assert "conversation_id" not in seen
    assert "whatsapp" not in seen


def test_memory_read_rejects_cross_scope_entity_shapes(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.list_for_entity",
        lambda session, **kwargs: calls.append(kwargs) or [],
    )

    with pytest.raises(ToolValidationError):
        execute_tool(
            SimpleNamespace(), "memory.read",
            {"scope": "own", "entity_id": "customer:42"},
        )
    with pytest.raises(ToolValidationError):
        execute_tool(
            SimpleNamespace(), "memory.read",
            {"scope": "own", "entity_id": "thread:999"}, trusted_thread_id=7,
        )

    own = execute_tool(
        SimpleNamespace(), "memory.read", {"scope": "own"}, trusted_thread_id=7
    )
    assert own["status"] == "completed"
    assert calls == [
        {"scope": "panel", "entity_id": "thread:7"},
        {"scope": "agent", "entity_id": "agent:default"},
    ]

    result = execute_tool(
        SimpleNamespace(), "memory.read", {"scope": "customer", "entity_id": "42"}
    )
    assert result["status"] == "completed"
    assert calls[-1] == {"scope": "customer", "entity_id": "42"}


def test_failed_compaction_is_not_reported_as_successful_completion():
    from app.chat.assistant.nodes import collect_evidence

    result = collect_evidence({
        "status": "completed",
        "evidence": [],
        "compaction": {"failed": True, "write": {"degraded_reason": "db unavailable"}},
    })

    assert result["status"] == "degraded"
    assert result["evidence"][-1]["status"] == "degraded"
