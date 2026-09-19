"""Strict structured planner contracts for the panel assistant."""

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.chat.assistant.nodes import _context_text, bounded_fallback, parse_planner_output, plan, plan_llm
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

    response, valid = parse_planner_output(
        {
            "kind": "respond",
            "arguments": {},
            "summary": "No tool is needed.",
            "requires_approval": False,
        }
    )
    assert valid is True
    assert response.tool is None


def test_parse_planner_output_returns_validity_with_plan():
    plan_result, valid = parse_planner_output(
        {
            "kind": "respond",
            "arguments": {},
            "summary": "No tool is needed.",
            "requires_approval": False,
        }
    )
    assert valid is True
    assert plan_result.tool is None

    malformed, valid = parse_planner_output({"kind": "tool"})
    assert valid is False
    assert malformed == bounded_fallback("x")


def test_plan_llm_does_not_treat_fallback_summary_collision_as_invalid(monkeypatch):
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(
            prompts={"plan": "{{user_input}}"},
            tools_whitelist=["customers.search"],
            persona="persona",
        ),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content='{"kind":"tool","tool":"customers.search","arguments":{"query":"Ana"},"summary":"I could not safely plan that request. Please try again.","requires_approval":false}',
            ))]),
        ))),
    )

    result = plan_llm({"content": "Find Ana", "context": {"items": []}})

    assert result["planner"]["valid"] is True
    assert result["plan"]["tool"] == "customers.search"
    assert result["plan"]["kind"] == "tool"


def test_plan_llm_includes_whitelisted_tool_catalog_in_prompt(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(
            prompts={"plan": "<available_tools>{{available_tools}}</available_tools>"},
            tools_whitelist=["memory.read", "customers.search"],
            persona="persona",
        ),
    )

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"kind":"respond","arguments":{},"summary":"Done.","requires_approval":false}'))])

    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),
    )

    plan_llm({"content": "Read the conversation memory", "context": {"items": []}})

    prompt = captured["messages"][1]["content"]
    catalog = json.loads(prompt.split("<available_tools>", 1)[1].split("</available_tools>", 1)[0])

    assert [entry["name"] for entry in catalog] == ["memory.read", "customers.search"]
    assert all(set(entry) == {"name", "description", "arguments"} for entry in catalog)
    memory_entry = catalog[0]
    assert memory_entry["description"] == "Read scoped memory."
    assert {"scope", "entity_id"}.issubset(memory_entry["arguments"]["required"])
    assert "project.archive" not in prompt


def test_plan_llm_keeps_malformed_output_invalid(monkeypatch):
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(prompts={"plan": "{{user_input}}"}, tools_whitelist=[], persona="persona"),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"kind":"tool"}'))]),
        ))),
    )

    result = plan_llm({"content": "Find Ana", "context": {"items": []}})

    assert result["planner"]["valid"] is False
    assert result["plan"]["summary"] == bounded_fallback("x").summary


def test_complex_plan_exposes_metadata_only_hook():
    result, valid = parse_planner_output(
        {
            "kind": "complex",
            "arguments": {"steps": ["research", "summarize"]},
            "summary": "This needs a future extension hook.",
            "requires_approval": False,
        }
    )
    assert valid is True
    assert result.kind == "complex"
    assert result.tool is None
    state = plan({"content": "complex request", "planner_output": result.model_dump()})
    assert state["extension_hooks"] == {"sdb": "deferred", "panel_subagents": "not_implemented"}
    assert state["status"] == "planned"


def test_overlong_summary_keeps_tool_plan_instead_of_falling_back():
    state = plan(
        {
            "content": "Find Ana's customer record.",
            "planner_output": {
                "kind": "tool",
                "tool": "customers.search",
                "arguments": {"query": "Ana"},
                "summary": "x" * 250,
                "requires_approval": False,
            },
        }
    )

    assert state["planner"]["valid"] is True
    assert state["plan"]["kind"] == "tool"
    assert state["plan"]["tool"] == "customers.search"
    assert len(state["plan"]["summary"]) == 200


def test_summary_at_limit_passes_through_unchanged():
    summary = "x" * 200

    result, valid = parse_planner_output(
        {
            "kind": "respond",
            "arguments": {},
            "summary": summary,
            "requires_approval": False,
        }
    )

    assert valid is True
    assert result.summary == summary


def test_non_string_summary_still_becomes_invalid_planner_fallback():
    state = plan(
        {
            "content": "Respond to the request.",
            "planner_output": {
                "kind": "respond",
                "arguments": {},
                "summary": 200,
                "requires_approval": False,
            },
        }
    )

    assert state["planner"]["valid"] is False
    assert state["plan"]["kind"] == "respond"
    assert state["error"] == "Invalid planner output."


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


def test_context_text_includes_conversation_identity_when_available():
    state = {
        "context": {
            "items": [{"content": "Pinned fact"}, {"content": "Recent message"}],
            "meta": {"scope": "panel", "entity_id": "thread:42"},
        }
    }

    assert _context_text(state) == "Pinned fact\nRecent message\nConversation identity: scope=panel entity_id=thread:42"


def test_context_text_omits_conversation_identity_without_complete_meta():
    state = {"context": {"items": [{"content": "Recent message"}], "meta": {}}}

    assert _context_text(state) == "Recent message"


def test_context_text_announces_saved_recap_after_rotation():
    state = {
        "context": {"items": [{"content": "Recent message"}], "meta": {"scope": "panel", "entity_id": "thread:42"}},
        "compaction": {"rotated": True, "failed": False},
    }

    text = _context_text(state)

    assert "recap saved" in text.lower()
    assert "memory.read with scope=panel and no entity_id" in text
    assert "conversation identity above" not in text
    assert "unavailable" not in text.lower()


def test_context_text_marks_failed_recap_as_unavailable():
    state = {
        "context": {"items": [{"content": "Recent message"}], "meta": {}},
        "compaction": {"rotated": False, "failed": True},
    }

    text = _context_text(state)

    assert "unavailable" in text.lower()
    assert "memory.read" not in text


def test_context_text_omits_recap_cue_when_compaction_did_not_rotate():
    state = {
        "context": {"items": [{"content": "Recent message"}], "meta": {}},
        "compaction": {"rotated": False, "failed": False},
    }

    assert _context_text(state) == "Recent message"
