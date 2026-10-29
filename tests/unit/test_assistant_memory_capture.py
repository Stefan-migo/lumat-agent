"""Deterministic capture gates for the panel assistant (MEM-13, S1-S5).

The rule under test is the *when*: the runtime decides, never the user and never
the model. Every case the rule names is covered here — turn interval, durable
write, compaction, blocked cost, daily budget, missing trusted thread — and the
decision depends on nothing else.
"""

from __future__ import annotations

import pytest

from app.chat.assistant import memory_capture
from app.chat.assistant.memory_capture import (
    CAPTURE_DAILY_LIMIT,
    CAPTURE_TURN_INTERVAL,
    CaptureDecision,
    capture_decision,
)

BASE = {
    "cost_allowed": True,
    "thread_id": 7,
    "turn_index": 1,
    "captures_today": 0,
    "durable_write": False,
    "compacted": False,
}


def test_capture_decision_is_none_for_a_plain_turn_inside_the_interval():
    assert capture_decision(**BASE) is None


def test_capture_decision_fires_on_the_turn_interval():
    assert capture_decision(**{**BASE, "turn_index": CAPTURE_TURN_INTERVAL}) == CaptureDecision("turns")


def test_capture_decision_does_not_fire_between_intervals():
    assert capture_decision(**{**BASE, "turn_index": CAPTURE_TURN_INTERVAL + 1}) is None


def test_capture_decision_fires_on_every_completed_interval():
    assert capture_decision(**{**BASE, "turn_index": CAPTURE_TURN_INTERVAL * 3}) == CaptureDecision("turns")


def test_capture_decision_fires_on_a_durable_write_outside_the_interval():
    assert capture_decision(**{**BASE, "turn_index": 2, "durable_write": True}) == CaptureDecision(
        "durable_write"
    )


def test_capture_decision_prefers_a_durable_write_over_the_turn_interval():
    decision = capture_decision(
        **{**BASE, "turn_index": CAPTURE_TURN_INTERVAL, "durable_write": True}
    )
    assert decision == CaptureDecision("durable_write")


def test_capture_decision_prefers_compaction_over_every_other_reason():
    decision = capture_decision(
        **{
            **BASE,
            "turn_index": CAPTURE_TURN_INTERVAL,
            "durable_write": True,
            "compacted": True,
        }
    )
    assert decision == CaptureDecision("compaction")


def test_capture_decision_never_spends_when_cost_is_blocked():
    decision = capture_decision(
        **{
            **BASE,
            "cost_allowed": False,
            "turn_index": CAPTURE_TURN_INTERVAL,
            "durable_write": True,
            "compacted": True,
        }
    )
    assert decision is None


def test_capture_decision_stops_at_the_daily_budget():
    assert (
        capture_decision(
            **{**BASE, "turn_index": CAPTURE_TURN_INTERVAL, "captures_today": CAPTURE_DAILY_LIMIT}
        )
        is None
    )


def test_capture_decision_still_fires_below_the_daily_budget():
    assert capture_decision(
        **{
            **BASE,
            "turn_index": CAPTURE_TURN_INTERVAL,
            "captures_today": CAPTURE_DAILY_LIMIT - 1,
        }
    ) == CaptureDecision("turns")


def test_capture_decision_requires_a_trusted_thread():
    assert capture_decision(**{**BASE, "thread_id": None, "turn_index": CAPTURE_TURN_INTERVAL}) is None
    assert capture_decision(**{**BASE, "thread_id": 0, "turn_index": CAPTURE_TURN_INTERVAL}) is None
    assert capture_decision(**{**BASE, "thread_id": "7", "turn_index": CAPTURE_TURN_INTERVAL}) is None


def _candidate(**overrides):
    return {
        "titulo": "Decision",
        "contenido": "The team chose the stable option for the next release.",
        "tipo": "decision",
        "visibility": "thread",
        "topic_key": "agent:release-choice",
        **overrides,
    }


def _extract(monkeypatch, raw, error=None):
    calls = []

    def provider(messages, state, call_key):
        calls.append((messages, state, call_key))
        return raw, None, error

    monkeypatch.setattr(memory_capture, "_planner_call", provider)
    result = memory_capture.extract_candidates(
        state={"thread_id": 7},
        user_request="Choose a release strategy",
        plan_summary="Compare stability and cost",
        tool_results=[{"tool": "settings.read", "result": "stable"}],
        final_response="We will proceed with the stable option.",
    )
    assert calls[0][1:] == ({"thread_id": 7}, "memory_capture")
    return result, calls[0][0]


def test_extract_candidates_accepts_empty_list(monkeypatch):
    import json

    result, _ = _extract(monkeypatch, json.dumps({"memories": []}))
    assert result == []


def test_extract_candidates_accepts_one_valid_candidate(monkeypatch):
    import json

    result, messages = _extract(monkeypatch, json.dumps({"memories": [_candidate()]}))
    assert result == [_candidate(handoff=False)]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Choose a release strategy" in messages[1]["content"]
    assert "Compare stability and cost" in messages[1]["content"]
    assert "settings.read" in messages[1]["content"]
    assert "stable" in messages[1]["content"]
    assert "We will proceed with the stable option." in messages[1]["content"]


def test_extract_candidates_rejects_invalid_json(monkeypatch):
    result, _ = _extract(monkeypatch, "{not json")
    assert result == []


def test_extract_candidates_rejects_out_of_schema_type(monkeypatch):
    import json

    result, _ = _extract(monkeypatch, json.dumps({"memories": [_candidate(tipo="fact")] }))
    assert result == []


def test_extract_candidates_rejects_topic_without_agent_prefix(monkeypatch):
    import json

    result, _ = _extract(monkeypatch, json.dumps({"memories": [_candidate(topic_key="release-choice")] }))
    assert result == []


def test_extract_candidates_rejects_missing_outer_key(monkeypatch):
    import json

    result, _ = _extract(monkeypatch, json.dumps({"candidate": [_candidate()]}))
    assert result == []


def test_extract_candidates_rejects_extra_outer_key(monkeypatch):
    import json

    result, _ = _extract(monkeypatch, json.dumps({"memories": [_candidate()], "extra": True}))
    assert result == []


def test_extract_candidates_rejects_missing_item_key(monkeypatch):
    import json

    candidate = _candidate()
    del candidate["titulo"]
    result, _ = _extract(monkeypatch, json.dumps({"memories": [candidate]}))
    assert result == []


def test_extract_candidates_rejects_extra_item_key(monkeypatch):
    import json

    result, _ = _extract(monkeypatch, json.dumps({"memories": [_candidate(extra="no")] }))
    assert result == []


def test_extract_candidates_keeps_at_most_three_valid_candidates(monkeypatch):
    import json

    candidates = [_candidate(titulo=f"Decision {index}") for index in range(4)]
    result, _ = _extract(monkeypatch, json.dumps({"memories": candidates}))
    assert result == [candidate | {"handoff": False} for candidate in candidates[:3]]


def test_extract_candidates_returns_none_when_provider_fails(monkeypatch):
    import json

    result, _ = _extract(monkeypatch, json.dumps({"memories": [_candidate()]}), error={"kind": "provider"})
    assert result == []


def test_capture_turn_skips_paid_calls_when_gate_is_closed(monkeypatch):
    monkeypatch.setattr(memory_capture, "should_capture", lambda _state: None)
    monkeypatch.setattr(memory_capture, "extract_candidates", lambda **_kwargs: pytest.fail("unexpected paid call"))

    result = memory_capture.capture_turn({"thread_id": 7})

    assert result == {"written": 0, "reason": None}


def test_capture_turn_writes_one_candidate_for_an_eligible_turn(monkeypatch):
    from app.chat.assistant.tools import registry

    state = {
        "content": "Keep this decision",
        "plan": {"summary": "Decision summary"},
        "tool_results": [{"tool": "customers.search", "result": ["Ana"]}],
        "response": "We will keep it.",
        "thread_id": 7,
        "user_id": 3,
        "session": object(),
        "actor_role": "admin",
        "project_authorization": None,
    }
    calls = []
    monkeypatch.setattr(memory_capture, "should_capture", lambda _state: CaptureDecision("durable_write"))
    monkeypatch.setattr(
        memory_capture,
        "extract_candidates",
        lambda **kwargs: calls.append(("extract", kwargs)) or [_candidate(handoff=False)],
    )
    monkeypatch.setattr(
        registry,
        "execute_tool",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {"status": "completed"},
    )

    result = memory_capture.capture_turn(state)

    assert result == {"written": 1, "reason": "durable_write"}
    assert calls[0] == (
        "extract",
        {
            "state": state,
            "user_request": "Keep this decision",
            "plan_summary": "Decision summary",
            "tool_results": state["tool_results"],
            "final_response": "We will keep it.",
        },
    )
    args, kwargs = calls[1]
    assert args == (state["session"], "memory.write", _candidate(handoff=False))
    assert kwargs == {
        "whitelist": {"memory.write"},
        "cost_allowed": True,
        "role": "admin",
        "trusted_thread_id": 7,
        "owner_id": 3,
        "proyecto": "default",
    }


def test_capture_turn_writes_nothing_when_extractor_returns_no_candidates(monkeypatch):
    from app.chat.assistant.tools import registry

    monkeypatch.setattr(memory_capture, "should_capture", lambda _state: CaptureDecision("turns"))
    monkeypatch.setattr(memory_capture, "extract_candidates", lambda **_kwargs: [])
    monkeypatch.setattr(registry, "execute_tool", lambda *_args, **_kwargs: pytest.fail("unexpected write"))

    assert memory_capture.capture_turn({"thread_id": 7}) == {"written": 0, "reason": "turns"}


def test_capture_turn_degrades_when_memory_write_raises(monkeypatch):
    from app.chat.assistant.tools import registry

    monkeypatch.setattr(memory_capture, "should_capture", lambda _state: CaptureDecision("compaction"))
    monkeypatch.setattr(memory_capture, "extract_candidates", lambda **_kwargs: [_candidate(handoff=False)])

    def fail(*_args, **_kwargs):
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(registry, "execute_tool", fail)

    result = memory_capture.capture_turn({"thread_id": 7})

    assert result == {
        "written": 0,
        "reason": "compaction",
        "degraded_reason": "memory capture unavailable",
    }


def test_capture_turn_counts_only_successful_memory_writes(monkeypatch):
    from app.chat.assistant.tools import registry

    monkeypatch.setattr(memory_capture, "should_capture", lambda _state: CaptureDecision("turns"))
    monkeypatch.setattr(memory_capture, "extract_candidates", lambda **_kwargs: [_candidate(handoff=False)])
    monkeypatch.setattr(
        registry,
        "execute_tool",
        lambda *_args, **_kwargs: {
            "status": "completed",
            "result": {"written": False, "degraded_reason": "Memory write unavailable"},
        },
    )

    assert memory_capture.capture_turn({"thread_id": 7}) == {
        "written": 0,
        "reason": "turns",
        "degraded_reason": "Memory write unavailable",
    }


def test_memory_capture_node_never_raises(monkeypatch):
    monkeypatch.setattr(memory_capture, "capture_turn", lambda _state: (_ for _ in ()).throw(RuntimeError("failure")))

    assert memory_capture.memory_capture_node({}) == {
        "memory_capture": {"written": 0, "reason": None, "degraded_reason": "memory capture unavailable"}
    }
