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


def test_planning_open_tool_creates_a_dedicated_thread(make_user):
    make_user("planning-open", "planning-pass", role="admin")
    owner_id, origin_id = _owned_thread("planning-open")

    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.open",
            {"topic": "Presupuesto 2026"},
            role="admin",
            trusted_thread_id=origin_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        session_id = result["result"]["thread_id"]

    assert result["status"] == "completed"
    assert result["result"]["origin_thread_id"] == origin_id
    assert session_id != origin_id
    assert result["result"]["session"]["status"] == "active"
    assert result["result"]["session"]["topic"] == "Presupuesto 2026"
    with SessionLocal() as session:
        session_thread = session.get(InternalChatThread, session_id)
        assert session_thread.user_id == owner_id
        assert session_thread.assistant_state["cortex_session"]["status"] == "active"
        origin = session.get(InternalChatThread, origin_id)
        assert (origin.assistant_state or {}).get("cortex_session") is None


def test_execution_events_emit_a_planning_event_for_a_completed_open():
    from app.services.agent_chat import _execution_events

    result = {
        "tool_results": [
            {"tool": "memory.read", "status": "completed", "result": {"rows": []}},
            {"tool": "planning.open", "status": "completed", "result": {"thread_id": 9, "session": {}}},
        ],
        "tool_result": {"tool": "planning.open", "status": "completed", "result": {"thread_id": 9, "session": {}}},
        "evidence": [],
        "status": "completed",
        "response": "Tool planning.open completed.",
    }

    events = _execution_events(result, 4, "run-1", 2)
    planning = [event for event in events if event["type"] == "planning"]

    assert len(planning) == 1
    assert planning[0] == {
        "type": "planning",
        "thread_id": 4,
        "run_id": "run-1",
        "sequence": 6,
        "planning_thread_id": 9,
    }


def test_execution_events_omit_planning_for_other_incomplete_or_invalid_results():
    from app.services.agent_chat import _execution_events

    def event_types(entry):
        return {event["type"] for event in _execution_events(entry, 4, "run-2", 2)}

    assert "planning" not in event_types({
        "tool_results": [{"tool": "customers.list", "status": "completed", "result": {}}],
        "tool_result": {"tool": "customers.list", "status": "completed", "result": {}},
    })
    assert "planning" not in event_types({
        "tool_results": [{"tool": "planning.open", "status": "error", "result": {"thread_id": 9}}],
        "tool_result": {"tool": "planning.open", "status": "error", "result": {"thread_id": 9}},
    })
    assert "planning" not in event_types({
        "tool_results": [{"tool": "planning.open", "status": "completed", "result": {"thread_id": 0}}],
        "tool_result": {"tool": "planning.open", "status": "completed", "result": {"thread_id": 0}},
    })
    assert "planning" not in event_types({
        "tool_results": [{"tool": "planning.open", "status": "completed", "result": {}}],
        "tool_result": {"tool": "planning.open", "status": "completed", "result": {}},
    })


def test_execution_events_prefer_the_most_recent_planning_open():
    from app.services.agent_chat import _execution_events

    result = {
        "tool_results": [
            {"tool": "planning.open", "status": "completed", "result": {"thread_id": 9}},
            {"tool": "planning.open", "status": "completed", "result": {"thread_id": 11}},
        ],
        "tool_result": {"tool": "planning.close", "status": "completed", "result": {}},
    }

    planning = [event for event in _execution_events(result, 4, "run-3", 2) if event["type"] == "planning"]

    assert len(planning) == 1
    assert planning[0]["planning_thread_id"] == 11


def test_planning_close_tool_closes_and_writes_one_agent_report(make_user):
    make_user("planning-close", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-close")

    with SessionLocal() as session:
        opened = execute_tool(
            session,
            "planning.open",
            {"topic": "Cierre de sesión"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        session_thread_id = opened["result"]["thread_id"]

    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.close",
            {},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["result"]["session"]["status"] == "closed"
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, session_thread_id)
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
        opened = execute_tool(
            session,
            "planning.open",
            {"topic": "Presupuesto 2026"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        session_thread_id = opened["result"]["thread_id"]

    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.record_decision",
            decision,
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["result"]["decision"] == decision
    assert result["result"]["decisions"] == [decision]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, session_thread_id)
        cortex = thread.assistant_state["cortex_session"]
        assert cortex["decisions"] == [decision]
        assert cortex["topic"] == "Presupuesto 2026"
        assert cortex["status"] == "active"


def test_planning_record_note_appends_a_structured_note(make_user):
    make_user("planning-note", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-note")
    note = {"kind": "risk", "content": "El proveedor puede fallar"}

    with SessionLocal() as session:
        opened = execute_tool(
            session,
            "planning.open",
            {"topic": "Riesgos del proyecto"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        session_thread_id = opened["result"]["thread_id"]

    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.record_note",
            note,
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["result"]["note"] == note
    assert result["result"]["notes"] == [note]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, session_thread_id)
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


def test_planning_close_writes_a_substantive_report(make_user):
    make_user("planning-report", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-report")

    with SessionLocal() as session:
        opened = execute_tool(
            session,
            "planning.open",
            {"topic": "Reporte sustantivo"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        session_thread_id = opened["result"]["thread_id"]

    with SessionLocal() as session:
        execute_tool(
            session,
            "planning.record_note",
            {"kind": "objective", "content": "Decidir el presupuesto"},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        execute_tool(
            session,
            "planning.record_decision",
            {"title": "Stack", "content": "Usar Postgres"},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        execute_tool(
            session,
            "planning.close",
            {},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, session_thread_id)
        topic_key = thread.assistant_state["cortex_session"]["report_key"]
        report = session.scalars(select(Memory).where(Memory.topic_key == topic_key)).one()
        assert "Decidir el presupuesto" in report.contenido
        assert "**Stack** — Usar Postgres" in report.contenido
        assert '{"topic"' not in report.contenido


def test_planning_close_reports_gaps_but_always_succeeds(make_user):
    make_user("planning-gaps", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-gaps")

    with SessionLocal() as session:
        opened = execute_tool(
            session,
            "planning.open",
            {"topic": "Sin checklist"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        session_thread_id = opened["result"]["thread_id"]

    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.close",
            {},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["result"]["session"]["status"] == "closed"
    assert set(result["result"]["gaps"]) == {"objective", "decisions", "risks", "next_steps"}
    assert result["result"]["minimum_met"] is False


def test_planning_close_offers_no_handoff_without_a_captured_next_step(make_user):
    make_user("planning-no-handoff", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-no-handoff")

    with SessionLocal() as session:
        opened = execute_tool(
            session,
            "planning.open",
            {"topic": "Sin handoff"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        session_thread_id = opened["result"]["thread_id"]

    with SessionLocal() as session:
        execute_tool(
            session,
            "planning.record_note",
            {"kind": "objective", "content": "Decidir el presupuesto"},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        result = execute_tool(
            session,
            "planning.close",
            {},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["result"]["handoff"] is None


def test_planning_close_offers_a_handoff_with_a_captured_next_step(make_user):
    make_user("planning-handoff", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-handoff")

    with SessionLocal() as session:
        opened = execute_tool(
            session,
            "planning.open",
            {"topic": "Con handoff"},
            role="admin",
            trusted_thread_id=thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        session_thread_id = opened["result"]["thread_id"]

    with SessionLocal() as session:
        execute_tool(
            session,
            "planning.record_note",
            {"kind": "next_step", "content": "Crear el proyecto X"},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        result = execute_tool(
            session,
            "planning.close",
            {},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["result"]["handoff"] == {"actions": ["Crear el proyecto X"]}


def test_execution_events_emit_a_handoff_event_for_a_completed_close_with_a_proposal():
    from app.services.agent_chat import _execution_events

    proposal = {"actions": ["Crear el proyecto X"]}
    result = {
        "tool_results": [
            {"tool": "memory.read", "status": "completed", "result": {"rows": []}},
            {"tool": "planning.close", "status": "completed", "result": {"handoff": proposal}},
        ],
        "tool_result": {"tool": "planning.close", "status": "completed", "result": {"handoff": proposal}},
        "evidence": [],
        "status": "completed",
        "response": "Tool planning.close completed.",
    }

    events = _execution_events(result, 4, "run-h1", 2)
    handoff = [event for event in events if event["type"] == "handoff"]

    assert len(handoff) == 1
    assert handoff[0]["handoff"] == proposal
    assert handoff[0]["thread_id"] == 4
    assert handoff[0]["run_id"] == "run-h1"


def test_execution_events_omit_handoff_without_a_proposal():
    from app.services.agent_chat import _execution_events

    def event_types(entry):
        return {event["type"] for event in _execution_events(entry, 4, "run-h2", 2)}

    assert "handoff" not in event_types({
        "tool_results": [{"tool": "planning.close", "status": "completed", "result": {"handoff": None}}],
        "tool_result": {"tool": "planning.close", "status": "completed", "result": {"handoff": None}},
    })
    assert "handoff" not in event_types({
        "tool_results": [{"tool": "planning.close", "status": "completed", "result": {"handoff": {"actions": []}}}],
        "tool_result": {"tool": "planning.close", "status": "completed", "result": {"handoff": {"actions": []}}},
    })
    assert "handoff" not in event_types({
        "tool_results": [{"tool": "planning.open", "status": "completed", "result": {"thread_id": 9}}],
        "tool_result": {"tool": "planning.open", "status": "completed", "result": {"thread_id": 9}},
    })


def test_planning_read_report_is_registered_and_authorized(make_user):
    make_user("planning-read", "planning-pass", role="admin")

    whitelist = load_assistant_config().tools_whitelist
    assert get_tool("planning.read_report").read_only is True
    assert "planning.read_report" in whitelist
    assert is_tool_allowed_for_role("planning.read_report", "admin") is True
    assert is_tool_allowed_for_role("planning.read_report", "operador") is True
    assert is_tool_allowed_for_role("planning.read_report", "tecnico") is False


def _closed_session_with_report(owner_id: int, origin_id: int, topic: str) -> str:
    with SessionLocal() as session:
        opened = execute_tool(
            session,
            "planning.open",
            {"topic": topic},
            role="admin",
            trusted_thread_id=origin_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        session_thread_id = opened["result"]["thread_id"]
        slug = opened["result"]["session"]["slug"]

    with SessionLocal() as session:
        execute_tool(
            session,
            "planning.record_note",
            {"kind": "objective", "content": "Decidir el presupuesto"},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        execute_tool(
            session,
            "planning.record_decision",
            {"title": "Stack", "content": "Usar Postgres"},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        execute_tool(
            session,
            "planning.close",
            {},
            role="admin",
            trusted_thread_id=session_thread_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
    return slug


def test_planning_read_report_returns_the_persisted_report(make_user):
    make_user("planning-read-run", "planning-pass", role="admin")
    owner_id, origin_id = _owned_thread("planning-read-run")
    slug = _closed_session_with_report(owner_id, origin_id, "Reporte leible")

    with SessionLocal() as session:
        result = execute_tool(
            session,
            "planning.read_report",
            {"slug": slug},
            role="admin",
            trusted_thread_id=origin_id,
            owner_id=owner_id,
            proyecto="default",
        )

    assert result["status"] == "completed"
    assert result["read_only"] is True
    report = result["result"]
    assert report["slug"] == slug
    assert "Decidir el presupuesto" in report["report"]
    assert "**Stack** — Usar Postgres" in report["report"]


def test_planning_read_report_rejects_an_unknown_slug(make_user):
    make_user("planning-read-miss", "planning-pass", role="admin")
    owner_id, thread_id = _owned_thread("planning-read-miss")

    with SessionLocal() as session:
        with pytest.raises(ToolValidationError, match="not found"):
            execute_tool(
                session,
                "planning.read_report",
                {"slug": "ghost-1"},
                role="admin",
                trusted_thread_id=thread_id,
                owner_id=owner_id,
                proyecto="default",
            )


def test_planning_read_report_rejects_a_session_without_a_report(make_user):
    make_user("planning-read-open", "planning-pass", role="admin")
    owner_id, origin_id = _owned_thread("planning-read-open")

    with SessionLocal() as session:
        opened = execute_tool(
            session,
            "planning.open",
            {"topic": "Aun abierta"},
            role="admin",
            trusted_thread_id=origin_id,
            owner_id=owner_id,
            proyecto="default",
        )
        session.commit()
        slug = opened["result"]["session"]["slug"]

    with SessionLocal() as session:
        with pytest.raises(ToolValidationError, match="no report"):
            execute_tool(
                session,
                "planning.read_report",
                {"slug": slug},
                role="admin",
                trusted_thread_id=origin_id,
                owner_id=owner_id,
                proyecto="default",
            )


def test_planning_read_report_rejects_a_foreign_owner(make_user):
    make_user("planning-read-victim", "planning-pass", role="admin")
    make_user("planning-read-attacker", "planning-pass", role="admin")
    victim_id, victim_origin = _owned_thread("planning-read-victim")
    attacker_id, attacker_origin = _owned_thread("planning-read-attacker")
    slug = _closed_session_with_report(victim_id, victim_origin, "Sesion victima")

    with SessionLocal() as session:
        with pytest.raises(ToolValidationError, match="not found"):
            execute_tool(
                session,
                "planning.read_report",
                {"slug": slug},
                role="admin",
                trusted_thread_id=attacker_origin,
                owner_id=attacker_id,
                proyecto="default",
            )
