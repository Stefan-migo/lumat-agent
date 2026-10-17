"""Independent verifier probes for T5 / S6: recovery is exactly-once and never bypasses approval.

Each assertion fails if the exactly-once claim, the atomic claim, or the approval
gate is false. Probes 4, 5 and 7 directly attempt to falsify the finding that a crash
never persists `execution_status=running`, by rolling back a real mid-execution
transaction and inspecting what survived, and by instrumenting commit/publish.
"""

import threading
import time
from types import SimpleNamespace
from uuid import uuid4

from app.chat.assistant import nodes as assistant_nodes
from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.recovery import claim_execution
from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import (
    approve_plan,
    reap_orphaned_runs,
    reap_stale_run,
    resume_thread,
)
from app.services.settings import MESSAGE_DEFAULTS, get_setting, set_setting
from app.services.users import hash_password

DEFAULT_FAREWELL = MESSAGE_DEFAULTS["farewell"]
_PLANNER_JSON = '{"kind": "respond", "summary": "hola", "requires_approval": false}'


class _Completions:
    def __init__(self, responder="Recuperado."):
        self.responder = responder
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=self.responder))])]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=_PLANNER_JSON))])


def _mount_client(monkeypatch, responder="Recuperado."):
    completions = _Completions(responder)
    monkeypatch.setattr(
        assistant_nodes, "_assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=completions)),
    )
    return completions


def _count_executions(monkeypatch):
    executed = []
    real = assistant_nodes.execute_tool

    def counting(session, tool, *args, **kwargs):
        executed.append(tool)
        return real(session, tool, *args, **kwargs)

    monkeypatch.setattr(assistant_nodes, "execute_tool", counting)
    return executed


def _seed(session, *, plan, approval, stage, execution_status, message_status, live,
          tool_results=None, tool_steps=0):
    suffix = uuid4().hex[:10]
    user = User(username=f"t5-recovery-{suffix}", password_hash=hash_password("pass"), role="admin")
    session.add(user)
    session.flush()
    run_id = f"t5-recovery-{suffix}"
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
            "live": {"run_id": run_id, "stage": stage, **live},
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


def _write_plan(value):
    return {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": value},
        "summary": "step", "requires_approval": True, "follow_up": False,
    }


def test_exactly_once_across_repeated_reclaims_and_direct_claims(migrated_db, monkeypatch):
    """S6: no matter how many callers try, an interrupted chain's write runs once."""
    _mount_client(monkeypatch)
    executed = _count_executions(monkeypatch)

    with SessionLocal() as session:
        set_setting(session, "messages.farewell", DEFAULT_FAREWELL)
        session.commit()
        value = f"once-{uuid4().hex[:6]}"
        plan = _write_plan(value)
        approval = issue_approval(plan)
        assert consume_approval(approval, approval["token"]) is True
        step_one = {"tool": "customers.search", "status": "completed", "result": {"count": 1}}
        user, thread = _seed(
            session, plan=plan, approval=approval, stage="executing",
            execution_status="pending", message_status="processing",
            live={"status": "approval_pending"}, tool_results=[step_one], tool_steps=1,
        )

        outcomes = [resume_thread(session, thread, user) for _ in range(3)]
        session.commit()
        session.refresh(thread)
        # Every later caller loses the claim; the direct API agrees.
        assert outcomes == [True, False, False], outcomes
        assert claim_execution(session, thread) is False
        session.commit()

        assert executed.count("settings.update") == 1
        assert get_setting(session, "messages.farewell") == value
        tools = [item["tool"] for item in thread.assistant_state["tool_results"]]
        assert tools[0] == "customers.search"
        assert tools[-1] == "settings.update"
        assert thread.assistant_state["tool_steps"] == 2
        assert thread.assistant_state["stage"] == "completed"
        assert thread.assistant_state["execution_status"] == "completed"


def test_concurrent_claims_only_one_winner(migrated_db):
    """S6 atomic claim: two racing claim_execution calls -> exactly one True."""
    with SessionLocal() as session:
        plan = _write_plan("race")
        approval = issue_approval(plan)
        assert consume_approval(approval, approval["token"]) is True
        user, thread = _seed(
            session, plan=plan, approval=approval, stage="executing",
            execution_status="pending", message_status="processing",
            live={"status": "approval_pending"},
        )
        thread_id = thread.id

    barrier = threading.Barrier(2)
    results = {}

    def worker(name):
        with SessionLocal() as s:
            row = s.get(InternalChatThread, thread_id)
            barrier.wait()
            results[name] = claim_execution(s, row)
            if results[name]:
                time.sleep(0.4)  # hold the row lock so the loser must re-evaluate
            s.commit()

    a = threading.Thread(target=worker, args=("a",))
    b = threading.Thread(target=worker, args=("b",))
    a.start(); b.start()
    a.join(15); b.join(15)
    assert not a.is_alive() and not b.is_alive(), "claim race deadlocked"
    assert sorted(results.values()) == [False, True], results

    with SessionLocal() as s2:
        raw = s2.get(InternalChatThread, thread_id).assistant_state["execution_status"]
        assert raw == "running"


def test_pending_approval_chain_is_not_resumable_even_with_consumed_approval(migrated_db, monkeypatch):
    """S6 + S2: the gate is the stage, so a parked chain is not resumed by recovery --
    not even when its stored approval already reads consumed."""
    _mount_client(monkeypatch)
    executed = _count_executions(monkeypatch)

    with SessionLocal() as session:
        before = get_setting(session, "messages.farewell")
        plan = _write_plan("nunca")
        approval = issue_approval(plan)
        assert consume_approval(approval, approval["token"]) is True
        user, thread = _seed(
            session, plan=plan, approval=approval, stage="approval_pending",
            execution_status="pending", message_status="approval_pending",
            live={"status": "approval_pending"},
        )
        assert resume_thread(session, thread, user) is False
        session.commit()
        assert executed == []
        assert get_setting(session, "messages.farewell") == before
        session.refresh(thread)
        assert thread.assistant_state["stage"] == "approval_pending"


def test_crash_mid_execution_rolls_the_claim_back_to_pending_and_resume_reclaims_once(
    migrated_db, monkeypatch
):
    """Falsification attempt: a crash after the write's side effect but before the
    transaction commits must NOT persist execution_status=running. The claim rolls
    back to pending, and a later resume reclaims it and commits the write once."""
    _mount_client(monkeypatch)
    real = assistant_nodes.execute_tool
    state = {"crash": True}
    executed = []

    def crashing(session, tool, *args, **kwargs):
        result = real(session, tool, *args, **kwargs)
        executed.append(tool)
        if state["crash"]:
            state["crash"] = False
            raise RuntimeError("simulated crash mid-execution")
        return result

    monkeypatch.setattr(assistant_nodes, "execute_tool", crashing)

    with SessionLocal() as session:
        set_setting(session, "messages.farewell", DEFAULT_FAREWELL)
        session.commit()
        value = f"crash-{uuid4().hex[:6]}"
        plan = _write_plan(value)
        approval = issue_approval(plan)
        assert consume_approval(approval, approval["token"]) is True
        user, thread = _seed(
            session, plan=plan, approval=approval, stage="executing",
            execution_status="pending", message_status="processing",
            live={"status": "approval_pending"},
        )
        thread_id = thread.id

    # Crash: resume_thread claims, the write runs, then the process dies.
    with SessionLocal() as dying:
        t = dying.get(InternalChatThread, thread_id)
        u = dying.get(User, t.user_id)
        try:
            resume_thread(dying, t, u)
        except RuntimeError:
            pass
        dying.rollback()

    # What survived the crash: the claim is NOT running, the effect is NOT applied.
    with SessionLocal() as s2:
        t = s2.get(InternalChatThread, thread_id)
        assert t.assistant_state["execution_status"] == "pending", t.assistant_state["execution_status"]
        assert t.assistant_state["stage"] == "executing"
        assert get_setting(s2, "messages.farewell") == DEFAULT_FAREWELL
        # Recovery reclaims and commits exactly once.
        executed.clear()
        assert resume_thread(s2, t, s2.get(User, t.user_id)) is True
        s2.commit()
        assert get_setting(s2, "messages.farewell") == value
        assert executed.count("settings.update") == 1, executed
        s2.refresh(t)
        assert t.assistant_state["execution_status"] == "completed"


def test_approve_plan_crash_rolls_back_consumption_and_claim(migrated_db, monkeypatch):
    """Falsification attempt on the real approval path: a crash inside the approved
    write transaction leaves the approval pending and execution_status pending --
    never running, never consumed. A retry then commits the write exactly once."""
    _mount_client(monkeypatch)
    real = assistant_nodes.execute_tool
    state = {"crash": True}

    def crashing(session, tool, *args, **kwargs):
        result = real(session, tool, *args, **kwargs)
        if state["crash"]:
            state["crash"] = False
            raise RuntimeError("simulated crash inside approval transaction")
        return result

    monkeypatch.setattr(assistant_nodes, "execute_tool", crashing)

    with SessionLocal() as session:
        set_setting(session, "messages.farewell", DEFAULT_FAREWELL)
        session.commit()
        value = f"approve-crash-{uuid4().hex[:6]}"
        plan = _write_plan(value)
        approval = issue_approval(plan)
        user, thread = _seed(
            session, plan=plan, approval=approval, stage="approval_pending",
            execution_status="pending", message_status="approval_pending",
            live={"status": "approval_pending"},
        )
        thread_id, token = thread.id, approval["token"]

    with SessionLocal() as dying:
        t = dying.get(InternalChatThread, thread_id)
        u = dying.get(User, t.user_id)
        try:
            approve_plan(dying, t, u, t.active_run_id, token)
        except RuntimeError:
            pass
        dying.rollback()

    with SessionLocal() as s2:
        t = s2.get(InternalChatThread, thread_id)
        st = t.assistant_state
        # The whole transaction rolled back: nothing consumed, claimed, or written.
        assert st["approval"]["status"] == "pending", st["approval"]["status"]
        assert st["execution_status"] == "pending", st["execution_status"]
        assert st["stage"] == "approval_pending"
        assert get_setting(s2, "messages.farewell") == DEFAULT_FAREWELL
        # Retry with the same token: the write commits exactly once.
        executed = _count_executions(monkeypatch)
        u = s2.get(User, t.user_id)
        assert approve_plan(s2, t, u, t.active_run_id, token) is not None
        s2.commit()
        assert get_setting(s2, "messages.farewell") == value
        assert executed.count("settings.update") == 1, executed


def test_boot_reaper_leaves_a_resumable_execution_for_recovery(migrated_db):
    """S6 interaction: the boot reaper must not fail a run the durable resume path
    can still reclaim, so recovery -- not fail-closed -- owns that thread."""
    with SessionLocal() as session:
        plan = _write_plan("resumable")
        approval = issue_approval(plan)
        assert consume_approval(approval, approval["token"]) is True
        user, thread = _seed(
            session, plan=plan, approval=approval, stage="executing",
            execution_status="pending", message_status="processing",
            live={"status": "running", "updated_at": "2000-01-01T00:00:00+00:00"},
        )
        thread_id = thread.id

    assert reap_orphaned_runs(SessionLocal) == 0
    with SessionLocal() as s2:
        t = s2.get(InternalChatThread, thread_id)
        assert t.assistant_state["stage"] == "executing"
        assert t.assistant_state["execution_status"] == "pending"


def test_resume_path_never_commits_or_publishes_mid_execution(migrated_db, monkeypatch):
    """Falsification attempt on the mechanism: `resume_thread` must not commit or call
    `publish_live` between the claim and the final persist, or a crash would leave
    execution_status=running committed. Instrument both and assert neither fires."""
    _mount_client(monkeypatch)
    import app.services.agent_chat as ac
    from sqlalchemy.orm import Session as SASession

    published = []
    monkeypatch.setattr(ac, "publish_live", lambda *a, **k: published.append((a, k)))
    commits = []
    real_commit = SASession.commit

    def counting_commit(self):
        commits.append(1)
        return real_commit(self)

    monkeypatch.setattr(SASession, "commit", counting_commit)

    with SessionLocal() as session:
        set_setting(session, "messages.farewell", DEFAULT_FAREWELL)
        session.commit()
        plan = _write_plan(f"nocommit-{uuid4().hex[:6]}")
        approval = issue_approval(plan)
        assert consume_approval(approval, approval["token"]) is True
        user, thread = _seed(
            session, plan=plan, approval=approval, stage="executing",
            execution_status="pending", message_status="processing",
            live={"status": "approval_pending"},
        )
        before = len(commits)
        assert resume_thread(session, thread, user) is True
        # No commit and no live publish happened inside the recovery call.
        assert len(commits) == before, commits
        assert published == [], published
        session.commit()
