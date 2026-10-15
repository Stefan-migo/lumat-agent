"""T2: an approved write chain continues inside one turn, pausing per class-A write."""

import json
from types import SimpleNamespace
from uuid import uuid4

from app.chat.assistant.approval import issue_approval
from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import approve_plan
from app.services.settings import get_setting
from app.services.users import hash_password


class _Completions:
    """Planner then responder, in call order: the chain re-plans once and narrates once."""

    def __init__(self, plans, text="Listo, hice los dos cambios."):
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
    user = User(
        username=f"chain-{uuid4().hex[:10]}", password_hash=hash_password("pass"), role="admin"
    )
    session.add(user)
    session.flush()
    thread = InternalChatThread(
        user_id=user.id,
        active_run_id=run_id,
        current_plan=plan,
        assistant_state={"stage": "approval_pending", "approval": approval, "actor_role": "admin"},
    )
    session.add(thread)
    session.flush()
    session.add(InternalChatMessage(
        thread_id=thread.id, author="admin", content="hacé los dos cambios",
        status="approval_pending", assistant_metadata={"run_id": run_id, "approval": approval},
    ))
    session.commit()
    return user, thread


def _planner_prompt(client, index=0) -> str:
    content = client.planner_calls[index]["messages"][-1]["content"]
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content


def test_chain_pauses_the_second_write_with_its_own_approval(migrated_db, monkeypatch):
    """S1+S2: after an approved write the chain re-plans inside the same turn; the next
    class-A write pauses with a fresh approval, and the chain keeps step 1's evidence."""
    from app.chat.assistant import nodes as assistant_nodes

    run_id = f"chain-{uuid4().hex[:10]}"
    first = {
        "kind": "tool",
        "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": "Nos vemos."},
        "summary": "Cambiar la despedida",
        "requires_approval": True,
        "follow_up": True,
    }
    second = {
        "kind": "tool",
        "tool": "settings.update",
        "arguments": {"key": "tone.style", "value": "formal"},
        "summary": "Cambiar el tono",
        "requires_approval": True,
        "follow_up": False,
    }
    client = _Completions([json.dumps(second)])
    monkeypatch.setattr(assistant_nodes, "_assistant_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=client)))

    with SessionLocal() as session:
        approval = issue_approval(first)
        user, thread = _pending_write_thread(session, plan=first, approval=approval, run_id=run_id)

        message = approve_plan(session, thread, user, run_id, approval["token"])
        session.commit()

        # Step 1 ran; step 2 has not, and it is waiting for its own approval.
        assert get_setting(session, "messages.farewell") == "Nos vemos."
        assert get_setting(session, "tone.style") == "cercano"
        assert message is not None
        assert message.status == "approval_pending"
        assert client.stream_calls == 0

        session.refresh(thread)
        state = thread.assistant_state
        assert state["stage"] == "approval_pending"
        assert state["execution_status"] == "pending"
        assert thread.current_plan["arguments"] == second["arguments"]
        assert state["tool_steps"] == 1
        assert [item["tool"] for item in state["tool_results"]] == ["settings.update"]
        fresh = state["approval"]
        assert fresh["status"] == "pending"
        assert fresh["token"] != approval["token"]

        # The continuation step planned from step 1's evidence, not from nothing.
        assert "Nos vemos." in _planner_prompt(client)

        second_message = approve_plan(session, thread, user, run_id, fresh["token"])
        session.commit()

        assert get_setting(session, "tone.style") == "formal"
        assert second_message is not None
        assert second_message.status == "processed"
        assert client.stream_calls == 1
        session.refresh(thread)
        assert thread.assistant_state["stage"] == "completed"
        assert thread.assistant_state["tool_steps"] == 2


def test_chain_rejecting_the_second_write_leaves_step_two_unexecuted(migrated_db, monkeypatch):
    """S5: rejecting the approval the chain paused on stops it without running step 2."""
    from app.chat.assistant import nodes as assistant_nodes

    run_id = f"chain-reject-{uuid4().hex[:10]}"
    first = {
        "kind": "tool",
        "tool": "settings.update",
        "arguments": {"key": "messages.farewell", "value": "Nos vemos."},
        "summary": "Cambiar la despedida",
        "requires_approval": True,
        "follow_up": True,
    }
    second = {
        "kind": "tool",
        "tool": "settings.update",
        "arguments": {"key": "tone.style", "value": "formal"},
        "summary": "Cambiar el tono",
        "requires_approval": True,
        "follow_up": False,
    }
    client = _Completions([json.dumps(second)])
    monkeypatch.setattr(assistant_nodes, "_assistant_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=client)))

    with SessionLocal() as session:
        approval = issue_approval(first)
        user, thread = _pending_write_thread(session, plan=first, approval=approval, run_id=run_id)

        approve_plan(session, thread, user, run_id, approval["token"])
        session.commit()
        session.refresh(thread)
        fresh = thread.assistant_state["approval"]

        rejected = approve_plan(session, thread, user, run_id, fresh["token"], reject=True)
        session.commit()

        assert rejected is not None
        assert rejected.status == "rejected"
        assert get_setting(session, "messages.farewell") == "Nos vemos."
        assert get_setting(session, "tone.style") == "cercano"
        assert client.stream_calls == 0
