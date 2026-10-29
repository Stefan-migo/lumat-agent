"""Deterministic capture gates for the panel assistant (MEM-13, S1-S5).

The rule under test is the *when*: the runtime decides, never the user and never
the model. Every case the rule names is covered here — turn interval, durable
write, compaction, blocked cost, daily budget, missing trusted thread — and the
decision depends on nothing else.
"""

from __future__ import annotations

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
