"""RED-first contracts for the Cortex-session foundation slice."""

from __future__ import annotations

from app.chat.assistant.nodes import parse_planning_command
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


def test_planning_parser_accepts_only_literal_commands():
    assert parse_planning_command("/planning budget review") == {
        "action": "open",
        "topic": "budget review",
    }
    assert parse_planning_command("/planning close") == {"action": "close", "topic": None}


def test_planning_parser_does_not_infer_from_free_text():
    assert parse_planning_command("Please start a planning session for the budget") is None
    assert parse_planning_command("/planning") is None
