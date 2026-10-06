"""RED-first contracts for the Cortex assistant loop and handoff."""

from types import SimpleNamespace

from app.chat.assistant.graph import _after_plan, build_assistant_graph
from app.chat.assistant.nodes import _effective_tools
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


def test_graph_planner_routes_to_guardrails_without_cortex_turn():
    graph = build_assistant_graph()
    edges = graph.get_graph().edges
    names = [(edge.source, edge.target) for edge in edges]

    assert ("assemble_context", "panel_cost_gate") in names
    assert ("panel_cost_gate", "plan_llm") in names
    assert _after_plan({"tool_steps": 0}) == "guardrails"
    assert ("plan_llm", "guardrails") in names
    assert "cortex_turn" not in graph.get_graph().nodes
    assert "cortex_session_gate" not in graph.get_graph().nodes


def test_active_planning_session_filters_write_tools_but_keeps_memory_write_and_reads():
    effective = {
        "tools_whitelist": (
            "memory.delete", "project.create", "automation.create_rule",
            "memory.write", "kb.retrieve",
        )
    }

    tools = _effective_tools({**_active_state(), "effective": effective})

    assert "memory.delete" not in tools
    assert "project.create" not in tools
    assert "automation.create_rule" not in tools
    assert "memory.write" in tools
    assert "kb.retrieve" in tools


def test_non_planning_effective_tools_are_unchanged():
    effective = {"tools_whitelist": ("memory.delete", "project.create", "kb.retrieve")}

    assert _effective_tools({"effective": effective}) == effective["tools_whitelist"]


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
