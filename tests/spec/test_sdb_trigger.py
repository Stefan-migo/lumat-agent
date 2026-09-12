"""OpenSpec scenarios for the native SDB trigger boundary."""

from app.chat.assistant.graph import sdb_trigger_gate
from app.chat.assistant.state import PlannerOutput, normalize_sdb_trigger


def test_classified_trigger_enters_sdb_at_clarify():
    result = normalize_sdb_trigger({"classification": "sdb"})

    assert result == {"route": "sdb", "trigger": "classified", "phase": "CLARIFY"}


def test_authenticated_admin_trigger_overrides_valid_non_sdb_plan():
    result = normalize_sdb_trigger(
        {"classification": "normal", "sdb_requested": True, "actor_role": "admin"}
    )

    assert result["route"] == "sdb"
    assert result["trigger"] == "admin"
    assert result["phase"] == "CLARIFY"


def test_malformed_classification_fails_closed():
    result = normalize_sdb_trigger({"classification": "SDB"})

    assert result["route"] == "normal"
    assert result["reason"] == "malformed-signal"


def test_malformed_signal_with_undeclared_field_fails_closed():
    result = normalize_sdb_trigger({"classification": "normal", "unexpected": True})

    assert result == {"route": "normal", "reason": "malformed-signal"}


def test_conflicting_sdb_signals_fail_closed():
    result = normalize_sdb_trigger(
        {"classification": "sdb", "sdb_requested": False}
    )

    assert result["route"] == "normal"
    assert result["reason"] == "conflicting-trigger"


def test_non_admin_explicit_request_fails_closed():
    result = normalize_sdb_trigger(
        {"classification": "normal", "sdb_requested": True, "actor_role": "operador"}
    )

    assert result["route"] == "normal"
    assert result["reason"] == "unauthorized-request"


def test_ordinary_complex_plan_remains_on_normal_route():
    plan = PlannerOutput(
        kind="complex",
        arguments={"steps": ["research", "summarize"]},
        summary="A normal complex request.",
    ).model_dump()

    result = sdb_trigger_gate({"plan": plan, "planner": {"valid": True}})

    assert result["sdb_route"] == "normal"
    assert result["sdb_trigger"] is None
    assert result["sdb_rejection"] is None
