"""Contracts for narrating a completed panel assistant tool call."""

import json
from types import SimpleNamespace

import pytest

from app.chat.assistant.graph import END, _after_cost_gate, _after_execute, _after_guardrails, _after_tool_loop, build_assistant_graph, run_assistant
from app.chat.assistant.nodes import (
    MAX_ASSISTANT_TOOL_STEPS,
    _TOOL_EVIDENCE_LIMIT,
    _context_text,
    execute,
    memory_bootstrap,
    guardrails,
    plan_llm,
    tool_loop_head,
    verify_effects,
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
    assert ("tool_loop_head", "respond_stream") not in edges
    assert ("tool_loop_head", "verify_effects") in edges
    assert ("verify_effects", "respond_stream") in edges
    assert ("tool_loop_head", "assemble_context") not in edges
    assert ("tool_loop_head", "panel_cost_gate") not in edges
    assert all(source != "cortex_turn" and target != "cortex_turn" for source, target in edges)


def test_memory_bootstrap_is_on_initial_plan_path_only():
    graph = build_assistant_graph()
    edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}

    assert ("panel_cost_gate", "memory_bootstrap") in edges
    assert ("memory_bootstrap", "plan_llm") in edges
    assert ("tool_loop_head", "memory_bootstrap") not in edges
    assert _after_cost_gate({"cost_mode": "blocked"}) == "evidence"
    assert _after_cost_gate({"cost_mode": "normal"}) == "memory_bootstrap"


def test_memory_bootstrap_adds_bounded_code_initiated_read_as_planner_evidence(monkeypatch):
    calls = []

    def read(_session, name, arguments, **kwargs):
        calls.append((name, arguments, kwargs))
        return {"tool": name, "status": "completed", "result": [{"contenido": "remembered"}]}

    monkeypatch.setattr("app.chat.assistant.nodes.execute_tool", read)
    state = {"thread_id": 7, "user_id": 2, "session": object(), "tool_results": [], "tool_steps": 0, "context": {"items": []}}
    result = memory_bootstrap(state)
    merged = {**state, **result}

    assert len(calls) == 1
    assert calls[0][0] == "memory.read"
    assert calls[0][1]["scope"] == "own"
    assert len(merged["tool_results"]) == 1
    assert merged["tool_results"][0]["code_initiated"] is True
    client = _client(calls, ['{"kind":"respond","tool":null,"arguments":{},"summary":"Done","requires_approval":false}'])
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)
    plan_llm({**merged, "content": "What do you remember?", "plan": None})
    assert "remembered" in calls[-1]["messages"][-1]["content"]
    assert merged.get("tool_steps", 0) == 0
    assert "tool_result" not in result
    assert "context" not in result
    monkeypatch.setattr("app.chat.assistant.nodes.run_verification", lambda **_kwargs: pytest.fail("read must not require verification"))
    assert verify_effects(merged) == {}


def test_memory_bootstrap_empty_and_missing_scope_are_noop(monkeypatch):
    from app.chat.assistant.nodes import assemble_context_node

    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *_args, **_kwargs: {"tool": "memory.read", "status": "completed", "result": []},
    )
    state = {"thread_id": 7, "user_id": 2, "session": object(), "tool_results": [], "context": {"items": []}, "status": "planned"}
    assert memory_bootstrap(state) == {}
    assert memory_bootstrap({**state, "session": None}) == {}
    assert memory_bootstrap({**state, "thread_id": None}) == {}
    assert "memory" not in assemble_context_node({"session": None, "context": {"items": [], "meta": {}}})["context"]


def test_memory_bootstrap_failure_does_not_change_turn_or_verification(monkeypatch):
    from app.chat.assistant.nodes import ToolExecutionError, ToolValidationError
    from app.chat.assistant.verification import verification_required

    for error in (ToolExecutionError("unavailable"), ToolValidationError("invalid")):
        def fail(*_args, _error=error, **_kwargs):
            raise _error

        monkeypatch.setattr("app.chat.assistant.nodes.execute_tool", fail)
        state = {"thread_id": 7, "user_id": 2, "session": object(), "tool_results": [], "tool_steps": 0, "status": "planned"}
        assert memory_bootstrap(state) == {}
        assert state["status"] == "planned"
        assert state["tool_steps"] == 0
        assert verification_required(dispatched_tools=["memory.read"]) == (False, "not-required")


def test_verify_effects_is_noop_without_gate(monkeypatch):
    monkeypatch.setattr("app.chat.assistant.nodes.run_verification", lambda **_kwargs: pytest.fail("unexpected verifier call"))
    assert verify_effects({"tool_results": [], "evidence": []}) == {}


def test_verify_effects_runs_for_memory_update_and_binds_read_only_executor(monkeypatch):
    captured = {}

    def verify(**kwargs):
        captured.update(kwargs)
        with pytest.raises(Exception):
            kwargs["tool_executor"]("project.create", {})
        return SimpleNamespace(status="failed", reason="not found")

    monkeypatch.setattr("app.chat.assistant.nodes.run_verification", verify)
    state = _tool_state(
        plan={"success_criterion": "Memory changed"},
        tool_results=[{"tool": "memory.update", "arguments": {"id": 4}, "result": {"status": "completed"}}],
        evidence=[{"tool": "memory.update", "status": "completed"}],
        session=object(), user_id=9, effective={"project_id": 12},
    )
    result = verify_effects(state)
    assert result["verification"] == {
        "required": True, "gate_reason": "effect-tool", "status": "failed", "detail": "not found"
    }
    assert captured["steps"] == state["tool_results"]


def test_verify_effects_runs_for_the_admin_handoff_signal(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.nodes.run_verification",
        lambda **_kwargs: SimpleNamespace(status="unverifiable", reason="no-observable-criterion"),
    )
    state = _tool_state(
        sdb_requested=True,
        tool_results=[{"tool": "assistant.capabilities", "arguments": {}, "result": {"tool_count": 1}}],
        evidence=[],
    )

    result = verify_effects(state)

    assert result["verification"] == {
        "required": True,
        "gate_reason": "handoff",
        "status": "unverifiable",
        "detail": "no-observable-criterion",
    }


@pytest.mark.parametrize("status", ["failed", "unverifiable"])
def test_failed_verification_qualification_is_deterministic_and_streamed(monkeypatch, status):
    calls = []
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: _streaming_client(calls, "Done"))
    state = _tool_state(
        status="completed", verification={"required": True, "status": status, "detail": "not visible"},
        tool_results=[{"tool": "memory.update", "arguments": {}, "result": {"status": "completed"}}],
        on_token=lambda token: calls.append(token),
    )
    result = execute(state)
    assert result["response"].endswith(f"verification: {status} — not visible")
    assert calls[-1] == f"\n\nThe effect ran. verification: {status} — not visible"


def test_confirmed_verification_has_no_qualification():
    result = execute(_tool_state(status="responding", verification={"required": True, "status": "confirmed", "detail": "ok"}))
    assert "verification:" not in result["response"].lower()


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

    assert _after_tool_loop(state) == "verify_effects"
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

    assert handler_calls == ["memory.read", "customers.search"]
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


def test_autonomous_write_turn_chains_in_loop(monkeypatch):
    """T2/S3: a class-B write that opted into a follow-up keeps the chain going with no
    approval prompt. U1's read-only-only loop is exactly what T2 reopens."""
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

    assert handler_calls == ["memory.write", "memory.search"]
    assert len([call for call in calls if not call.get("stream")]) == 2


def test_read_only_tool_with_follow_up_still_chains():
    state = _tool_state(tool_steps=1, plan={**_tool_state()["plan"], "follow_up": True})

    result = tool_loop_head(state)

    assert result["status"] == "planned"
    assert _after_tool_loop(result) == "plan_llm"


def test_step_two_write_plan_gets_its_own_approval(monkeypatch):
    """T2/S2: a class-A write at step 2+ no longer ends the turn; it pauses with a fresh
    approval bound to its own arguments."""
    monkeypatch.setattr("app.chat.assistant.nodes._effective_tools", lambda _state: {"automation.create_rule"})
    state = _tool_state(
        tool_steps=1,
        plan={
            "kind": "tool", "tool": "automation.create_rule",
            "arguments": {"recipe_id": "appointment_confirmation", "parameters": {"channel": "whatsapp"}},
            "summary": "Create rule", "requires_approval": True, "follow_up": False,
        },
    )

    result = guardrails(state)

    assert result["status"] == "approval_pending"
    assert result["guardrails"]["decision"] == "approval_pending"
    assert result["guardrails"]["approval_required"] is True
    assert result["approval"]["status"] == "pending"
    assert result["approval"]["tool"] == "automation.create_rule"


def test_global_skill_name_collision_is_audited_and_never_issues_approval(monkeypatch):
    audited = []
    monkeypatch.setattr("app.chat.assistant.nodes._effective_tools", lambda _state: {"skill.propose"})
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: audited.append(kwargs))
    state = _tool_state(
        session=object(),
        plan={"kind": "tool", "tool": "skill.propose", "arguments": {
            "name": "memoria-tukulpan", "description": "D", "body": "B",
        }},
    )

    result = guardrails(state)

    assert result["status"] == "completed"
    assert result["approval"] is None
    assert result["guardrails"]["decision"] == "skill_shadow_refused"
    assert audited[0]["action"] == "skill.propose.rejected"


def test_valid_skill_proposal_is_gated_by_existing_approval_flow(monkeypatch):
    monkeypatch.setattr("app.chat.assistant.nodes._effective_tools", lambda _state: {"skill.propose"})
    state = _tool_state(plan={
        "kind": "tool", "tool": "skill.propose",
        "arguments": {"name": "local-guide", "description": "Project guide", "body": "Use grounded data."},
    })

    result = guardrails(state)

    assert result["status"] == "approval_pending"
    assert result["approval"]["status"] == "pending"
    assert result["approval"]["tool"] == "skill.propose"


def test_rejecting_skill_proposal_audits_without_executing(monkeypatch):
    from app.chat.assistant.approval import issue_approval
    from app.services import agent_chat

    plan = {"tool": "skill.propose", "arguments": {"name": "local", "description": "D", "body": "B"}}
    approval = issue_approval(plan)
    audits = []
    message = SimpleNamespace(status="processed")
    thread = SimpleNamespace(id=9, active_run_id="run", current_plan=plan, assistant_state={"approval": approval})

    class Session:
        def execute(self, *_args, **_kwargs):
            return SimpleNamespace(scalar_one_or_none=lambda: 9)

        def refresh(self, _thread):
            pass

        def scalar(self, _query):
            return message

        def flush(self):
            pass

    monkeypatch.setattr(agent_chat, "record_audit", lambda session, **kwargs: audits.append(kwargs))
    result = agent_chat.approve_plan(Session(), thread, SimpleNamespace(username="admin", role="admin"), "run", approval["token"], reject=True)

    assert result is message
    assert message.status == "rejected"
    assert [item["action"] for item in audits] == ["internal_chat.approval_rejected", "skill.propose.rejected"]


def test_graph_pauses_step_two_class_a_write_for_its_own_approval(monkeypatch):
    """T2/S1+S2: the chain reaches the second step inside the same turn, and that step's
    class-A write pauses with a fresh approval instead of ending the turn."""
    calls = []
    handler_calls = []
    plans = [
        '{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"Find Ana","requires_approval":false,"follow_up":true}',
        json.dumps({
            "kind": "tool",
            "tool": "automation.create_rule",
            "arguments": {"recipe_id": "appointment_confirmation", "parameters": {"channel": "whatsapp"}},
            "summary": "Write",
            "requires_approval": True,
            "follow_up": False,
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
        thread_id=7, user_id=1, content="Find Ana", run_id="run-write-chain", on_token=lambda _token: None
    )

    assert handler_calls == ["customers.search"]
    assert final["status"] == "approval_pending"
    assert final["approval"] == {"status": "pending"}
    assert [plan["tool"] for plan in issued] == ["automation.create_rule"]
    assert [call for call in calls if call.get("stream")] == []


def test_graph_runs_step_two_class_b_write_in_loop(monkeypatch):
    """T2/S3: the bounded autonomous class keeps running inside the chain with no
    per-step approval."""
    calls = []
    handler_calls = []
    plans = [
        '{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"Find Ana","requires_approval":false,"follow_up":true}',
        json.dumps({
            "kind": "tool",
            "tool": "memory.write",
            "arguments": {"titulo": "N", "contenido": "Content", "topic_key": "agent:test", "tipo": "discovery"},
            "summary": "Write",
            "requires_approval": False,
            "follow_up": False,
        }),
    ]
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, name, *_args, **_kwargs: handler_calls.append(name)
        or {"tool": name, "status": "completed", "result": [{"name": "Ana"}]},
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    client = _client(calls, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    final = run_assistant(
        thread_id=7, user_id=1, content="Find Ana", run_id="run-write-chain-b", on_token=lambda _token: None
    )

    assert handler_calls == ["customers.search", "memory.write"]
    assert final["status"] == "completed"
    assert final["tool_steps"] == 2
    assert final["tool_results"][-1]["tool"] == "memory.write"


def test_write_with_follow_up_chains_and_spends_its_approval():
    """T2/S1+S2: a write that opted into a follow-up continues the chain, and the approval
    that authorized it does not carry into the next plan."""
    state = _tool_state(
        tool_steps=1,
        plan={**_tool_state()["plan"], "tool": "settings.update", "follow_up": True},
        approval={"status": "consumed"},
    )

    result = tool_loop_head(state)

    assert result["status"] == "planned"
    assert result["approval"] is None
    assert _after_tool_loop(result) == "plan_llm"


def test_write_without_follow_up_still_ends_the_turn():
    """S4 regression: a write that did not opt into a follow-up ends the turn as before."""
    state = _tool_state(
        tool_steps=1,
        plan={**_tool_state()["plan"], "tool": "settings.update", "follow_up": False},
    )

    assert tool_loop_head(state) == {"status": "completed"}


def test_write_chain_stops_at_the_iteration_cap():
    """T2/S7: the cap still terminates a chain that keeps requesting follow-ups."""
    state = _tool_state(
        tool_steps=MAX_ASSISTANT_TOOL_STEPS,
        plan={**_tool_state()["plan"], "tool": "settings.update", "follow_up": True},
    )

    result = tool_loop_head(state)

    assert result["status"] == "completed"
    assert result["cap_reached"] is True


def test_step_two_write_with_a_spent_approval_gets_a_fresh_one(monkeypatch):
    """T2/S2: the previous step's consumed approval cannot authorize the next plan."""
    from app.chat.assistant.approval import consume_approval, issue_approval

    monkeypatch.setattr("app.chat.assistant.nodes._effective_tools", lambda _state: {"settings.update"})
    spent = issue_approval({"tool": "settings.update", "arguments": {"key": "tone.style", "value": "formal"}})
    assert consume_approval(spent, spent["token"]) is True
    state = _tool_state(
        tool_steps=1,
        approval=spent,
        plan={
            "kind": "tool", "tool": "settings.update",
            "arguments": {"key": "messages.farewell", "value": "Nos vemos."},
            "requires_approval": True,
        },
    )

    result = guardrails(state)

    assert result["status"] == "approval_pending"
    assert result["guardrails"]["decision"] == "approval_pending"
    assert result["approval"]["status"] == "pending"
    assert result["approval"]["token"] != spent["token"]


def test_resumed_plan_with_its_consumed_approval_executes_without_a_new_prompt(monkeypatch):
    """S4 regression (T1): the resume path already holds the approval it was granted, so
    guardrails must not ask for it again."""
    from app.chat.assistant.approval import consume_approval, issue_approval

    monkeypatch.setattr("app.chat.assistant.nodes._effective_tools", lambda _state: {"settings.update"})
    plan = {
        "kind": "tool",
        "tool": "settings.update",
        "arguments": {"key": "tone.style", "value": "formal"},
        "requires_approval": True,
    }
    approval = issue_approval(plan)
    assert consume_approval(approval, approval["token"]) is True
    state = _tool_state(plan=plan, approval=approval)

    result = guardrails(state)

    assert result["status"] == "executing"


def test_single_class_a_write_at_step_zero_still_pauses_once(monkeypatch):
    """S4: the single-write path still asks for exactly one approval before executing."""
    monkeypatch.setattr("app.chat.assistant.nodes._effective_tools", lambda _state: {"settings.update"})
    state = _tool_state(plan={
        "kind": "tool",
        "tool": "settings.update",
        "arguments": {"key": "tone.style", "value": "formal"},
        "requires_approval": True,
        "follow_up": False,
    })

    result = guardrails(state)

    assert result["status"] == "approval_pending"
    assert result["guardrails"]["decision"] == "approval_pending"
    assert result["approval"]["status"] == "pending"
    assert result["approval"]["tool"] == "settings.update"


def test_read_only_turn_still_issues_no_approval(monkeypatch):
    """S4: read-only chaining is unchanged — it never asks for an approval, at any step."""
    issued = []
    monkeypatch.setattr("app.chat.assistant.approval.issue_approval", lambda plan: issued.append(plan))
    monkeypatch.setattr("app.chat.assistant.nodes._effective_tools", lambda _state: {"customers.search"})
    state = _tool_state(tool_steps=1, plan={**_tool_state()["plan"], "follow_up": True})

    result = guardrails(state)

    assert result["status"] == "executing"
    assert issued == []


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


def test_execution_boundary_refuses_write_tool_in_active_planning_session():
    state = _tool_state(
        actor_role="admin",
        user_id=1,
        effective={"tools_whitelist": ("kb.retrieve",)},
        cortex_session={
            "slug": "budget-review",
            "topic": "Budget review",
            "status": "active",
            "opened_at": "2026-09-13T12:00:00Z",
            "closed_at": None,
            "report_key": None,
        },
        plan={
            "kind": "tool", "tool": "memory.delete", "arguments": {"memory_id": 1},
            "summary": "Delete memory", "requires_approval": False,
        },
    )

    result = execute(state)

    assert result["status"] == "error"
    assert isinstance(result["error"], str)
    assert "not whitelisted" in result["error"]


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
