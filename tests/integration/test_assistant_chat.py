"""PR1 contract tests for the isolated assistant graph boundary."""

import asyncio
import json
import time
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
from app.chat.assistant.nodes import MAX_ASSISTANT_TOOL_STEPS
from app.models import InternalChatMessage, InternalChatThread, Message, User
from app.services.agent_chat import (
    STALE_RUN_SECONDS,
    _generate_thread_title,
    _opening_message,
    create_run_message,
    reap_orphaned_runs,
    reap_stale_run,
    stream_events,
    stream_events_async,
)
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


def _wait_for_run(client, thread_id: int, run_id: str) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        result = client.get(f"/panel/api/chat/threads/{thread_id}").json()
        message = next((item for item in result["messages"] if item.get("assistant_metadata", {}).get("run_id") == run_id and item["author"] == "admin"), None)
        if message and message["status"] != "processing":
            return result
        time.sleep(0.05)
    raise AssertionError("assistant run did not finish")


def test_stream_events_emits_live_stage_and_terminal_status():
    class Session:
        def get(self, model, thread_id):
            return SimpleNamespace(assistant_state={"live": {
                "run_id": "run-live", "stage": "streaming", "preview": "partial", "status": "failed",
            }, "events": []})

        def close(self):
            pass

    events = list(stream_events(lambda: Session(), 1, "run-live", timeout=1, interval=0))

    assert [event["type"] for event in events] == ["status", "response"]
    assert events[0]["status"] == "streaming"
    assert events[1]["content"] == "partial"


def test_stream_events_treats_cancelled_as_terminal():
    class Session:
        def get(self, model, thread_id):
            return SimpleNamespace(assistant_state={"live": {
                "run_id": "run-cancelled", "stage": "cancelled", "preview": "partial",
                "status": "cancelled",
            }, "events": []})

        def close(self):
            pass

    events = list(stream_events(lambda: Session(), 1, "run-cancelled", timeout=1, interval=0))

    assert events[-2]["status"] == "cancelled"
    assert events[-1]["content"] == "partial"


def test_reap_stale_run_fails_an_orphaned_run_once_it_stops_advancing():
    message = SimpleNamespace(status="processing", error=None, completed_at=None)

    class Session:
        def scalar(self, statement):
            return message

        def flush(self):
            pass

    stale = (datetime.now(timezone.utc) - timedelta(seconds=STALE_RUN_SECONDS + 1)).isoformat()
    thread = SimpleNamespace(id=7, active_run_id="run-orphan", assistant_state={
        "stage": "planning", "execution_status": "pending",
        "live": {
            "run_id": "run-orphan", "stage": "planning", "preview": "", "status": "running",
            "updated_at": stale,
        },
    })

    assert reap_stale_run(Session(), thread) is True
    assert message.status == "failed"
    assert message.error == "El agente no pudo procesar este mensaje. Reinténtalo."
    assert message.completed_at is not None
    assert thread.assistant_state["stage"] == "failed"
    assert thread.assistant_state["execution_status"] == "failed"
    assert thread.assistant_state["recoverable"] is True
    assert thread.assistant_state["live"]["status"] == "failed"


def test_reap_stale_run_leaves_a_live_run_and_a_resumable_run_alone():
    class Session:
        def scalar(self, statement):
            raise AssertionError("a reclaimable run must not be touched")

        def flush(self):
            pass

    fresh = SimpleNamespace(id=7, active_run_id="run-live", assistant_state={
        "stage": "planning", "execution_status": "pending",
        "live": {
            "run_id": "run-live", "status": "running",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    })
    # `resume_thread` owns a persisted execution it can still claim: recovering
    # it beats failing it, so the reaper must not pre-empt that path.
    resumable = SimpleNamespace(id=8, active_run_id="run-resume", assistant_state={
        "stage": "executing", "execution_status": "pending",
        "live": {
            "run_id": "run-resume", "status": "running",
            "updated_at": "2000-01-01T00:00:00+00:00",
        },
    })

    assert reap_stale_run(Session(), fresh) is False
    assert reap_stale_run(Session(), resumable) is False
    assert fresh.assistant_state["live"]["status"] == "running"
    assert resumable.assistant_state["live"]["status"] == "running"


def test_create_run_message_stamps_live_state_for_stale_run_recovery(migrated_db):
    with SessionLocal() as session:
        owner = User(username="reap-stamp-admin", password_hash=hash_password("pass"), role="admin")
        session.add(owner)
        session.flush()
        thread = InternalChatThread(user_id=owner.id)
        session.add(thread)
        session.flush()

        message = create_run_message(session, thread, owner, "hello")

        live = thread.assistant_state["live"]
        assert live["run_id"] == message.assistant_metadata["run_id"]
        assert live["status"] == "running"
        # The reaper parses this value; assert the round trip, because a stamp
        # that cannot be parsed reads as stale and would fail a live run.
        assert datetime.fromisoformat(live["updated_at"]).tzinfo is not None
        session.rollback()


def test_non_admin_run_message_keeps_role_as_human_author_and_is_opening_message(migrated_db):
    with SessionLocal() as session:
        owner = User(username="assistant-tecnico-author", password_hash=hash_password("pass"), role="tecnico")
        session.add(owner)
        session.flush()
        thread = InternalChatThread(user_id=owner.id)
        session.add(thread)
        session.flush()

        message = create_run_message(session, thread, owner, "hello")

        assert message.author == "tecnico"
        assert _opening_message(session, thread.id) is message
        session.rollback()


def test_operator_cannot_read_assistant_stream(client):
    _user("assistant-operator", "operador")
    _login(client, "assistant-operator")

    response = client.get("/panel/api/chat/threads/1/stream")

    assert response.status_code == 404
    assert "plan" not in response.text.lower()
    assert "evidence" not in response.text.lower()


def test_stop_route_requires_owned_active_run_and_current_run_id(client):
    _user("assistant-stop-owner", "admin")
    _user("assistant-stop-other", "admin")
    _login(client, "assistant-stop-owner")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

    assert client.post(f"/panel/api/chat/threads/{thread_id}/stop").status_code == 409
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        thread.active_run_id = "current-run"
        thread.assistant_state = {"live": {"run_id": "current-run", "status": "running"}, "sibling": {"keep": True}}
        session.commit()

    assert client.post(f"/panel/api/chat/threads/{thread_id}/stop", json={"run_id": "stale-run"}).status_code == 409
    accepted = client.post(f"/panel/api/chat/threads/{thread_id}/stop", json={"run_id": "current-run"})
    assert accepted.status_code == 200
    assert accepted.json() == {"status": "stopping", "run_id": "current-run"}
    repeated = client.post(f"/panel/api/chat/threads/{thread_id}/stop", json={"run_id": "current-run"})
    assert repeated.status_code == 200
    assert repeated.json() == accepted.json()
    with SessionLocal() as session:
        state = session.get(InternalChatThread, thread_id).assistant_state
        assert state["stop_request"] == {"run_id": "current-run"}
        assert state["sibling"] == {"keep": True}

    client.post("/panel/api/logout")
    _login(client, "assistant-stop-other")
    assert client.post(f"/panel/api/chat/threads/{thread_id}/stop").status_code == 404


def test_runner_cooperatively_cancels_at_graph_stage_boundary(monkeypatch):
    from app.services import agent_chat

    with SessionLocal() as session:
        owner = User(username="assistant-stop-runner", password_hash=hash_password("pass"), role="admin")
        session.add(owner)
        session.flush()
        thread = InternalChatThread(user_id=owner.id, active_run_id="stop-run", assistant_state={
            "live": {"run_id": "stop-run", "status": "running"}, "sibling": {"keep": True},
        })
        session.add(thread)
        session.flush()
        message = InternalChatMessage(thread_id=thread.id, author="admin", content="work", status="processing",
                                      assistant_metadata={"run_id": "stop-run"})
        session.add(message)
        session.flush()
        thread_id, message_id, owner_id = thread.id, message.id, owner.id
        session.commit()

    def stop_during_run(**kwargs):
        with SessionLocal() as stopping:
            thread = stopping.get(InternalChatThread, thread_id)
            thread.assistant_state = {**thread.assistant_state, "stop_request": {"run_id": "stop-run"}}
            stopping.commit()
        kwargs["on_stage"]("planning")

    monkeypatch.setattr(agent_chat, "run_assistant", stop_during_run)
    agent_chat.run_agent_turn(thread_id=thread_id, run_id="stop-run", user_id=owner_id,
                              attachment_ids=[], sdb_requested=None)

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        message = session.get(InternalChatMessage, message_id)
        assert thread.assistant_state["live"]["status"] == "cancelled"
        assert "stop_request" not in thread.assistant_state
        assert thread.assistant_state["sibling"] == {"keep": True}
        assert message.status == "cancelled"
        assert message.assistant_metadata["cancellation"]["status"] == "cancelled"


def test_runner_honors_stop_requested_after_last_stage_boundary(monkeypatch):
    from app.services import agent_chat

    with SessionLocal() as session:
        owner = User(username="assistant-stop-terminal", password_hash=hash_password("pass"), role="admin")
        session.add(owner)
        session.flush()
        thread = InternalChatThread(user_id=owner.id, active_run_id="terminal-stop-run", assistant_state={
            "live": {"run_id": "terminal-stop-run", "status": "running"},
        })
        session.add(thread)
        session.flush()
        message = InternalChatMessage(thread_id=thread.id, author="admin", content="work", status="processing",
                                      assistant_metadata={"run_id": "terminal-stop-run"})
        session.add(message)
        session.flush()
        thread_id, message_id, owner_id = thread.id, message.id, owner.id
        session.commit()

    def stop_after_last_stage(**kwargs):
        with SessionLocal() as stopping:
            thread = stopping.get(InternalChatThread, thread_id)
            thread.assistant_state = {**thread.assistant_state, "stop_request": {"run_id": "terminal-stop-run"}}
            stopping.commit()
        return _completed_result()

    monkeypatch.setattr(agent_chat, "run_assistant", stop_after_last_stage)
    agent_chat.run_agent_turn(thread_id=thread_id, run_id="terminal-stop-run", user_id=owner_id,
                              attachment_ids=[], sdb_requested=None)

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        message = session.get(InternalChatMessage, message_id)
        assert thread.assistant_state["live"]["status"] == "cancelled"
        assert "stop_request" not in thread.assistant_state
        assert message.status == "cancelled"


def test_stop_route_accepts_approval_pending_as_running(client):
    _user("assistant-stop-approval", "admin")
    _login(client, "assistant-stop-approval")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        thread.assistant_state = {"live": {"run_id": "approval-run", "status": "approval_pending", "stage": "approval_pending"}}
        session.add(InternalChatMessage(thread_id=thread_id, author="admin", content="pending",
                                        status="approval_pending", assistant_metadata={"run_id": "approval-run"}))
        session.commit()

    response = client.post(f"/panel/api/chat/threads/{thread_id}/stop", json={"run_id": "approval-run"})

    assert response.status_code == 200
    assert response.json() == {"status": "cancelled", "run_id": "approval-run"}
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        message = session.scalar(select(InternalChatMessage).where(InternalChatMessage.thread_id == thread_id))
        assert thread.assistant_state["live"]["status"] == "cancelled"
        assert message.status == "cancelled"
        assert message.assistant_metadata["cancellation"]["status"] == "cancelled"


def test_stopping_approval_pending_revokes_approval_and_prevents_execution(client, monkeypatch):
    _user("assistant-stop-revoke-approval", "admin")
    _login(client, "assistant-stop-revoke-approval")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    run_id = "revoked-approval-run"
    plan = {"tool": "stub", "arguments": {}, "requires_approval": True}
    approval = issue_approval(plan)
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        thread.current_plan = plan
        thread.active_run_id = run_id
        thread.assistant_state = {
            "stage": "approval_pending",
            "live": {"run_id": run_id, "stage": "approval_pending", "status": "approval_pending"},
            "approval": approval,
        }
        session.add(InternalChatMessage(
            thread_id=thread_id, author="admin", content="pending", status="approval_pending",
            assistant_metadata={"run_id": run_id, "approval": approval},
        ))
        session.commit()

    stopped = client.post(f"/panel/api/chat/threads/{thread_id}/stop", json={"run_id": run_id})
    assert stopped.status_code == 200
    assert stopped.json() == {"status": "cancelled", "run_id": run_id}
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["approval"]["status"] == "revoked"

    executed = []
    monkeypatch.setattr("app.services.agent_chat.execute", lambda state: executed.append(state) or {
        "status": "completed", "response": "Executed", "evidence": [],
    })
    rejected = client.post(
        f"/panel/api/chat/threads/{thread_id}/approval",
        json={"run_id": run_id, "token": approval["token"]},
    )

    assert rejected.status_code == 409
    assert executed == []
    with SessionLocal() as session:
        messages = list(session.scalars(select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread_id,
        )))
        assert len(messages) == 1
        assert messages[0].status == "cancelled"


def test_sdb_requested_is_admin_only(client):
    _user("assistant-sdb-operator", "operador")
    _login(client, "assistant-sdb-operator")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

    denied = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages",
        json={"content": "verify this", "sdb_requested": True},
    )

    assert denied.status_code == 403


def test_sdb_requested_is_accepted_for_admin(client):
    _user("assistant-sdb-admin", "admin")
    _login(client, "assistant-sdb-admin")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

    accepted = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages",
        json={"content": "verify this", "sdb_requested": True},
    )

    assert accepted.status_code == 201


def test_admin_handoff_run_reaches_verification_with_the_handoff_gate(client, monkeypatch):
    _user("assistant-sdb-handoff", "admin")
    _login(client, "assistant-sdb-handoff")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

    provider = _scripted_client([
        json.dumps({
            "kind": "tool", "tool": "assistant.capabilities", "arguments": {},
            "summary": "list capabilities", "requires_approval": False,
        }),
    ])
    monkeypatch.setattr("app.services.llm.openai_client", lambda: provider)

    posted = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages",
        json={"content": "verify this", "sdb_requested": True},
    )
    assert posted.status_code == 201
    _wait_for_run(client, thread_id, posted.json()["message"]["assistant_metadata"]["run_id"])

    with SessionLocal() as session:
        verification = session.get(InternalChatThread, thread_id).assistant_state["verification"]

    assert verification["required"] is True
    assert verification["gate_reason"] == "handoff"


def test_cross_thread_read_is_not_exposed(client):
    _user("assistant-owner", "admin")
    _user("assistant-other", "admin")
    _login(client, "assistant-owner")
    own_thread = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

    client.post("/panel/api/logout")
    _login(client, "assistant-other")
    response = client.get(f"/panel/api/chat/threads/{own_thread}")

    assert response.status_code == 404
    assert "current_plan" not in response.text


def test_pending_plan_survives_thread_reload(client):
    _user("assistant-recovery", "admin")
    _login(client, "assistant-recovery")
    created = client.post("/panel/api/chat/threads", json={"proyecto": "default"})
    assert created.status_code == 201, created.text
    thread_id = created.json()["thread"]["id"]

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        thread.current_plan = {
            "run_id": "run-recovery",
            "status": "approval_pending",
            "tool": "automation.create_rule",
            "arguments": {"recipe_id": "appointment_confirmation", "parameters": {"channel": "whatsapp"}},
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
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

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
        "plan", "approval", "tool", "evidence", "status", "response", "status", "response"
    ]
    assert all(event["thread_id"] == thread_id for event in events)
    assert all(event["run_id"] == run_id for event in events)
    assert [event["sequence"] for event in events] == list(range(len(events)))


def test_blocked_cost_gate_persists_canned_reply_without_llm(client, monkeypatch):
    _user("assistant-cost-block", "admin")
    _login(client, "assistant-cost-block")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
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
    assert response.json()["message"]["status"] == "processing"
    _wait_for_run(client, thread_id, response.json()["message"]["assistant_metadata"]["run_id"])
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
    first_response = client.post("/panel/api/chat/threads", json={"proyecto": "default"})
    second_response = client.post("/panel/api/chat/threads", json={"proyecto": "default"})
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

    with SessionLocal() as session:
        session.query(InternalChatThread).filter_by(id=first).update({"proyecto": "other-project"})
        session.commit()

    all_threads = client.get("/panel/api/chat/threads?limit=10")
    default_threads = client.get("/panel/api/chat/threads?limit=10&proyecto=default")
    assert {row["id"] for row in all_threads.json()["threads"]} == {first, second}
    assert {row["id"]: row["proyecto"] for row in all_threads.json()["threads"]} == {
        first: "other-project",
        second: "default",
    }
    assert [row["id"] for row in default_threads.json()["threads"]] == [second]
    assert default_threads.json()["threads"][0]["proyecto"] == "default"

    client.post("/panel/api/logout")
    _login(client, "thread-list-operator")
    assert client.get("/panel/api/chat/threads?limit=1").json()["threads"] == []


def test_thread_list_rejects_unbounded_or_oversized_requests(client):
    _user("thread-list-bounds", "admin")
    _login(client, "thread-list-bounds")

    assert client.get("/panel/api/chat/threads").status_code == 422
    assert client.get("/panel/api/chat/threads?limit=51").status_code == 422


def test_active_run_list_is_owner_scoped_and_includes_legacy_cortex_threads(client):
    _user("active-run-owner", "admin")
    _user("active-run-other", "admin")
    _login(client, "active-run-owner")
    running = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    terminal = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    with SessionLocal() as session:
        running_thread = session.get(InternalChatThread, running)
        running_thread.title = "Running work"
        running_thread.proyecto = "workspace"
        running_thread.assistant_state = {
            "live": {"run_id": "live-run", "stage": "planning", "status": "running"},
            "cortex_session": {"slug": "legacy-session", "status": "active"},
        }
        terminal_thread = session.get(InternalChatThread, terminal)
        terminal_thread.proyecto = "workspace"
        terminal_thread.assistant_state = {
            "live": {"run_id": "done-run", "stage": "completed", "status": "completed"},
        }
        session.commit()

    client.post("/panel/api/logout")
    _login(client, "active-run-other")
    other_running = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    with SessionLocal() as session:
        other_thread = session.get(InternalChatThread, other_running)
        other_thread.proyecto = "other-project"
        other_thread.assistant_state = {
            "live": {"run_id": "private-run", "stage": "executing", "status": "running"},
        }
        session.commit()

    client.post("/panel/api/logout")
    _login(client, "active-run-owner")
    response = client.get("/panel/api/chat/active-runs")

    assert response.status_code == 200
    rows = response.json()["active_runs"]
    assert len(rows) == 1
    assert {key: rows[0][key] for key in (
        "thread_id", "title", "proyecto", "agent", "stage", "run_id",
    )} == {
        "thread_id": running,
        "title": "Running work",
        "proyecto": "workspace",
        "agent": "orchestrator",
        "stage": "planning",
        "run_id": "live-run",
    }
    assert datetime.fromisoformat(rows[0]["updated_at"]).tzinfo is not None
    assert terminal not in [row["thread_id"] for row in rows]
    assert other_running not in [row["thread_id"] for row in rows]


def test_active_run_list_limit_is_bounded(client):
    _user("active-run-bounds", "admin")
    _login(client, "active-run-bounds")

    assert client.get("/panel/api/chat/active-runs?limit=0").status_code == 422
    assert client.get("/panel/api/chat/active-runs?limit=101").status_code == 422


def test_thread_list_includes_legacy_cortex_threads_as_normal_chats(client):
    _user("thread-list-legacy", "admin")
    _login(client, "thread-list-legacy")
    regular = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    with SessionLocal() as session:
        owner_id = session.scalar(select(User.id).where(User.username == "thread-list-legacy"))
        legacy = InternalChatThread(
            user_id=owner_id, proyecto="default",
            assistant_state={"cortex_session": {"slug": "legacy-session", "status": "closed"}},
        )
        session.add(legacy)
        session.flush()
        session.add_all([
            InternalChatMessage(thread_id=regular, author="admin", content="regular", status="processed"),
            InternalChatMessage(thread_id=legacy.id, author="admin", content="legacy", status="processed"),
        ])
        legacy_id = legacy.id
        session.commit()

    response = client.get("/panel/api/chat/threads?limit=10")

    assert response.status_code == 200
    assert {row["id"] for row in response.json()["threads"]} == {regular, legacy_id}


def test_thread_list_excludes_empty_threads_and_orders_message_ties_by_id(client):
    _user("thread-list-empty", "admin")
    _login(client, "thread-list-empty")
    empty = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    older = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    newer = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
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


def test_thread_list_preview_is_a_single_line_snippet_of_the_latest_message(client):
    _user("thread-preview", "admin")
    _login(client, "thread-preview")
    short_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    long_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    long_body = "Consulta de las **herramientas**\n\ndisponibles " + ("para el proyecto " * 20)
    with SessionLocal() as session:
        session.add_all([
            InternalChatMessage(thread_id=short_id, author="admin", content="Consulta breve", status="processed",
                                created_at=datetime(2026, 3, 1, tzinfo=timezone.utc)),
            InternalChatMessage(thread_id=long_id, author="agent", content="primer mensaje", status="processed",
                                created_at=datetime(2026, 3, 2, tzinfo=timezone.utc)),
            InternalChatMessage(thread_id=long_id, author="agent", content=long_body, status="processed",
                                created_at=datetime(2026, 3, 3, tzinfo=timezone.utc)),
        ])
        session.commit()

    rows = {row["id"]: row for row in client.get("/panel/api/chat/threads?limit=10&proyecto=default").json()["threads"]}

    assert rows[short_id]["preview"] == "Consulta breve"
    preview = rows[long_id]["preview"]
    assert "\n" not in preview and "  " not in preview
    assert preview.startswith("Consulta de las herramientas disponibles para el proyecto")
    assert preview.endswith("…")
    assert len(preview) <= 140


def test_thread_list_preview_is_null_when_the_latest_message_is_blank(client):
    _user("thread-preview-blank", "admin")
    _login(client, "thread-preview-blank")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    with SessionLocal() as session:
        session.add(InternalChatMessage(thread_id=thread_id, author="agent", content="   \n  ", status="processed",
                                        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc)))
        session.commit()

    rows = client.get("/panel/api/chat/threads?limit=10&proyecto=default").json()["threads"]

    assert rows[0]["preview"] is None


def test_thread_rename_and_delete_are_owned_and_not_exposed(client):
    _user("thread-owner", "admin")
    _user("thread-other-owner", "admin")
    _login(client, "thread-owner")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

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
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    monkeypatch.setattr(
        "app.services.agent_chat.run_assistant",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("planner failed")),
    )

    response = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Run this"}
    )

    assert response.status_code == 201
    assert response.json()["message"]["status"] == "processing"
    failed = _wait_for_run(client, thread_id, response.json()["message"]["assistant_metadata"]["run_id"])
    failed_message = next(item for item in failed["messages"] if item["author"] == "admin")
    assert failed_message["status"] == "failed"
    assert failed_message["error"] == "El agente no pudo procesar este mensaje. Reinténtalo."
    messages = client.get(f"/panel/api/chat/threads/{thread_id}").json()["messages"]
    assert not any(message["author"] == "agent" for message in messages)
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["events"][0]["type"] == "error"
        assert thread.assistant_state["events"][0]["sequence"] == 0


def test_empty_agent_response_is_localized(client, monkeypatch):
    _user("assistant-empty-response", "admin")
    _login(client, "assistant-empty-response")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    monkeypatch.setattr(
        "app.services.agent_chat.run_assistant",
        lambda *args, **kwargs: {"status": "completed", "response": None},
    )

    response = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Answer"})

    assert response.status_code == 201
    messages = _wait_for_run(client, thread_id, response.json()["message"]["assistant_metadata"]["run_id"])["messages"]
    assert messages[-1]["content"] == "No pude generar una respuesta. Inténtalo nuevamente."


def test_planner_and_terminal_stream_usage_are_persisted_once(client, monkeypatch):
    _user("assistant-usage", "admin")
    _login(client, "assistant-usage")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
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
    settled = _wait_for_run(client, thread_id, metadata["run_id"])
    metadata = next(item["assistant_metadata"] for item in settled["messages"] if item["author"] == "admin")
    assert set(metadata["cost_calls"]) == {metadata["run_id"] + ":planner", metadata["run_id"] + ":response"}
    assert metadata["cost_calls"][metadata["run_id"] + ":planner"]["prompt_tokens"] == 10
    response_call = metadata["cost_calls"][metadata["run_id"] + ":response"]
    assert response_call["prompt_tokens"] == 20
    assert response_call["completion_tokens"] == 7
    assert response_call["cost"] == pytest.approx(0.0000072)
    with SessionLocal() as session:
        request = session.get(InternalChatMessage, result.json()["message"]["id"])
        assert float(request.cost_llm) == pytest.approx(0.000012)


def test_a_plain_respond_turn_keeps_the_state_and_cost_contract(client, monkeypatch):
    _user("assistant-normal-turn-baseline", "admin")
    _login(client, "assistant-normal-turn-baseline")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    monkeypatch.setattr(
        "app.services.llm.get_settings",
        lambda: SimpleNamespace(assistant_chat_model="gpt-4o-mini"),
    )
    planner = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            "kind": "respond", "arguments": {}, "summary": "planned", "requires_approval": False,
        })))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
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

    posted = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "hello"})
    settled = _wait_for_run(client, thread_id, posted.json()["message"]["assistant_metadata"]["run_id"])
    request_message = next(item for item in settled["messages"] if item["author"] == "admin")

    # A plain respond plan acquires no tool steps and no capped chain.
    with SessionLocal() as session:
        state = session.get(InternalChatThread, thread_id).assistant_state
        request = session.get(InternalChatMessage, request_message["id"])
    assert state["planner"] == {
        "kind": "respond",
        "tool": None, "arguments": {}, "summary": "planned",
        "requires_approval": False, "follow_up": False, "skills": [], "valid": True,
        "success_criterion": None,
    }
    assert state["tool_steps"] == 0
    assert state["cap_reached"] is False
    assert state["guardrails"]["decision"] == "respond"
    cost_calls = request_message["assistant_metadata"]["cost_calls"]
    run_id = request_message["assistant_metadata"]["run_id"]
    assert set(cost_calls) == {run_id + ":planner", run_id + ":response"}
    assert cost_calls[run_id + ":planner"] == {
        "prompt_tokens": 10, "completion_tokens": 5, "cost": pytest.approx(0.0000045),
        "model": "gpt-4o-mini",
    }
    assert cost_calls[run_id + ":response"] == {
        "prompt_tokens": 20, "completion_tokens": 7, "cost": pytest.approx(0.0000072),
        "model": "gpt-4o-mini",
    }
    assert float(request.cost_llm) == pytest.approx(0.000012)


def _scripted_client(planner_outputs, stream_calls=None):
    """Fake provider: planner calls consume the scripted outputs; the title call gets plain text."""
    outputs = list(planner_outputs)

    class Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    if kwargs.get("stream"):
                        if stream_calls is not None:
                            stream_calls.append(kwargs)
                        return iter([
                            SimpleNamespace(
                                choices=[SimpleNamespace(delta=SimpleNamespace(content="answer"))], usage=None
                            ),
                            SimpleNamespace(choices=[], usage=None),
                        ])
                    prompt = kwargs["messages"][-1]["content"]
                    if "<available_tools>" not in prompt:
                        return SimpleNamespace(
                            choices=[SimpleNamespace(message=SimpleNamespace(content="thread title"))], usage=None
                        )
                    content = outputs.pop(0)
                    return SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content=content))], usage=None
                    )

    return Client()


def _run_turn(client, thread_id: int, content: str) -> dict:
    posted = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": content})
    run_id = posted.json()["message"]["assistant_metadata"]["run_id"]
    return _wait_for_run(client, thread_id, run_id)


def _persisted_planner(thread_id: int) -> dict:
    with SessionLocal() as session:
        return dict(session.get(InternalChatThread, thread_id).assistant_state["planner"])


def test_a_successful_turn_records_no_failure_diagnostic_from_an_earlier_turn(client, monkeypatch):
    _user("assistant-stale-planner", "admin")
    _login(client, "assistant-stale-planner")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    provider = _scripted_client([
        "this is not json",
        json.dumps({"kind": "respond", "arguments": {}, "summary": "done", "requires_approval": False}),
    ])
    monkeypatch.setattr("app.services.llm.openai_client", lambda: provider)

    _run_turn(client, thread_id, "first")
    assert "failure" in _persisted_planner(thread_id)

    _run_turn(client, thread_id, "second")
    planner = _persisted_planner(thread_id)

    assert planner["valid"] is True
    assert "failure" not in planner


def test_planner_arguments_belong_to_the_current_turn_only(client, monkeypatch):
    _user("assistant-stale-arguments", "admin")
    _login(client, "assistant-stale-arguments")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    provider = _scripted_client([
        json.dumps({
            "kind": "tool", "tool": "customers.search", "arguments": {"query": "ana"},
            "summary": "first", "requires_approval": False,
        }),
        json.dumps({
            "kind": "tool", "tool": "customers.search", "arguments": {"limit": 3},
            "summary": "second", "requires_approval": False,
        }),
    ])
    monkeypatch.setattr("app.services.llm.openai_client", lambda: provider)

    _run_turn(client, thread_id, "first")
    _run_turn(client, thread_id, "second")

    assert _persisted_planner(thread_id)["arguments"] == {"limit": 3}


_FALLBACK_SUMMARY = "No pude planificar esa solicitud de forma segura. Inténtalo nuevamente."


def _agent_answer(settled: dict) -> str:
    return [item for item in settled["messages"] if item["author"] == "agent"][-1]["content"]


def _turn_with_plan(client, monkeypatch, content: str, planner_output: str | list[str]):
    _user(f"assistant-failure-{content}", "admin")
    _login(client, f"assistant-failure-{content}")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    stream_calls: list = []
    outputs = [planner_output] if isinstance(planner_output, str) else planner_output
    provider = _scripted_client(outputs, stream_calls=stream_calls)
    monkeypatch.setattr("app.services.llm.openai_client", lambda: provider)
    return _run_turn(client, thread_id, content), stream_calls, thread_id


def test_a_failed_planner_does_not_reach_the_responder(client, monkeypatch):
    settled, stream_calls, _ = _turn_with_plan(client, monkeypatch, "plannerfailed", "this is not json")

    assert stream_calls == []
    assert _agent_answer(settled) == _FALLBACK_SUMMARY


def test_a_boundary_rejected_plan_does_not_reach_the_responder(client, monkeypatch):
    rejected = json.dumps({
        "kind": "tool", "tool": "customers.search", "arguments": {"limit": 999},
        "summary": "too many", "requires_approval": False,
    })
    settled, stream_calls, _ = _turn_with_plan(client, monkeypatch, "boundaryrejected", rejected)

    assert stream_calls == []
    assert _agent_answer(settled) == _FALLBACK_SUMMARY


def test_a_legitimate_respond_plan_still_reaches_the_responder(client, monkeypatch):
    respond = json.dumps({
        "kind": "respond", "arguments": {}, "summary": "te contesto", "requires_approval": False,
    })
    monkeypatch.setattr(
        "app.services.kb.retrieve",
        lambda *args, **kwargs: [{"content": "Grounded panel evidence", "similarity": 0.9}],
    )
    settled, stream_calls, _ = _turn_with_plan(client, monkeypatch, "legitrespond", respond)

    assert len(stream_calls) == 1
    assert _agent_answer(settled) == "answer"


def test_a_successful_tool_plan_still_executes_and_responds(client, monkeypatch):
    tool = json.dumps({
        "kind": "tool", "tool": "customers.search", "arguments": {"query": "ana"},
        "summary": "busco", "requires_approval": False,
    })
    settled, stream_calls, thread_id = _turn_with_plan(client, monkeypatch, "toolplan", tool)

    assert len(stream_calls) == 1
    assert _agent_answer(settled) == "answer"
    with SessionLocal() as session:
        guardrails_state = session.get(InternalChatThread, thread_id).assistant_state["guardrails"]
    assert guardrails_state["decision"] == "execute"


def test_a_customer_read_chain_persists_three_named_steps_and_events(client, monkeypatch):
    plans = [
        json.dumps({
            "kind": "tool", "tool": "customers.list", "arguments": {"limit": 2},
            "summary": "list customers", "requires_approval": False, "follow_up": True,
        }),
        json.dumps({
            "kind": "tool", "tool": "customers.search", "arguments": {"query": "Ana"},
            "summary": "search customer", "requires_approval": False, "follow_up": True,
        }),
        json.dumps({
            "kind": "tool", "tool": "customers.operational_history", "arguments": {"customer_id": 1},
            "summary": "read history", "requires_approval": False,
        }),
    ]
    _, _, thread_id = _turn_with_plan(client, monkeypatch, "three-customer-reads", plans)

    with SessionLocal() as session:
        state = session.get(InternalChatThread, thread_id).assistant_state
    assert state["tool_steps"] == 3
    assert [item["tool"] for item in state["tool_results"]] == [
        "customers.list", "customers.search", "customers.operational_history",
    ]
    assert [item["status"] for item in state["tool_results"]] == ["completed"] * 3
    tool_events = [event for event in state["events"] if event["type"] == "tool"]
    assert [event["tool"] for event in tool_events] == [
        "customers.list", "customers.search", "customers.operational_history",
    ]
    assert [event["status"] for event in tool_events] == ["completed"] * 3


def test_a_paged_read_chain_advances_instead_of_stalling_as_a_repeat(client, monkeypatch):
    """S1 + S10 + S11: paging forward is progress, not the repeated call the guard stops."""
    plans = [
        json.dumps({
            "kind": "tool", "tool": "customers.list", "arguments": {"limit": 20},
            "summary": "first page", "requires_approval": False, "follow_up": True,
        }),
        json.dumps({
            "kind": "tool", "tool": "customers.list", "arguments": {"limit": 20, "offset": 20},
            "summary": "next page", "requires_approval": False, "follow_up": True,
        }),
        json.dumps({
            "kind": "tool", "tool": "customers.operational_history",
            "arguments": {"customer_id": 1, "limit": 20},
            "summary": "history", "requires_approval": False,
        }),
    ]
    _, _, thread_id = _turn_with_plan(client, monkeypatch, "paged-read-chain", plans)

    with SessionLocal() as session:
        state = session.get(InternalChatThread, thread_id).assistant_state
    assert state["tool_steps"] == 3
    assert [item["tool"] for item in state["tool_results"]] == [
        "customers.list", "customers.list", "customers.operational_history",
    ]
    assert [item["status"] for item in state["tool_results"]] == ["completed"] * 3
    assert state["execution_stall"] is None
    assert state["cap_reached"] is False


def test_repeated_customer_read_persists_stall_without_spending_cap(client, monkeypatch):
    repeated = json.dumps({
        "kind": "tool", "tool": "customers.list", "arguments": {"limit": 20},
        "summary": "list customers", "requires_approval": False, "follow_up": True,
    })
    _, _, thread_id = _turn_with_plan(client, monkeypatch, "repeated-customer-read", [repeated, repeated])

    with SessionLocal() as session:
        state = session.get(InternalChatThread, thread_id).assistant_state
    assert state["tool_steps"] == 1
    assert state["execution_stall"] == "repeated_tool_call"
    assert state["cap_reached"] is False


def test_a_chained_read_only_turn_persists_tool_steps_and_cap_state(client, monkeypatch):
    plans = [
        json.dumps({
            "kind": "tool", "tool": "customers.search", "arguments": {"query": "ana"},
            "summary": "find customer", "requires_approval": False, "follow_up": True,
        }),
        json.dumps({
            "kind": "tool", "tool": "memory.search", "arguments": {"query": "ana"},
            "summary": "find memory", "requires_approval": False,
        }),
    ]
    _, _, thread_id = _turn_with_plan(client, monkeypatch, "chained-read-only", plans)

    with SessionLocal() as session:
        state = session.get(InternalChatThread, thread_id).assistant_state
    assert state["tool_steps"] == 2
    assert state["cap_reached"] is False
    # S3: what ran must stay auditable after the turn, without re-reading the events log.
    assert [item["tool"] for item in state["tool_results"]] == ["customers.search", "memory.search"]
    assert {item["status"] for item in state["tool_results"]} == {"completed"}
    assert state["guardrails"]["decision"] == "execute"


def test_a_chained_read_only_turn_responder_receives_combined_tool_evidence(client, monkeypatch):
    plans = [
        json.dumps({
            "kind": "tool", "tool": "assistant.capabilities", "arguments": {},
            "summary": "list capabilities", "requires_approval": False, "follow_up": True,
        }),
        json.dumps({
            "kind": "tool", "tool": "dashboard.summary", "arguments": {"window_days": 7},
            "summary": "read dashboard", "requires_approval": False,
        }),
    ]
    settled, stream_calls, _ = _turn_with_plan(client, monkeypatch, "combined-evidence", plans)

    responder_prompt = "\n".join(message["content"] for message in stream_calls[-1]["messages"])
    assert '"tool_count"' in responder_prompt
    assert '"contacts"' in responder_prompt
    assert _agent_answer(settled) == "answer"


def test_a_chained_read_only_turn_persists_the_tool_step_cap(client, monkeypatch):
    plans = [
        json.dumps({
            "kind": "tool", "tool": "customers.search", "arguments": {"query": f"ana {step}"},
            "summary": "find customer", "requires_approval": False, "follow_up": True,
        })
        for step in range(MAX_ASSISTANT_TOOL_STEPS)
    ]
    _, _, thread_id = _turn_with_plan(client, monkeypatch, "capped-read-only", plans)

    with SessionLocal() as session:
        state = session.get(InternalChatThread, thread_id).assistant_state
    assert state["tool_steps"] == MAX_ASSISTANT_TOOL_STEPS
    assert state["cap_reached"] is True


def test_a_capped_read_only_turn_responder_receives_combined_tool_evidence(client, monkeypatch):
    plans = [
        json.dumps({
            "kind": "tool", "tool": "assistant.capabilities", "arguments": {},
            "summary": "list capabilities", "requires_approval": False, "follow_up": True,
        }),
        json.dumps({
            "kind": "tool", "tool": "dashboard.summary", "arguments": {"window_days": 7},
            "summary": "read dashboard", "requires_approval": False, "follow_up": True,
        }),
        json.dumps({
            "kind": "tool", "tool": "assistant.capabilities", "arguments": {},
            "summary": "list capabilities again", "requires_approval": False, "follow_up": True,
        }),
        json.dumps({
            "kind": "tool", "tool": "customers.search", "arguments": {"query": "ana"},
            "summary": "find customer", "requires_approval": False, "follow_up": True,
        }),
    ]
    settled, stream_calls, _ = _turn_with_plan(client, monkeypatch, "capped-evidence", plans)

    responder_prompt = "\n".join(message["content"] for message in stream_calls[-1]["messages"])
    assert '"tool_count"' in responder_prompt
    assert '"contacts"' in responder_prompt
    assert _agent_answer(settled) == "answer"


def test_a_write_chain_emits_each_executed_step_before_the_next_approval(client, monkeypatch):
    """S1/S2 + T7 timeline: a chain shares one run id, and the panel renders a run's
    activity from every `evidence` event it can see. Each time the chain pauses again it
    must emit the steps the resume executed, so the write the operator just approved is
    visible before the next approval card -- and each step is reported exactly once."""
    _user("assistant-chain-timeline", "admin")
    _login(client, "assistant-chain-timeline")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    plans = [
        json.dumps({
            "kind": "tool", "tool": "settings.update",
            "arguments": {"key": "messages.farewell", "value": "Nos vemos."},
            "summary": "Cambiar la despedida", "requires_approval": True, "follow_up": True,
        }),
        json.dumps({
            "kind": "tool", "tool": "settings.update",
            "arguments": {"key": "tone.style", "value": "formal"},
            "summary": "Cambiar el tono", "requires_approval": True, "follow_up": False,
        }),
    ]
    stream_calls: list = []
    provider = _scripted_client(plans, stream_calls=stream_calls)
    monkeypatch.setattr("app.services.llm.openai_client", lambda: provider)

    posted = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "cambiá las dos cosas"})
    run_id = posted.json()["message"]["assistant_metadata"]["run_id"]
    settled = _wait_for_run(client, thread_id, run_id)
    first = next(item["assistant_metadata"]["approval"] for item in settled["messages"] if item["author"] == "admin")

    approved = client.post(
        f"/panel/api/chat/threads/{thread_id}/approval", json={"run_id": run_id, "token": first["token"]},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approval_pending"
    settled = _wait_for_run(client, thread_id, run_id)

    with SessionLocal() as session:
        state = session.get(InternalChatThread, thread_id).assistant_state
    chain_events = [event for event in state["events"] if event["run_id"] == run_id]
    # The approved step is on the stream before the next approval card, and the sequences
    # keep climbing so nothing is de-duplicated away.
    assert [event["type"] for event in chain_events] == ["plan", "approval", "tool", "evidence", "plan", "approval"]
    assert [event["sequence"] for event in chain_events] == list(range(6))
    assert [entry["tool"] for event in chain_events for entry in event.get("evidence", [])] == ["settings.update"]

    second = next(item["assistant_metadata"]["approval"] for item in settled["messages"] if item["author"] == "admin")
    final = client.post(
        f"/panel/api/chat/threads/{thread_id}/approval", json={"run_id": run_id, "token": second["token"]},
    )
    assert final.status_code == 200
    assert final.json()["status"] == "processed"

    with SessionLocal() as session:
        state = session.get(InternalChatThread, thread_id).assistant_state
    chain_events = [event for event in state["events"] if event["run_id"] == run_id]
    assert [event["type"] for event in chain_events] == [
        "plan", "approval", "tool", "evidence", "plan", "approval", "tool", "evidence", "status", "response",
    ]
    # The operator's activity shows both executed writes, each reported exactly once.
    assert [entry["tool"] for event in chain_events for entry in event.get("evidence", [])] == [
        "settings.update", "settings.update",
    ]
    assert stream_calls  # the responder narrated the completed chain


def test_stream_disconnect_keeps_known_usage_and_failed_request(client, monkeypatch):
    _user("assistant-disconnect", "admin")
    _login(client, "assistant-disconnect")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    planner = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            "kind": "respond", "arguments": {}, "summary": "planned", "requires_approval": False,
        })))]
        , usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5)
    )

    def disconnecting(**kwargs):
        # This must not be a generator function: `return planner` inside one yields a generator, so the
        # planner call would silently fail with `empty_completion` and the test would pass for the wrong
        # reason. Only the streaming path is lazy.
        if not kwargs.get("stream"):
            return planner

        def chunks():
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="partial"))], usage=None)
            yield SimpleNamespace(choices=[], usage=SimpleNamespace(prompt_tokens=20, completion_tokens=7))
            raise ConnectionError("stream disconnected")

        return chunks()

    client_stub = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=disconnecting)))
    monkeypatch.setattr("app.services.llm.openai_client", lambda: client_stub)
    result = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "hello"})
    assert result.json()["message"]["status"] == "processing"
    _wait_for_run(client, thread_id, result.json()["message"]["assistant_metadata"]["run_id"])
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
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

    pending = client.post(
        f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "create a rule"}
    )
    metadata = pending.json()["message"]["assistant_metadata"]
    settled = _wait_for_run(client, thread_id, metadata["run_id"])
    approval = next(item["assistant_metadata"]["approval"] for item in settled["messages"] if item["author"] == "admin")
    metadata = next(item["assistant_metadata"] for item in settled["messages"] if item["author"] == "admin")

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
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    monkeypatch.setattr(
        "app.services.agent_chat.execute",
        lambda state: {"status": "completed", "response": "Rule created.", "evidence": [{"tool": "automation.create_rule", "status": "completed", "detail": "created"}]},
    )

    pending = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "create a rule"})
    metadata = pending.json()["message"]["assistant_metadata"]
    settled = _wait_for_run(client, thread_id, metadata["run_id"])
    metadata = next(item["assistant_metadata"] for item in settled["messages"] if item["author"] == "admin")
    settled = _wait_for_run(client, thread_id, metadata["run_id"])
    metadata = next(item["assistant_metadata"] for item in settled["messages"] if item["author"] == "admin")
    approved = client.post(
        f"/panel/api/chat/threads/{thread_id}/approval",
        json={"run_id": metadata["run_id"], "token": metadata["approval"]["token"]},
    )
    assert approved.status_code == 200

    stream = client.get(f"/panel/api/chat/threads/{thread_id}/stream?run_id={metadata['run_id']}")
    events = [json.loads(line.removeprefix("data: ")) for line in stream.text.splitlines() if line.startswith("data: ")]
    assert [event["type"] for event in events] == ["plan", "approval", "tool", "evidence", "status", "response", "status", "response"]
    assert all(event["thread_id"] == thread_id and event["run_id"] == metadata["run_id"] for event in events)
    assert [event["sequence"] for event in events[:6]] == list(range(6))


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
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    pending = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "create a rule"})
    assert pending.status_code == 201
    metadata = pending.json()["message"]["assistant_metadata"]
    settled = _wait_for_run(client, thread_id, metadata["run_id"])
    metadata = next(item["assistant_metadata"] for item in settled["messages"] if item["author"] == "admin")

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
    thread_id = client.post(f"/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    pending = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "create a rule"})
    metadata = pending.json()["message"]["assistant_metadata"]
    settled = _wait_for_run(client, thread_id, metadata["run_id"])
    metadata = next(item["assistant_metadata"] for item in settled["messages"] if item["author"] == "admin")
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
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    monkeypatch.setattr("app.services.agent_chat.run_assistant", lambda *args, **kwargs: _completed_result())
    calls = []
    monkeypatch.setattr(
        "app.services.llm.openai_client",
        lambda provider=None: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs) or _title_completion()
        ))),
    )

    first = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "  Need a gas leak inspection  "})
    _wait_for_run(client, thread_id, first.json()["message"]["assistant_metadata"]["run_id"])
    second = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "More details"})
    _wait_for_run(client, thread_id, second.json()["message"]["assistant_metadata"]["run_id"])

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
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
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
    _wait_for_run(client, thread_id, response.json()["message"]["assistant_metadata"]["run_id"])

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
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
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
    _wait_for_run(client, thread_id, response.json()["message"]["assistant_metadata"]["run_id"])

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
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    monkeypatch.setattr("app.services.agent_chat.run_assistant", lambda *args, **kwargs: _completed_result())
    monkeypatch.setattr(
        "app.services.llm.openai_client",
        lambda provider=None: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: (_ for _ in ()).throw(failure)
        ))),
    )
    opening = "Request: " + " revisión" * 100

    response = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": opening})
    _wait_for_run(client, thread_id, response.json()["message"]["assistant_metadata"]["run_id"])

    assert response.status_code == 201
    with SessionLocal() as session:
        title = session.get(InternalChatThread, thread_id).title
        assert title == opening.strip()[: len(title)]
        assert len(title.encode("utf-8")) <= 120


def test_title_fallback_is_non_empty_when_an_assistant_response_has_no_admin_opening(monkeypatch):
    user = _user("assistant-title-no-opening", "admin")
    with SessionLocal() as session:
        owner = session.scalar(select(User).where(User.username == "assistant-title-no-opening"))
        thread = InternalChatThread(user_id=owner.id)
        session.add(thread)
        session.flush()
        response = InternalChatMessage(
            thread_id=thread.id, author="agent", content="Respuesta persistida", status="processed"
        )
        session.add(response)
        session.flush()
        monkeypatch.setattr("app.services.costs.internal_thread_cost_state", lambda session, thread_id: (0, "conservative"))
        _generate_thread_title(session, thread, response)
        assert thread.title == "Conversación con el asistente"
        assert thread.title


def test_stream_events_async_polls_without_blocking_the_event_loop():
    """A stream idles on the event loop; a blocking poll would starve every other task.

    The ticker only advances when the poll loop yields. A `time.sleep` between
    polls (or a generator consumed on a worker thread) freezes it for the whole
    stream window — the resource hold `assistant-sse-resource-hold` fixes.
    """
    polls = 0

    class Session:
        def get(self, model, thread_id):
            nonlocal polls
            polls += 1
            return SimpleNamespace(assistant_state={"events": [], "live": {
                "run_id": "run-live", "stage": "streaming", "preview": f"chunk-{polls}", "status": "processing",
            }})

        def close(self):
            pass

    async def collect() -> tuple[list[dict], int]:
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        beat = asyncio.create_task(ticker())
        try:
            events = [
                event
                async for event in stream_events_async(lambda: Session(), 1, "run-live", timeout=0.3, interval=0.05)
            ]
        finally:
            beat.cancel()
        return events, ticks

    events, ticks = asyncio.run(collect())

    assert [event["type"] for event in events] == ["status"] + ["response"] * polls + ["timeout"]
    assert polls >= 3
    assert ticks >= 10
    assert events[-1] == {"type": "timeout", "thread_id": 1, "run_id": "run-live"}
    assert sum(event["type"] == "timeout" for event in events) == 1
    assert "status" not in events[-1]


def test_stream_events_async_does_not_timeout_terminal_run():
    class Session:
        def get(self, model, thread_id):
            return SimpleNamespace(assistant_state={"events": [], "live": {
                "run_id": "run-done", "stage": "completed", "preview": "done", "status": "completed",
            }})

        def close(self):
            pass

    async def collect():
        return [
            event
            async for event in stream_events_async(lambda: Session(), 1, "run-done", timeout=0.01, interval=0)
        ]

    events = asyncio.run(collect())

    assert all(event["type"] != "timeout" for event in events)


def test_stream_events_emits_timeout_for_a_non_terminal_run():
    class Session:
        def get(self, model, thread_id):
            return SimpleNamespace(assistant_state={"events": [], "live": {
                "run_id": "run-sync", "stage": "streaming", "preview": "partial", "status": "processing",
            }})

        def close(self):
            pass

    events = list(stream_events(lambda: Session(), 1, "run-sync", timeout=0.01, interval=0))

    assert events[-1] == {"type": "timeout", "thread_id": 1, "run_id": "run-sync"}


def test_open_assistant_stream_releases_its_pooled_connection(client):
    """An open SSE stream must not keep a request-scoped connection checked out.

    FastAPI closes request dependencies only after the response is fully sent, so
    a stream would hold one pooled connection for its whole life (up to 300 s)
    unless the route releases the session before it starts yielding.
    """
    from sqlalchemy import event as sqlalchemy_event

    from app.db import engine

    _user("stream-pool", "admin")
    _login(client, "stream-pool")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    sent = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Summarize operations"})
    run_id = sent.json()["message"]["assistant_metadata"]["run_id"]

    open_connections = 0
    peak = 0

    def _checkout(*args):
        nonlocal open_connections, peak
        open_connections += 1
        peak = max(peak, open_connections)

    def _checkin(*args):
        nonlocal open_connections
        open_connections -= 1

    sqlalchemy_event.listen(engine, "checkout", _checkout)
    sqlalchemy_event.listen(engine, "checkin", _checkin)
    try:
        assert engine.pool.checkedout() == 0
        with client.stream("GET", f"/panel/api/chat/threads/{thread_id}/stream?run_id={run_id}") as stream:
            assert stream.status_code == 200
            first = next(stream.iter_lines(), None)
            assert first is not None and first.startswith("data: ")
            assert peak == 1
    finally:
        sqlalchemy_event.remove(engine, "checkout", _checkout)
        sqlalchemy_event.remove(engine, "checkin", _checkin)


def test_open_assistant_stream_never_reads_the_thread_messages(client):
    """Opening a stream needs the thread row, never its message history.

    The route reads only `active_run_id`, but it used `get_thread`, which also
    loads every message of the thread — an unbounded read whose result was
    discarded. The cost grew with the thread's history for nothing.
    """
    from sqlalchemy import event as sqlalchemy_event

    from app.db import engine

    _user("stream-read", "admin")
    _login(client, "stream-read")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    sent = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Summarize operations"})
    run_id = sent.json()["message"]["assistant_metadata"]["run_id"]

    statements: list[str] = []

    def _record_statement(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    sqlalchemy_event.listen(engine, "before_cursor_execute", _record_statement)
    try:
        with client.stream("GET", f"/panel/api/chat/threads/{thread_id}/stream?run_id={run_id}") as stream:
            assert stream.status_code == 200
            first = next(stream.iter_lines(), None)
            assert first is not None and first.startswith("data: ")
    finally:
        sqlalchemy_event.remove(engine, "before_cursor_execute", _record_statement)

    read_messages = [statement for statement in statements if "internal_chat_messages" in statement]
    assert read_messages == []


def test_stream_without_run_id_follows_the_thread_active_run(client):
    """`run_id` is optional: without it the stream follows the thread's active run.

    Coverage for the fallback the route takes when the query string omits it —
    every other stream test either passes a `run_id` or is rejected by role
    before the handler runs.
    """
    _user("stream-fallback", "admin")
    _login(client, "stream-fallback")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    sent = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Summarize operations"})
    run_id = sent.json()["message"]["assistant_metadata"]["run_id"]

    response = client.get(f"/panel/api/chat/threads/{thread_id}/stream")

    assert response.status_code == 200
    payloads = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert payloads
    assert {payload["run_id"] for payload in payloads} == {run_id}


def _seed_assistant_run(
    username: str, run_id: str, *, stage: str, execution_status: str, updated_at: datetime, live_status: str = "running"
) -> tuple[int, int]:
    """Seed one thread holding a live run and its `processing` message."""
    with SessionLocal() as session:
        user = User(username=username, password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
        thread = InternalChatThread(
            user_id=user.id,
            active_run_id=run_id,
            assistant_state={
                "stage": stage,
                "execution_status": execution_status,
                "live": {
                    "run_id": run_id, "stage": stage, "preview": "", "status": live_status,
                    "updated_at": updated_at.isoformat(),
                },
            },
        )
        session.add(thread)
        session.flush()
        message = InternalChatMessage(
            thread_id=thread.id, author="admin", content="hola", status="processing",
            assistant_metadata={"run_id": run_id},
        )
        session.add(message)
        session.commit()
        return thread.id, message.id


def test_reap_orphaned_runs_fails_a_fresh_run_the_read_path_would_spare():
    """At boot a `running` live state is proof of orphanhood; the 600 s timer is not needed."""
    now = datetime.now(timezone.utc)
    thread_id, _ = _seed_assistant_run(
        "orphan-boot", "run-orphan-boot", stage="planning", execution_status="pending", updated_at=now
    )

    with SessionLocal() as session:
        assert reap_stale_run(session, session.get(InternalChatThread, thread_id)) is False

    assert reap_orphaned_runs(SessionLocal) == 1

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["stage"] == "failed"
        assert thread.assistant_state["live"]["status"] == "failed"
        assert thread.assistant_state["recoverable"] is True
        message = session.scalar(select(InternalChatMessage).where(InternalChatMessage.thread_id == thread_id))
        assert message.status == "failed"
        assert message.error == "El agente no pudo procesar este mensaje. Reinténtalo."
        assert message.completed_at is not None


def test_reap_orphaned_runs_leaves_a_resumable_execution_alone():
    """`resume_thread` can still reclaim a pending execution: boot must not discard it."""
    now = datetime.now(timezone.utc)
    thread_id, message_id = _seed_assistant_run(
        "orphan-resumable", "run-resumable", stage="executing", execution_status="pending", updated_at=now
    )

    assert reap_orphaned_runs(SessionLocal) == 0

    with SessionLocal() as session:
        assert session.get(InternalChatThread, thread_id).assistant_state["stage"] == "executing"
        assert session.get(InternalChatMessage, message_id).status == "processing"


def test_reap_orphaned_runs_leaves_settled_and_never_ran_threads_alone():
    """Only a `running` live state proves orphanhood; nothing else may be reaped.

    The settled thread's message stays `processing` on purpose: it shows the SELECT excludes the
    thread, not that the UPDATE's own guard saved it. The never-ran thread is the JSONB boundary —
    `{}` yields a NULL path, so the comparison must not match.
    """
    now = datetime.now(timezone.utc)
    settled_id, settled_message_id = _seed_assistant_run(
        "orphan-settled", "run-settled", stage="completed", execution_status="completed",
        updated_at=now, live_status="completed",
    )
    with SessionLocal() as session:
        user = User(username="orphan-never-ran", password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
        never_ran = InternalChatThread(user_id=user.id, assistant_state={})
        session.add(never_ran)
        session.commit()
        never_ran_id = never_ran.id

    assert reap_orphaned_runs(SessionLocal) == 0

    with SessionLocal() as session:
        assert session.get(InternalChatThread, settled_id).assistant_state["stage"] == "completed"
        assert session.get(InternalChatMessage, settled_message_id).status == "processing"
        assert session.get(InternalChatThread, never_ran_id).assistant_state == {}


def test_startup_sweep_fails_orphaned_assistant_runs():
    from fastapi.testclient import TestClient

    from app.main import create_app

    now = datetime.now(timezone.utc)
    thread_id, message_id = _seed_assistant_run(
        "orphan-startup", "run-startup", stage="responding", execution_status="pending", updated_at=now
    )

    with TestClient(create_app()):
        pass  # lifespan runs the startup sweeps

    with SessionLocal() as session:
        assert session.get(InternalChatMessage, message_id).status == "failed"
        assert session.get(InternalChatThread, thread_id).assistant_state["stage"] == "failed"


def test_startup_sweep_isolation_survives_an_earlier_sweep_failing(monkeypatch):
    """The sweeps are independent recoveries: one breaking must not skip the rest."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    def explode() -> int:
        raise RuntimeError("notification sweep exploded")

    monkeypatch.setattr("app.main.run_notification_sweep", explode)

    now = datetime.now(timezone.utc)
    thread_id, message_id = _seed_assistant_run(
        "orphan-isolated", "run-isolated", stage="responding", execution_status="pending", updated_at=now
    )

    with TestClient(create_app()):
        pass  # lifespan runs the startup sweeps

    with SessionLocal() as session:
        assert session.get(InternalChatMessage, message_id).status == "failed"
        assert session.get(InternalChatThread, thread_id).assistant_state["stage"] == "failed"
