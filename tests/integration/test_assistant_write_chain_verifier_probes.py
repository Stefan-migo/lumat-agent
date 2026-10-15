"""Independent regression probes for the approved-write chain (T2)."""

import json
from types import SimpleNamespace
from uuid import uuid4

from app.chat.assistant.approval import issue_approval
from app.chat.assistant.nodes import MAX_ASSISTANT_TOOL_STEPS, tool_loop_head
from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import approve_plan, reap_orphaned_runs, reap_stale_run, resume_thread
from app.services.settings import get_setting
from app.services.users import hash_password


class _Completions:
    def __init__(self, plans, text="Listo."):
        self.plans, self.text, self.planner_calls, self.stream_calls = list(plans), text, [], 0

    def create(self, **kwargs):
        if kwargs.get("stream"):
            self.stream_calls += 1
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=self.text))])]
        self.planner_calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.plans[len(self.planner_calls) - 1]))])


def _client(monkeypatch, plans):
    from app.chat.assistant import nodes as n

    c = _Completions(plans)
    monkeypatch.setattr(n, "_assistant_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=c)))
    return c


def _thread(session, *, plan, approval, run_id):
    user = User(username=f"p-{uuid4().hex[:10]}", password_hash=hash_password("pass"), role="admin")
    session.add(user)
    session.flush()
    thread = InternalChatThread(
        user_id=user.id, active_run_id=run_id, current_plan=plan,
        assistant_state={"stage": "approval_pending", "approval": approval, "actor_role": "admin"},
    )
    session.add(thread)
    session.flush()
    session.add(InternalChatMessage(
        thread_id=thread.id, author="admin", content="hacelo",
        status="approval_pending", assistant_metadata={"run_id": run_id, "approval": approval},
    ))
    session.commit()
    return user, thread


def _first():
    return {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": "Nos vemos."},
        "summary": "despedida", "requires_approval": True, "follow_up": True,
    }


def _second():
    return {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "tone.style", "value": "formal"},
        "summary": "tono", "requires_approval": True, "follow_up": False,
    }


def _park_on_second(session, monkeypatch, run_id):
    c = _client(monkeypatch, [json.dumps(_second())])
    a1 = issue_approval(_first())
    user, thread = _thread(session, plan=_first(), approval=a1, run_id=run_id)
    msg = approve_plan(session, thread, user, run_id, a1["token"])
    session.commit()
    assert msg is not None and msg.status == "approval_pending"
    session.refresh(thread)
    return c, user, thread, a1


def test_s2_second_approval_binds_step_two_args_and_spent_token_rejected(migrated_db, monkeypatch):
    with SessionLocal() as session:
        _c, user, thread, a1 = _park_on_second(session, monkeypatch, f"p-{uuid4().hex[:10]}")
        a2 = thread.assistant_state["approval"]
        assert a2["token"] != a1["token"] and a2["status"] == "pending"
        assert a2["arguments"] == _second()["arguments"]
        assert a2["arguments_sha256"] == issue_approval(_second())["arguments_sha256"] != a1["arguments_sha256"]
        assert approve_plan(session, thread, user, thread.active_run_id, a1["token"]) is None
        assert get_setting(session, "tone.style") == "cercano"


def test_s2_step_two_never_executes_without_consumed_approval(migrated_db, monkeypatch):
    with SessionLocal() as session:
        _c, user, thread, _a1 = _park_on_second(session, monkeypatch, f"p-{uuid4().hex[:10]}")
        assert resume_thread(session, thread, user) is False
        session.commit()
        assert get_setting(session, "tone.style") == "cercano"


def test_s2_tampered_plan_after_approval_is_refused(migrated_db, monkeypatch):
    run_id = f"p-{uuid4().hex[:10]}"
    with SessionLocal() as session:
        before = get_setting(session, "messages.farewell")
        a1 = issue_approval(_first())
        user, thread = _thread(session, plan=_first(), approval=a1, run_id=run_id)
        thread.current_plan = {**_first(), "arguments": {"key": "messages.farewell", "value": "TAMPERED"}}
        session.flush()
        assert approve_plan(session, thread, user, run_id, a1["token"]) is None
        assert get_setting(session, "messages.farewell") == before


def test_s2_approval_for_other_plan_is_refused(migrated_db, monkeypatch):
    from app.chat.assistant.approval import consume_approval
    from app.chat.assistant.nodes import guardrails

    with SessionLocal() as session:
        _c, _u, thread, _a1 = _park_on_second(session, monkeypatch, f"p-{uuid4().hex[:10]}")
        a2 = thread.assistant_state["approval"]
        assert consume_approval(a2, a2["token"]) is True
        other = {**_second(), "arguments": {"key": "tone.style", "value": "explicito"}}
        result = guardrails({"thread_id": thread.id, "plan": other, "approval": a2, "planner": {"valid": True}, "guardrails": {}})
        assert result["status"] == "approval_pending" and result["approval"]["token"] != a2["token"]


def test_s5_reject_second_approval_executes_nothing_further(migrated_db, monkeypatch):
    with SessionLocal() as session:
        c, user, thread, _a1 = _park_on_second(session, monkeypatch, f"p-{uuid4().hex[:10]}")
        a2 = thread.assistant_state["approval"]
        rejected = approve_plan(session, thread, user, thread.active_run_id, a2["token"], reject=True)
        session.commit()
        assert rejected is not None and rejected.status == "rejected"
        assert get_setting(session, "tone.style") == "cercano" and c.stream_calls == 0


def test_s6_parked_chain_survives_restart_and_second_approval(migrated_db, monkeypatch):
    run_id = f"p-{uuid4().hex[:10]}"
    with SessionLocal() as session:
        c, user, thread, _a1 = _park_on_second(session, monkeypatch, run_id)
        thread_id, a2_token = thread.id, thread.assistant_state["approval"]["token"]
    assert reap_orphaned_runs(SessionLocal, limit=50) == 0
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        user = session.get(User, thread.user_id)
        assert thread.assistant_state["approval"]["status"] == "pending"
        assert reap_stale_run(session, thread) is False
        msg = approve_plan(session, thread, user, run_id, a2_token)
        session.commit()
        assert msg is not None and msg.status == "processed"
        assert get_setting(session, "tone.style") == "formal"
        session.refresh(thread)
        assert thread.assistant_state["stage"] == "completed" and thread.assistant_state["tool_steps"] == 2
    assert c.stream_calls == 1


def test_s7_cap_bounds_chain_across_pause(migrated_db, monkeypatch):
    run_id = f"p-{uuid4().hex[:10]}"
    second = {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "tone.style", "value": "formal"},
        "summary": "tono", "requires_approval": True, "follow_up": True,
    }
    c = _client(monkeypatch, [json.dumps(second)])
    with SessionLocal() as session:
        a1 = issue_approval(_first())
        user, thread = _thread(session, plan=_first(), approval=a1, run_id=run_id)
        assert approve_plan(session, thread, user, run_id, a1["token"]).status == "approval_pending"
        session.commit()
        session.refresh(thread)
        a2 = thread.assistant_state["approval"]
        assert approve_plan(session, thread, user, run_id, a2["token"]).status == "processed"
        session.commit()
        session.refresh(thread)
        state = thread.assistant_state
        assert state["tool_steps"] == MAX_ASSISTANT_TOOL_STEPS and state["cap_reached"] is True
        assert len(c.planner_calls) == 1


def test_s7_cost_gate_stops_the_loop(monkeypatch):
    from app.chat.assistant import nodes as n

    monkeypatch.setattr(n, "_cost_snapshot", lambda *a, **k: {"mode": "blocked"})
    result = tool_loop_head({"thread_id": 7, "plan": {"kind": "tool", "tool": "settings.update", "follow_up": True}, "tool_steps": 1, "guardrails": {}})
    assert result["status"] == "completed" and result["guardrails"]["decision"] == "loop_cost_stopped"


def test_t1_advisory_resume_with_no_approval_parks_without_crash(migrated_db, monkeypatch):
    run_id = f"p-{uuid4().hex[:10]}"
    c = _client(monkeypatch, [])
    with SessionLocal() as session:
        before = get_setting(session, "messages.farewell")
        user, thread = _thread(session, plan=_first(), approval=None, run_id=run_id)
        thread.assistant_state = {
            "stage": "executing", "execution_status": "pending", "actor_role": "admin",
            "approval": None, "tool_results": [], "tool_steps": 0,
        }
        session.query(InternalChatMessage).filter_by(thread_id=thread.id).one().status = "processing"
        session.flush()
        assert resume_thread(session, thread, user) is True
        session.commit()
        assert get_setting(session, "messages.farewell") == before and c.stream_calls == 0
