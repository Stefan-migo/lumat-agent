"""Independent verifier probes for T6 / S7 (raised tool-loop budget).

Each assertion fails if the raised budget does not fit a 3-step chain, if the cap stops
cutting a runaway chain, or if a blocked cost mode fails to end the turn.
"""

import json
from types import SimpleNamespace

from app.chat.assistant.graph import run_assistant
from app.chat.assistant.nodes import MAX_ASSISTANT_TOOL_STEPS, tool_loop_head


def _plan(tool, *, follow_up, summary="s", requires_approval=False):
    return json.dumps({
        "kind": "tool", "tool": tool, "arguments": {"query": "Ana"},
        "summary": summary, "requires_approval": requires_approval, "follow_up": follow_up,
    })


class _Completions:
    def __init__(self, plans):
        self.plans = list(plans)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Listo."))])]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.plans.pop(0)))])


def _wire(monkeypatch, plans):
    handler_calls = []
    completions = _Completions(plans)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, tool_name, *_a, **_k: handler_calls.append(tool_name)
        or {"tool": tool_name, "status": "completed", "result": [{"evidence": tool_name}]},
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *a, **k: None)
    return completions, handler_calls


def test_s7_surplus_plans_do_not_extend_a_read_only_chain(monkeypatch):
    """The budget must cut a runaway chain at 4 executions even when plans keep coming."""
    plans = [_plan("customers.search", follow_up=True, summary=f"s{i}") for i in range(8)]
    _completions, handler_calls = _wire(monkeypatch, plans)

    final = run_assistant(thread_id=7, user_id=1, content="go", run_id="run-surplus", on_token=lambda _t: None)

    assert handler_calls == ["customers.search"] * MAX_ASSISTANT_TOOL_STEPS
    assert final["tool_steps"] == MAX_ASSISTANT_TOOL_STEPS
    assert final["cap_reached"] is True


def test_s7_three_step_chain_is_not_capped(monkeypatch):
    """A 3-step chain runs all three steps in one turn and is not capped (S7 raise)."""
    plans = [
        _plan("customers.search", follow_up=True, summary="s1"),
        _plan("memory.search", follow_up=True, summary="s2"),
        _plan("customers.search", follow_up=False, summary="s3"),
    ]
    _completions, handler_calls = _wire(monkeypatch, plans)

    final = run_assistant(thread_id=7, user_id=1, content="go", run_id="run-three", on_token=lambda _t: None)

    assert handler_calls == ["customers.search", "memory.search", "customers.search"]
    assert final["tool_steps"] == 3
    assert not final.get("cap_reached", False)


def test_s7_blocked_cost_gate_stops_the_loop_regardless_of_budget(monkeypatch):
    """A blocked per-turn cost mode ends the turn after the first step, whatever the budget."""
    plans = [_plan("customers.search", follow_up=True, summary=f"s{i}") for i in range(MAX_ASSISTANT_TOOL_STEPS)]
    _completions, handler_calls = _wire(monkeypatch, plans)
    monkeypatch.setattr("app.chat.assistant.nodes._cost_snapshot", lambda *a, **k: {"mode": "blocked"})

    final = run_assistant(thread_id=7, user_id=1, content="go", run_id="run-cost", on_token=lambda _t: None)

    assert len(handler_calls) == 1
    assert final["guardrails"]["cost_allowed"] is False
    assert final["guardrails"]["decision"] == "loop_cost_stopped"


def test_s7_cap_boundary_is_exactly_the_budget():
    """At 3 steps the loop continues; at the budget it caps -- the exact S7 boundary."""
    base = {"thread_id": 7, "guardrails": {"cost_allowed": True}, "session": None}
    at_three = tool_loop_head({
        **base, "tool_steps": 3,
        "plan": {"kind": "tool", "tool": "customers.search", "follow_up": True},
    })
    assert at_three.get("status") == "planned"
    assert at_three.get("cap_reached") is None

    at_four = tool_loop_head({
        **base, "tool_steps": MAX_ASSISTANT_TOOL_STEPS,
        "plan": {"kind": "tool", "tool": "customers.search", "follow_up": True},
    })
    assert at_four["cap_reached"] is True
    assert at_four["status"] == "completed"


def test_s7_budget_fits_a_three_step_chain_and_is_bounded():
    assert MAX_ASSISTANT_TOOL_STEPS >= 3
    assert MAX_ASSISTANT_TOOL_STEPS == 4
