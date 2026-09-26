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


def _tool_loop_state(**overrides):
    state = {
        "thread_id": 7,
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
        first = execute(_tool_loop_state(session=session))
        execute({**_tool_loop_state(session=session), **first, "on_token": lambda _token: None})

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
    denial while the panel advertises every whitelisted tool and available memory.
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


def test_delegated_customer_gathering_answers_with_cross_domain_evidence(migrated_db, monkeypatch):
    from app.chat.assistant.graph import run_assistant
    from app.models import (
        Appointment,
        AppointmentStatus,
        Case,
        Conversation,
        Customer,
        InternalChatThread,
        User,
        UserRole,
    )

    now = datetime.now(timezone.utc)
    appointment_start = now + timedelta(days=5)
    with SessionLocal() as session:
        user = User(username="delegate-harness-admin", password_hash="test", role=UserRole.ADMIN)
        session.add(user)
        session.flush()
        customer = Customer(phone_e164="+56900009991", name="Ana Example")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        case = Case(
            conversation_id=conversation.id,
            customer_id=customer.id,
            service="water-heater repair",
            status="open",
            summary="No hot water",
        )
        session.add(case)
        session.flush()
        appointment = Appointment(
            service="water-heater repair",
            customer_id=customer.id,
            case_id=case.id,
            technician_id=user.id,
            local_start=appointment_start.replace(tzinfo=None),
            timezone="UTC",
            starts_at=appointment_start,
            ends_at=appointment_start + timedelta(hours=1),
            duration_minutes=60,
            status=AppointmentStatus.BOOKED,
        )
        thread = InternalChatThread(user_id=user.id, title="Delegation integration")
        session.add_all([appointment, thread])
        session.flush()
        thread_id, user_id, case_id, appointment_id, customer_id = (
            thread.id, user.id, case.id, appointment.id, customer.id
        )
        session.commit()

        plans = iter([
            json.dumps({
                "kind": "delegate", "sub_agent": "customer_records",
                "summary": "Gather open cases and upcoming appointments.",
            }),
            json.dumps({
                "kind": "tool", "tool": "cases.list", "arguments": {"limit": 10},
                "summary": "Find open cases.", "requires_approval": False,
            }),
            json.dumps({
                "kind": "tool", "tool": "appointments.upcoming", "arguments": {"limit": 10},
                "summary": "Find upcoming appointments.", "requires_approval": False,
            }),
        ])
        provider_calls = []
        responder_text = (
            f"Customer ID {customer_id} has an open water-heater repair case and an appointment in five days. "
            "[cases.list] [appointments.upcoming]"
        )

        class Provider:
            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        provider_calls.append(kwargs)
                        if kwargs.get("stream"):
                            return [SimpleNamespace(choices=[SimpleNamespace(
                                delta=SimpleNamespace(content=responder_text)
                            )])]
                        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                            content=next(plans)
                        ))])

        monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: Provider())
        result = run_assistant(
            thread_id=thread_id,
            user_id=user_id,
            content="Which customers have open cases and an appointment in the next 30 days?",
            run_id="delegated-cross-domain",
            session=session,
            context={"items": [], "meta": {}},
            on_token=lambda _token: None,
        )

    assert result["plan"]["kind"] == "delegate"
    assert result["delegation"]["sub_agent"] == "customer_records"
    assert result["delegation"]["steps"] == 2
    assert [item["tool"] for item in result["tool_results"]] == ["cases.list", "appointments.upcoming"]
    case_result = result["tool_results"][0]["result"]
    appointment_result = result["tool_results"][1]["result"]
    assert any(item["id"] == case_id and item["customer_id"] == customer_id for item in case_result)
    assert any(item["id"] == appointment_id and item["customer_id"] == customer_id for item in appointment_result)
    assert f"Customer ID {customer_id}" in result["response"]
    assert "[cases.list]" in result["response"]
    assert "[appointments.upcoming]" in result["response"]
    responder_prompt = provider_calls[-1]["messages"][-1]["content"]
    assert str(case_id) in responder_prompt and "water-heater repair" in responder_prompt
    assert f'"id": {appointment_id}' in responder_prompt
    assert f'"customer_id": {customer_id}' in responder_prompt


def test_delegated_customer_operational_history_uses_real_bounded_projection(migrated_db, monkeypatch):
    from app.chat.assistant.graph import run_assistant
    from app.models import (
        Appointment,
        AppointmentStatus,
        Case,
        Conversation,
        Customer,
        CustomerNote,
        InternalChatThread,
        Message,
        MessageDirection,
        User,
        UserRole,
    )

    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        user = User(username="drilldown-harness-admin", password_hash="test", role=UserRole.ADMIN)
        session.add(user)
        session.flush()
        customer = Customer(
            phone_e164="+56900009992", name="Drilldown Example", email="private@example.test",
            address="Private address", comuna="Private comuna", consent_status=True,
        )
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        closed_case = Case(
            conversation_id=conversation.id, customer_id=customer.id, service="closed service",
            priority="high", status="closed", summary="Closed case summary",
            created_at=now - timedelta(days=20), closed_at=now - timedelta(days=10),
        )
        open_case = Case(
            conversation_id=conversation.id, customer_id=customer.id, service="open service",
            priority="normal", status="open", summary="Open case summary",
        )
        session.add_all([closed_case, open_case])
        session.flush()
        past_start = now - timedelta(days=5)
        future_start = now + timedelta(days=5)
        past_appointment = Appointment(
            service="closed service", customer_id=customer.id, case_id=closed_case.id,
            technician_id=user.id, local_start=past_start.replace(tzinfo=None), timezone="UTC",
            starts_at=past_start, ends_at=past_start + timedelta(hours=1), duration_minutes=60,
            status=AppointmentStatus.COMPLETED,
        )
        future_appointment = Appointment(
            service="open service", customer_id=customer.id, case_id=open_case.id,
            technician_id=user.id, local_start=future_start.replace(tzinfo=None), timezone="UTC",
            starts_at=future_start, ends_at=future_start + timedelta(hours=1), duration_minutes=60,
            status=AppointmentStatus.BOOKED,
        )
        thread = InternalChatThread(user_id=user.id, title="Customer drill-down")
        session.add_all([
            past_appointment,
            future_appointment,
            thread,
            Message(
                conversation_id=conversation.id, direction=MessageDirection.INBOUND,
                text="PRIVATE_MESSAGE_SENTINEL", media_url="https://private.example.test/media",
            ),
            CustomerNote(customer_id=customer.id, note="PRIVATE_NOTE_SENTINEL", author="admin"),
        ])
        session.flush()
        thread_id, user_id, customer_id = thread.id, user.id, customer.id
        closed_case_id, open_case_id = closed_case.id, open_case.id
        past_appointment_id, future_appointment_id = past_appointment.id, future_appointment.id
        session.commit()

        plans = iter([
            json.dumps({
                "kind": "delegate", "sub_agent": "customer_records",
                "summary": "Find this customer's operational history.",
            }),
            json.dumps({
                "kind": "tool", "tool": "customers.search", "arguments": {"query": "Drilldown Example"},
                "summary": "Resolve the customer.", "requires_approval": False,
            }),
            json.dumps({
                "kind": "tool", "tool": "customers.operational_history",
                "arguments": {"customer_id": customer_id, "limit": 10},
                "summary": "Read all cases and appointments.", "requires_approval": False,
            }),
        ])
        provider_calls = []

        class Provider:
            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        provider_calls.append(kwargs)
                        if kwargs.get("stream"):
                            return [SimpleNamespace(choices=[SimpleNamespace(
                                delta=SimpleNamespace(content="Operational history gathered.")
                            )])]
                        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                            content=next(plans)
                        ))])

        monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: Provider())
        result = run_assistant(
            thread_id=thread_id,
            user_id=user_id,
            content="Show this customer's cases and appointments.",
            run_id="delegated-customer-operational-history",
            session=session,
            context={"items": [], "meta": {}},
            on_token=lambda _token: None,
        )

    assert result["delegation"]["steps"] == 2
    assert result["delegation"]["cap"] == 2
    assert [item["tool"] for item in result["tool_results"]] == [
        "customers.search", "customers.operational_history",
    ]
    assert result["tool_results"][0]["result"][0]["id"] == customer_id
    drilldown = result["tool_results"][1]["result"]
    cases = drilldown["cases"]
    appointments = drilldown["appointments"]
    assert {item["id"] for item in cases} == {closed_case_id, open_case_id}
    assert {item["id"] for item in appointments} == {past_appointment_id, future_appointment_id}
    assert next(item for item in cases if item["id"] == closed_case_id)["closed_at"] is not None
    assert next(item for item in appointments if item["id"] == past_appointment_id)["starts_at"]
    assert all({"created_at", "priority", "status", "summary"} <= item.keys() for item in cases)
    assert all({"local_start", "timezone", "starts_at", "ends_at", "status"} <= item.keys()
               for item in appointments)
    serialized = json.dumps(result["tool_results"][1], ensure_ascii=False)
    for forbidden in (
        "phone_e164", "email", "address", "comuna", "consent_status", "media_url",
        "PRIVATE_MESSAGE_SENTINEL", "PRIVATE_NOTE_SENTINEL",
    ):
        assert forbidden not in serialized
    assert len(cases) <= 10
    assert len(appointments) <= 10
    assert len(serialized) <= 4_000
    assert sum(not call.get("stream") for call in provider_calls) == 3


def test_customer_search_real_database_payload_excludes_private_fields(migrated_db):
    from app.models import Customer

    with SessionLocal() as session:
        customer = Customer(
            phone_e164="+56900009993", name="PII Search Example", email="private@example.test",
            address="Private address", comuna="Private comuna", consent_status=True,
        )
        second_customer = Customer(
            phone_e164="+56900009994", name="PII Search Example Two", email="second@example.test",
            address="Second private address", comuna="Second private comuna", consent_status=True,
        )
        session.add_all([customer, second_customer])
        session.flush()
        customer_id = customer.id
        payload = execute_tool(
            session, "customers.search", {"query": "PII Search Example"},
            whitelist={"customers.search"},
        )
        phone_match = execute_tool(
            session, "customers.search", {"query": "00009993"},
            whitelist={"customers.search"},
        )["result"]
        bounded = execute_tool(
            session, "customers.search", {"query": "PII Search", "limit": 1},
            whitelist={"customers.search"},
        )["result"]

    assert payload["status"] == "completed"
    assert {"id": customer_id, "name": "PII Search Example", "state": "nuevo"} in payload["result"]
    assert all(set(row) == {"id", "name", "state"} for row in payload["result"])
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("phone_e164", "email", "address", "comuna", "consent_status", "consent_at"):
        assert forbidden not in serialized
    assert [row["id"] for row in phone_match] == [customer_id]
    assert len(bounded) == 1


def test_memory_read_still_rejects_an_entity_the_prompt_no_longer_orders():
    result = guardrails({
        "thread_id": 7,
        "plan": _memory_read_plan(scope="panel", entity_id="thread:7"),
        "planner": {"valid": True},
    })

    assert result["guardrails"]["arguments_valid"] is False
    assert result["guardrails"]["decision"] == "fallback"
    assert result["status"] == "responding"


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
            select(Memory).where(Memory.topic_key == "agent:fact", Memory.entity_id == "agent:default")
        ).scalar_one()

    assert result["status"] == "completed"
    assert row.scope == "agent"
    assert row.entity_id == "agent:default"
    assert row.visibility.value == "global"


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
            "thread_id": 7,
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
        execute({"thread_id": 7, "run_id": "run-memory-first", "plan": first, "session": session, "evidence": []})
        second = {
            **first,
            "arguments": {**first["arguments"], "contenido": "Refreshed fact"},
        }
        execute({"thread_id": 7, "run_id": "run-memory-second", "plan": second, "session": session, "evidence": []})

        rows = session.execute(
            select(Memory).where(Memory.topic_key == "agent:fact", Memory.entity_id == "agent:default")
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
