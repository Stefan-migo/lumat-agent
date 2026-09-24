"""Contracts for narrating a completed panel assistant tool call."""

from types import SimpleNamespace

import pytest

from app.chat.assistant.graph import _after_execute, _after_tool_loop, build_assistant_graph, run_assistant
from app.chat.assistant.nodes import MAX_ASSISTANT_TOOL_STEPS, _context_text, execute, tool_loop_head


def _tool_state(**overrides):
    state = {
        "thread_id": 7,
        "run_id": "run-tool-loop",
        "content": "Find Ana",
        "plan": {
            "kind": "tool",
            "tool": "customers.search",
            "arguments": {"query": "Ana"},
            "requires_approval": False,
        },
        "guardrails": {"cost_allowed": True},
        "evidence": [],
    }
    state.update(overrides)
    return state


def _client(calls, plans, text="Ana is a customer"):
    plan_index = 0

    def create(**kwargs):
        nonlocal plan_index
        calls.append(kwargs)
        if kwargs.get("stream"):
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])]
        plan = plans[plan_index]
        plan_index += 1
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=plan))])

    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create)
        )
    )


def _streaming_client(calls, text="Ana is a customer"):
    return _client(calls, [], text)


def test_completed_tool_routes_through_opt_in_loop_head():
    graph = build_assistant_graph()
    edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}

    assert ("execute_tool", "tool_loop_head") in edges
    assert ("tool_loop_head", "plan_llm") in edges
    assert ("tool_loop_head", "respond_stream") in edges
    assert ("tool_loop_head", "assemble_context") not in edges
    assert ("tool_loop_head", "panel_cost_gate") not in edges
    assert ("tool_loop_head", "cortex_session_gate") not in edges
    assert ("tool_loop_head", "sdb_trigger_gate") not in edges


def test_opted_in_turn_executes_two_tools_and_narrates_combined_evidence(monkeypatch):
    calls = []
    handler_calls = []
    plans = [
        '{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"Find Ana","requires_approval":false,"follow_up":true}',
        '{"kind":"tool","tool":"memory.search","arguments":{"query":"Ana"},"summary":"Find memory","requires_approval":false,"follow_up":true}',
    ]
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, tool_name, *_args, **_kwargs: handler_calls.append(tool_name) or {
            "tool": tool_name,
            "status": "completed",
            "result": [{"evidence": tool_name}],
        },
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    final = run_assistant(
        thread_id=7, user_id=1, content="Find Ana", run_id="run-tool-loop", on_token=lambda _token: None
    )

    assert handler_calls == ["customers.search", "memory.search"]
    assert len([call for call in calls if not call.get("stream")]) == 2
    assert final["response"] == "Ana is a customer"
    assert '"customers.search"' in calls[-1]["messages"][-1]["content"]
    assert '"memory.search"' in calls[-1]["messages"][-1]["content"]


def test_cap_refuses_a_third_execution(monkeypatch):
    calls = []
    handler_calls = []
    plans = [
        '{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"Find Ana","requires_approval":false,"follow_up":true}',
        '{"kind":"tool","tool":"memory.search","arguments":{"query":"Ana"},"summary":"Find memory","requires_approval":false,"follow_up":true}',
        '{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"Find Ana again","requires_approval":false,"follow_up":true}',
    ]
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, tool_name, *_args, **_kwargs: handler_calls.append(tool_name)
        or {"tool": tool_name, "status": "completed", "result": [{"evidence": tool_name}]},
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    final = run_assistant(
        thread_id=7, user_id=1, content="Find Ana", run_id="run-cap", on_token=lambda _token: None
    )

    assert len(handler_calls) == MAX_ASSISTANT_TOOL_STEPS
    assert final["cap_reached"] is True

    state = _tool_state(tool_steps=MAX_ASSISTANT_TOOL_STEPS, plan={**_tool_state()["plan"], "follow_up": True})

    assert _after_tool_loop(state) == "respond_stream"
    result = tool_loop_head(state)
    assert result["cap_reached"] is True
    assert result["status"] == "completed"


def test_non_opted_in_turn_keeps_one_planner_call_and_one_execution(monkeypatch):
    calls = []
    handler_calls = []
    plans = ['{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"Find Ana","requires_approval":false}']
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, tool_name, *_args, **_kwargs: handler_calls.append(tool_name)
        or {"tool": tool_name, "status": "completed", "result": [{"name": "Ana"}]},
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    run_assistant(thread_id=7, user_id=1, content="Find Ana", run_id="run-single", on_token=lambda _token: None)

    assert handler_calls == ["customers.search"]
    assert len([call for call in calls if not call.get("stream")]) == 1


def test_step_two_write_plan_finishes_without_execution_or_approval():
    from app.chat.assistant.nodes import tool_loop_head

    state = _tool_state(
        tool_steps=1,
        plan={
            "kind": "tool", "tool": "memory.write", "arguments": {},
            "summary": "Write memory", "requires_approval": True, "follow_up": False,
        },
    )

    result = tool_loop_head(state)

    assert result["status"] == "completed"
    assert result["approval"] is None
    assert result["guardrails"]["decision"] == "loop_write_refused"


def test_single_tool_responder_receives_evidence_once_and_context_stays_clean(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: {
            "tool": "customers.search",
            "status": "completed",
            "result": [{"name": "Ana"}],
        },
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: _streaming_client(calls))

    first = execute(_tool_state())
    execute({**_tool_state(), **first, "on_token": lambda _token: None})

    prompt = calls[0]["messages"][-1]["content"]
    assert prompt.count('[{"name": "Ana"}]') == 1
    assert "Prior tool evidence" not in _context_text({**_tool_state(), **first})


def test_tool_evidence_is_bounded_and_prompt_statement_is_truthful(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: {
            "tool": "customers.search",
            "status": "completed",
            "result": [{"name": "Ana", "notes": "x" * 10_000}],
        },
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: _streaming_client(calls))

    first = execute(_tool_state())
    execute({**_tool_state(), **first, "on_token": lambda _token: None})

    prompt = calls[0]["messages"][-1]["content"]
    evidence = prompt.split("<tool_evidence>", 1)[1].split("</tool_evidence>", 1)[0]
    assert evidence
    assert len(evidence) <= 4_000
    assert "Ana" in evidence
    assert "Tool customers.search completed." not in prompt
    assert "already run" in prompt


@pytest.mark.parametrize("tool_name", ["memory.read", "memory.search"])
def test_failed_read_only_tool_degrades_without_exposing_raw_error(monkeypatch, tool_name):
    raw_error = "internal memory backend secret"
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: {
            "tool": tool_name,
            "status": "error",
            "read_only": True,
            "error": raw_error,
        },
    )

    result = execute(_tool_state(plan={**_tool_state()["plan"], "tool": tool_name}))

    assert result["status"] == "degraded"
    assert result["tool_result"]["result"] == {
        "unavailable": True,
        "tool": tool_name,
        "degraded_reason": "Read-only tool unavailable",
    }
    assert raw_error not in result.get("response", "")
    assert raw_error not in result["evidence"][0]["detail"]


def test_degraded_tool_routes_to_responder():
    assert _after_execute({"status": "degraded"}) == "tool_loop_head"


def test_degraded_read_evidence_reaches_responder(monkeypatch):
    calls = []
    raw_error = "internal memory backend secret"
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: {
            "tool": "memory.read",
            "status": "error",
            "read_only": True,
            "error": raw_error,
        },
    )
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: _streaming_client(calls, "I could not access memory."))

    first = execute(_tool_state(plan={**_tool_state()["plan"], "tool": "memory.read"}))
    final = execute({**_tool_state(), **first, "on_token": lambda _token: None})

    prompt = calls[0]["messages"][-1]["content"]
    evidence = prompt.split("<tool_evidence>", 1)[1].split("</tool_evidence>", 1)[0]
    assert final["response"] == "I could not access memory."
    assert '"unavailable": true' in evidence
    assert "memory.read" in evidence
    assert raw_error not in prompt


def test_failed_write_tool_remains_terminal_error(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: {
            "tool": "memory.write",
            "status": "error",
            "read_only": False,
            "error": "write failed",
        },
    )

    result = execute(_tool_state(plan={**_tool_state()["plan"], "tool": "memory.write"}))

    assert result["status"] == "error"
    assert result["response"] == "Tool execution failed: write failed"


def test_no_tool_prompt_keeps_non_invoking_statement(monkeypatch):
    calls = []
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: _streaming_client(calls, "Text reply"))

    execute(
        {
            "thread_id": 7,
            "run_id": "run-no-tool",
            "content": "Hello",
            "plan": {"kind": "respond", "tool": None, "arguments": {}, "requires_approval": False},
            "context": {"items": []},
            "on_token": lambda _token: None,
        }
    )

    prompt = calls[0]["messages"][-1]["content"]
    assert "cannot invoke" in prompt
    assert "must not emit tool-call markup" in prompt
