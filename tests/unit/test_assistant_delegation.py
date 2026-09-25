"""Trust-boundary tests for delegated assistant plans."""

from dataclasses import replace
from pathlib import Path

import pytest


CUSTOMER_RECORD_TOOLS = (
    "customers.search",
    "conversations.search",
    "appointments.upcoming",
    "cases.list",
    "memory.read",
    "memory.search",
)


def test_resolves_customer_records_with_exact_read_only_scope():
    from app.chat.assistant.delegation import resolve_delegation_scope
    from app.chat.assistant.tools.registry import TOOL_REGISTRY

    scope = resolve_delegation_scope("customer_records")

    assert scope.tools_whitelist == CUSTOMER_RECORD_TOOLS
    assert scope.memoria_scope == "customer"
    assert all(TOOL_REGISTRY[name].read_only for name in scope.tools_whitelist)
    assert "return evidence" in scope.persona.lower()


def test_unknown_subagent_is_refused_explicitly():
    from app.chat.assistant.delegation import DelegationScopeError, resolve_delegation_scope

    with pytest.raises(DelegationScopeError, match="unknown sub-agent"):
        resolve_delegation_scope("not_declared")


def test_empty_subagent_scope_is_refused_explicitly():
    from app.agent_registry import get_registry
    from app.chat.assistant.delegation import DelegationScopeError, resolve_delegation_scope

    registry = get_registry()
    empty = replace(registry.sub_agents["customer_records"], tools_whitelist=())
    registry = replace(registry, sub_agents={**registry.sub_agents, "customer_records": empty})

    with pytest.raises(DelegationScopeError, match="empty"):
        resolve_delegation_scope("customer_records", registry=registry)


def test_write_tool_in_subagent_scope_is_refused_explicitly():
    from app.agent_registry import get_registry
    from app.chat.assistant.delegation import DelegationScopeError, resolve_delegation_scope

    registry = get_registry()
    subagent = replace(
        registry.sub_agents["customer_records"],
        tools_whitelist=("memory.write",),
    )
    registry = replace(registry, sub_agents={**registry.sub_agents, "customer_records": subagent})

    with pytest.raises(DelegationScopeError, match="read-only"):
        resolve_delegation_scope("customer_records", registry=registry)


def test_unknown_tool_in_subagent_scope_is_refused_explicitly():
    from app.agent_registry import get_registry
    from app.chat.assistant.delegation import DelegationScopeError, resolve_delegation_scope

    registry = get_registry()
    subagent = replace(
        registry.sub_agents["customer_records"],
        tools_whitelist=("missing.tool",),
    )
    registry = replace(registry, sub_agents={**registry.sub_agents, "customer_records": subagent})

    with pytest.raises(DelegationScopeError, match="unknown tool"):
        resolve_delegation_scope("customer_records", registry=registry)


def test_valid_delegate_routes_into_span_then_grounding(monkeypatch):
    from app.chat.assistant import graph, nodes
    plans = iter([
        nodes.PlannerOutput(kind="tool", tool="customers.search", arguments={"query": "open cases"},
                            summary="Gather customer evidence.", requires_approval=False),
        nodes.PlannerOutput(kind="respond", summary="Done."),
    ])
    monkeypatch.setattr(nodes, "_delegation_plan", lambda *args, **kwargs: next(plans))
    monkeypatch.setattr(nodes, "execute_tool", lambda *args, **kwargs: {
        "tool": "customers.search", "status": "completed", "result": [{"name": "Ana"}],
    })
    result = nodes.guardrails(
        {"content": "Which customers have open cases?", "planner": {"valid": True},
         "plan": {"kind": "delegate", "sub_agent": "customer_records", "summary": "Gather."}}
    )

    state = {"content": "Which customers have open cases?", "plan": {"kind": "delegate", "sub_agent": "customer_records"}, **result}
    assert graph._after_guardrails(state) == "delegation_span"
    wired = nodes.delegation_node(state)
    assert wired["delegation"]["steps"] == 1
    assert wired["tool_steps"] == 1
    assert wired["status"] == "completed"
    assert wired["tool_results"][0]["result"] == [{"name": "Ana"}]
    assert wired["evidence"]


def test_valid_delegate_scope_routes_terminally_instead_of_answering_without_evidence():
    from app.chat.assistant.graph import _after_guardrails
    from app.chat.assistant.nodes import guardrails

    result = guardrails(
        {
            "content": "Which customers have open cases?",
            "planner": {"valid": True},
            "plan": {"kind": "delegate", "sub_agent": "customer_records", "summary": "Gather records."},
        }
    )

    state = {"plan": {"kind": "delegate"}, **result}
    assert _after_guardrails(state) == "delegation_span"


@pytest.mark.parametrize(
    ("key", "tools", "expected_error"),
    [
        ("not_declared", None, "unknown sub-agent"),
        ("customer_records", (), "empty"),
    ],
)
def test_guardrails_explicitly_refuses_invalid_delegate_scope(key, tools, expected_error):
    from app.agent_registry import get_registry
    from app.chat.assistant.nodes import guardrails

    plan = {"kind": "delegate", "sub_agent": key, "summary": "Gather records."}
    if tools is not None:
        registry = get_registry()
        subagent = replace(registry.sub_agents["customer_records"], tools_whitelist=tools)
        # Guardrails resolves the runtime registry; monkeypatch only this local test's source.
        from app.chat.assistant import delegation
        original = delegation.get_registry
        delegation.get_registry = lambda: replace(
            registry, sub_agents={**registry.sub_agents, "customer_records": subagent}
        )
        try:
            result = guardrails({"content": "Gather records", "planner": {"valid": True}, "plan": plan})
        finally:
            delegation.get_registry = original
    else:
        result = guardrails({"content": "Gather records", "planner": {"valid": True}, "plan": plan})

    assert result["guardrails"]["decision"] == "delegate_refused"
    assert expected_error in result["guardrails"]["reason"]
    assert result["status"] == "completed"
    assert result["response"]


def test_delegate_refusal_routes_terminally_without_responder():
    from langgraph.graph import END

    from app.chat.assistant.graph import _after_guardrails
    from app.chat.assistant.nodes import PANEL_DELEGATION_REFUSAL, guardrails

    result = guardrails(
        {
            "content": "Gather records",
            "planner": {"valid": True},
            "plan": {"kind": "delegate", "sub_agent": "missing", "summary": "Gather."},
        }
    )

    assert result["guardrails"]["decision"] == "delegate_refused"
    assert result["status"] == "completed"
    assert result["response"] == PANEL_DELEGATION_REFUSAL
    assert _after_guardrails({"plan": {"kind": "delegate"}, **result}) == END


def test_planner_prompt_advertises_executable_delegation():
    prompt = (Path(__file__).resolve().parents[2] / "agent" / "prompts" / "assistant_plan.md").read_text()

    assert 'kind: "delegate"' in prompt
    assert 'sub_agent: "customer_records"' in prompt


def test_planner_output_accepts_delegate_selector_and_forbids_other_extras():
    from app.chat.assistant.state import PlannerOutput

    plan = PlannerOutput.model_validate(
        {"kind": "delegate", "sub_agent": "customer_records", "summary": "Gather records."}
    )
    assert plan.sub_agent == "customer_records"
    with pytest.raises(Exception):
        PlannerOutput.model_validate(
            {"kind": "delegate", "sub_agent": "customer_records", "summary": "Gather.", "extra": 1}
        )


def test_delegate_plan_requires_selector():
    from app.chat.assistant.state import PlannerOutput

    with pytest.raises(Exception):
        PlannerOutput.model_validate({"kind": "delegate", "summary": "Gather records."})


def test_delegation_span_refuses_write_and_stops_at_its_own_cap(monkeypatch):
    from app.chat.assistant import nodes
    from app.chat.assistant.delegation import resolve_delegation_scope

    plans = iter([
        {"kind": "tool", "tool": "memory.write", "arguments": {}, "summary": "write", "requires_approval": False},
        {"kind": "tool", "tool": "customers.search", "arguments": {"query": "Ana"}, "summary": "read", "requires_approval": False},
        {"kind": "tool", "tool": "customers.search", "arguments": {"query": "Ana"}, "summary": "read", "requires_approval": False},
    ])
    monkeypatch.setattr(nodes, "_assistant_client", lambda: None)
    monkeypatch.setattr(nodes, "_delegation_plan", lambda *args, **kwargs: next(plans))
    executed = []
    monkeypatch.setattr(nodes, "execute_tool", lambda *args, **kwargs: executed.append(args[1]) or {"tool": args[1], "status": "completed", "result": []})

    result = nodes.delegation_span(
        {"content": "Find Ana", "thread_id": 1},
        resolve_delegation_scope("customer_records"),
    )

    assert result["delegation"]["decisions"][0] == nodes.DELEGATION_WRITE_REFUSED
    assert result["delegation"]["cap"] == nodes.DELEGATION_SPAN_MAX_STEPS
    assert result["delegation"]["steps"] == nodes.DELEGATION_SPAN_MAX_STEPS
    assert executed == ["customers.search"]


def test_customer_memory_scope_refuses_own_read_and_permits_customer_read(monkeypatch):
    from app.chat.assistant import nodes
    from app.chat.assistant.delegation import resolve_delegation_scope

    plans = iter([
        {"kind": "tool", "tool": "memory.read", "arguments": {"scope": "own"}, "summary": "own", "requires_approval": False},
        {"kind": "tool", "tool": "memory.read", "arguments": {"scope": "customer", "entity_id": "customer-1"}, "summary": "customer", "requires_approval": False},
    ])
    monkeypatch.setattr(nodes, "_delegation_plan", lambda *args, **kwargs: next(plans))
    executed = []
    monkeypatch.setattr(nodes, "execute_tool", lambda *args, **kwargs: executed.append(args[2]) or {"tool": args[1], "status": "completed", "result": []})

    result = nodes.delegation_span(
        {"content": "Find memory", "thread_id": 1},
        resolve_delegation_scope("customer_records"),
    )

    assert nodes.DELEGATION_MEMORY_SCOPE_REFUSED in result["delegation"]["decisions"]
    assert [call["scope"] for call in executed] == ["customer"]


def test_delegation_span_returns_budgeted_provenance_evidence(monkeypatch):
    from app.chat.assistant import nodes
    from app.chat.assistant.delegation import resolve_delegation_scope

    monkeypatch.setattr(nodes, "_delegation_plan", lambda *args, **kwargs: {
        "kind": "tool", "tool": "customers.search", "arguments": {"query": "Ana"},
        "summary": "find", "requires_approval": False,
    })
    monkeypatch.setattr(nodes, "execute_tool", lambda *args, **kwargs: {
        "tool": "customers.search", "status": "completed", "result": [{"name": "Ana"}],
    })

    result = nodes.delegation_span(
        {"content": "Find Ana", "thread_id": 1},
        resolve_delegation_scope("customer_records"),
    )

    assert result["evidence"][0]["provenance"] == {
        "sub_agent": "customer_records", "step": 1, "tool": "customers.search",
    }
    assert len(result["evidence"]) <= result["delegation"]["cap"]
    assert "status" not in result


def test_delegation_span_refuses_a_read_outside_the_worker_scope(monkeypatch):
    from app.chat.assistant import nodes
    from app.chat.assistant.delegation import resolve_delegation_scope

    plans = iter([
        {"kind": "tool", "tool": "customers.list", "arguments": {"limit": 5}, "summary": "list", "requires_approval": False},
        {"kind": "respond", "summary": "done"},
    ])
    monkeypatch.setattr(nodes, "_delegation_plan", lambda *args, **kwargs: next(plans))
    executed = []
    monkeypatch.setattr(nodes, "execute_tool", lambda *args, **kwargs: executed.append(args[1]) or {"tool": args[1], "status": "completed", "result": []})

    result = nodes.delegation_span(
        {"content": "List every customer", "thread_id": 1},
        resolve_delegation_scope("customer_records"),
    )

    assert result["delegation"]["decisions"] == [nodes.DELEGATION_TOOL_REFUSED]
    assert executed == []
