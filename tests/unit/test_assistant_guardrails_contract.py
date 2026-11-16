import json
from types import SimpleNamespace

import pytest

from app.chat.assistant.graph import run_assistant
from app.chat.assistant.state import ASSISTANT_STATE_KEYS
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool


SAFE_FAILURE = "No pude planificar esa solicitud de forma segura. Inténtalo nuevamente."


def _client(calls, plans, *, response="Read complete"):
    plan_index = 0

    def create(**kwargs):
        nonlocal plan_index
        calls.append(kwargs)
        if kwargs.get("stream"):
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=response))])]
        content = plans[plan_index]
        plan_index += 1
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def _read_plan(limit=6000, file_id=3, tool="read_project_file"):
    return json.dumps({
        "kind": "tool", "tool": tool, "arguments": {"file_id": file_id, "limit": limit},
        "summary": "Read file", "requires_approval": False,
    })


def test_unsafe_plan_is_repaired_and_executes(monkeypatch):
    calls = []
    executed = []
    plans = [_read_plan(tool="not_allowed"), _read_plan(120)]
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)
    monkeypatch.setattr("app.chat.assistant.nodes.execute_tool", lambda _s, name, args, **_kw: executed.append((name, args)) or {
        "tool": name, "status": "completed", "arguments": args, "result": {"text": "ok"},
    })
    final = run_assistant(thread_id=7, user_id=1, content="Read file", run_id="repair-ok", on_token=lambda _t: None)
    assert executed == [("read_project_file", {"file_id": 3, "limit": 120})]
    assert final["status"] == "completed"
    repair = [call for call in calls if not call.get("stream")]
    assert len(repair) == 2
    messages = repair[1]["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "assistant", "user"]
    assert "read_project_file" in messages[1]["content"]
    assert "customers.search" in messages[1]["content"]
    prompt = messages[-1]["content"]
    assert "whitelisted=false" in prompt
    assert "arguments_valid=false" in prompt
    assert "ONLY one JSON object" in prompt
    assert "plan_repair_attempted" not in ASSISTANT_STATE_KEYS


def test_second_unsafe_plan_ends_with_exact_fallback_after_one_repair(monkeypatch):
    calls = []
    executed = []
    client = _client(calls, [_read_plan(file_id=0), _read_plan(6000, file_id=0)])
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)
    monkeypatch.setattr("app.chat.assistant.nodes.execute_tool", lambda *_a, **_k: executed.append(True))
    final = run_assistant(thread_id=7, user_id=1, content="Read file", run_id="repair-fail", on_token=lambda _t: None)
    planner_calls = [call for call in calls if not call.get("stream")]
    assert len(planner_calls) == 2
    assert executed == []
    assert final["response"] == SAFE_FAILURE
    assert final["planner"]["failure"]["reason"] == "unsafe_plan"
    assert final["planner"]["failure"]["stage"] == "guardrails"


def test_guardrails_route_only_ends_when_repair_is_exhausted(monkeypatch):
    from langgraph.graph import END

    from app.chat.assistant.graph import _after_guardrails

    state = {
        "plan": {"kind": "respond"}, "status": "responding", "plan_repair_attempted": True,
        "guardrails": {"decision": "fallback"},
        "planner": {"failure": {"stage": "validation", "reason": "planner_output_validation_failed"}},
    }
    assert _after_guardrails(state) == "respond_stream"
    assert _after_guardrails({
        **state,
        "planner": {"failure": {"stage": "guardrails", "reason": "unsafe_plan"}},
    }) == END
    assert _after_guardrails({
        **state, "plan_repair_terminal": True,
        "planner": {"failure": {"stage": "provider", "reason": "provider_call_failed"}},
    }) == END


def test_in_range_plan_executes_without_repair(monkeypatch):
    calls = []
    executed = []
    client = _client(calls, [_read_plan(3890)])
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)
    monkeypatch.setattr("app.chat.assistant.nodes.execute_tool", lambda _s, name, args, **_kw: executed.append((name, args)) or {
        "tool": name, "status": "completed", "arguments": args, "result": {"text": "ok"},
    })
    final = run_assistant(thread_id=7, user_id=1, content="Read file", run_id="in-range", on_token=lambda _t: None)
    assert executed == [("read_project_file", {"file_id": 3, "limit": 3890})]
    assert len([call for call in calls if not call.get("stream")]) == 1
    assert final["status"] == "completed"
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "customers.search", {"limit": 999}, owner_id=1, role="admin")


def test_truncated_excerpt_never_invents_a_previous_plan(monkeypatch):
    """The persisted excerpt is bounded, so a long plan arrives cut: show none, never the fallback."""
    from app.chat.assistant.nodes import repair_plan

    calls = []
    client = _client(calls, [_read_plan(120)])
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)
    state = {
        "content": "Read file",
        "run_id": "truncated-excerpt",
        # Guardrails already replaced the rejected plan with the bounded fallback by the time the
        # repair runs, which is exactly why it cannot stand in for the model's previous answer.
        "plan": {"kind": "respond", "tool": None, "arguments": {}, "summary": SAFE_FAILURE},
        "guardrails": {"decision": "fallback", "whitelisted": True, "arguments_valid": False},
        "planner": {"valid": False, "failure": {
            "reason": "unsafe_plan", "stage": "guardrails",
            "raw_excerpt": '{"kind": "tool", "tool": "read_project_file", "arguments": {"file',
        }},
    }

    result = repair_plan(state)

    messages = calls[0]["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "user"]
    assert "Previous plan:" not in messages[-1]["content"]
    assert SAFE_FAILURE not in messages[-1]["content"]
    assert "whitelisted=true" in messages[-1]["content"]
    assert "arguments_valid=false" in messages[-1]["content"]
    assert "ONLY one JSON object" in messages[-1]["content"]
    assert result["plan_repair_attempted"] is True
    assert result["plan"]["arguments"] == {"file_id": 3, "limit": 120}
