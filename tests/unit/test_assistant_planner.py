"""Strict structured planner contracts for the panel assistant."""

import pytest
from pydantic import ValidationError

from app.chat.assistant.nodes import bounded_fallback, parse_planner_output, plan
from app.chat.assistant.state import PlannerOutput


def test_planner_accepts_strict_tool_plan_and_rejects_extra_fields():
    result = PlannerOutput.model_validate(
        {
            "kind": "tool",
            "tool": "customers.search",
            "arguments": {"query": "Ana"},
            "summary": "Find Ana's customer record.",
            "requires_approval": False,
        }
    )
    assert result.kind == "tool"
    assert result.arguments == {"query": "Ana"}

    with pytest.raises(ValidationError):
        PlannerOutput.model_validate(
            {
                "kind": "respond",
                "arguments": {},
                "summary": "Answer the request.",
                "requires_approval": False,
                "unexpected": "reject me",
            }
        )


def test_tool_plan_requires_tool_but_response_plan_does_not():
    with pytest.raises(ValidationError):
        PlannerOutput.model_validate(
            {
                "kind": "tool",
                "arguments": {},
                "summary": "Missing tool name.",
                "requires_approval": False,
            }
        )

    response = parse_planner_output(
        {
            "kind": "respond",
            "arguments": {},
            "summary": "No tool is needed.",
            "requires_approval": False,
        }
    )
    assert response.tool is None


def test_complex_plan_exposes_metadata_only_hook():
    result = parse_planner_output(
        {
            "kind": "complex",
            "arguments": {"steps": ["research", "summarize"]},
            "summary": "This needs a future extension hook.",
            "requires_approval": False,
        }
    )
    assert result.kind == "complex"
    assert result.tool is None
    state = plan({"content": "complex request", "planner_output": result.model_dump()})
    assert state["extension_hooks"] == {"sdb": "deferred", "panel_subagents": "not_implemented"}
    assert state["status"] == "planned"


def test_invalid_planner_output_becomes_bounded_response_fallback():
    fallback = bounded_fallback("malformed planner output")
    assert fallback.kind == "respond"
    assert fallback.requires_approval is False
    assert len(fallback.summary) <= 200

    state = plan(
        {
            "content": "unsafe request",
            "planner_output": {"kind": "tool", "arguments": {"secret": "no"}},
        }
    )
    assert state["planner"]["valid"] is False
    assert state["planner"]["kind"] == "respond"
    assert state["error"] == "Invalid planner output."


def test_normal_planner_flow_remains_unmodified():
    state = plan({
        "content": "What is the current status?",
        "planner_output": {
            "kind": "respond",
            "arguments": {},
            "summary": "The system is operational.",
            "requires_approval": False,
        },
    })

    assert state["status"] == "planned"
    assert state["plan"]["summary"] == "The system is operational."
    assert state["plan"]["requires_approval"] is False
