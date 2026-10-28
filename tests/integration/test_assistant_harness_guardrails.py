"""Ordered assistant guardrail contracts for typed tool execution."""

import json
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.nodes import (
    _planner_tool_catalog,
    execute,
    guardrails,
    panel_cost_gate,
    plan_llm,
    tool_loop_head,
)
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.db import SessionLocal
from app.models import AuditLog, Memory, MemoryProducer, MemoryType, MemoryVisibility
from app.services.prompts import load_assistant_config
from sqlalchemy import select


def _rule_args():
    return {
        "recipe_id": "appointment_confirmation",
        "parameters": {"channel": "whatsapp"},
    }


def test_whitelist_rejects_before_handler(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.customers.search_customers",
        lambda *args: called.append(args),
    )
    with pytest.raises(ToolValidationError, match="not whitelisted"):
        execute_tool(SimpleNamespace(), "customers.search", {"query": "Ana"}, whitelist=set(), role="admin")
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
            role="admin",
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
            role="admin",
        )
    assert called == []


def test_write_requires_exact_consumed_approval_before_handler(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.automation_installations.install",
        lambda *args, **kwargs: called.append((args, kwargs)),
    )
    approval = issue_approval({"tool": "automation.create_rule", "arguments": _rule_args()})
    with pytest.raises(ToolValidationError, match="approval"):
        execute_tool(
            SimpleNamespace(),
            "automation.create_rule",
            {**_rule_args(), "parameters": {"channel": "email"}},
            whitelist={"automation.create_rule"},
            approval={**approval, "status": "consumed"},
            role="admin",
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
            "actor_role": "admin",
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


def _tool_loop_state(*, actor_role: str, **overrides):
    state = {
        "actor_role": actor_role,
        "thread_id": 7,
        "user_id": 7,
        "run_id": "run-tool-loop",
        "content": "Find Ana",
        "plan": {
            "kind": "tool",
            "tool": "customers.search",
            "arguments": {"query": "Ana"},
            "requires_approval": False,
        },
        "guardrails": {"cost_allowed": True},
        "evidence": [],
    }
    state.update(overrides)
    return state


def _streaming_client(calls, text="Ana is a customer"):
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: calls.append(kwargs)
                or [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])]
            )
        )
    )


def test_web_search_snippets_are_grounded_and_cited(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: {
            "tool": "web.search",
            "status": "completed",
            "result": [
                {
                    "title": "Boiler maintenance guidance",
                    "url": "https://example.test/boiler",
                    "snippet": "Annual maintenance reduces breakdown risk.",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: _streaming_client(calls, text="Annual maintenance reduces breakdown risk. https://example.test/boiler"),
    )

    state = _tool_loop_state(
        actor_role="admin",
        content="What does the web say about boiler maintenance?",
        plan={
            "kind": "tool",
            "tool": "web.search",
            "arguments": {"query": "boiler maintenance"},
            "requires_approval": False,
        },
    )
    first = execute(state)
    execute({**state, **first, "on_token": lambda _token: None})

    prompt = calls[0]["messages"][-1]["content"]
    assert "Annual maintenance reduces breakdown risk." in prompt
    assert "https://example.test/boiler" in prompt


def test_web_search_failure_is_visible_instead_of_empty_evidence(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: {
            "tool": "web.search",
            "status": "error",
            "error": "search provider timed out",
            "evidence": {"tool": "web.search", "status": "error"},
        },
    )

    result = execute(_tool_loop_state(
        actor_role="admin",
        content="Search the web for boiler maintenance.",
        plan={
            "kind": "tool",
            "tool": "web.search",
            "arguments": {"query": "boiler maintenance"},
            "requires_approval": False,
        },
    ))

    assert result["status"] == "degraded"
    assert result["tool_result"]["status"] == "error"
    assert result["tool_result"]["evidence"]["status"] == "error"


def test_a_chained_search_then_fetch_turn_answers_from_the_page_text_and_cites_it(monkeypatch):
    """`web.search` finds the page, `web.fetch` reads it, and the answer comes from the page text.

    The chain is proven rather than assumed: `tool_loop_head` must take the back-edge after the
    search because the planner asked for a follow-up, and must finish after the fetch. A reader that
    never became reachable, or a chain that quietly stopped at the snippets, fails here.
    """
    calls = []
    page_url = "https://example.test/boiler"
    page_text = "Annual maintenance reduces breakdown risk. Book a technician every twelve months."
    results = {
        "web.search": {
            "tool": "web.search",
            "status": "completed",
            "result": [
                {
                    "title": "Boiler maintenance",
                    "url": page_url,
                    "snippet": "Annual maintenance reduces breakdown risk.",
                }
            ],
        },
        "web.fetch": {
            "tool": "web.fetch",
            "status": "completed",
            "result": {"url": page_url, "title": "Boiler maintenance", "text": page_text},
        },
    }
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda _session, name, _arguments, **_kwargs: results[name],
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: _streaming_client(calls, text=f"{page_text} {page_url}"),
    )

    content = "What does the web say about boiler maintenance?"
    search_state = _tool_loop_state(
        actor_role="admin",
        content=content,
        plan={
            "kind": "tool",
            "tool": "web.search",
            "arguments": {"query": "boiler maintenance"},
            "requires_approval": False,
            "follow_up": True,
        },
    )
    searched = execute(search_state)
    assert tool_loop_head({**search_state, **searched})["status"] == "planned"

    fetch_state = {
        **search_state,
        **searched,
        "status": "executing",
        "plan": {
            "kind": "tool",
            "tool": "web.fetch",
            "arguments": {"url": page_url},
            "requires_approval": False,
        },
    }
    fetched = execute(fetch_state)
    assert tool_loop_head({**fetch_state, **fetched})["status"] == "completed"
    assert [entry["tool"] for entry in fetched["tool_results"]] == ["web.search", "web.fetch"]

    execute({**fetch_state, **fetched, "on_token": lambda _token: None})

    prompt = calls[0]["messages"][-1]["content"]
    assert page_text in prompt
    assert page_url in prompt


def test_a_refused_fetch_url_reaches_the_turn_as_an_explicit_error():
    """A blocked URL must fail visibly, never as an empty result.

    This runs the real `execute_tool` and the real policy: the loopback address is refused while
    resolving, before any client is built, so the assertion covers the registry wiring and the
    reader's refusal together without touching the network.
    """
    result = execute(_tool_loop_state(
        actor_role="admin",
        content="Read http://127.0.0.1/admin and summarise it.",
        plan={
            "kind": "tool",
            "tool": "web.fetch",
            "arguments": {"url": "http://127.0.0.1/admin"},
            "requires_approval": False,
        },
    ))

    assert result["status"] == "degraded"
    assert result["tool_result"]["status"] == "error"
    assert "non-public address 127.0.0.1" in result["tool_result"]["error"]
    assert result["evidence"][0]["status"] == "degraded"
    assert result["tool_result"]["result"]["unavailable"] is True


def test_completed_tool_traversal_records_one_execution_audit(monkeypatch, migrated_db):
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: {
            "tool": "customers.search",
            "status": "completed",
            "result": [{"id": 1, "name": "Ana"}],
        },
    )
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: _streaming_client(calls))

    with SessionLocal() as session:
        first = execute(_tool_loop_state(actor_role="admin", session=session))
        execute({**_tool_loop_state(actor_role="admin", session=session), **first, "on_token": lambda _token: None})

        session.flush()
        audits = session.scalars(
            select(AuditLog).where(AuditLog.action == "internal_chat.execution")
        ).all()

    assert len(audits) == 1
    assert audits[0].after == {
        "run_id": "run-tool-loop",
        "tool": "customers.search",
        "status": "completed",
    }


def test_memory_read_orm_result_is_readable_tool_evidence(monkeypatch, migrated_db):
    calls = []
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: _streaming_client(calls))

    with SessionLocal() as session:
        session.add(
            Memory(
                proyecto="default",
                scope="panel",
                entity_id="thread:7",
                tipo=MemoryType.DISCOVERY,
                titulo="Billing preference",
                contenido="Customer prefers email receipts",
                topic_key="billing-preference",
                embedding=[0.0] * 384,
            )
        )
        session.commit()

        tool_state = _tool_loop_state(
            actor_role="admin",
            session=session,
            plan={
                "kind": "tool",
                "tool": "memory.read",
                "arguments": {"scope": "own"},
                "requires_approval": False,
            },
        )
        first = execute(tool_state)
        execute({**tool_state, **first, "on_token": lambda _token: None})

    assert first["tool_result"]["result"][0]["titulo"] == "Billing preference"
    prompt = calls[0]["messages"][-1]["content"]
    evidence = prompt.split("<tool_evidence>", 1)[1].split("</tool_evidence>", 1)[0]
    assert "Billing preference" in evidence
    assert "Customer prefers email receipts" in evidence
    assert "<... object at 0x...>" not in evidence
    assert "sqlalchemy" not in evidence.lower()


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
        lambda **_kwargs: SimpleNamespace(
            prompts={"plan": "{{user_input}} {{available_tools}} {{context}}"},
            tools_whitelist=[], persona="persona", skills=(),
        ),
    )
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda **_kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
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
    denial while the panel advertises every whitelisted tool and available memory.
    """
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda **_kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs) or [
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))]),
            ],
        ))),
    )

    execute({
        "thread_id": 7,
        "actor_role": "admin",
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
        lambda **_kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs) or [
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))]),
            ],
        ))),
    )

    execute({
        "thread_id": 7,
        "actor_role": "admin",
        "run_id": "run-instructions",
        "content": "which tools do you have",
        "plan": {"kind": "respond", "tool": None, "arguments": {}, "requires_approval": False},
        "context": {"items": []},
        "on_token": lambda token: None,
    })

    prompt = calls[0]["messages"][-1]["content"].lower()
    assert "must not emit tool-call markup" in prompt
    assert "cannot invoke" not in prompt
    assert "never state that you cannot use or execute them" in prompt


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
        lambda **_kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: [
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=token))])
                for token in streamed
            ],
        ))),
    )
    emitted = []

    result = execute({
        "thread_id": 7,
        "actor_role": "admin",
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
        execute({"actor_role": "admin", "thread_id": 7, "run_id": "run-denied", "plan": plan, "approval": {**approval, "status": "rejected"}, "session": SimpleNamespace(add=lambda entry: None), "evidence": []})

    assert calls == []


def _memory_plan():
    return {
        "kind": "tool",
        "tool": "memory.write",
        "arguments": {
            "titulo": "Fact",
            "contenido": "Project fact",
            "topic_key": "agent:fact",
            "tipo": "decision",
        },
        "requires_approval": False,
    }


def test_memory_write_guardrail_is_autonomous_for_trusted_thread():
    result = guardrails({"thread_id": 7, "plan": _memory_plan(), "planner": {"valid": True}})

    assert result["status"] == "executing"
    assert result["guardrails"]["approval_required"] is False


def test_assistant_capabilities_guardrail_is_read_only_without_approval():
    result = guardrails({
        "thread_id": 7,
        "plan": {
            "kind": "tool",
            "tool": "assistant.capabilities",
            "arguments": {},
            "requires_approval": False,
        },
        "planner": {"valid": True},
    })

    assert result["status"] == "executing"
    assert result["guardrails"]["approval_required"] is False


def test_memory_write_guardrail_requires_approval_without_trusted_thread():
    result = guardrails({"plan": _memory_plan(), "planner": {"valid": True}})

    assert result["status"] == "approval_pending"
    assert result["guardrails"]["approval_required"] is True


@pytest.mark.parametrize("tool", ["memory.update", "memory.delete"])
def test_memory_correction_guardrail_matches_memory_write_autonomy(tool):
    plan = {
        "kind": "tool",
        "tool": tool,
        "arguments": {"id": 4, "titulo": "Fixed"} if tool.endswith("update") else {"id": 4},
        "requires_approval": False,
    }
    assert guardrails({"thread_id": 7, "plan": plan, "planner": {"valid": True}})["status"] == "executing"
    assert guardrails({"plan": plan, "planner": {"valid": True}})["status"] == "approval_pending"


def _memory_read_plan(**arguments):
    return {"kind": "tool", "tool": "memory.read", "arguments": arguments, "requires_approval": False}


def _advertised_memory_read_variants() -> dict:
    """The per-scope variants the planner can actually read from the catalog."""
    catalog = json.loads(_planner_tool_catalog(["memory.read"]))
    schema = next(entry["arguments"] for entry in catalog if entry["name"] == "memory.read")
    assert "$defs" in schema, "the catalog announces no per-scope variant"
    return {variant["properties"]["scope"]["const"]: variant for variant in schema["$defs"].values()}


def _memory_read_arguments_from_schema(variant: dict) -> dict:
    properties = variant["properties"]
    arguments = {"scope": properties["scope"]["const"], "topic": "agent:fact"}
    entity_schema = properties.get("entity_id")
    if entity_schema and "pattern" in entity_schema:
        entity_id = "customer:42"
        assert re.fullmatch(entity_schema["pattern"], entity_id)
        arguments["entity_id"] = entity_id
    return arguments


def test_memory_read_plan_derived_from_the_advertised_schema_survives_guardrails():
    variants = _advertised_memory_read_variants()

    own = guardrails({
        "thread_id": 7,
        "plan": _memory_read_plan(**_memory_read_arguments_from_schema(variants["own"])),
        "planner": {"valid": True},
    })
    customer = guardrails({
        "thread_id": 7,
        "plan": _memory_read_plan(**_memory_read_arguments_from_schema(variants["customer"])),
        "planner": {"valid": True},
    })

    assert own["status"] == "executing"
    assert customer["status"] == "executing"


@pytest.mark.parametrize("tool", ["memory.update", "memory.delete"])
def test_execute_forwards_trusted_thread_to_memory_correction(migrated_db, tool):
    with SessionLocal() as session:
        row = Memory(
            proyecto="default",
            scope="agent",
            entity_id="agent:default",
            tipo=MemoryType.DISCOVERY,
            titulo="Original",
            contenido="Original content",
            topic_key=f"agent:correction-{tool.rsplit('.', 1)[-1]}",
            embedding=[0.0] * 384,
            producer=MemoryProducer.AGENT,
            visibility=MemoryVisibility.GLOBAL,
        )
        session.add(row)
        session.flush()
        memory_id = row.id
        result = execute({
            "actor_role": "admin",
            "thread_id": 7,
            "user_id": 7,
            "run_id": "run-memory-correction",
            "plan": {
                "kind": "tool",
                "tool": tool,
                "arguments": {"id": memory_id, "titulo": "Fixed"} if tool.endswith("update") else {"id": memory_id},
                "requires_approval": False,
            },
            "session": session,
            "evidence": [],
        })
        assert result["status"] == "completed"
        assert result["tool_result"]["result"]["id"] == memory_id
        assert session.get(Memory, memory_id) is None if tool.endswith("delete") else session.get(Memory, memory_id).titulo == "Fixed"


def test_memory_write_is_idempotent_in_db(migrated_db):
    first = _memory_plan()
    with SessionLocal() as session:
        execute({"actor_role": "admin", "thread_id": 7, "user_id": 7, "run_id": "run-memory-first", "plan": first, "session": session, "evidence": []})
        second = {
            **first,
            "arguments": {**first["arguments"], "contenido": "Refreshed fact"},
        }
        execute({"actor_role": "admin", "thread_id": 7, "user_id": 7, "run_id": "run-memory-second", "plan": second, "session": session, "evidence": []})

        rows = session.execute(
            select(Memory).where(Memory.topic_key == "agent:fact", Memory.entity_id == "agent:default")
        ).scalars().all()

    assert len(rows) == 1
    assert rows[0].contenido == "Refreshed fact"


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


def test_technician_upcoming_appointments_are_scoped_to_the_caller(migrated_db):
    """U3.2: a technician observes only their own appointments (D3)."""
    from app.models import Appointment, AppointmentStatus, Case, Conversation, Customer, User, UserRole

    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        tech_a = User(username="scope-tech-a", password_hash="test", role=UserRole.TECNICO)
        tech_b = User(username="scope-tech-b", password_hash="test", role=UserRole.TECNICO)
        session.add_all([tech_a, tech_b])
        session.flush()
        customer = Customer(phone_e164="+56900009977", name="Scope Customer")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        case = Case(
            conversation_id=conversation.id,
            customer_id=customer.id,
            service="scope check",
            status="open",
            summary="Scope check",
        )
        session.add(case)
        session.flush()

        def _appointment(technician_id, offset_days):
            start = now + timedelta(days=offset_days)
            return Appointment(
                service="scope check",
                customer_id=customer.id,
                case_id=case.id,
                technician_id=technician_id,
                local_start=start.replace(tzinfo=None),
                timezone="UTC",
                starts_at=start,
                ends_at=start + timedelta(hours=1),
                duration_minutes=60,
                status=AppointmentStatus.BOOKED,
            )

        own = _appointment(tech_a.id, 2)
        foreign = _appointment(tech_b.id, 3)
        session.add_all([own, foreign])
        session.flush()
        own_id, foreign_id = own.id, foreign.id
        tech_a_id, tech_b_id = tech_a.id, tech_b.id
        session.commit()

    with SessionLocal() as session:
        mine = execute_tool(
            session, "appointments.upcoming", {"limit": 10}, role="tecnico", owner_id=tech_a_id
        )
        mine_ids = [item["id"] for item in mine["result"]]
        assert own_id in mine_ids
        assert foreign_id not in mine_ids

        # The other technician sees their own appointment, never mine.
        theirs = execute_tool(
            session, "appointments.upcoming", {"limit": 10}, role="tecnico", owner_id=tech_b_id
        )
        assert [item["id"] for item in theirs["result"]] == [foreign_id]

        # admin and operador keep the mapped, unfiltered agenda view.
        for role in ("admin", "operador"):
            staff = execute_tool(
                session, "appointments.upcoming", {"limit": 10}, role=role, owner_id=tech_a_id
            )
            staff_ids = [item["id"] for item in staff["result"]]
            assert own_id in staff_ids and foreign_id in staff_ids
