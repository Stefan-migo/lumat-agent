"""Deterministic verification gate contract for assistant tool effects."""

import pytest
from pydantic import ValidationError

from app.chat.assistant.state import PlannerOutput
from app.chat.assistant.verification import EFFECT_TOOLS, verification_required


@pytest.mark.parametrize("tool", sorted(EFFECT_TOOLS))
def test_each_effect_tool_requires_verification(tool):
    assert verification_required(dispatched_tools=[tool]) == (True, "effect-tool")


def test_memory_write_does_not_require_verification():
    assert verification_required(dispatched_tools=["memory.write"]) == (False, "not-required")


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"explicit": True}, (True, "explicit")),
        ({"handoff": True}, (True, "handoff")),
        ({}, (False, "not-required")),
    ],
)
def test_signal_and_empty_cases(kwargs, expected):
    assert verification_required(dispatched_tools=[], **kwargs) == expected


def test_effect_tool_precedes_explicit_and_handoff_signals():
    assert verification_required(
        dispatched_tools=["memory.update"], explicit=True, handoff=True
    ) == (True, "effect-tool")


def test_explicit_signal_precedes_handoff():
    assert verification_required(dispatched_tools=[], explicit=True, handoff=True) == (
        True,
        "explicit",
    )


def test_gate_is_deterministic_for_repeated_inputs():
    inputs = {"dispatched_tools": ["project.archive", "memory.write"], "handoff": True}
    assert verification_required(**inputs) == verification_required(**inputs)


def test_planner_success_criterion_is_optional_but_bounded_and_non_empty():
    base = {"kind": "respond", "summary": "Done."}
    assert PlannerOutput.model_validate(base).success_criterion is None
    assert PlannerOutput.model_validate(
        {**base, "success_criterion": "The project appears in the list."}
    ).success_criterion == "The project appears in the list."

    for invalid in ("", "   ", "x" * 301):
        with pytest.raises(ValidationError):
            PlannerOutput.model_validate({**base, "success_criterion": invalid})
