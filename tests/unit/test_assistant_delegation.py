"""Trust-boundary tests for delegated assistant plans."""

from dataclasses import replace
from pathlib import Path

import pytest


CUSTOMER_RECORD_TOOLS = (
    "customers.search",
    "conversations.search",
    "appointments.upcoming",
    "cases.list",
    "customers.operational_history",
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


def test_panel_planner_catalog_matches_pre_delegation_bytes():
    import hashlib

    from app.chat.assistant.nodes import _planner_tool_catalog
    from app.services.prompts import load_assistant_config

    config = load_assistant_config()
    catalog = _planner_tool_catalog(list(config.tools_whitelist))

    # SHA-256 of the serialized assistant catalog at the post-tool-catalog-trim
    # baseline, plus the planning-facilitator, unit-2 conversation-inspection,
    # unit-3 settings.update, the planning read-report tools, view_image, the
    # read_project_file offset/limit paging fields, and the T3/T4 appointment
    # recipes (appointment_reminder, appointment_followup,
    # appointment_followup_no_show) in automation.create_rule's recipe list.
    assert hashlib.sha256(catalog.encode("utf-8")).hexdigest() == (
        "c73d185ddbcaf0de35b2385f53fa98d65e334f008dd25857fddf26b6b58994e4"
    )


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

    state = {"content": "Which customers have open cases?", "actor_role": "admin", "plan": {"kind": "delegate", "sub_agent": "customer_records"}, **result}
    assert graph._after_guardrails(state) == "delegation_span"
    wired = nodes.delegation_node(state)
    assert wired["delegation"]["steps"] == 1
    assert wired["tool_steps"] == 1
    assert wired["status"] == "completed"
    assert wired["tool_results"][0]["result"] == [{"name": "Ana"}]
    assert wired["evidence"]


def test_customer_drilldown_chain_uses_two_step_span_cap(monkeypatch):
    from app.chat.assistant import graph, nodes

    plans = iter([
        nodes.PlannerOutput(
            kind="tool", tool="customers.search", arguments={"query": "Ana"},
            summary="Find the customer.", requires_approval=False,
        ),
        nodes.PlannerOutput(
            kind="tool", tool="customers.operational_history", arguments={"customer_id": 42},
            summary="Read the customer's operational history.", requires_approval=False,
        ),
        nodes.PlannerOutput(kind="respond", summary="Evidence gathered."),
    ])
    planner_states = []

    def plan(state, _scope):
        planner_states.append({**state, "tool_results": list(state["tool_results"])})
        return next(plans)

    executed = []

    def execute_tool(_session, tool_name, arguments, **_kwargs):
        executed.append((tool_name, arguments, _kwargs["role"]))
        return {
            "tool": tool_name,
            "status": "completed",
            "result": {"source": tool_name, "customer_id": 42},
        }

    monkeypatch.setattr(nodes, "_delegation_plan", plan)
    monkeypatch.setattr(nodes, "execute_tool", execute_tool)
    validated = nodes.guardrails({
        "content": "Show Ana's cases and appointments.",
        "planner": {"valid": True},
        "plan": {"kind": "delegate", "sub_agent": "customer_records", "summary": "Gather."},
    })
    state = {
        "content": "Show Ana's cases and appointments.",
        "actor_role": "admin",
        "plan": {"kind": "delegate", "sub_agent": "customer_records"},
        **validated,
    }

    assert graph._after_guardrails(state) == "delegation_span"
    result = nodes.delegation_node(state)

    assert result["delegation"]["steps"] == 2
    assert result["delegation"]["cap"] == 2
    assert result["delegation"]["cap_reached"] is True
    assert executed == [
        ("customers.search", {"query": "Ana"}, "admin"),
        ("customers.operational_history", {"customer_id": 42}, "admin"),
    ]
    assert result["tool_results"][0]["provenance"]["step"] == 1
    assert result["tool_results"][1]["provenance"]["step"] == 2
    assert result["tool_results"][0]["result"]["source"] == "customers.search"
    assert result["tool_results"][1]["result"]["source"] == "customers.operational_history"
    assert len(result["evidence"]) == 2
    assert len(planner_states) == 2
    assert planner_states[1]["tool_results"] == [result["tool_results"][0]]


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


def test_guardrails_carries_a_complete_scope_including_memory_scope():
    """The scope guardrails validated must travel complete, or the node loses memory scope."""
    from app.chat.assistant.nodes import guardrails

    result = guardrails(
        {
            "content": "Gather records",
            "planner": {"valid": True},
            "plan": {"kind": "delegate", "sub_agent": "customer_records", "summary": "Gather."},
        }
    )

    carried = result["delegation"]
    assert carried["key"] == "customer_records"
    assert set(carried["tools_whitelist"]) == set(CUSTOMER_RECORD_TOOLS)
    assert carried["persona"]
    assert carried["memoria_scope"] == "customer"


def test_delegation_node_uses_the_guardrail_validated_scope_without_re_resolving(monkeypatch):
    """R3-001: the registry or persona can stop resolving between guardrails and the node.

    The node must consume the scope guardrails already validated instead of resolving it
    again, so a resolver failure can no longer escape the turn.
    """
    from app.chat.assistant import delegation, nodes

    plans = iter([
        nodes.PlannerOutput(
            kind="tool", tool="customers.search", arguments={"query": "open cases"},
            summary="Gather customer evidence.", requires_approval=False,
        ),
        nodes.PlannerOutput(kind="respond", summary="Done."),
    ])
    monkeypatch.setattr(nodes, "_delegation_plan", lambda *args, **kwargs: next(plans))
    monkeypatch.setattr(nodes, "execute_tool", lambda *args, **kwargs: {
        "tool": "customers.search", "status": "completed", "result": [{"name": "Ana"}],
    })
    validated = nodes.guardrails(
        {
            "content": "Which customers have open cases?",
            "planner": {"valid": True},
            "plan": {"kind": "delegate", "sub_agent": "customer_records", "summary": "Gather."},
        }
    )
    state = {
        "content": "Which customers have open cases?",
        "plan": {"kind": "delegate", "sub_agent": "customer_records"},
        **validated,
    }

    def _registry_broke_after_guardrails(*args, **kwargs):
        raise delegation.DelegationScopeError("registry became unresolvable after guardrails")

    monkeypatch.setattr(delegation, "resolve_delegation_scope", _registry_broke_after_guardrails)

    wired = nodes.delegation_node(state)

    assert wired["status"] == "completed"
    assert wired["delegation"]["steps"] == 1
    assert wired["tool_steps"] == 1
    assert wired["tool_results"][0]["result"] == [{"name": "Ana"}]
    assert wired["evidence"]


def test_delegation_node_preserves_the_customer_memory_scope_from_carried_state(monkeypatch):
    """Regression guard: the carried scope must still enforce the worker's memory scope."""
    from app.chat.assistant import nodes

    plans = iter([
        {"kind": "tool", "tool": "memory.read", "arguments": {"scope": "own"}, "summary": "own", "requires_approval": False},
        {"kind": "respond", "summary": "done"},
    ])
    monkeypatch.setattr(nodes, "_delegation_plan", lambda *args, **kwargs: next(plans))
    executed = []
    monkeypatch.setattr(
        nodes, "execute_tool",
        lambda *args, **kwargs: executed.append(args[1]) or {"tool": args[1], "status": "completed", "result": []},
    )
    validated = nodes.guardrails(
        {
            "content": "What do I know?",
            "planner": {"valid": True},
            "plan": {"kind": "delegate", "sub_agent": "customer_records", "summary": "Gather."},
        }
    )
    state = {"content": "What do I know?", "plan": {"kind": "delegate", "sub_agent": "customer_records"}, **validated}

    wired = nodes.delegation_node(state)

    assert nodes.DELEGATION_MEMORY_SCOPE_REFUSED in wired["delegation"]["decisions"]
    assert executed == []


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


def test_delegation_planner_accounts_for_llm_usage(monkeypatch):
    from types import SimpleNamespace

    from app.chat.assistant import nodes
    from app.chat.assistant.delegation import resolve_delegation_scope

    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"kind":"respond","summary":"Done."}'))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=2),
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: completion)))
    monkeypatch.setattr(nodes, "_assistant_client", lambda: client)
    records = []
    monkeypatch.setattr(nodes, "_record_usage", lambda *args: records.append(args))

    nodes._delegation_plan({"content": "Gather", "run_id": "run-1"}, resolve_delegation_scope("customer_records"))

    assert len(records) == 1
    assert records[0][1] == "delegation:customer_records"
    assert records[0][2] is completion
