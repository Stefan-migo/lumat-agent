"""Ordered assistant guardrail contracts for typed tool execution."""

from types import SimpleNamespace

import pytest

from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.nodes import execute, guardrails, panel_cost_gate, plan_llm
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.db import SessionLocal
from app.models import Memory
from app.services.prompts import load_assistant_config
from sqlalchemy import select


def _rule_args():
    return {
        "name": "notify",
        "event_type": "case.created",
        "conditions": {},
        "channel": "email",
        "template_event": "case.created",
        "cooldown_seconds": 0,
    }


def test_whitelist_rejects_before_handler(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.customers.search_customers",
        lambda *args: called.append(args),
    )
    with pytest.raises(ToolValidationError, match="not whitelisted"):
        execute_tool(SimpleNamespace(), "customers.search", {"query": "Ana"}, whitelist=set())
    assert called == []


def test_typed_arguments_reject_before_handler(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.customers.search_customers",
        lambda *args: called.append(args),
    )
    with pytest.raises(ToolValidationError, match="invalid arguments"):
        execute_tool(
            SimpleNamespace(),
            "customers.search",
            {"query": "Ana", "limit": 999},
            whitelist={"customers.search"},
        )
    assert called == []


def test_cost_guard_rejects_before_handler(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.customers.search_customers",
        lambda *args: called.append(args),
    )
    with pytest.raises(ToolValidationError, match="cost"):
        execute_tool(
            SimpleNamespace(),
            "customers.search",
            {"query": "Ana"},
            whitelist={"customers.search"},
            cost_allowed=False,
        )
    assert called == []


def test_write_requires_exact_consumed_approval_before_handler(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.automation.create_rule",
        lambda *args, **kwargs: called.append((args, kwargs)),
    )
    approval = issue_approval({"tool": "automation.create_rule", "arguments": _rule_args()})
    with pytest.raises(ToolValidationError, match="approval"):
        execute_tool(
            SimpleNamespace(),
            "automation.create_rule",
            {**_rule_args(), "name": "tampered"},
            whitelist={"automation.create_rule"},
            approval={**approval, "status": "consumed"},
        )
    assert called == []


def test_execution_audits_before_evidence(monkeypatch):
    order = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: order.append("handler") or {
            "tool": "customers.search", "status": "completed", "result": [{"id": 1}]
        },
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: order.append("audit"))
    result = execute(
        {
            "thread_id": 1,
            "run_id": "run-1",
            "plan": {
                "kind": "tool",
                "tool": "customers.search",
                "arguments": {"query": "Ana"},
                "requires_approval": False,
            },
            "session": SimpleNamespace(),
            "evidence": [],
        }
    )
    assert order == ["handler", "audit"]
    assert result["evidence"][0]["status"] == "completed"
    assert result["status"] == "completed"


def test_cost_gate_injects_conservative_directive_after_context(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.nodes.internal_thread_cost_state",
        lambda session, thread_id: (80.0, "conservative"),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes.daily_cost_state",
        lambda session: (0.0, "normal"),
    )
    monkeypatch.setattr("app.chat.assistant.nodes.maybe_alert_owner", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.chat.assistant.nodes.internal_thread_spend", lambda *args: 1.2)
    monkeypatch.setattr("app.chat.assistant.nodes.daily_spend", lambda *args: 0.0)
    state = panel_cost_gate({"thread_id": 7, "session": SimpleNamespace(), "content": "Explain this"})

    assert state["cost_mode"] == "conservative"
    assert "Answer concisely" in state["cost_directive"]


def test_cost_gate_blocked_never_invokes_planner(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.nodes.internal_thread_cost_state",
        lambda session, thread_id: (100.0, "blocked"),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes.daily_cost_state",
        lambda session: (0.0, "normal"),
    )
    monkeypatch.setattr("app.chat.assistant.nodes.maybe_alert_owner", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.chat.assistant.nodes.internal_thread_spend", lambda *args: 1.5)
    monkeypatch.setattr("app.chat.assistant.nodes.daily_spend", lambda *args: 0.0)
    monkeypatch.setattr(
        "app.chat.assistant.nodes.plan_llm",
        lambda state: (_ for _ in ()).throw(AssertionError("planner must not run")),
    )

    result = panel_cost_gate({"thread_id": 7, "session": SimpleNamespace(), "content": "Explain this"})

    assert result["cost_mode"] == "blocked"
    assert result["response"] == (
        "The assistant is temporarily unavailable because the configured usage "
        "limit was reached. Please review cost settings."
    )


def test_conservative_directive_is_added_to_planner_user_prompt(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(
            prompts={"plan": "{{user_input}} {{available_tools}} {{context}}"},
            tools_whitelist=[], persona="persona",
        ),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content='{"kind":"respond","summary":"done"}',
                ))],
            ),
        ))),
    )

    plan_llm({
        "content": "Explain this", "context": {"items": []},
        "cost_mode": "conservative",
        "cost_directive": "Answer concisely; use the minimum necessary context and avoid optional tool calls.",
    })

    assert "Answer concisely" in calls[0]["messages"][-1]["content"]


def test_responder_user_prompt_carries_the_declared_tool_inventory(monkeypatch):
    """The writer of the reply must see the tools the panel sidebar reports.

    The sidebar reads `assistant.tools_whitelist` straight from the registry, so a
    responder that never receives that inventory answers capability questions with a
    denial while the panel advertises 19 tools and available memory.
    """
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs) or [
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))]),
            ],
        ))),
    )

    execute({
        "thread_id": 7,
        "run_id": "run-tools",
        "content": "which tools do you have",
        "plan": {"kind": "respond", "tool": None, "arguments": {}, "requires_approval": False},
        "context": {"items": []},
        "on_token": lambda token: None,
    })

    prompt = calls[0]["messages"][-1]["content"]
    for name in load_assistant_config().tools_whitelist:
        assert name in prompt


def test_responder_user_prompt_forbids_tool_invocation_markup(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs) or [
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))]),
            ],
        ))),
    )

    execute({
        "thread_id": 7,
        "run_id": "run-instructions",
        "content": "which tools do you have",
        "plan": {"kind": "respond", "tool": None, "arguments": {}, "requires_approval": False},
        "context": {"items": []},
        "on_token": lambda token: None,
    })

    prompt = calls[0]["messages"][-1]["content"].lower()
    assert "cannot invoke" in prompt
    assert "must not emit tool-call markup" in prompt


def test_responder_stream_and_persisted_response_strip_split_dsml(monkeypatch):
    bar = "\uff5c"
    streamed = [
        "Answer ",
        f"<{bar}tool_calls{bar}",
        f"{bar}>",
        f'<{bar}invoke name="customers.search"{bar}>',
        f'<{bar}parameter name="query" string="true"{bar}>Ana\n',
        "García",
        f"</{bar}parameter{bar}></{bar}invoke{bar}>",
        f"</{bar}tool_calls{bar}> done",
    ]
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: [
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=token))])
                for token in streamed
            ],
        ))),
    )
    emitted = []

    result = execute({
        "thread_id": 7,
        "run_id": "run-split-dsml",
        "content": "search",
        "plan": {"kind": "respond", "tool": None, "arguments": {}, "requires_approval": False},
        "context": {"items": []},
        "on_token": emitted.append,
    })

    emitted_text = "".join(emitted)
    assert "Ana" not in emitted_text
    assert "García" not in emitted_text
    assert "tool_calls" not in emitted_text
    assert "invoke" not in emitted_text
    assert "Ana" not in result["response"]
    assert "García" not in result["response"]
    assert "tool_calls" not in result["response"]
    assert "invoke" not in result["response"]


def test_denied_approval_keeps_completed_planner_cost_but_never_executes(monkeypatch):
    calls = []
    monkeypatch.setattr("app.chat.assistant.nodes.record_llm_cost", lambda *args, **kwargs: calls.append(kwargs))
    plan = {"kind": "tool", "tool": "automation.create_rule", "arguments": _rule_args(), "requires_approval": True}
    approval = issue_approval(plan)

    with pytest.raises(PermissionError):
        execute({"thread_id": 7, "run_id": "run-denied", "plan": plan, "approval": {**approval, "status": "rejected"}, "session": SimpleNamespace(add=lambda entry: None), "evidence": []})

    assert calls == []


def _memory_plan():
    return {
        "kind": "tool",
        "tool": "memory.write",
        "arguments": {"titulo": "Fact", "contenido": "Panel fact", "topic_key": "agent:fact"},
        "requires_approval": False,
    }


def test_memory_write_guardrail_is_autonomous_for_trusted_thread():
    result = guardrails({"thread_id": 7, "plan": _memory_plan(), "planner": {"valid": True}})

    assert result["status"] == "executing"
    assert result["guardrails"]["approval_required"] is False


def test_memory_write_guardrail_requires_approval_without_trusted_thread():
    result = guardrails({"plan": _memory_plan(), "planner": {"valid": True}})

    assert result["status"] == "approval_pending"
    assert result["guardrails"]["approval_required"] is True


def test_other_write_guardrail_still_requires_approval_with_trusted_thread():
    plan = {"kind": "tool", "tool": "automation.create_rule", "arguments": _rule_args(), "requires_approval": True}

    result = guardrails({"thread_id": 7, "plan": plan, "planner": {"valid": True}})

    assert result["status"] == "approval_pending"
    assert result["guardrails"]["approval_required"] is True


def test_execute_forwards_trusted_thread_to_memory_write(migrated_db):
    with SessionLocal() as session:
        result = execute({
            "thread_id": 7,
            "run_id": "run-memory-write",
            "plan": _memory_plan(),
            "session": session,
            "evidence": [],
        })

        row = session.execute(
            select(Memory).where(Memory.topic_key == "agent:fact", Memory.entity_id == "thread:7")
        ).scalar_one()

    assert result["status"] == "completed"
    assert row.entity_id == "thread:7"


def test_memory_write_is_idempotent_in_db(migrated_db):
    first = _memory_plan()
    with SessionLocal() as session:
        execute({"thread_id": 7, "run_id": "run-memory-first", "plan": first, "session": session, "evidence": []})
        second = {
            **first,
            "arguments": {**first["arguments"], "contenido": "Refreshed fact"},
        }
        execute({"thread_id": 7, "run_id": "run-memory-second", "plan": second, "session": session, "evidence": []})

        rows = session.execute(
            select(Memory).where(Memory.topic_key == "agent:fact", Memory.entity_id == "thread:7")
        ).scalars().all()

    assert len(rows) == 1
    assert rows[0].contenido == "Refreshed fact"


def test_sdb_dispatch_fails_closed_for_memory_write(monkeypatch):
    from app.services import agent_chat

    task = {
        "id": "memory-write",
        "scope": {"proyecto": "default"},
        "summary": "remember fact",
        "verifiable_output": "memory row",
        "tool": "memory.write",
        "arguments": {"titulo": "Fact", "contenido": "Panel fact", "topic_key": "agent:fact"},
    }
    sdb_plan = {"phase": "EXECUTE", "spec": {"sha256": "spec"}, "tasks": [task]}
    approval = issue_approval({"sdb": sdb_plan})
    assert consume_approval(approval, approval["token"])
    thread = SimpleNamespace(
        id=7,
        current_plan={"sdb": sdb_plan},
        assistant_state={"sdb": {"checkpoints": []}, "approval": approval},
    )
    calls = []
    monkeypatch.setattr(agent_chat, "execute_tool", lambda *args, **kwargs: calls.append(args) or {"status": "completed"})
    monkeypatch.setattr(agent_chat, "persist_sdb_state", lambda *args, **kwargs: None)

    result = agent_chat._run_sdb_tasks(SimpleNamespace(), thread, "run-sdb-memory", SimpleNamespace(slug="default"))

    assert result["results"][0]["status"] == "failed"
    assert calls == []


def test_alerts_are_emitted_for_each_scope(monkeypatch):
    alerts = []
    monkeypatch.setattr("app.chat.assistant.nodes.internal_thread_cost_state", lambda *args: (80.0, "conservative"))
    monkeypatch.setattr("app.chat.assistant.nodes.daily_cost_state", lambda *args: (80.0, "conservative"))
    monkeypatch.setattr("app.chat.assistant.nodes.internal_thread_spend", lambda *args: 1.0)
    monkeypatch.setattr("app.chat.assistant.nodes.daily_spend", lambda *args: 2.0)
    monkeypatch.setattr("app.chat.assistant.nodes.maybe_alert_owner", lambda *args, **kwargs: alerts.append(kwargs))

    result = panel_cost_gate({"thread_id": 7, "session": SimpleNamespace()})

    assert result["cost_mode"] == "conservative"
    assert {alert["scope"] for alert in alerts} == {"conversation", "daily"}
