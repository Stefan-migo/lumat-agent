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


def test_valid_delegate_scope_is_explicitly_not_executable_yet():
    from app.chat.assistant.nodes import PANEL_DELEGATION_UNAVAILABLE, guardrails

    result = guardrails(
        {
            "content": "Which customers have open cases?",
            "planner": {"valid": True},
            "plan": {
                "kind": "delegate",
                "sub_agent": "customer_records",
                "summary": "Gather customer and case records.",
            },
        }
    )

    assert result["guardrails"]["decision"] == "delegate_unavailable"
    assert result["guardrails"]["scope_valid"] is True
    assert result["status"] == "completed"
    assert result["response"] == PANEL_DELEGATION_UNAVAILABLE


def test_valid_delegate_scope_routes_terminally_instead_of_answering_without_evidence():
    from langgraph.graph import END

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
    assert _after_guardrails(state) == END


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


def test_planner_prompt_does_not_advertise_unavailable_delegation():
    prompt = (Path(__file__).resolve().parents[2] / "agent" / "prompts" / "assistant_plan.md").read_text()

    assert 'kind: "delegate"' not in prompt
    assert "sub_agent: \"customer_records\"" not in prompt


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
