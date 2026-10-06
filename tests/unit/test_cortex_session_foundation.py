"""RED-first contracts for the Cortex-session foundation slice."""

from __future__ import annotations

from app.chat.assistant.state import (
    merge_assistant_state,
    validate_cortex_session,
)


def test_cortex_state_schema_accepts_active_session():
    state = {
        "cortex_session": {
            "slug": "budget-review",
            "topic": "Budget review",
            "status": "active",
            "opened_at": "2026-09-13T12:00:00Z",
            "closed_at": None,
            "turn_index": 0,
            "next_decision": None,
            "last_class": None,
            "decision_keys": [],
            "report_key": None,
            "handoff": {"status": "none", "sdb_phase": None},
        }
    }

    assert validate_cortex_session(state) is True


def test_recursive_merge_preserves_unrelated_and_nested_state():
    current = {
        "planner": {"model": "configured"},
        "cortex_session": {"topic": "Budget review", "turn_index": 1},
    }

    merged = merge_assistant_state(
        current,
        {"cortex_session": {"turn_index": 2, "last_class": "question"}},
    )

    assert merged == {
        "planner": {"model": "configured"},
        "cortex_session": {
            "topic": "Budget review",
            "turn_index": 2,
            "last_class": "question",
        },
    }


def test_invalid_cortex_state_fails_closed():
    assert validate_cortex_session({"cortex_session": {"status": "planning"}}) is False
    assert validate_cortex_session({}) is False
