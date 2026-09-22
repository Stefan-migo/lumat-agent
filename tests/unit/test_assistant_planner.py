"""Strict structured planner contracts for the panel assistant."""

import json
import logging
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.chat.assistant.nodes import (
    _PLANNER_FAILURE_EXCERPT_LIMIT,
    _context_text,
    bounded_fallback,
    guardrails,
    parse_planner_output,
    plan,
    plan_llm,
)
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

    response, valid, diagnosis = parse_planner_output(
        {
            "kind": "respond",
            "arguments": {},
            "summary": "No tool is needed.",
            "requires_approval": False,
        }
    )
    assert valid is True
    assert diagnosis is None
    assert response.tool is None


def test_parse_planner_output_returns_validity_with_plan():
    plan_result, valid, diagnosis = parse_planner_output(
        {
            "kind": "respond",
            "arguments": {},
            "summary": "No tool is needed.",
            "requires_approval": False,
        }
    )
    assert valid is True
    assert diagnosis is None
    assert plan_result.tool is None

    malformed, valid, diagnosis = parse_planner_output({"kind": "tool"})
    assert valid is False
    assert malformed == bounded_fallback("x")
    assert diagnosis["reason"] == "planner_output_validation_failed"


def test_planner_output_accepts_explicit_null_arguments():
    result, valid, diagnosis = parse_planner_output(
        {
            "kind": "respond",
            "arguments": None,
            "summary": "No tool is needed.",
            "requires_approval": False,
        }
    )

    assert valid is True
    assert diagnosis is None
    assert result.arguments == {}


def test_plan_llm_keeps_respond_plan_with_null_arguments(monkeypatch, caplog):
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(prompts={"plan": "{{user_input}}"}, tools_whitelist=[], persona="persona"),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content='{"kind":"respond","classification":"normal","tool":null,"arguments":null,"summary":"Si: tengo acceso a memoria por ambitos (panel, cliente, agente) en modo lectura con memory.read/memory.search, y escritura solo con tu aprobacion. No accedo a memoria fuera del panel autorizado.","requires_approval":false}',
            ))]),
        ))),
    )

    with caplog.at_level(logging.ERROR, logger="app.chat.assistant.nodes"):
        result = plan_llm({"content": "Do you have access to memory?", "context": {"items": []}})

    assert result["planner"]["valid"] is True
    assert "failure" not in result["planner"]
    assert result["plan"]["arguments"] == {}
    assert result["plan"]["summary"] == (
        "Si: tengo acceso a memoria por ambitos (panel, cliente, agente) en modo lectura con "
        "memory.read/memory.search, y escritura solo con tu aprobacion. No accedo a memoria fuera "
        "del panel autorizado."
    )
    assert not [
        record
        for record in caplog.records
        if record.name == "app.chat.assistant.nodes" and record.levelno >= logging.ERROR
    ]


def test_planner_output_normalizes_null_arguments_for_tool_plans():
    result = PlannerOutput.model_validate(
        {
            "kind": "tool",
            "tool": "memory.read",
            "arguments": None,
            "summary": "Read memory.",
            "requires_approval": False,
        }
    )

    assert result.arguments == {}


def test_planner_output_still_rejects_wrong_argument_types_and_extra_keys():
    payload = {
        "kind": "respond",
        "summary": "Answer the request.",
        "requires_approval": False,
    }

    with pytest.raises(ValidationError, match="dict_type"):
        PlannerOutput.model_validate({**payload, "arguments": []})

    with pytest.raises(ValidationError, match="extra_forbidden"):
        PlannerOutput.model_validate({**payload, "arguments": {}, "type": "json_object"})


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
    assert sorted(memory_entry["arguments"]["discriminator"]["mapping"]) == [
        "customer", "own"
    ]
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


@pytest.mark.parametrize(
    ("client", "reason", "stage", "exception_type", "raw_text"),
    [
        (
            SimpleNamespace(
                chat=SimpleNamespace(
                    completions=SimpleNamespace(create=lambda **kwargs: (_ for _ in ()).throw(ConnectionError("down")))
                )
            ),
            "provider_call_failed",
            "provider",
            "ConnectionError",
            "",
        ),
        (
            SimpleNamespace(
                chat=SimpleNamespace(
                    completions=SimpleNamespace(
                        create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=" "))])
                    )
                )
            ),
            "empty_completion",
            "completion",
            "ValueError",
            "",
        ),
        (
            SimpleNamespace(
                chat=SimpleNamespace(
                    completions=SimpleNamespace(
                        create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))])
                    )
                )
            ),
            "invalid_json",
            "parse",
            "JSONDecodeError",
            "not json",
        ),
        (
            SimpleNamespace(
                chat=SimpleNamespace(
                    completions=SimpleNamespace(
                        create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"kind":"tool"}'))])
                    )
                )
            ),
            "planner_output_validation_failed",
            "validation",
            "ValidationError",
            '{"kind":"tool"}',
        ),
    ],
)
def test_plan_llm_records_distinct_failure_diagnostics(monkeypatch, caplog, client, reason, stage, exception_type, raw_text):
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(prompts={"plan": "{{user_input}}"}, tools_whitelist=[], persona="persona"),
    )
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: client)

    with caplog.at_level(logging.ERROR, logger="app.chat.assistant.nodes"):
        result = plan_llm({"content": "Find Ana", "context": {"items": []}})

    diagnosis = result["planner"]["failure"]
    assert diagnosis["reason"] == reason
    assert diagnosis["stage"] == stage
    assert diagnosis["exception_type"] == exception_type
    assert diagnosis["raw_excerpt"] == raw_text
    assert caplog.records[-1].diagnosis == diagnosis
    rendered = caplog.records[-1].getMessage()
    assert reason in rendered
    assert stage in rendered
    assert exception_type in rendered


def test_plan_llm_bounds_usage_recording_failure(monkeypatch, caplog):
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(prompts={"plan": "{{user_input}}"}, tools_whitelist=[], persona="persona"),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content='{"kind":"respond","arguments":{},"summary":"Done","requires_approval":false}'
            ))]),
        ))),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._record_usage",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ledger down")),
    )

    with caplog.at_level(logging.ERROR, logger="app.chat.assistant.nodes"):
        result = plan_llm({"content": "Find Ana", "context": {"items": []}})

    diagnosis = result["planner"]["failure"]
    assert diagnosis["reason"] == "usage_recording_failed"
    assert diagnosis["stage"] == "instrumentation"
    assert diagnosis["exception_type"] == "RuntimeError"
    assert result["planner"]["valid"] is False
    assert result["plan"] == bounded_fallback("x").model_dump()
    assert caplog.records[-1].diagnosis == diagnosis
    rendered = caplog.records[-1].getMessage()
    assert "usage_recording_failed" in rendered
    assert "instrumentation" in rendered
    assert "RuntimeError" in rendered


def test_plan_llm_bounds_completion_extraction_failure(monkeypatch, caplog):
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(prompts={"plan": "{{user_input}}"}, tools_whitelist=[], persona="persona"),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content='{"kind":"respond","arguments":{},"summary":"Done","requires_approval":false}'
            ))]),
        ))),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._completion_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("malformed response")),
    )

    with caplog.at_level(logging.ERROR, logger="app.chat.assistant.nodes"):
        result = plan_llm({"content": "Find Ana", "context": {"items": []}})

    diagnosis = result["planner"]["failure"]
    assert diagnosis["reason"] == "completion_extraction_failed"
    assert diagnosis["stage"] == "extraction"
    assert diagnosis["exception_type"] == "RuntimeError"
    assert result["planner"]["valid"] is False
    assert result["plan"] == bounded_fallback("x").model_dump()
    assert caplog.records[-1].diagnosis == diagnosis
    rendered = caplog.records[-1].getMessage()
    assert "completion_extraction_failed" in rendered
    assert "extraction" in rendered
    assert "RuntimeError" in rendered


def test_plan_llm_records_no_failure_for_valid_plan(monkeypatch, caplog):
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(prompts={"plan": "{{user_input}}"}, tools_whitelist=[], persona="persona"),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content='{"kind":"respond","arguments":{},"summary":"Done","requires_approval":false}'
            ))]),
        ))),
    )

    with caplog.at_level(logging.ERROR, logger="app.chat.assistant.nodes"):
        result = plan_llm({"content": "Find Ana", "context": {"items": []}})

    assert result["planner"]["valid"] is True
    assert "failure" not in result["planner"]
    assert not caplog.records


def test_invalid_plan_keeps_degraded_user_visible_output():
    state = plan({"content": "unsafe request", "planner_output": {"kind": "tool"}})

    assert state["response"] == "No pude planificar esa solicitud de forma segura. Inténtalo nuevamente."


def test_plan_invalid_output_and_guardrail_unsafe_plan_have_distinct_diagnostics(caplog):
    invalid = plan({"content": "unsafe request", "planner_output": {"kind": "tool"}})
    unsafe = guardrails(
        {
            "planner": {"valid": True},
            "plan": {"kind": "tool", "tool": "not-whitelisted", "arguments": {}, "requires_approval": False},
        }
    )

    assert invalid["planner"]["failure"]["reason"] == "planner_output_validation_failed"
    assert unsafe["planner"]["failure"]["reason"] == "unsafe_plan"


def test_planner_failure_excerpt_is_bounded_and_guardrail_logs_diagnosis(caplog):
    raw_text = "x" * (_PLANNER_FAILURE_EXCERPT_LIMIT + 100)
    plan_state = {
        "planner": {"valid": True},
        "plan": {
            "kind": "tool",
            "tool": "not-whitelisted",
            "arguments": {"payload": raw_text},
            "requires_approval": False,
        },
    }

    with caplog.at_level(logging.ERROR, logger="app.chat.assistant.nodes"):
        result = guardrails(plan_state)

    diagnosis = result["planner"]["failure"]
    assert len(diagnosis["raw_excerpt"]) <= _PLANNER_FAILURE_EXCERPT_LIMIT
    assert caplog.records[-1].diagnosis == diagnosis
    assert diagnosis["raw_excerpt"]


def test_complex_plan_exposes_metadata_only_hook():
    result, valid, diagnosis = parse_planner_output(
        {
            "kind": "complex",
            "arguments": {"steps": ["research", "summarize"]},
            "summary": "This needs a future extension hook.",
            "requires_approval": False,
        }
    )
    assert valid is True
    assert diagnosis is None
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

    result, valid, diagnosis = parse_planner_output(
        {
            "kind": "respond",
            "arguments": {},
            "summary": summary,
            "requires_approval": False,
        }
    )

    assert valid is True
    assert diagnosis is None
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

    assert _context_text(state) == (
        "Pinned fact\nRecent message\nConversation identity: scope=panel "
        "(the panel memory read target is derived server-side)"
    )
    assert "entity_id=thread:42" not in _context_text(state)


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
