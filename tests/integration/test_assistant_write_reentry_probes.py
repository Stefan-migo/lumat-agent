"""Independent regression probes for assistant-write-chaining T1 (approval graph re-entry).

Covers:
  S1  re-entry continues the turn and the reply is responder-produced
  S2  binding: tampered args refused; unconsumed approval never executes
  S4  non-resume behaviour and the legacy single-node approval path are unchanged
  S6  resume reclaims a pending execution exactly once
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.chat.assistant import nodes as assistant_nodes
from app.chat.assistant.approval import consume_approval, issue_approval
from app.db import SessionLocal
from app.models import AuditLog, InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import approve_plan, resume_thread
from app.services.settings import MESSAGE_DEFAULTS, get_setting, set_setting
from app.services.users import hash_password

from tests.integration._capture_aware import planner_only

DEFAULT_FAREWELL = MESSAGE_DEFAULTS["farewell"]
_PLANNER_JSON = '{"kind": "respond", "summary": "hola", "requires_approval": false}'


class _Completions:
    def __init__(self, responder):
        self.calls = []
        self.responder = responder

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "response_format" in kwargs:  # planner call
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=_PLANNER_JSON))])
        if kwargs.get("stream"):  # responder call
            if self.responder == "raise":
                raise RuntimeError("provider down during response")
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=self.responder))])]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=_PLANNER_JSON))])


class _Client:
    def __init__(self, responder):
        self.completions = _Completions(responder)
        self.chat = SimpleNamespace(completions=self.completions)

    @property
    def calls(self):
        return self.completions.calls


@pytest.fixture
def fake_assistant_client(monkeypatch):
    def mount(responder="RESPONDER-TEXT"):
        client = _Client(responder)
        monkeypatch.setattr(assistant_nodes, "_assistant_client", lambda: client)
        return client

    return mount


def _seed(session, *, plan, approval, stage="approval_pending", msg_status="approval_pending"):
    suffix = uuid4().hex[:10]
    user = User(username=f"reentry-{suffix}", password_hash=hash_password("pass"), role="admin")
    session.add(user)
    session.flush()
    run_id = f"reentry-{suffix}"
    thread = InternalChatThread(
        user_id=user.id,
        active_run_id=run_id,
        current_plan=plan,
        assistant_state={"stage": stage, "approval": approval, "actor_role": "admin"},
    )
    session.add(thread)
    session.flush()
    session.add(
        InternalChatMessage(
            thread_id=thread.id,
            author="admin",
            content="change the farewell",
            status=msg_status,
            assistant_metadata={"run_id": run_id, "approval": approval},
        )
    )
    session.commit()
    return user, thread, run_id


def _agent_message(session, thread_id):
    return session.scalar(
        select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread_id, InternalChatMessage.author == "agent"
        )
    )


def test_approved_write_executes_once_and_persists_responder_text(migrated_db, fake_assistant_client):
    """S1/S2: the re-entered graph runs the write exactly once and replies with the responder text."""
    client = fake_assistant_client("Listo, actualicé la despedida.")
    executed = []
    real_execute_tool = assistant_nodes.execute_tool

    def counting_execute_tool(session, tool, *args, **kwargs):
        executed.append(tool)
        return real_execute_tool(session, tool, *args, **kwargs)

    assistant_nodes.execute_tool = counting_execute_tool
    try:
        with SessionLocal() as session:
            set_setting(session, "messages.farewell", DEFAULT_FAREWELL)
            session.commit()
            value = f"reentry-{uuid4().hex[:6]}"
            plan = {
                "tool": "settings.update",
                "arguments": {"key": "messages.farewell", "value": value},
                "requires_approval": True,
            }
            approval = issue_approval(plan)
            user, thread, run_id = _seed(session, plan=plan, approval=approval)

            assert approve_plan(session, thread, user, run_id, approval["token"]) is not None
            session.commit()

            assert get_setting(session, "messages.farewell") == value
            assert executed.count("settings.update") == 1
            agent = _agent_message(session, thread.id)
            assert agent is not None and agent.content == "Listo, actualicé la despedida."
            # plan_llm is skipped on resume, so the planner (response_format) is never called.
            assert sum(1 for call in planner_only(client.calls) if "response_format" in call) == 0
            assert (
                session.query(AuditLog)
                .filter_by(action="internal_chat.execution", entity_id=str(thread.id))
                .count()
                == 1
            )
    finally:
        assistant_nodes.execute_tool = real_execute_tool


def test_tampered_plan_arguments_are_refused_at_approval(migrated_db):
    """S2: a plan whose arguments differ from the bound token is refused."""
    with SessionLocal() as session:
        set_setting(session, "messages.farewell", DEFAULT_FAREWELL)
        session.commit()
        plan = {
            "tool": "settings.update",
            "arguments": {"key": "messages.farewell", "value": "bound"},
            "requires_approval": True,
        }
        approval = issue_approval(plan)
        user, thread, run_id = _seed(session, plan=plan, approval=approval)
        thread.current_plan = {
            "tool": "settings.update",
            "arguments": {"key": "messages.farewell", "value": "HACKED"},
            "requires_approval": True,
        }
        session.flush()

        assert approve_plan(session, thread, user, run_id, approval["token"]) is None
        session.commit()
        assert get_setting(session, "messages.farewell") != "HACKED"


def test_resume_with_pending_approval_refuses_execution(migrated_db, fake_assistant_client):
    """S2/S4: resume never executes a write without a consumed approval. T2 keeps that
    invariant but changes how it is enforced: instead of a hard `PermissionError` the gate
    parks the plan behind a fresh approval, and the write still does not run."""
    fake_assistant_client()
    with SessionLocal() as session:
        set_setting(session, "messages.farewell", DEFAULT_FAREWELL)
        session.commit()
        value = f"pending-{uuid4().hex[:6]}"
        plan = {
            "tool": "settings.update",
            "arguments": {"key": "messages.farewell", "value": value},
            "requires_approval": True,
        }
        approval = issue_approval(plan)  # deliberately left unconsumed
        user, thread, run_id = _seed(session, plan=plan, approval=approval, stage="executing", msg_status="processing")
        thread.assistant_state = {**thread.assistant_state, "execution_status": "pending"}
        session.flush()

        assert resume_thread(session, thread, user) is True
        session.commit()
        assert get_setting(session, "messages.farewell") != value
        assert _agent_message(session, thread.id) is None
        session.refresh(thread)
        assert thread.assistant_state["stage"] == "approval_pending"
        fresh = thread.assistant_state["approval"]
        assert fresh["status"] == "pending"
        assert fresh["token"] != approval["token"]


def test_resume_responder_failure_degrades_without_rolling_back_the_write(migrated_db, fake_assistant_client):
    """S1: a write already executed survives a responder failure on the resume path."""
    fake_assistant_client("raise")
    with SessionLocal() as session:
        set_setting(session, "messages.farewell", DEFAULT_FAREWELL)
        session.commit()
        value = f"degrade-{uuid4().hex[:6]}"
        plan = {
            "tool": "settings.update",
            "arguments": {"key": "messages.farewell", "value": value},
            "requires_approval": True,
        }
        approval = issue_approval(plan)
        user, thread, run_id = _seed(session, plan=plan, approval=approval)

        assert approve_plan(session, thread, user, run_id, approval["token"]) is not None
        session.commit()

        assert get_setting(session, "messages.farewell") == value
        agent = _agent_message(session, thread.id)
        assert agent is not None and agent.content.startswith("I received your request")
        events = (thread.assistant_state or {}).get("events") or []
        assert any(
            event.get("type") == "evidence"
            and any(item.get("status") == "degraded" for item in event.get("evidence", []))
            for event in events
        )


def test_non_resume_responder_failure_still_raises(migrated_db, fake_assistant_client):
    """S4: the resume-scoped resilience does not swallow failures on ordinary turns."""
    fake_assistant_client("raise")
    from app.services.agent_chat import run_assistant

    with SessionLocal() as session, pytest.raises(RuntimeError):
        run_assistant(
            thread_id=1, user_id=1, content="hola", run_id="non-resume",
            on_token=lambda _token: None, session=session,
        )


def test_tool_less_approval_keeps_the_single_node_execution_path(migrated_db, monkeypatch):
    """S4: the legacy_compat approval path still records internal_chat.execution once."""
    import app.services.agent_chat as agent_chat

    calls = []
    real_execute = agent_chat.execute

    def recording_execute(state):
        calls.append(state)
        return real_execute(state)

    monkeypatch.setattr(agent_chat, "execute", recording_execute)
    with SessionLocal() as session:
        plan = {"tool": None, "arguments": {}, "summary": "create a rule", "requires_approval": True}
        approval = issue_approval(plan)
        user, thread, run_id = _seed(session, plan=plan, approval=approval)

        assert approve_plan(session, thread, user, run_id, approval["token"]) is not None
        session.commit()

        assert len(calls) == 1
        assert (
            session.query(AuditLog)
            .filter_by(action="internal_chat.execution", entity_id=str(thread.id))
            .count()
            == 1
        )


def test_resume_executes_a_tool_plan_exactly_once(migrated_db, fake_assistant_client):
    """S4/S6: resume reclaims the pending execution once and refuses the second call."""
    fake_assistant_client("Resumed.")
    executed = []
    real_execute_tool = assistant_nodes.execute_tool

    def counting_execute_tool(session, tool, *args, **kwargs):
        executed.append(tool)
        return real_execute_tool(session, tool, *args, **kwargs)

    assistant_nodes.execute_tool = counting_execute_tool
    try:
        with SessionLocal() as session:
            set_setting(session, "messages.farewell", DEFAULT_FAREWELL)
            session.commit()
            value = f"resume-{uuid4().hex[:6]}"
            plan = {
                "tool": "settings.update",
                "arguments": {"key": "messages.farewell", "value": value},
                "requires_approval": True,
            }
            approval = issue_approval(plan)
            consume_approval(approval, approval["token"])
            user, thread, run_id = _seed(session, plan=plan, approval=approval, stage="executing", msg_status="processing")
            thread.assistant_state = {**thread.assistant_state, "execution_status": "pending"}
            session.flush()

            assert resume_thread(session, thread, user) is True
            session.commit()
            assert resume_thread(session, thread, user) is False
            session.commit()
            assert get_setting(session, "messages.farewell") == value
            assert executed.count("settings.update") == 1
            agent = _agent_message(session, thread.id)
            assert agent is not None and agent.content == "Resumed."
    finally:
        assistant_nodes.execute_tool = real_execute_tool
