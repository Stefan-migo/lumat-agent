"""PR1 contract tests for the isolated assistant graph boundary."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.db import SessionLocal
from app.chat.assistant.approval import (
    consume_approval,
    issue_approval,
    validate_approval,
    validate_execution,
)
from app.models import InternalChatMessage, InternalChatThread, User
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


def test_approval_is_consumed_once_and_execution_requires_consumed_state():
    plan = {"tool": "automation.create_rule", "arguments": {"name": "notify"}}
    approval = issue_approval(plan)

    assert consume_approval(approval, approval["token"]) is True
    assert consume_approval(approval, approval["token"]) is False
    assert validate_execution(plan, approval) is True


def test_approved_plan_route_records_execution_audit(client):
    _user("assistant-approval", "admin")
    _login(client, "assistant-approval")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]

    pending = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "create a rule"}
    )
    approval = pending.json()["message"]["assistant_metadata"]["approval"]

    response = client.post(
        f"/panel/api/chat/threads/{thread_id}/approval",
        json={"run_id": pending.json()["message"]["assistant_metadata"]["run_id"], "token": approval["token"]},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    with SessionLocal() as session:
        from app.models import AuditLog

        assert session.query(AuditLog).filter_by(action="internal_chat.execution").count() == 1


def test_approved_plan_stream_replays_complete_execution_sequence(client, monkeypatch):
    _user("assistant-approval-stream", "admin")
    _login(client, "assistant-approval-stream")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    monkeypatch.setattr(
        "app.services.agent_chat.execute",
        lambda state: {"status": "completed", "response": "Rule created.", "evidence": [{"tool": "automation.create_rule", "status": "completed", "detail": "created"}]},
    )

    pending = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "create a rule"})
    metadata = pending.json()["message"]["assistant_metadata"]
    approved = client.post(
        f"/panel/api/chat/threads/{thread_id}/approval",
        json={"run_id": metadata["run_id"], "token": metadata["approval"]["token"]},
    )
    assert approved.status_code == 200

    stream = client.get(f"/panel/api/chat/threads/{thread_id}/stream?run_id={metadata['run_id']}")
    events = [json.loads(line.removeprefix("data: ")) for line in stream.text.splitlines() if line.startswith("data: ")]
    assert [event["type"] for event in events] == ["plan", "approval", "tool", "evidence", "status", "response"]
    assert all(event["thread_id"] == thread_id and event["run_id"] == metadata["run_id"] for event in events)
    assert [event["sequence"] for event in events] == list(range(6))


def test_recovery_resumes_pending_execution_once():
    from app.services.agent_chat import resume_thread

    with SessionLocal() as session:
        user = User(username="recovery-executor", password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
        thread = InternalChatThread(
            user_id=user.id,
            active_run_id="recover-run",
            current_plan={"tool": "stub", "arguments": {}, "requires_approval": False},
            assistant_state={"stage": "executing", "execution_status": "pending", "recoverable": True},
        )
        session.add(thread)
        session.flush()
        session.add(InternalChatMessage(
            thread_id=thread.id, author="admin", content="resume this", status="processing",
            assistant_metadata={"run_id": "recover-run"},
        ))
        session.commit()

        assert resume_thread(session, thread, user) is True
        session.commit()
        assert resume_thread(session, thread, user) is False
