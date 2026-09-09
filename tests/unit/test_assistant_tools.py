from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.chat.assistant.tools.registry import (
    ToolValidationError,
    execute_tool,
    get_tool,
    tool_schemas,
)
from app.chat.assistant.tools.search import DuckDuckGoSearch, SearchFailure


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
    html = "<html><body>" + "".join(
        f'<a class="result__a" href="https://example.test/{n}">{"x" * 2000}</a>'
        for n in range(8)
    ) + "</body></html>"

    class Client:
        def get(self, _url):
            return type("Response", (), {"text": html, "raise_for_status": lambda self: None})()

    results = DuckDuckGoSearch(Client()).search("safe query", limit=99)
    assert len(results) == 5
    assert all(len(result["title"]) <= 1000 for result in results)


def test_conversations_and_appointments_use_service_seams(monkeypatch):
    conversation = SimpleNamespace(id=1)
    appointment = SimpleNamespace(id=2, starts_at=datetime.now(timezone.utc) + timedelta(days=1))
    monkeypatch.setattr(
        "app.services.conversations.list_conversations",
        lambda session, query, limit: [conversation],
    )
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.scheduling.list_for_range",
        lambda *args, **kwargs: [(appointment, None, None, None, None)],
    )
    assert execute_tool(SimpleNamespace(), "conversations.search", {"query": "a"})["result"] == [{"id": 1}]
    assert execute_tool(SimpleNamespace(), "appointments.upcoming", {})["result"][0]["id"] == 2


def test_memory_read_is_bounded_and_uses_memory_service(monkeypatch):
    memories = [SimpleNamespace(id=index, topic_key="topic") for index in range(30)]
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.list_for_entity",
        lambda *args, **kwargs: memories,
    )
    result = execute_tool(
        SimpleNamespace(),
        "memory.read",
        {"scope": "customer", "entity_id": "42", "topic": "topic", "limit": 5},
    )
    assert result["status"] == "completed"
    assert len(result["result"]) == 5


def test_websearch_failure_is_error_evidence(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.websearch.search",
        lambda *args, **kwargs: (_ for _ in ()).throw(SearchFailure("timeout")),
    )
    result = execute_tool(SimpleNamespace(), "web.search", {"query": "status"})
    assert result["status"] == "error"
    assert result["evidence"]["status"] == "error"
    assert result["evidence"]["reason"] == "timeout"


def test_websearch_malformed_response_is_failure():
    class Client:
        def get(self, _url):
            return type(
                "Response",
                (),
                {
                    "text": "<html><body><a class='result__a' href='javascript:alert(1)'>unsafe</a></body></html>",
                    "raise_for_status": lambda self: None,
                },
            )()

    with pytest.raises(SearchFailure, match="unsafe"):
        DuckDuckGoSearch(Client()).search("unsafe")


def test_approval_failure_records_error_evidence_before_raising(monkeypatch):
    from app.chat.assistant.nodes import execute

    state = {
        "thread_id": 4,
        "run_id": "run-4",
        "plan": {"tool": "automation.create_rule", "arguments": {}, "requires_approval": True},
        "approval": None,
        "evidence": [],
        "session": SimpleNamespace(),
    }
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    with pytest.raises(PermissionError, match="approval") as caught:
        execute(state)
    assert state["evidence"][0]["status"] == "error"
    assert "approval" in state["evidence"][0]["detail"]
    assert caught.value.evidence[0]["status"] == "error"
