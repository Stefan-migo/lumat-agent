"""Agent tools that drive the planning (Cortex) session lifecycle (S3, S4, D3, D5)."""

import pytest
from sqlalchemy import select

from app.chat.assistant.tools.registry import (
    AUTONOMOUS_WRITE_ALLOWLIST,
    ToolValidationError,
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


def test_planning_capture_tools_are_registered_and_authorized(make_user):
    make_user("planning-capture", "planning-pass", role="admin")

    whitelist = load_assistant_config().tools_whitelist
    for name in ("planning.record_decision", "planning.record_note"):
        assert get_tool(name).read_only is False
        assert name in whitelist
        assert name in AUTONOMOUS_WRITE_ALLOWLIST
        assert is_tool_allowed_for_role(name, "admin") is True
        assert is_tool_allowed_for_role(name, "operador") is True
        assert is_tool_allowed_for_role(name, "tecnico") is False


def test_planning_record_decision_appends_a_structured_decision(make_user):
    make_user("planning-decision", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-decision")
    decision = {"title": "Usar proveedor X", "content": "Porque es más barato"}

    with SessionLocal() as session:
        execute_tool(
            session,
            "planning.open",
            {"topic": "Presupuesto 2026"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.record_decision",
            decision,
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["result"]["decision"] == decision
    assert result["result"]["decisions"] == [decision]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        cortex = thread.assistant_state["cortex_session"]
        assert cortex["decisions"] == [decision]
        assert cortex["topic"] == "Presupuesto 2026"
        assert cortex["status"] == "active"


def test_planning_record_note_appends_a_structured_note(make_user):
    make_user("planning-note", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-note")
    note = {"kind": "risk", "content": "El proveedor puede fallar"}

    with SessionLocal() as session:
        execute_tool(
            session,
            "planning.open",
            {"topic": "Riesgos del proyecto"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.record_note",
            note,
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["result"]["note"] == note
    assert result["result"]["notes"] == [note]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["cortex_session"]["notes"] == [note]


def test_planning_capture_tools_reject_without_an_active_session(make_user):
    make_user("planning-inactive", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-inactive")

    for name, arguments in (
        ("planning.record_decision", {"title": "Decisión", "content": "Contenido"}),
        ("planning.record_note", {"kind": "general", "content": "Contenido"}),
    ):
        with SessionLocal() as session:
            with pytest.raises(ToolValidationError, match="not active"):
                execute_tool(
                    session,
                    name,
                    arguments,
                    role="admin",
                    trusted_thread_id=thread_id,
                    owner_id=owner_id,
                    proyecto="default",
                )
