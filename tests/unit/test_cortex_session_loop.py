"""RED-first contracts for the Cortex assistant loop and handoff."""

from types import SimpleNamespace

import pytest

from app.chat.assistant.graph import build_assistant_graph
from app.chat.assistant.nodes import classify_cortex_turn, cortex_session_turn
from app.models import MemoryStatus


def _active_state(**overrides):
    session = {
        "slug": "budget-review",
        "topic": "Budget review",
        "status": "active",
        "opened_at": "2026-09-13T12:00:00Z",
        "closed_at": None,
        "turn_index": 0,
        "next_decision": None,
        "last_class": None,
        "decision_keys": [],
        "report_key": None,
        "handoff": {"status": "none", "sdb_phase": None},
    }
    session.update(overrides)
    return {"cortex_session": session}


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("What does this cost?", "question"),
        ("Research the current supplier rates", "research"),
        ("We will use the existing provider", "decision"),
        ("Keep going", "continue"),
        ("/planning close", "close"),
    ],
)
def test_cortex_turn_classification_has_five_classes(content, expected):
    assert classify_cortex_turn(content) == expected


def test_cortex_question_does_not_require_decision(monkeypatch):
    state = {"content": "What does this cost?", **_active_state()}
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)

    result = cortex_session_turn(state)

    assert result["cortex_session"]["last_class"] == "question"
    assert result["cortex_session"]["turn_index"] == 1
    assert result["cortex_session"]["decision_keys"] == []


def test_graph_places_cortex_gate_after_context_and_cost_preflight():
    graph = build_assistant_graph()
    edges = graph.get_graph().edges
    names = [(edge.source, edge.target) for edge in edges]

    assert ("assemble_context", "panel_cost_gate") in names
    assert ("panel_cost_gate", "plan_llm") in names
    assert ("plan_llm", "cortex_session_gate") in names


def test_inactive_session_routes_to_normal_graph():
    from app.chat.assistant.nodes import cortex_session_gate

    state = _active_state(status="closed")
    result = cortex_session_gate(state)

    assert result["cortex_route"] == "normal"
    assert result["cortex_rejection"] == "inactive-session"


def test_report_closure_archives_upserted_report(monkeypatch):
    calls = []
    report = SimpleNamespace(id=41, topic_key="cortex-session/budget-review:report")
    monkeypatch.setattr("app.services.tukulpan.upsert", lambda *args, **kwargs: calls.append(("upsert", kwargs)) or report)
    monkeypatch.setattr("app.services.tukulpan.set_mark", lambda *args, **kwargs: calls.append(("set_mark", kwargs)) or report)

    from app.services.agent_chat import close_cortex_session

    result = close_cortex_session("db", SimpleNamespace(id=7, assistant_state=_active_state()), report="closed report")

    assert result["report_key"] == report.topic_key
    assert calls[0][0] == "upsert"
    assert calls[1] == ("set_mark", {"status": MemoryStatus.ARCHIVED})


def test_approved_cortex_plan_is_truthful_pending_handoff():
    from app.services.agent_chat import cortex_approved_plan

    result = cortex_approved_plan({"scope": {"request": "review budget"}}, [{"id": "task-1"}])

    assert result["status"] == "approved-plan"
    assert result["execution"] == "pending-approval"
