"""Agent tools that drive the planning (Cortex) session lifecycle (S3, D3)."""

from sqlalchemy import select

from app.chat.assistant.tools.registry import (
    AUTONOMOUS_WRITE_ALLOWLIST,
    execute_tool,
    get_tool,
    is_tool_allowed_for_role,
)
from app.db import SessionLocal
from app.models import InternalChatThread, Memory, User
from app.services.agent_chat import create_thread
from app.services.prompts import load_assistant_config


def _owned_thread(username: str) -> tuple[int, int]:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == username))
        thread = create_thread(session, user)
        session.commit()
        return user.id, thread.id


def test_planning_lifecycle_tools_are_registered_and_authorized(make_user):
    make_user("planning-tools", "planning-pass", role="admin")

    whitelist = load_assistant_config().tools_whitelist
    for name in ("planning.open", "planning.close"):
        assert get_tool(name).read_only is False
        assert name in whitelist
        assert name in AUTONOMOUS_WRITE_ALLOWLIST
        assert is_tool_allowed_for_role(name, "admin") is True
        assert is_tool_allowed_for_role(name, "tecnico") is False


def test_planning_open_tool_activates_a_session_on_the_thread(make_user):
    make_user("planning-open", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-open")

    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.open",
            {"topic": "Presupuesto 2026"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["result"]["session"]["status"] == "active"
    assert result["result"]["session"]["topic"] == "Presupuesto 2026"
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["cortex_session"]["status"] == "active"


def test_planning_close_tool_closes_and_writes_one_agent_report(make_user):
    make_user("planning-close", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-close")

    with SessionLocal() as session:
        execute_tool(
            session,
            "planning.open",
            {"topic": "Cierre de sesión"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.close",
            {},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["result"]["session"]["status"] == "closed"
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        topic_key = thread.assistant_state["cortex_session"]["report_key"]
        reports = session.scalars(select(Memory).where(Memory.topic_key == topic_key)).all()
        assert len(reports) == 1
        assert reports[0].scope == "agent"
