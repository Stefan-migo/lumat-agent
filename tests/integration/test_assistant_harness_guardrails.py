"""Ordered assistant guardrail contracts for typed tool execution."""

from types import SimpleNamespace

import pytest

from app.chat.assistant.approval import issue_approval
from app.chat.assistant.nodes import execute, panel_cost_gate, plan_llm
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool


def _rule_args():
    return {
        "name": "notify",
        "event_type": "case.created",
        "conditions": {},
        "channel": "email",
        "template_event": "case.created",
        "cooldown_seconds": 0,
    }


def test_whitelist_rejects_before_handler(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.customers.search_customers",
        lambda *args: called.append(args),
    )
    with pytest.raises(ToolValidationError, match="not whitelisted"):
        execute_tool(SimpleNamespace(), "customers.search", {"query": "Ana"}, whitelist=set())
    assert called == []


def test_typed_arguments_reject_before_handler(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.customers.search_customers",
        lambda *args: called.append(args),
    )
    with pytest.raises(ToolValidationError, match="invalid arguments"):
        execute_tool(
            SimpleNamespace(),
            "customers.search",
            {"query": "Ana", "limit": 999},
            whitelist={"customers.search"},
        )
    assert called == []


def test_cost_guard_rejects_before_handler(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.customers.search_customers",
        lambda *args: called.append(args),
    )
    with pytest.raises(ToolValidationError, match="cost"):
        execute_tool(
            SimpleNamespace(),
            "customers.search",
            {"query": "Ana"},
            whitelist={"customers.search"},
            cost_allowed=False,
        )
    assert called == []


def test_write_requires_exact_consumed_approval_before_handler(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.automation.create_rule",
        lambda *args, **kwargs: called.append((args, kwargs)),
    )
    approval = issue_approval({"tool": "automation.create_rule", "arguments": _rule_args()})
    with pytest.raises(ToolValidationError, match="approval"):
        execute_tool(
            SimpleNamespace(),
            "automation.create_rule",
            {**_rule_args(), "name": "tampered"},
            whitelist={"automation.create_rule"},
            approval={**approval, "status": "consumed"},
        )
    assert called == []


def test_execution_audits_before_evidence(monkeypatch):
    order = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: order.append("handler") or {
            "tool": "customers.search", "status": "completed", "result": [{"id": 1}]
        },
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: order.append("audit"))
    result = execute(
        {
            "thread_id": 1,
            "run_id": "run-1",
            "plan": {
                "kind": "tool",
                "tool": "customers.search",
                "arguments": {"query": "Ana"},
                "requires_approval": False,
            },
            "session": SimpleNamespace(),
            "evidence": [],
        }
    )
    assert order == ["handler", "audit"]
    assert result["evidence"][0]["status"] == "completed"
    assert result["status"] == "completed"


def test_cost_gate_injects_conservative_directive_after_context(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.nodes.internal_thread_cost_state",
        lambda session, thread_id: (80.0, "conservative"),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes.daily_cost_state",
        lambda session: (0.0, "normal"),
    )
    monkeypatch.setattr("app.chat.assistant.nodes.maybe_alert_owner", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.chat.assistant.nodes.internal_thread_spend", lambda *args: 1.2)
    monkeypatch.setattr("app.chat.assistant.nodes.daily_spend", lambda *args: 0.0)
    state = panel_cost_gate({"thread_id": 7, "session": SimpleNamespace(), "content": "Explain this"})

    assert state["cost_mode"] == "conservative"
    assert "Answer concisely" in state["cost_directive"]


def test_cost_gate_blocked_never_invokes_planner(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.nodes.internal_thread_cost_state",
        lambda session, thread_id: (100.0, "blocked"),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes.daily_cost_state",
        lambda session: (0.0, "normal"),
    )
    monkeypatch.setattr("app.chat.assistant.nodes.maybe_alert_owner", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.chat.assistant.nodes.internal_thread_spend", lambda *args: 1.5)
    monkeypatch.setattr("app.chat.assistant.nodes.daily_spend", lambda *args: 0.0)
    monkeypatch.setattr(
        "app.chat.assistant.nodes.plan_llm",
        lambda state: (_ for _ in ()).throw(AssertionError("planner must not run")),
    )

    result = panel_cost_gate({"thread_id": 7, "session": SimpleNamespace(), "content": "Explain this"})

    assert result["cost_mode"] == "blocked"
    assert result["response"] == (
        "The assistant is temporarily unavailable because the configured usage "
        "limit was reached. Please review cost settings."
    )


def test_conservative_directive_is_added_to_planner_user_prompt(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(
            prompts={"plan": "{{user_input}} {{available_tools}} {{context}}"},
            tools_whitelist=[], persona="persona",
        ),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content='{"kind":"respond","summary":"done"}',
                ))],
            ),
        ))),
    )

    plan_llm({
        "content": "Explain this", "context": {"items": []},
        "cost_mode": "conservative",
        "cost_directive": "Answer concisely; use the minimum necessary context and avoid optional tool calls.",
    })

    assert "Answer concisely" in calls[0]["messages"][-1]["content"]
