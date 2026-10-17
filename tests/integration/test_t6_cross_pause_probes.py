"""Independent T6/S7 probes: the raised budget holds across the approval pause."""

import json
from types import SimpleNamespace
from uuid import uuid4

from app.chat.assistant.approval import issue_approval
from app.chat.assistant.nodes import MAX_ASSISTANT_TOOL_STEPS
from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import approve_plan
from app.services.users import hash_password


class _Completions:
    def __init__(self, plans):
        self.plans, self.planner_calls, self.stream_calls = list(plans), [], 0

    def create(self, **kwargs):
        if kwargs.get("stream"):
            self.stream_calls += 1
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Listo."))])]
        self.planner_calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.plans.pop(0)))])


def _client(monkeypatch, plans):
    from app.chat.assistant import nodes as n

    c = _Completions(plans)
    monkeypatch.setattr(n, "_assistant_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=c)))
    return c


def _write_step():
    return {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": "Nos vemos."},
        "summary": "despedida", "requires_approval": True, "follow_up": True,
    }


def _thread(session, *, plan, approval, run_id):
    user = User(username=f"t6-{uuid4().hex[:10]}", password_hash=hash_password("pass"), role="admin")
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


def test_s7_across_pause_cuts_at_budget_with_surplus_plans(migrated_db, monkeypatch):
    """Plans keep requesting follow-ups; the cumulative cap cuts the paused chain at 4,
    never executes a 5th, and never asks the planner for a 5th plan."""
    run_id = f"t6-{uuid4().hex[:10]}"
    step = _write_step()
    c = _client(monkeypatch, [json.dumps(step) for _ in range(MAX_ASSISTANT_TOOL_STEPS + 2)])
    with SessionLocal() as session:
        approval = issue_approval(step)
        user, thread = _thread(session, plan=step, approval=approval, run_id=run_id)
        message = None
        for executed in range(1, MAX_ASSISTANT_TOOL_STEPS + 1):
            message = approve_plan(session, thread, user, run_id, approval["token"])
            assert message is not None
            session.commit()
            session.refresh(thread)
            assert thread.assistant_state["tool_steps"] == executed
            approval = thread.assistant_state["approval"]
            if executed < MAX_ASSISTANT_TOOL_STEPS:
                assert message.status == "approval_pending"
        assert message.status == "processed"
        assert thread.assistant_state["cap_reached"] is True

    # A continuation is planned only for steps 2..4; the 5th/6th plans are never consumed.
    assert len(c.planner_calls) == MAX_ASSISTANT_TOOL_STEPS - 1
    assert len(c.plans) == (MAX_ASSISTANT_TOOL_STEPS + 2) - (MAX_ASSISTANT_TOOL_STEPS - 1)


def test_s7_three_step_paused_chain_is_not_cut_before_the_budget(migrated_db, monkeypatch):
    """A chain that keeps requesting follow-ups pauses per step and is only cut at the
    budget: after the *third* write it still awaits approval, not terminated."""
    run_id = f"t6-{uuid4().hex[:10]}"
    step = _write_step()
    _client(monkeypatch, [json.dumps(step) for _ in range(3)])
    with SessionLocal() as session:
        approval = issue_approval(step)
        user, thread = _thread(session, plan=step, approval=approval, run_id=run_id)
        for _ in (1, 2):
            message = approve_plan(session, thread, user, run_id, approval["token"])
            session.commit()
            session.refresh(thread)
            assert message.status == "approval_pending"
            approval = thread.assistant_state["approval"]

        message = approve_plan(session, thread, user, run_id, approval["token"])
        session.commit()
        session.refresh(thread)
        # The third step ran and the chain continues (3 < budget), so it parks again.
        assert thread.assistant_state["tool_steps"] == 3
        assert message.status == "approval_pending"
        assert thread.assistant_state["cap_reached"] is False
