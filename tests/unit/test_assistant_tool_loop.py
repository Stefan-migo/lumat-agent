"""Contracts for narrating a completed panel assistant tool call."""

import json
from types import SimpleNamespace

import pytest

from app.chat.assistant.graph import END, _after_execute, _after_guardrails, _after_tool_loop, build_assistant_graph, run_assistant
from app.chat.assistant.nodes import (
    MAX_ASSISTANT_TOOL_STEPS,
    PANEL_LOOP_WRITE_REFUSAL,
    _TOOL_EVIDENCE_LIMIT,
    _context_text,
    execute,
    guardrails,
    plan_llm,
    tool_loop_head,
)


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
    planner_calls = [call for call in calls if not call.get("stream")]
    planner_prompt = planner_calls[-1]["messages"][-1]["content"]
    responder_prompt = calls[-1]["messages"][-1]["content"]
    assert '"customers.search"' in planner_prompt
    assert responder_prompt.count('[{"evidence": "customers.search"}]') == 1
    assert responder_prompt.count('[{"evidence": "memory.search"}]') == 1


def test_chained_turn_publishes_planning_after_first_execution(monkeypatch):
    calls = []
    stages = []
    plans = [
        '{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"Find Ana","requires_approval":false,"follow_up":true}',
        '{"kind":"tool","tool":"memory.search","arguments":{"query":"Ana"},"summary":"Find memory","requires_approval":false,"follow_up":true}',
    ]
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, tool_name, *_args, **_kwargs: {
            "tool": tool_name,
            "status": "completed",
            "result": [{"evidence": tool_name}],
        },
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    run_assistant(
        thread_id=7,
        user_id=1,
        content="Find Ana",
        run_id="run-stage-loop",
        on_token=lambda _token: None,
        on_stage=stages.append,
    )

    first_executing = stages.index("executing")
    assert "planning" in stages[first_executing + 1:]


def test_replan_keeps_newest_tool_evidence_within_budget(monkeypatch):
    calls = []
    marker = "NEWEST_RESULT_MARKER"
    plans = ['{"kind":"respond","tool":null,"arguments":{},"summary":"Done","requires_approval":false}']

    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    plan_llm(
        {
            "content": "Find Ana",
            "context": {"items": [], "meta": {}},
            "tool_results": [
                {"result": [{"evidence": "customers.search", "payload": "x" * 10_000}]},
                {"result": [{"evidence": "memory.search", "marker": marker}]},
            ],
        }
    )

    evidence = calls[-1]["messages"][-1]["content"].split("Prior tool evidence:\n", 1)[1]
    assert marker in evidence
    assert "1 earlier tool result(s) omitted" in evidence
    assert len(evidence) <= _TOOL_EVIDENCE_LIMIT


def test_replan_marker_never_cuts_the_newest_result(monkeypatch):
    calls = []
    marker = "NEWEST_RESULT_MARKER"
    plans = ['{"kind":"respond","tool":null,"arguments":{},"summary":"Done","requires_approval":false}']

    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    # The middle result fills the budget almost exactly and the oldest is dropped, so the
    # omission marker gets prepended. Budgeting it outside the limit made the final cut
    # remove the newest result instead of older evidence.
    plan_llm(
        {
            "content": "Find Ana",
            "context": {"items": [], "meta": {}},
            "tool_results": [
                {"result": [{"evidence": "kb.retrieve", "pad": "o" * 10_000}]},
                {"result": [{"evidence": "customers.search", "pad": "m" * 3_870}]},
                {"result": [{"evidence": "memory.search", "tail": marker}]},
            ],
        }
    )

    evidence = calls[-1]["messages"][-1]["content"].split("Prior tool evidence:\n", 1)[1]
    assert marker in evidence
    assert "earlier tool result(s) omitted" in evidence
    assert len(evidence) <= _TOOL_EVIDENCE_LIMIT


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


def test_cap_is_recorded_only_when_follow_up_is_still_requested():
    completed_state = _tool_state(
        tool_steps=MAX_ASSISTANT_TOOL_STEPS,
        plan={**_tool_state()["plan"], "follow_up": False},
    )

    result = tool_loop_head(completed_state)

    assert "cap_reached" not in result
    assert result["status"] == "completed"

    capped_state = _tool_state(
        tool_steps=MAX_ASSISTANT_TOOL_STEPS,
        plan={**_tool_state()["plan"], "follow_up": True},
    )

    result = tool_loop_head(capped_state)

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


@pytest.mark.parametrize("flipped_mode", ["conservative", "blocked"])
def test_cost_mode_flip_stops_loop_before_second_planner(monkeypatch, flipped_mode):
    calls = []
    handler_calls = []
    cost_calls = 0
    plans = [
        '{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"Find Ana","requires_approval":false,"follow_up":true}',
        '{"kind":"tool","tool":"memory.search","arguments":{"query":"Ana"},"summary":"Find memory","requires_approval":false,"follow_up":true}',
    ]

    def thread_cost(_session, _thread_id):
        nonlocal cost_calls
        cost_calls += 1
        return (0.0, "normal") if cost_calls == 1 else (100.0, flipped_mode)

    monkeypatch.setattr("app.chat.assistant.graph.assemble_context_node", lambda _state: {"context": {"items": [], "meta": {}}})
    monkeypatch.setattr("app.chat.assistant.nodes.internal_thread_cost_state", thread_cost)
    monkeypatch.setattr("app.chat.assistant.nodes.daily_cost_state", lambda _session: (0.0, "normal"))
    monkeypatch.setattr("app.chat.assistant.nodes.maybe_alert_owner", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.chat.assistant.nodes.internal_thread_spend", lambda *args: 0.0)
    monkeypatch.setattr("app.chat.assistant.nodes.daily_spend", lambda *args: 0.0)
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, tool_name, *_args, **_kwargs: handler_calls.append(tool_name)
        or {"tool": tool_name, "status": "completed", "result": [{"evidence": "Ana"}]},
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    final = run_assistant(
        thread_id=7,
        user_id=1,
        content="Find Ana",
        run_id=f"run-cost-{flipped_mode}",
        session=SimpleNamespace(),
        on_token=lambda _token: None,
    )

    assert handler_calls == ["customers.search"]
    assert len([call for call in calls if not call.get("stream")]) == 1
    assert final["response"] == "Ana is a customer"
    assert final["guardrails"]["decision"] == "loop_cost_stopped"


def test_sessionless_normal_cost_mode_keeps_two_step_chain(monkeypatch):
    calls = []
    handler_calls = []
    plans = [
        '{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"Find Ana","requires_approval":false,"follow_up":true}',
        '{"kind":"tool","tool":"memory.search","arguments":{"query":"Ana"},"summary":"Find memory","requires_approval":false,"follow_up":true}',
    ]
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, tool_name, *_args, **_kwargs: handler_calls.append(tool_name)
        or {"tool": tool_name, "status": "completed", "result": [{"evidence": tool_name}]},
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    run_assistant(thread_id=7, user_id=1, content="Find Ana", run_id="run-normal", on_token=lambda _token: None)

    assert handler_calls == ["customers.search", "memory.search"]
    assert len([call for call in calls if not call.get("stream")]) == 2


def test_autonomous_write_turn_does_not_chain(monkeypatch):
    calls = []
    handler_calls = []
    plans = [
        json.dumps(
            {
                "kind": "tool",
                "tool": "memory.write",
                "arguments": {"titulo": "N", "contenido": "Content", "topic_key": "agent:test", "tipo": "discovery"},
                "summary": "Write memory",
                "requires_approval": False,
                "follow_up": True,
            }
        ),
        '{"kind":"tool","tool":"memory.search","arguments":{"query":"Ana"},"summary":"Find memory","requires_approval":false,"follow_up":true}',
    ]
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, name, *_args, **_kwargs: handler_calls.append(name)
        or {"tool": name, "status": "completed", "result": [{"name": "Ana"}]},
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    run_assistant(
        thread_id=7, user_id=1, content="Save Ana", run_id="run-write-close", on_token=lambda _token: None
    )

    assert handler_calls == ["memory.write"]
    assert len([call for call in calls if not call.get("stream")]) == 1


def test_read_only_tool_with_follow_up_still_chains():
    state = _tool_state(tool_steps=1, plan={**_tool_state()["plan"], "follow_up": True})

    result = tool_loop_head(state)

    assert result["status"] == "planned"
    assert _after_tool_loop(result) == "plan_llm"


def test_step_two_write_plan_is_refused_by_guardrails():
    state = _tool_state(
        tool_steps=1,
        plan={
            "kind": "tool", "tool": "memory.write",
            "arguments": {"titulo": "N", "contenido": "Content", "topic_key": "agent:test", "tipo": "discovery"},
            "summary": "Write memory", "requires_approval": True, "follow_up": False,
        },
    )

    result = guardrails(state)

    assert result["status"] == "completed"
    assert result["approval"] is None
    assert result["guardrails"]["decision"] == "loop_write_refused"
    assert result["response"] == PANEL_LOOP_WRITE_REFUSAL


@pytest.mark.parametrize(
    "tool_name,arguments",
    [
        (
            "memory.write",
            {
                "titulo": "N",
                "contenido": "Content",
                "topic_key": "agent:test",
                "tipo": "discovery",
            },
        ),
        (
            "automation.create_rule",
            {
                "name": "N",
                "event_type": "appointment.created",
                "conditions": {},
                "channel": "whatsapp",
                "template_event": "reminder",
                "cooldown_seconds": 0,
            },
        ),
    ],
)
@pytest.mark.parametrize("follow_up", [True, False])
def test_graph_refuses_step_two_write_before_execution_or_approval(
    monkeypatch, tool_name, arguments, follow_up
):
    calls = []
    handler_calls = []
    plans = [
        '{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"Find Ana","requires_approval":false,"follow_up":true}',
        json.dumps({
            "kind": "tool",
            "tool": tool_name,
            "arguments": arguments,
            "summary": "Write",
            "requires_approval": True,
            "follow_up": follow_up,
        }),
    ]
    issued = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, name, *_args, **_kwargs: handler_calls.append(name)
        or {"tool": name, "status": "completed", "result": [{"name": "Ana"}]},
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "app.chat.assistant.approval.issue_approval",
        lambda plan: issued.append(plan) or {"status": "pending"},
    )
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    final = run_assistant(
        thread_id=7, user_id=1, content="Find Ana", run_id="run-write-refusal", on_token=lambda _token: None
    )

    assert handler_calls == ["customers.search"]
    assert final["response"] == PANEL_LOOP_WRITE_REFUSAL
    assert final.get("approval") is None
    assert issued == []
    assert [call for call in calls if call.get("stream")] == []
    assert _after_guardrails({**final, "guardrails": {"decision": "loop_write_refused"}}) == END


def test_single_autonomous_write_executes_without_loop_refusal(monkeypatch):
    calls = []
    handler_calls = []
    plans = [
        '{"kind":"tool","tool":"memory.write","arguments":{"titulo":"N","contenido":"Content","topic_key":"agent:test","tipo":"discovery"},"summary":"Write","requires_approval":false,"follow_up":false}',
    ]
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, name, *_args, **_kwargs: handler_calls.append(name)
        or {"tool": name, "status": "completed", "result": [{"written": True}]},
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    final = run_assistant(
        thread_id=7, user_id=1, content="Save this", run_id="run-single-write", on_token=lambda _token: None
    )

    assert handler_calls == ["memory.write"]
    assert final["guardrails"]["decision"] == "execute"


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
