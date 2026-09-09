from types import SimpleNamespace

import pytest

from app.chat.assistant.tools.registry import (
    ToolValidationError,
    execute_tool,
    get_tool,
    tool_schemas,
)
from app.chat.assistant.tools.search import DuckDuckGoSearch


def test_registry_exposes_typed_bounded_tools():
    schemas = tool_schemas()
    assert "customers.search" in schemas
    assert schemas["customers.search"]["type"] == "object"
    assert get_tool("customers.search").read_only is True
    assert get_tool("automation.create_rule").read_only is False


def test_unknown_and_invalid_tools_are_rejected_before_execution():
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "not-a-tool", {})
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "customers.search", {"limit": 1000})


def test_write_requires_consumed_exact_approval(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.automation.create_rule",
        lambda *args, **kwargs: called.append((args, kwargs)),
    )
    args = {
        "name": "notify",
        "event_type": "case.created",
        "conditions": {},
        "channel": "email",
        "template_event": "case.created",
        "cooldown_seconds": 0,
    }
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "automation.create_rule", args)
    assert called == []
    approval = {
        "status": "consumed",
        "arguments_sha256": "wrong",
    }
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "automation.create_rule", args, approval=approval)
    assert called == []


def test_web_search_is_bounded_and_failures_are_empty():
    html = "".join(
        f'<a class="result__a" href="https://example.test/{n}">{"x" * 2000}</a>'
        for n in range(8)
    )

    class Client:
        def get(self, _url):
            return type("Response", (), {"text": html, "raise_for_status": lambda self: None})()

    results = DuckDuckGoSearch(Client()).search("safe query", limit=99)
    assert len(results) == 5
    assert all(len(result["title"]) <= 1000 for result in results)
