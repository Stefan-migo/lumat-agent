"""T5 / S6: an interrupted chain recovers exactly once and never re-runs a consumed write.

The exactly-once guarantee rests on two mechanisms that this file pins directly:
  * `claim_execution` flips `execution_status` from `pending` to `running` in one
    `UPDATE ... WHERE ... = 'pending'`, so only the first caller wins;
  * `resume_thread` refuses any thread whose `stage` is not `executing`, so recovery can
    never bypass a write that still awaits the operator's approval.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.chat.assistant import nodes as assistant_nodes
from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.recovery import claim_execution
from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import reap_stale_run, resume_thread
from app.services.settings import MESSAGE_DEFAULTS, get_setting, set_setting
from app.services.users import hash_password

DEFAULT_FAREWELL = MESSAGE_DEFAULTS["farewell"]
_PLANNER_JSON = '{"kind": "respond", "summary": "hola", "requires_approval": false}'


class _Completions:
    def __init__(self, responder="Recuperado."):
        self.calls = []
        self.responder = responder

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=self.responder))])]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=_PLANNER_JSON))])


@pytest.fixture
def fake_assistant_client(monkeypatch):
    def mount(responder="Recuperado."):
        completions = _Completions(responder)
        monkeypatch.setattr(
            assistant_nodes, "_assistant_client",
            lambda: SimpleNamespace(chat=SimpleNamespace(completions=completions)),
        )
        return completions

    return mount


def _seed(session, *, plan, approval, stage, execution_status, message_status, live_status,
          tool_results=None, tool_steps=0):
    suffix = uuid4().hex[:10]
    user = User(username=f"chain-recovery-{suffix}", password_hash=hash_password("pass"), role="admin")
    session.add(user)
    session.flush()
    run_id = f"chain-recovery-{suffix}"
    thread = InternalChatThread(
        user_id=user.id,
        active_run_id=run_id,
        current_plan=plan,
        assistant_state={
            "stage": stage,
            "execution_status": execution_status,
            "approval": approval,
            "actor_role": "admin",
            "tool_results": tool_results or [],
            "tool_steps": tool_steps,
            "live": {"run_id": run_id, "stage": stage, "status": live_status},
        },
    )
    session.add(thread)
    session.flush()
    session.add(InternalChatMessage(
        thread_id=thread.id, author="admin", content="hacelo", status=message_status,
        assistant_metadata={"run_id": run_id, "approval": approval},
    ))
    session.commit()
    return user, thread


def _count_executions(monkeypatch):
    """Record every tool `execute_tool` call so a re-run is observable."""
    executed = []
    real_execute_tool = assistant_nodes.execute_tool

    def counting(session, tool, *args, **kwargs):
        executed.append(tool)
        return real_execute_tool(session, tool, *args, **kwargs)

    monkeypatch.setattr(assistant_nodes, "execute_tool", counting)
    return executed


def _write_plan(value):
    return {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": value},
        "summary": "step 2", "requires_approval": True, "follow_up": False,
    }


def test_resume_reclaims_an_interrupted_chain_step_exactly_once(migrated_db, monkeypatch, fake_assistant_client):
    """S6: a chain interrupted mid-execution (step 1 ran, step 2 claimed but unfinished)
    re-enters at the pending step, runs it exactly once, and keeps step 1's evidence."""
    fake_assistant_client()
    executed = _count_executions(monkeypatch)

    with SessionLocal() as session:
        set_setting(session, "messages.farewell", DEFAULT_FAREWELL)
        session.commit()
        value = f"recovered-{uuid4().hex[:6]}"
        plan = _write_plan(value)
        approval = issue_approval(plan)
        assert consume_approval(approval, approval["token"]) is True
        step_one = {"tool": "customers.search", "status": "completed", "result": {"count": 1}}
        user, thread = _seed(
            session, plan=plan, approval=approval,
            stage="executing", execution_status="pending", message_status="processing",
            live_status="approval_pending", tool_results=[step_one], tool_steps=1,
        )

        assert resume_thread(session, thread, user) is True
        session.commit()
        assert resume_thread(session, thread, user) is False  # the claim is spent
        session.commit()

        assert get_setting(session, "messages.farewell") == value
        assert executed.count("settings.update") == 1
        session.refresh(thread)
        tools = [item["tool"] for item in thread.assistant_state["tool_results"]]
        assert tools[0] == "customers.search"  # step 1's evidence survived the recovery
        assert tools[-1] == "settings.update"
        assert thread.assistant_state["tool_steps"] == 2


def test_recovery_never_resumes_a_chain_that_still_awaits_approval(migrated_db, monkeypatch, fake_assistant_client):
    """S6+S2: a chain parked on a pending approval is not resumable. Recovery must not
    bypass the human gate -- only the operator's approval continues the chain."""
    fake_assistant_client()
    executed = _count_executions(monkeypatch)

    with SessionLocal() as session:
        before = get_setting(session, "messages.farewell")
        approval = issue_approval(_write_plan("no-debe-correr"))  # pending, NOT consumed
        user, thread = _seed(
            session, plan=_write_plan("no-debe-correr"), approval=approval,
            stage="approval_pending", execution_status="pending", message_status="approval_pending",
            live_status="approval_pending",
        )

        assert resume_thread(session, thread, user) is False
        session.commit()

        assert executed == []
        assert get_setting(session, "messages.farewell") == before
        session.refresh(thread)
        assert thread.assistant_state["stage"] == "approval_pending"
        assert thread.assistant_state["approval"]["status"] == "pending"


def test_a_claimed_execution_is_never_reclaimed_and_is_failed_closed(migrated_db, monkeypatch, fake_assistant_client):
    """S6 fail-closed: an execution already claimed (execution_status='running') is never
    claimed again. When its live marker says a runner owned it, the reaper settles the run
    failed instead of re-running the write."""
    fake_assistant_client()
    executed = _count_executions(monkeypatch)

    with SessionLocal() as session:
        before = get_setting(session, "messages.farewell")
        plan = _write_plan("no-debe-correr")
        approval = issue_approval(plan)
        assert consume_approval(approval, approval["token"]) is True
        user, thread = _seed(
            session, plan=plan, approval=approval,
            stage="executing", execution_status="running", message_status="processing",
            live_status="running",
        )

        assert resume_thread(session, thread, user) is False        # never a second claim
        assert claim_execution(session, thread) is False            # the atomic gate refuses
        session.commit()
        assert executed == []

        assert reap_stale_run(session, thread) is True              # no runner owns it -> fail closed
        session.commit()
        session.refresh(thread)
        assert thread.assistant_state["stage"] == "failed"
        assert get_setting(session, "messages.farewell") == before  # the write never re-ran
