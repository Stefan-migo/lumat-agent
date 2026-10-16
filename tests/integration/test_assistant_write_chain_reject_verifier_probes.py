"""Independent verifier probes for T4 / S5: rejecting an approval aborts the chain.

Each assertion fails if the terminal-settlement claim for a rejected write is false.
"""

import json
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import func, select, text

from app.chat.assistant.approval import issue_approval, validate_execution
from app.db import SessionLocal
from app.models import AuditLog, InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import approve_plan, reap_orphaned_runs, reap_stale_run, resume_thread
from app.services.settings import get_setting
from app.services.users import hash_password


class _Completions:
    def __init__(self, plans, text="Listo."):
        self.plans = list(plans)
        self.text = text
        self.planner_calls = []
        self.stream_calls = 0

    def create(self, **kwargs):
        if kwargs.get("stream"):
            self.stream_calls += 1
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=self.text))])]
        self.planner_calls.append(kwargs)
        plan = self.plans[len(self.planner_calls) - 1]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=plan))])


def _pending_write_thread(session, *, plan, approval, run_id):
    user = User(username=f"t4-{uuid4().hex[:10]}", password_hash=hash_password("pass"), role="admin")
    session.add(user)
    session.flush()
    thread = InternalChatThread(
        user_id=user.id,
        active_run_id=run_id,
        current_plan=plan,
        assistant_state={
            "stage": "approval_pending",
            "execution_status": "pending",
            "approval": approval,
            "actor_role": "admin",
            "live": {"run_id": run_id, "status": "approval_pending", "stage": "approval_pending"},
        },
    )
    session.add(thread)
    session.flush()
    session.add(InternalChatMessage(
        thread_id=thread.id, author="admin", content="hacelo", status="approval_pending",
        assistant_metadata={"run_id": run_id, "approval": approval},
    ))
    session.commit()
    return user, thread


def _audit_actions(session, thread_id):
    return {
        entry.action for entry in session.scalars(
            select(AuditLog).where(AuditLog.entity_id == str(thread_id))
        )
    }


def _agent_replies(session, thread_id, run_id):
    return session.scalar(
        select(func.count()).select_from(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread_id,
            InternalChatMessage.author == "agent",
            InternalChatMessage.assistant_metadata["run_id"].as_string() == run_id,
        )
    )


def test_reject_step_two_chain_is_terminal_and_survives_fresh_read(migrated_db, monkeypatch):
    """S5: rejecting the second write of a chain is terminal, dispatch stops, audit persists."""
    from app.chat.assistant import nodes as assistant_nodes

    run_id = f"t4-chain-{uuid4().hex[:10]}"
    first = {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": "Nos vemos."},
        "summary": "s1", "requires_approval": True, "follow_up": True,
    }
    second = {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "tone.style", "value": "formal"},
        "summary": "s2", "requires_approval": True, "follow_up": False,
    }
    client = _Completions([json.dumps(second)])
    monkeypatch.setattr(assistant_nodes, "_assistant_client",
                        lambda: SimpleNamespace(chat=SimpleNamespace(completions=client)))

    with SessionLocal() as session:
        approval = issue_approval(first)
        user, thread = _pending_write_thread(session, plan=first, approval=approval, run_id=run_id)
        thread_id = thread.id
        approve_plan(session, thread, user, run_id, approval["token"])
        session.commit()
        session.refresh(thread)
        assert thread.assistant_state["stage"] == "approval_pending"  # sanity: chain paused at step 2
        fresh = thread.assistant_state["approval"]

        rejected = approve_plan(session, thread, user, run_id, fresh["token"], reject=True)
        session.commit()
        assert rejected is not None and rejected.status == "rejected"
        # The token can never be reused.
        assert approve_plan(session, thread, user, run_id, fresh["token"], reject=True) is None
        assert approve_plan(session, thread, user, run_id, fresh["token"]) is None
        assert client.stream_calls == 0

    # Fresh session: none of the above may be an in-memory artefact.
    with SessionLocal() as s2:
        t = s2.get(InternalChatThread, thread_id)
        st = t.assistant_state
        assert st["stage"] == "rejected"
        assert st["execution_status"] == "rejected"
        assert st["live"]["status"] == "rejected"
        assert st["approval"]["status"] == "rejected"
        assert validate_execution(t.current_plan, st["approval"]) is False
        assert get_setting(s2, "tone.style") == "cercano"            # rejected step never ran
        assert get_setting(s2, "messages.farewell") == "Nos vemos."  # step 1 did run
        assert _agent_replies(s2, thread_id, run_id) == 0
        assert any(e.get("type") == "status" and e.get("status") == "rejected" for e in st["events"])
        assert "internal_chat.approval_rejected" in _audit_actions(s2, thread_id)
        raw = s2.execute(text(
            "SELECT assistant_state #>> '{approval,status}' FROM internal_chat_threads WHERE id = :i"
        ), {"i": thread_id}).scalar_one()
        assert raw == "rejected"  # persisted jsonb, not just the ORM object
        assert reap_stale_run(s2, t) is False
        assert resume_thread(s2, t, s2.get(User, t.user_id)) is False

    # No pending run: the boot reaper must not touch it either.
    assert reap_orphaned_runs(SessionLocal) == 0
    with SessionLocal() as s3:
        t = s3.get(InternalChatThread, thread_id)
        assert t.assistant_state["live"]["status"] == "rejected"
        assert t.assistant_state["stage"] == "rejected"


def test_reject_single_write_is_terminal_and_audited(migrated_db):
    """S5: rejecting the only write of a turn settles it terminal with an audit record."""
    run_id = f"t4-single-{uuid4().hex[:10]}"
    plan = {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": "Adios."},
        "summary": "s", "requires_approval": True, "follow_up": False,
    }
    with SessionLocal() as session:
        before = get_setting(session, "messages.farewell")
        approval = issue_approval(plan)
        user, thread = _pending_write_thread(session, plan=plan, approval=approval, run_id=run_id)
        thread_id = thread.id
        rejected = approve_plan(session, thread, user, run_id, approval["token"], reject=True)
        session.commit()
        assert rejected is not None and rejected.status == "rejected"
        assert rejected.completed_at is not None

    with SessionLocal() as s2:
        t = s2.get(InternalChatThread, thread_id)
        st = t.assistant_state
        assert (st["stage"], st["execution_status"], st["live"]["status"]) == ("rejected", "rejected", "rejected")
        assert st["approval"]["status"] == "rejected"
        assert validate_execution(t.current_plan, st["approval"]) is False
        assert get_setting(s2, "messages.farewell") == before
        assert _agent_replies(s2, thread_id, run_id) == 0
        assert "internal_chat.approval_rejected" in _audit_actions(s2, thread_id)
        assert reap_stale_run(s2, t) is False
        assert resume_thread(s2, t, s2.get(User, t.user_id)) is False


def test_second_reject_over_http_is_409(migrated_db, client):
    """No dangling approval: a second reject with the same token is refused with HTTP 409."""
    run_id = f"t4-http-{uuid4().hex[:10]}"
    plan = {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": "Https"},
        "summary": "s", "requires_approval": True, "follow_up": False,
    }
    with SessionLocal() as session:
        approval = issue_approval(plan)
        user, thread = _pending_write_thread(session, plan=plan, approval=approval, run_id=run_id)
        thread_id, username, token = thread.id, user.username, approval["token"]

    assert client.post("/panel/api/login", json={"username": username, "password": "pass"}).status_code == 200
    url = f"/panel/api/chat/threads/{thread_id}/approval"
    first = client.post(url, json={"run_id": run_id, "token": token, "reject": True})
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "rejected"
    second = client.post(url, json={"run_id": run_id, "token": token, "reject": True})
    assert second.status_code == 409, second.text
    assert second.json()["detail"] == "approval is invalid, expired, or already consumed"


def test_control_approving_the_same_pending_write_executes(migrated_db, monkeypatch):
    """Positive control: the SAME harness approves cleanly, so the reject probes are not vacuous."""
    from app.chat.assistant import nodes as assistant_nodes

    class _C:
        def create(self, **kwargs):
            if kwargs.get("stream"):
                return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Listo."))])]
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))])

    monkeypatch.setattr(assistant_nodes, "_assistant_client",
                        lambda: SimpleNamespace(chat=SimpleNamespace(completions=_C())))

    run_id = f"t4-control-{uuid4().hex[:10]}"
    plan = {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": "Control."},
        "summary": "s", "requires_approval": True, "follow_up": False,
    }
    with SessionLocal() as session:
        approval = issue_approval(plan)
        user, thread = _pending_write_thread(session, plan=plan, approval=approval, run_id=run_id)
        message = approve_plan(session, thread, user, run_id, approval["token"])
        session.commit()
        assert message is not None
        assert get_setting(session, "messages.farewell") == "Control."


def test_second_approve_after_reject_is_refused(migrated_db):
    """A rejected approval cannot be flipped to approved afterwards."""
    run_id = f"t4-flip-{uuid4().hex[:10]}"
    plan = {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": "Flip."},
        "summary": "s", "requires_approval": True, "follow_up": False,
    }
    with SessionLocal() as session:
        before = get_setting(session, "messages.farewell")
        approval = issue_approval(plan)
        user, thread = _pending_write_thread(session, plan=plan, approval=approval, run_id=run_id)
        assert approve_plan(session, thread, user, run_id, approval["token"], reject=True) is not None
        session.commit()
        assert approve_plan(session, thread, user, run_id, approval["token"]) is None
        session.commit()
        assert get_setting(session, "messages.farewell") == before
