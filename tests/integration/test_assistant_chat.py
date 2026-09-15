"""PR1 contract tests for the isolated assistant graph boundary."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.chat.assistant.approval import (
    consume_approval,
    issue_approval,
    validate_approval,
    validate_execution,
)
from app.models import InternalChatMessage, InternalChatThread, Message, User
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


def test_blocked_cost_gate_persists_canned_reply_without_llm(client, monkeypatch):
    _user("assistant-cost-block", "admin")
    _login(client, "assistant-cost-block")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        session.add(InternalChatMessage(
            thread_id=thread_id, author="agent", content="previous", status="processed",
            cost_llm=1.50,
        ))
        session.commit()

    calls = []
    monkeypatch.setattr(
        "app.services.llm.openai_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs),
        ))),
    )
    response = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages",
        json={"content": "Summarize operations"},
    )

    assert response.status_code == 201
    assert response.json()["message"]["status"] == "processed"
    messages = client.get(f"/panel/api/chat/threads/{thread_id}").json()["messages"]
    assert messages[-1]["author"] == "agent"
    assert messages[-1]["content"] == (
        "The assistant is temporarily unavailable because the configured usage "
        "limit was reached. Please review cost settings."
    )
    assert calls == []


def test_operator_can_still_read_panel_when_cost_gate_blocks(client):
    _user("assistant-cost-operator", "operador")
    _login(client, "assistant-cost-operator")
    assert client.get("/panel/api/me").status_code == 200


def test_thread_list_is_admin_only_bounded_and_ordered(client):
    _user("thread-list-admin", "admin")
    _user("thread-list-operator", "operador")
    _login(client, "thread-list-admin")
    first_response = client.post("/panel/api/chat/threads", json={})
    second_response = client.post("/panel/api/chat/threads", json={})
    assert first_response.status_code == 201
    assert second_response.status_code == 201
    first = first_response.json()["thread"]["id"]
    second = second_response.json()["thread"]["id"]
    with SessionLocal() as session:
        session.add_all([
            InternalChatMessage(thread_id=first, author="admin", content="older request", status="processed",
                                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
            InternalChatMessage(thread_id=second, author="admin", content="newer request", status="processing",
                                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
        ])
        session.query(InternalChatThread).filter_by(id=first).update({"title": "Older"})
        session.query(InternalChatThread).filter_by(id=second).update({"title": "Newer"})
        session.commit()

    listed = client.get("/panel/api/chat/threads?limit=1")

    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()["threads"]] == [second]
    assert listed.json()["threads"][0]["title"] == "Newer"
    assert listed.json()["threads"][0]["created_at"]
    assert listed.json()["threads"][0]["updated_at"]
    assert "status" not in listed.json()["threads"][0]

    client.post("/panel/api/logout")
    _login(client, "thread-list-operator")
    assert client.get("/panel/api/chat/threads?limit=1").status_code == 403


def test_thread_list_rejects_unbounded_or_oversized_requests(client):
    _user("thread-list-bounds", "admin")
    _login(client, "thread-list-bounds")

    assert client.get("/panel/api/chat/threads").status_code == 422
    assert client.get("/panel/api/chat/threads?limit=51").status_code == 422


def test_thread_list_does_not_fabricate_planning_sessions(client):
    _user("thread-list-planning", "admin")
    _login(client, "thread-list-planning")
    regular = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    planning = client.post("/panel/api/planning/sessions", json={"topic": "Planning only"}).json()["thread_id"]
    with SessionLocal() as session:
        session.add(InternalChatMessage(thread_id=regular, author="admin", content="regular", status="processed"))
        session.commit()

    response = client.get("/panel/api/chat/threads?limit=10")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["threads"]] == [regular]
    assert planning not in [row["id"] for row in response.json()["threads"]]


def test_thread_list_excludes_empty_threads_and_orders_message_ties_by_id(client):
    _user("thread-list-empty", "admin")
    _login(client, "thread-list-empty")
    empty = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    older = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    newer = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    with SessionLocal() as session:
        timestamp = datetime(2026, 2, 1, tzinfo=timezone.utc)
        session.add_all([
            InternalChatMessage(thread_id=older, author="admin", content="older", created_at=timestamp),
            InternalChatMessage(thread_id=newer, author="agent", content="newer", created_at=timestamp),
        ])
        session.commit()

    response = client.get("/panel/api/chat/threads?limit=10")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["threads"]] == [newer, older]
    assert empty not in [row["id"] for row in response.json()["threads"]]


def test_thread_rename_and_delete_are_owned_and_not_exposed(client):
    _user("thread-owner", "admin")
    _user("thread-other-owner", "admin")
    _login(client, "thread-owner")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]

    renamed = client.patch(f"/panel/api/chat/threads/{thread_id}", json={"title": "Operations"})
    assert renamed.status_code == 200
    assert renamed.json()["thread"]["title"] == "Operations"

    client.post("/panel/api/logout")
    _login(client, "thread-other-owner")
    assert client.patch(f"/panel/api/chat/threads/{thread_id}", json={"title": "Nope"}).status_code == 404
    assert client.delete(f"/panel/api/chat/threads/{thread_id}").status_code == 404

    client.post("/panel/api/logout")
    _login(client, "thread-owner")
    deleted = client.delete(f"/panel/api/chat/threads/{thread_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}
    assert client.get(f"/panel/api/chat/threads/{thread_id}").status_code == 404


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
    assert response.json()["message"]["error"] == "El agente no pudo procesar este mensaje. Reinténtalo."
    messages = client.get(f"/panel/api/chat/threads/{thread_id}").json()["messages"]
    assert not any(message["author"] == "agent" for message in messages)
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["events"][0]["type"] == "error"
        assert thread.assistant_state["events"][0]["sequence"] == 0


def test_empty_agent_response_is_localized(client, monkeypatch):
    _user("assistant-empty-response", "admin")
    _login(client, "assistant-empty-response")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    monkeypatch.setattr(
        "app.services.agent_chat.run_assistant",
        lambda *args, **kwargs: {"status": "completed", "response": None},
    )

    response = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Answer"})

    assert response.status_code == 201
    messages = client.get(f"/panel/api/chat/threads/{thread_id}").json()["messages"]
    assert messages[-1]["content"] == "No pude generar una respuesta. Inténtalo nuevamente."


def test_planner_and_terminal_stream_usage_are_persisted_once(client, monkeypatch):
    _user("assistant-usage", "admin")
    _login(client, "assistant-usage")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    monkeypatch.setattr(
        "app.services.llm.get_settings",
        lambda: SimpleNamespace(assistant_chat_model="gpt-4o-mini"),
    )
    planner = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            "kind": "respond", "arguments": {}, "summary": "planned", "requires_approval": False,
        })))]
        , usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5)
    )
    response_chunks = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="answer"))], usage=None),
        SimpleNamespace(choices=[], usage=SimpleNamespace(prompt_tokens=20, completion_tokens=7)),
    ]

    class Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return planner if not kwargs.get("stream") else iter(response_chunks)

    monkeypatch.setattr("app.services.llm.openai_client", lambda: Client())
    result = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "hello"})
    assert result.status_code == 201
    metadata = result.json()["message"]["assistant_metadata"]
    assert set(metadata["cost_calls"]) == {metadata["run_id"] + ":planner", metadata["run_id"] + ":response"}
    assert metadata["cost_calls"][metadata["run_id"] + ":planner"]["prompt_tokens"] == 10
    response_call = metadata["cost_calls"][metadata["run_id"] + ":response"]
    assert response_call["prompt_tokens"] == 20
    assert response_call["completion_tokens"] == 7
    assert response_call["cost"] == pytest.approx(0.0000072)
    with SessionLocal() as session:
        request = session.get(InternalChatMessage, result.json()["message"]["id"])
        assert float(request.cost_llm) == pytest.approx(0.000012)


def test_stream_disconnect_keeps_known_usage_and_failed_request(client, monkeypatch):
    _user("assistant-disconnect", "admin")
    _login(client, "assistant-disconnect")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    planner = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            "kind": "respond", "arguments": {}, "summary": "planned", "requires_approval": False,
        })))]
        , usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5)
    )

    def disconnecting(**kwargs):
        if not kwargs.get("stream"):
            return planner
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="partial"))], usage=None)
        yield SimpleNamespace(choices=[], usage=SimpleNamespace(prompt_tokens=20, completion_tokens=7))
        raise ConnectionError("stream disconnected")

    client_stub = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=disconnecting)))
    monkeypatch.setattr("app.services.llm.openai_client", lambda: client_stub)
    result = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "hello"})
    assert result.json()["message"]["status"] == "failed"
    with SessionLocal() as session:
        message = session.scalar(select(InternalChatMessage).where(InternalChatMessage.thread_id == thread_id,
                                                                    InternalChatMessage.author == "admin"))
        assert set(message.assistant_metadata["cost_calls"]) == {message.assistant_metadata["run_id"] + ":planner",
                                                                    message.assistant_metadata["run_id"] + ":response"}


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


def test_rejected_approval_only_leaves_planner_cost_and_preserves_whatsapp_totals(client):
    _user("assistant-denied-cost", "admin")
    _login(client, "assistant-denied-cost")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    pending = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "create a rule"})
    assert pending.status_code == 201
    metadata = pending.json()["message"]["assistant_metadata"]

    rejected = client.post(
        f"/panel/api/chat/threads/{thread_id}/approval",
        json={"run_id": metadata["run_id"], "token": metadata["approval"]["token"], "reject": True},
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    with SessionLocal() as session:
        request = session.scalar(select(InternalChatMessage).where(InternalChatMessage.thread_id == thread_id, InternalChatMessage.author == "admin"))
        assert list((request.assistant_metadata or {}).get("cost_calls", {})) == [metadata["run_id"] + ":planner"]
        assert session.query(Message).count() == 0


def test_expired_approval_cannot_add_execution_cost(client):
    _user("assistant-expired-cost", "admin")
    _login(client, "assistant-expired-cost")
    thread_id = client.post(f"/panel/api/chat/threads", json={}).json()["thread"]["id"]
    pending = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "create a rule"})
    metadata = pending.json()["message"]["assistant_metadata"]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        thread.assistant_state = {
            **thread.assistant_state,
            "approval": {
                **thread.assistant_state["approval"],
                "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            },
        }
        session.commit()

    response = client.post(f"/panel/api/chat/threads/{thread_id}/approval", json={"run_id": metadata["run_id"], "token": metadata["approval"]["token"]})

    assert response.status_code == 409
    with SessionLocal() as session:
        request = session.scalar(select(InternalChatMessage).where(InternalChatMessage.thread_id == thread_id, InternalChatMessage.author == "admin"))
        assert list((request.assistant_metadata or {}).get("cost_calls", {})) == [metadata["run_id"] + ":planner"]


def _completed_result(response="Answer"):
    return {"status": "completed", "response": response, "cost_mode": "normal"}


def _title_completion(title="Opening title", prompt_tokens=4, completion_tokens=3):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=title))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


def test_title_is_generated_once_after_first_response_and_uses_opening_admin_message(client, monkeypatch):
    _user("assistant-title-once", "admin")
    _login(client, "assistant-title-once")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    monkeypatch.setattr("app.services.agent_chat.run_assistant", lambda *args, **kwargs: _completed_result())
    calls = []
    monkeypatch.setattr(
        "app.services.llm.openai_client",
        lambda provider=None: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs) or _title_completion()
        ))),
    )

    first = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "  Need a gas leak inspection  "})
    second = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "More details"})

    assert first.status_code == second.status_code == 201
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.title == "Opening title"
        agent_messages = session.scalars(select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread_id, InternalChatMessage.author == "agent"
        ).order_by(InternalChatMessage.id)).all()
        assert len(agent_messages) == 2
        assert list((agent_messages[0].assistant_metadata or {}).get("cost_calls", {})) == [f"{first.json()['message']['assistant_metadata']['run_id']}:title"]
    assert len(calls) == 1
    assert calls[0]["messages"][-1]["content"].endswith("Need a gas leak inspection")


def test_title_cost_is_gated_and_recorded_on_first_assistant_message(client, monkeypatch):
    _user("assistant-title-cost", "admin")
    _login(client, "assistant-title-cost")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    monkeypatch.setattr("app.services.agent_chat.run_assistant", lambda *args, **kwargs: _completed_result())
    monkeypatch.setattr(
        "app.services.llm.get_settings",
        lambda: SimpleNamespace(assistant_chat_provider=None, assistant_chat_model="gpt-4o-mini"),
    )
    monkeypatch.setattr(
        "app.services.llm.openai_client",
        lambda provider=None: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: _title_completion()
        ))),
    )

    response = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Inspect the boiler"})

    assert response.status_code == 201
    with SessionLocal() as session:
        agent = session.scalar(select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread_id, InternalChatMessage.author == "agent"
        ))
        request = session.scalar(select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread_id, InternalChatMessage.author == "admin"
        ))
        assert agent.cost_llm > 0
        assert float(request.cost_llm or 0) == 0
        assert f"{request.assistant_metadata['run_id']}:title" in agent.assistant_metadata["cost_calls"]


def test_non_normal_title_mode_uses_free_bounded_utf8_fallback(client, monkeypatch):
    _user("assistant-title-gate", "admin")
    _login(client, "assistant-title-gate")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    monkeypatch.setattr("app.services.agent_chat.run_assistant", lambda *args, **kwargs: _completed_result())
    monkeypatch.setattr("app.services.costs.internal_thread_cost_state", lambda *args: (80.0, "conservative"))
    calls = []
    monkeypatch.setattr(
        "app.services.llm.openai_client",
        lambda provider=None: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs)
        ))),
    )
    opening = "á" * 200

    response = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": opening})

    assert response.status_code == 201
    with SessionLocal() as session:
        title = session.get(InternalChatThread, thread_id).title
        assert title
        assert len(title.encode("utf-8")) <= 120
        assert title == opening[: len(title)]
    assert calls == []


@pytest.mark.parametrize("failure", [TimeoutError("title timed out"), RuntimeError("title failed")])
def test_title_generation_failures_store_the_same_bounded_fallback(client, monkeypatch, failure):
    _user("assistant-title-failure", "admin")
    _login(client, "assistant-title-failure")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    monkeypatch.setattr("app.services.agent_chat.run_assistant", lambda *args, **kwargs: _completed_result())
    monkeypatch.setattr(
        "app.services.llm.openai_client",
        lambda provider=None: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: (_ for _ in ()).throw(failure)
        ))),
    )
    opening = "Request: " + " revisión" * 100

    response = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": opening})

    assert response.status_code == 201
    with SessionLocal() as session:
        title = session.get(InternalChatThread, thread_id).title
        assert title == opening.strip()[: len(title)]
        assert len(title.encode("utf-8")) <= 120
