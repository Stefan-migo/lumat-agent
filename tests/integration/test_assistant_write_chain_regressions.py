"""T3: S4 regression pins — the read-only loop and the single-write path are unchanged.

T2 reopened the read-only-only loop on purpose, so these pin the two behaviours S4
protects and that the chain must not have changed: a single class-A write still asks for
exactly one approval and ends the turn, and a read-only turn still never asks for one.
"""

from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select

from app.chat.assistant.approval import issue_approval
from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import approve_plan
from app.services.settings import get_setting
from app.services.users import hash_password

from tests.integration._capture_aware import planner_only


class _Completions:
    """The responder only: a single write must not trigger a re-plan."""

    def __init__(self, text="Listo."):
        self.text, self.planner_calls, self.stream_calls = text, [], 0

    def create(self, **kwargs):
        if kwargs.get("stream"):
            self.stream_calls += 1
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=self.text))])]
        self.planner_calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))])


def _pending_write_thread(session, *, plan, approval, run_id):
    user = User(
        username=f"reg-{uuid4().hex[:10]}", password_hash=hash_password("pass"), role="admin"
    )
    session.add(user)
    session.flush()
    thread = InternalChatThread(
        user_id=user.id, active_run_id=run_id, current_plan=plan,
        assistant_state={"stage": "approval_pending", "approval": approval, "actor_role": "admin"},
    )
    session.add(thread)
    session.flush()
    session.add(InternalChatMessage(
        thread_id=thread.id, author="admin", content="cambiá la despedida",
        status="approval_pending", assistant_metadata={"run_id": run_id, "approval": approval},
    ))
    session.commit()
    return user, thread


def test_single_write_turn_issues_one_approval_and_never_chains(migrated_db, monkeypatch):
    """S4: the one-write-one-approval turn is unchanged by the chain. The approved write
    runs once, the turn completes, and no second approval is ever issued."""
    from app.chat.assistant import approval as approval_module
    from app.chat.assistant import nodes as assistant_nodes

    run_id = f"single-{uuid4().hex[:10]}"
    plan = {
        "kind": "tool", "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": "Nos vemos."},
        "summary": "Cambiar la despedida",
        "requires_approval": True, "follow_up": False,
    }
    client = _Completions()
    monkeypatch.setattr(
        assistant_nodes, "_assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=client)),
    )
    issued = []
    original = approval_module.issue_approval
    monkeypatch.setattr(approval_module, "issue_approval", lambda p: issued.append(p) or original(p))

    with SessionLocal() as session:
        approval = issue_approval(plan)
        user, thread = _pending_write_thread(session, plan=plan, approval=approval, run_id=run_id)

        message = approve_plan(session, thread, user, run_id, approval["token"])
        session.commit()

        assert message is not None
        assert message.status == "processed"
        assert get_setting(session, "messages.farewell") == "Nos vemos."
        assert client.stream_calls == 1
        assert planner_only(client.planner_calls) == []  # no re-plan: the turn ended at the write
        assert issued == []  # no fresh approval was requested
        session.refresh(thread)
        assert thread.assistant_state["stage"] == "completed"
        assert thread.assistant_state["tool_steps"] == 1
        assert thread.assistant_state["approval"]["status"] == "consumed"
        agent = session.scalar(select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread.id, InternalChatMessage.author == "agent",
        ))
        assert agent is not None and agent.content == "Listo."
