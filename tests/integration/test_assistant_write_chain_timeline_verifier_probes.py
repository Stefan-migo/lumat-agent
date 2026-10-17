"""Independent verifier probes for assistant-write-chaining Unit 1 (S1-S7 + T7 timeline).

Derived from the feature document's acceptance rules, not from the writer's tests.
"""

import json
import time
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select

from app.chat.assistant.approval import issue_approval
from app.chat.assistant.nodes import MAX_ASSISTANT_TOOL_STEPS, tool_loop_head
from app.chat.assistant.tools.registry import AUTONOMOUS_WRITE_ALLOWLIST
from app.db import SessionLocal
from app.models import AuditLog, InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import (
    _paused_step_events, approve_plan, reap_orphaned_runs, reap_stale_run, resume_thread,
)
from app.services.settings import get_setting
from app.services.users import hash_password


def _user(username, role="admin"):
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role=role))
        session.commit()


def _login(client, username):
    assert client.post("/panel/api/login", json={"username": username, "password": "pass"}).status_code == 200
    assert client.get("/panel/api/me").status_code == 200


def _wait(client, thread_id, run_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        result = client.get(f"/panel/api/chat/threads/{thread_id}").json()
        message = next((m for m in result["messages"]
                        if m.get("assistant_metadata", {}).get("run_id") == run_id and m["author"] == "admin"), None)
        if message and message["status"] != "processing":
            return result
        time.sleep(0.05)
    raise AssertionError("assistant run did not finish")


def _provider(plans, stream_calls=None):
    outputs = list(plans)

    class Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    if kwargs.get("stream"):
                        if stream_calls is not None:
                            stream_calls.append(kwargs)
                        return iter([SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="answer"))], usage=None),
                                     SimpleNamespace(choices=[], usage=None)])
                    if "<available_tools>" not in kwargs["messages"][-1]["content"]:
                        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="title"))], usage=None)
                    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=outputs.pop(0)))], usage=None)

    return Client()


class _Completions:
    def __init__(self, plans):
        self.plans, self.planner_calls, self.stream_calls = list(plans), [], []

    def create(self, **kwargs):
        if kwargs.get("stream"):
            self.stream_calls.append(kwargs)
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Listo."))])]
        self.planner_calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.plans[len(self.planner_calls) - 1]))])


def _client(monkeypatch, plans):
    from app.chat.assistant import nodes as n
    provider = _Completions(plans)
    monkeypatch.setattr(n, "_assistant_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=provider)))
    return provider


def _write(key, value, *, follow_up):
    return {"kind": "tool", "tool": "settings.update", "arguments": {"key": key, "value": value},
            "summary": f"update {key}", "requires_approval": True, "follow_up": follow_up}


def _thread(session, *, plan, approval, run_id, extra=None):
    user = User(username=f"t7-{uuid4().hex[:10]}", password_hash=hash_password("pass"), role="admin")
    session.add(user)
    session.flush()
    state = {"stage": "approval_pending", "approval": approval, "actor_role": "admin", **(extra or {})}
    thread = InternalChatThread(user_id=user.id, active_run_id=run_id, current_plan=plan, assistant_state=state)
    session.add(thread)
    session.flush()
    session.add(InternalChatMessage(thread_id=thread.id, author="admin", content="hacelo",
                                    status="approval_pending", assistant_metadata={"run_id": run_id}))
    session.commit()
    return user, thread


def _events(thread_id, run_id):
    with SessionLocal() as session:
        state = session.get(InternalChatThread, thread_id).assistant_state
    return [event for event in state["events"] if event["run_id"] == run_id]


def _tools(events):
    return [entry["tool"] for event in events for entry in event.get("evidence", [])]


def test_s2_spent_token_cannot_authorize_an_identical_next_write(migrated_db, monkeypatch):
    """S2: step 2 repeats step 1's exact arguments, so the spent token's digest matches the
    next plan; only the pending/consumed gate stops it from authorizing step 2."""
    run_id = f"t7-s2-{uuid4().hex[:10]}"
    first = _write("messages.farewell", "Repetido.", follow_up=True)
    second = _write("messages.farewell", "Repetido.", follow_up=False)
    provider = _client(monkeypatch, [json.dumps(second)])
    with SessionLocal() as session:
        a1 = issue_approval(first)
        user, thread = _thread(session, plan=first, approval=a1, run_id=run_id)
        parked = approve_plan(session, thread, user, run_id, a1["token"])
        session.commit()
        assert parked is not None and parked.status == "approval_pending"
        session.refresh(thread)
        a2 = thread.assistant_state["approval"]
        assert a1["arguments_sha256"] == a2["arguments_sha256"] and a1["token"] != a2["token"]
        assert a2["status"] == "pending" and a2["arguments"] == second["arguments"]
        assert approve_plan(session, thread, user, run_id, a1["token"]) is None
        assert thread.assistant_state["tool_steps"] == 1 and get_setting(session, "messages.farewell") == "Repetido."
        done = approve_plan(session, thread, user, run_id, a2["token"])
        session.commit()
        assert done.status == "processed"
        session.refresh(thread)
        assert thread.assistant_state["tool_steps"] == 2 and len(provider.planner_calls) == 1


def test_s2_other_plan_token_is_refused(migrated_db, monkeypatch):
    run_id = f"t7-s2-bind-{uuid4().hex[:10]}"
    plan = _write("messages.farewell", "Original.", follow_up=False)
    _client(monkeypatch, [])
    with SessionLocal() as session:
        approval = issue_approval(plan)
        user, thread = _thread(session, plan=plan, approval=approval, run_id=run_id)
        thread.current_plan = {**plan, "arguments": {"key": "messages.farewell", "value": "Otro."}}
        session.flush()
        assert approve_plan(session, thread, user, run_id, approval["token"]) is None
        session.commit()
        assert get_setting(session, "messages.farewell") != "Otro."
        session.refresh(thread)
        assert thread.assistant_state["approval"]["status"] == "pending"


def test_s3_class_b_set_is_exactly_agreed_and_chains_without_approval(migrated_db, monkeypatch):
    assert AUTONOMOUS_WRITE_ALLOWLIST == frozenset({
        "memory.write", "memory.update", "memory.delete", "artifact.save",
        "planning.open", "planning.close", "planning.record_decision", "planning.record_note",
    })
    from app.chat.assistant.graph import run_assistant

    run_id = f"t7-s3-{uuid4().hex[:10]}"
    write = {"kind": "tool", "tool": "memory.write",
             "arguments": {"titulo": "T7", "contenido": "clase B", "topic_key": "agent:t7", "tipo": "discovery"},
             "summary": "guardar", "requires_approval": False, "follow_up": True}
    search = {"kind": "tool", "tool": "memory.search", "arguments": {"query": "clase B"},
              "summary": "buscar", "requires_approval": False, "follow_up": False}
    _client(monkeypatch, [json.dumps(write), json.dumps(search)])
    with SessionLocal() as session:
        user = User(username=f"t7-s3-{uuid4().hex[:10]}", password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
        thread = InternalChatThread(user_id=user.id, active_run_id=run_id, assistant_state={})
        session.add(thread)
        session.commit()
        result = run_assistant(thread_id=thread.id, user_id=user.id, content="guardá y buscá", run_id=run_id,
                               on_token=lambda _t: None, session=session, actor=user.username, actor_role="admin")
        assert result["status"] == "completed" and result.get("approval") is None
        assert [entry["tool"] for entry in result["tool_results"]] == ["memory.write", "memory.search"]
        assert result["tool_steps"] == 2


def test_s5_reject_is_terminal_audited_and_never_resumable(migrated_db, monkeypatch):
    run_id = f"t7-s5-{uuid4().hex[:10]}"
    first = _write("messages.farewell", "Nos vemos.", follow_up=True)
    second = _write("tone.style", "formal", follow_up=False)
    _client(monkeypatch, [json.dumps(second)])
    with SessionLocal() as session:
        a1 = issue_approval(first)
        user, thread = _thread(session, plan=first, approval=a1, run_id=run_id)
        approve_plan(session, thread, user, run_id, a1["token"])
        session.commit()
        session.refresh(thread)
        a2, thread_id = thread.assistant_state["approval"], thread.id
        rejected = approve_plan(session, thread, user, run_id, a2["token"], reject=True)
        session.commit()
        assert rejected.status == "rejected" and rejected.completed_at is not None
        state = thread.assistant_state
        assert (state["stage"], state["execution_status"], state["live"]["status"]) == ("rejected", "rejected", "rejected")
        assert state["approval"]["status"] == "rejected" and state["tool_steps"] == 1
        assert get_setting(session, "tone.style") == "cercano"
        assert [entry["tool"] for entry in state["tool_results"]] == ["settings.update"]
        assert approve_plan(session, thread, user, run_id, a2["token"]) is None
        assert approve_plan(session, thread, user, run_id, a2["token"], reject=True) is None
        audit = session.scalars(select(AuditLog).where(
            AuditLog.entity_id == str(thread_id), AuditLog.action == "internal_chat.approval_rejected")).all()
        assert len(audit) == 1 and audit[0].after == {
            "run_id": run_id, "tool": "settings.update", "reason": "operator_rejected", "step": 1,
        }
        assert resume_thread(session, thread, user) is False
        assert reap_stale_run(session, thread) is False
        session.commit()
        assert reap_orphaned_runs(SessionLocal) == 0
    with SessionLocal() as fresh:
        thread = fresh.get(InternalChatThread, thread_id)
        assert thread.assistant_state["stage"] == "rejected"
        assert fresh.scalar(select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread_id, InternalChatMessage.author == "agent")) is None


def _consumed(plan):
    approval = issue_approval(plan)
    approval["status"] = "consumed"
    return approval


def test_s6_resume_requires_executing_stage_and_runs_once(migrated_db, monkeypatch):
    run_id = f"t7-s6-{uuid4().hex[:10]}"
    plan = _write("messages.farewell", "Una vez.", follow_up=False)
    _client(monkeypatch, [])
    with SessionLocal() as session:
        user, thread = _thread(session, plan=plan, approval=_consumed(plan), run_id=run_id,
                               extra={"stage": "executing", "execution_status": "pending",
                                      "tool_results": [], "tool_steps": 0})
        session.scalar(select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread.id)).status = "processing"
        session.flush()
        assert resume_thread(session, thread, user) is True
        session.commit()
        assert get_setting(session, "messages.farewell") == "Una vez."
        session.refresh(thread)
        assert thread.assistant_state["stage"] == "completed" and thread.assistant_state["tool_steps"] == 1
        assert resume_thread(session, thread, user) is False
        assert thread.assistant_state["tool_steps"] == 1
    with SessionLocal() as session:
        user, thread = _thread(session, plan=plan, approval=_consumed(plan), run_id=f"{run_id}-parked",
                               extra={"stage": "approval_pending", "execution_status": "pending"})
        assert resume_thread(session, thread, user) is False
        assert get_setting(session, "messages.farewell") == "Una vez."


def test_s7_cap_and_blocked_cost_gate_bound_the_loop(monkeypatch):
    from app.chat.assistant import nodes as n
    assert MAX_ASSISTANT_TOOL_STEPS == 4
    plan = {"kind": "tool", "tool": "assistant.capabilities", "arguments": {}, "follow_up": True}
    state = {"thread_id": 7, "plan": plan, "tool_steps": MAX_ASSISTANT_TOOL_STEPS, "guardrails": {}}
    assert tool_loop_head(state) == {"cap_reached": True, "status": "completed"}
    assert tool_loop_head({**state, "tool_steps": MAX_ASSISTANT_TOOL_STEPS - 1})["status"] == "planned"
    monkeypatch.setattr(n, "_cost_snapshot", lambda *a, **k: {"mode": "blocked"})
    stopped = tool_loop_head({**state, "tool_steps": 1})
    assert stopped["status"] == "completed"
    assert stopped["guardrails"]["decision"] == "loop_cost_stopped"
    assert stopped["guardrails"]["cost_allowed"] is False


def test_s7_cap_bounds_a_write_chain_across_approvals(migrated_db, monkeypatch):
    run_id = f"t7-cap-{uuid4().hex[:10]}"
    plan = _write("messages.farewell", "Cadena.", follow_up=True)
    provider = _client(monkeypatch, [json.dumps(plan) for _ in range(MAX_ASSISTANT_TOOL_STEPS)])
    with SessionLocal() as session:
        approval = issue_approval(plan)
        user, thread = _thread(session, plan=plan, approval=approval, run_id=run_id)
        for _ in range(MAX_ASSISTANT_TOOL_STEPS + 2):
            message = approve_plan(session, thread, user, run_id, approval["token"])
            assert message is not None
            session.commit()
            session.refresh(thread)
            if message.status != "approval_pending":
                break
            approval = thread.assistant_state["approval"]
        assert thread.assistant_state["tool_steps"] == MAX_ASSISTANT_TOOL_STEPS
        assert thread.assistant_state["cap_reached"] is True and message.status == "processed"
        assert len(provider.planner_calls) == MAX_ASSISTANT_TOOL_STEPS - 1


def test_t7_paused_step_events_is_a_delta_only():
    result = {"tool_results": [{"tool": "a"}, {"tool": "b"}, {"tool": "c"}]}
    events = _paused_step_events(result, 1, "run", 10, reported=2)
    assert [(event["type"], event.get("tool")) for event in events] == [("tool", "c"), ("evidence", None)]
    assert [entry["tool"] for entry in events[1]["evidence"]] == ["c"]
    assert [event["sequence"] for event in events] == [10, 11]
    assert _paused_step_events(result, 1, "run", 0, reported=3) == []
    assert _paused_step_events({"tool_results": []}, 1, "run", 0, reported=0) == []


def test_t7_timeline_reports_each_executed_step_once_across_pauses(client, monkeypatch):
    """S1/S2 + T7: a resume that executes a write plus a read-only follow-up reports both
    before the next approval; the final completion does not repeat them. The panel's
    flatMap over `events[].evidence` is exactly `_tools(events)`."""
    _user("t7-timeline")
    _login(client, "t7-timeline")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    write_one = _write("messages.farewell", "Primero.", follow_up=True)
    read = {"kind": "tool", "tool": "assistant.capabilities", "arguments": {},
            "summary": "listar", "requires_approval": False, "follow_up": True}
    write_two = _write("tone.style", "formal", follow_up=False)
    stream_calls = []
    provider = _provider([json.dumps(write_one), json.dumps(read), json.dumps(write_two)], stream_calls)
    monkeypatch.setattr("app.services.llm.openai_client", lambda: provider)

    posted = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "hacé la cadena"})
    run_id = posted.json()["message"]["assistant_metadata"]["run_id"]
    settled = _wait(client, thread_id, run_id)
    first = next(m["assistant_metadata"]["approval"] for m in settled["messages"] if m["author"] == "admin")
    approved = client.post(f"/panel/api/chat/threads/{thread_id}/approval",
                           json={"run_id": run_id, "token": first["token"]})
    assert approved.status_code == 200 and approved.json()["status"] == "approval_pending"
    settled = _wait(client, thread_id, run_id)

    events = _events(thread_id, run_id)
    assert [event["type"] for event in events] == ["plan", "approval", "tool", "tool", "evidence", "plan", "approval"]
    assert [event["sequence"] for event in events] == list(range(7))
    assert _tools(events) == ["settings.update", "assistant.capabilities"]

    second = next(m["assistant_metadata"]["approval"] for m in settled["messages"] if m["author"] == "admin")
    final = client.post(f"/panel/api/chat/threads/{thread_id}/approval",
                        json={"run_id": run_id, "token": second["token"]})
    assert final.status_code == 200 and final.json()["status"] == "processed"
    events = _events(thread_id, run_id)
    assert [event["type"] for event in events] == [
        "plan", "approval", "tool", "tool", "evidence", "plan", "approval", "tool", "evidence", "status", "response",
    ]
    assert _tools(events) == ["settings.update", "assistant.capabilities", "settings.update"]
    blob = str(stream_calls[0]["messages"])
    evidence_block = blob.split("<tool_evidence>", 1)[1].split("</tool_evidence>", 1)[0]
    assert "Primero." in evidence_block and "formal" in evidence_block
