"""Independent security probes for the planning tools, kept as regression tests.

Converted from the read-only verification probes (S3, S4, S5, S6, S7): cross-owner
rejection, input boundaries, double close, and the active-session tool filter.
"""

import pytest
from sqlalchemy import select

from app.chat.assistant.nodes import _effective_tools
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.db import SessionLocal
from app.models import User
from app.services.agent_chat import create_thread


def _owner_and_thread(username: str) -> tuple[int, int]:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == username))
        thread = create_thread(session, user)
        session.commit()
        return user.id, thread.id


def _open_session(owner_id: int, origin_id: int, topic: str) -> int:
    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.open",
            {"topic": topic},
            role="admin",
            trusted_thread_id=origin_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        return result["result"]["thread_id"]


@pytest.mark.parametrize(
    "tool,arguments",
    [
        ("planning.record_note", {"kind": "general", "content": "x"}),
        ("planning.record_decision", {"title": "t", "content": "c"}),
        ("planning.close", {}),
    ],
)
def test_planning_tools_reject_a_foreign_owner(make_user, tool, arguments):
    make_user("probe-victim", "probe-pass", role="admin")
    make_user("probe-attacker", "probe-pass", role="admin")
    victim_id, victim_origin = _owner_and_thread("probe-victim")
    attacker_id, _ = _owner_and_thread("probe-attacker")
    victim_session = _open_session(victim_id, victim_origin, "Victim topic")

    with SessionLocal() as session:
        with pytest.raises(ToolValidationError, match="chat thread not found"):
            execute_tool(
                session,
                tool,
                arguments,
                role="admin",
                trusted_thread_id=victim_session,
                owner_id=attacker_id,
                proyecto="default",
            )


def test_planning_open_rejects_a_whitespace_topic(make_user):
    make_user("probe-blank", "probe-pass", role="admin")
    owner_id, origin_id = _owner_and_thread("probe-blank")

    with SessionLocal() as session:
        with pytest.raises(ToolValidationError, match="topic must not be blank"):
            execute_tool(
                session,
                "planning.open",
                {"topic": "   "},
                role="admin",
                trusted_thread_id=origin_id,
                owner_id=owner_id,
                proyecto="default",
            )


def test_planning_record_note_rejects_an_extra_argument(make_user):
    make_user("probe-extra", "probe-pass", role="admin")
    owner_id, origin_id = _owner_and_thread("probe-extra")
    session_thread = _open_session(owner_id, origin_id, "Extra arg")

    with SessionLocal() as session:
        with pytest.raises(ToolValidationError):
            execute_tool(
                session,
                "planning.record_note",
                {"kind": "general", "content": "x", "extra": 1},
                role="admin",
                trusted_thread_id=session_thread,
                owner_id=owner_id,
                proyecto="default",
            )


def test_planning_close_rejects_a_second_close(make_user):
    make_user("probe-double", "probe-pass", role="admin")
    owner_id, origin_id = _owner_and_thread("probe-double")
    session_thread = _open_session(owner_id, origin_id, "Double close")

    with SessionLocal() as session:
        execute_tool(
            session,
            "planning.close",
            {},
            role="admin",
            trusted_thread_id=session_thread,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    with SessionLocal() as session:
        with pytest.raises(ToolValidationError, match="not active"):
            execute_tool(
                session,
                "planning.close",
                {},
                role="admin",
                trusted_thread_id=session_thread,
                owner_id=owner_id,
                proyecto="default",
            )


def test_effective_tools_keeps_only_planning_and_memory_write_when_active():
    inactive = set(_effective_tools({}))
    active = set(
        _effective_tools(
            {
                "cortex_session": {
                    "slug": "s",
                    "topic": "t",
                    "status": "active",
                    "opened_at": "2026-10-14T00:00:00Z",
                    "closed_at": None,
                    "report_key": None,
                    "decisions": [],
                    "notes": [],
                }
            }
        )
    )

    assert "project.create" in inactive and "artifact.save" in inactive
    assert "project.create" not in active and "artifact.save" not in active
    assert {
        "planning.open",
        "planning.close",
        "planning.record_decision",
        "planning.record_note",
    } <= active
    assert "memory.write" in active
    assert "memory.update" not in active
    assert "customers.list" in active
