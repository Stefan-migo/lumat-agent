"""Ordered assistant guardrail contracts for typed tool execution."""

from types import SimpleNamespace

import pytest

from app.chat.assistant.approval import issue_approval
from app.chat.assistant.nodes import execute
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
