"""Panel API acceptance coverage for the native SDB boundary (WU-5)."""

import json
import pytest

from app.db import SessionLocal
from app.models import InternalChatThread, User
from app.services.users import hash_password


@pytest.fixture(autouse=True)
def assistant_graph(monkeypatch):
    def run_assistant(**kwargs):
        assert kwargs["sdb_requested"] is True
        return {
            "status": "approval_pending",
            "sdb_phase": "APPROVE",
            "sdb_spec": {"scope": {"entities": ["service history"]}, "scope_frozen": True, "sha256": "spec-digest"},
            "sdb_tasks": [{"id": "task-1", "scope": {"entities": ["service history"], "request": "Review service history"}, "summary": "Read service history", "tool": "conversations.search", "arguments": {"query": "Review service history", "limit": 10}, "verifiable_output": "A bounded service-history summary"}],
            "planner": {"classification": "normal", "valid": True},
        }

    monkeypatch.setattr("app.services.agent_chat.run_assistant", run_assistant)


def _user(username: str, role: str) -> None:
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role=role))
        session.commit()


def _login(client, username: str) -> None:
    response = client.post("/panel/api/login", json={"username": username, "password": "pass"})
    assert response.status_code == 200, response.text


def _events(response):
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


def test_authenticated_admin_can_explicitly_enter_sdb(client, migrated_db, mock_openai_chat):
    _user("sdb-api-admin", "admin")
    _login(client, "sdb-api-admin")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

    response = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages",
        json={"content": "Review service history", "sdb_requested": True},
    )

    assert response.status_code == 201, response.text
    settled = client.get(f"/panel/api/chat/threads/{thread_id}").json()
    assert settled["messages"][0]["status"] == "approval_pending"
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["sdb"]["phase"] == "APPROVE"
        assert thread.current_plan["sdb"]["tasks"][0]["verifiable_output"]


def test_operator_cannot_request_or_stream_sdb(client, migrated_db):
    _user("sdb-api-operator", "operador")
    _login(client, "sdb-api-operator")

    created = client.post("/panel/api/chat/threads", json={"proyecto": "default"})
    assert created.status_code == 403
    stream = client.get("/panel/api/chat/threads/1/stream?run_id=operator-run")
    assert stream.status_code == 403
    assert "sdb" not in stream.text.lower()


def test_sdb_stream_contains_ordered_phases_and_evidence(client, migrated_db, mock_openai_chat):
    _user("sdb-api-events", "admin")
    _login(client, "sdb-api-events")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    pending = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages",
        json={"content": "Review service history", "sdb_requested": True},
    ).json()["message"]
    thread = client.get(f"/panel/api/chat/threads/{thread_id}").json()
    metadata = thread["messages"][0]["assistant_metadata"]

    approval = client.post(
        f"/panel/api/chat/threads/{thread_id}/approval",
        json={"run_id": metadata["run_id"], "token": metadata["approval"]["token"]},
    )
    assert approval.status_code == 200, approval.text
    events = _events(client.get(f"/panel/api/chat/threads/{thread_id}/stream?run_id={metadata['run_id']}"))

    phases = [event["phase"] for event in events if event["type"] == "phase"]
    assert phases[:4] == ["CLARIFY", "SPEC", "PLAN", "APPROVE"]
    assert any(event["type"] == "evidence" for event in events)
    assert [event["sequence"] for event in events] == list(range(len(events)))


def test_sdb_stream_reconnect_replays_same_persisted_events(client, migrated_db, mock_openai_chat):
    _user("sdb-api-reconnect", "admin")
    _login(client, "sdb-api-reconnect")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    pending = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages",
        json={"content": "Review service history", "sdb_requested": True},
    ).json()["message"]
    run_id = pending["assistant_metadata"]["run_id"]

    first = client.get(f"/panel/api/chat/threads/{thread_id}/stream?run_id={run_id}")
    second = client.get(f"/panel/api/chat/threads/{thread_id}/stream?run_id={run_id}")

    assert first.status_code == second.status_code == 200
    assert _events(first) == _events(second)
    reloaded = client.get(f"/panel/api/chat/threads/{thread_id}").json()["thread"]
    assert reloaded["assistant_state"]["sdb"]["run_id"] == run_id


def test_failed_sdb_task_stream_is_error_and_never_completed(client, migrated_db, mock_openai_chat, monkeypatch):
    from app.chat.assistant.tools.registry import ToolExecutionError

    _user("sdb-api-failed", "admin")
    _login(client, "sdb-api-failed")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    pending = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages",
        json={"content": "Review service history", "sdb_requested": True},
    ).json()["message"]
    thread = client.get(f"/panel/api/chat/threads/{thread_id}").json()
    metadata = thread["messages"][0]["assistant_metadata"]
    monkeypatch.setattr(
        "app.services.agent_chat.execute_tool",
        lambda *args, **kwargs: (_ for _ in ()).throw(ToolExecutionError("read failed")),
    )

    approval = client.post(
        f"/panel/api/chat/threads/{thread_id}/approval",
        json={"run_id": metadata["run_id"], "token": metadata["approval"]["token"]},
    )
    assert approval.status_code == 200, approval.text
    events = _events(client.get(f"/panel/api/chat/threads/{thread_id}/stream?run_id={metadata['run_id']}"))
    task_events = [event for event in events if event.get("type") == "task"]
    assert task_events and task_events[-1]["status"] == "failed"
    assert not any(event.get("type") == "task" and event.get("status") == "completed" for event in events)
    assert any(event.get("type") == "status" and event.get("status") == "failed" for event in events)
