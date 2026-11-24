"""Provider calls must fit the panel database transaction budget."""

import re
from types import SimpleNamespace

import pytest

from app.chat.assistant import nodes
from app.services import llm


class SpySession:
    def __init__(self):
        self.active = True
        self.events = []

    def in_transaction(self):
        return self.active

    def commit(self):
        self.events.append("commit")
        self.active = False


def _planner_config(monkeypatch):
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda **_kwargs: SimpleNamespace(
            prompts={"plan": "{{user_input}}"}, tools_whitelist=[], skills=(), persona="persona"
        ),
    )


def _completion(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_plan_llm_releases_transaction_before_first_provider_call(monkeypatch):
    _planner_config(monkeypatch)
    session = SpySession()

    def create(**_kwargs):
        assert not session.active, "planner provider call began with an open transaction"
        session.events.append("provider")
        return _completion('{"kind":"respond","summary":"ok"}')

    monkeypatch.setattr(nodes, "_assistant_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    ))
    nodes.plan_llm({"content": "hello", "context": {"items": []}, "session": session,
                    "request_message_id": None})

    assert session.events == ["commit", "provider"]


def test_plan_llm_releases_again_before_repair_provider_call(monkeypatch):
    _planner_config(monkeypatch)
    session = SpySession()
    calls = 0

    def create(**_kwargs):
        nonlocal calls
        calls += 1
        assert not session.active, f"planner provider call {calls} began with an open transaction"
        session.events.append(f"provider-{calls}")
        if calls == 1:
            session.active = True  # record_llm_cost writes after the first completion
            return _completion('{"kind":"tool"}')
        return _completion('{"kind":"respond","summary":"repaired"}')

    monkeypatch.setattr(nodes, "_assistant_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    ))
    nodes.plan_llm({"content": "hello", "context": {"items": []}, "session": session,
                    "request_message_id": None})

    assert session.events == ["commit", "provider-1", "commit", "provider-2"]


def test_responder_releases_transaction_before_streaming_provider_call(monkeypatch):
    session = SpySession()
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda **_kwargs: SimpleNamespace(
            prompts={"respond": "{{user_input}}"}, tools_whitelist=[], skills=(), persona="persona"
        ),
    )

    class Stream:
        def __iter__(self):
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="hello"))])

    def create(**_kwargs):
        assert not session.active, "responder provider call began with an open transaction"
        session.events.append("provider")
        return Stream()

    monkeypatch.setattr(nodes, "_assistant_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    ))
    monkeypatch.setattr(nodes, "record_audit", lambda *args, **kwargs: None)
    nodes.execute({
        "plan": {"kind": "respond", "tool": None, "arguments": {}, "requires_approval": False},
        "content": "hello", "session": session, "thread_id": 1, "run_id": "r1",
        "on_token": lambda _token: None, "request_message_id": None,
    })

    assert session.events == ["commit", "provider"]


def test_llm_retry_budget_is_strictly_below_database_idle_transaction_guard():
    from pathlib import Path

    migration = Path("db/migrations/070_session_safety.sql").read_text(encoding="utf-8")
    match = re.search(r"'([0-9]+)s'", migration)
    assert match, "migration must declare idle_in_transaction_session_timeout in seconds"
    guard_seconds = int(match.group(1))

    import openai

    total_seconds = (1 + llm.LLM_MAX_RETRIES) * llm.LLM_TIMEOUT_SECONDS
    assert total_seconds < guard_seconds
    assert llm.LLM_MAX_RETRIES != openai.DEFAULT_MAX_RETRIES, "the SDK default must not be in play"
    assert total_seconds <= guard_seconds * 0.8, "client budget needs meaningful margin below the DB guard"


def test_openai_client_passes_an_explicit_retry_limit(monkeypatch):
    captured = {}
    monkeypatch.setattr(llm, "get_settings", lambda: SimpleNamespace(
        chat_provider="deepseek", openrouter_api_key=None
    ))
    monkeypatch.setattr(llm, "resolve_model_api_key", lambda: "test-key")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(llm, "OpenAI", FakeOpenAI)
    llm.openai_client()

    assert captured["max_retries"] == llm.LLM_MAX_RETRIES


def test_failed_orphan_records_bounded_reason_audit_and_preserves_operator_copy(monkeypatch):
    from datetime import datetime, timezone
    from app.services import agent_chat

    class Session:
        def __init__(self):
            self.message = SimpleNamespace(status="processing", error=None, completed_at=None)

        def scalar(self, _query):
            return self.message

        def begin_nested(self):
            from contextlib import nullcontext

            return nullcontext()

        def flush(self):
            pass

    session = Session()
    thread = SimpleNamespace(
        id=17, active_run_id="run-1",
        assistant_state={"live": {"run_id": "run-1", "status": "running"}},
    )
    audit = []
    monkeypatch.setattr(agent_chat, "record_audit", lambda *args, **kwargs: audit.append(kwargs))
    reason = agent_chat._failed_run_reason(RuntimeError("database unavailable"), "private operator message")

    assert agent_chat._fail_orphaned_run(
        session, thread, now=datetime.now(timezone.utc), run_id="run-1", reason=reason
    )

    assert thread.assistant_state["live"]["reason"] == "RuntimeError: database unavailable"
    assert len(audit) == 1
    assert audit[0]["action"] == "internal_chat.run_failed"
    assert audit[0]["entity"] == "internal_chat_thread"
    assert audit[0]["after"] == {
        "run_id": "run-1", "reason": "RuntimeError: database unavailable", "stage": "failed"
    }
    assert session.message.error == "El agente no pudo procesar este mensaje. Reinténtalo."


def test_failed_orphan_survives_a_rejected_audit_write(monkeypatch):
    """The failure path must still terminalise the run when the audit row is refused."""
    from contextlib import nullcontext
    from datetime import datetime, timezone
    from sqlalchemy.exc import OperationalError

    from app.services import agent_chat

    class Session:
        def __init__(self):
            self.message = SimpleNamespace(status="processing", error=None, completed_at=None)

        def scalar(self, _query):
            return self.message

        def begin_nested(self):
            return nullcontext()

        def flush(self):
            pass

    session = Session()
    thread = SimpleNamespace(
        id=19, active_run_id="run-3",
        assistant_state={"live": {"run_id": "run-3", "status": "running"}},
    )
    monkeypatch.setattr(
        agent_chat, "record_audit",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OperationalError("INSERT INTO audit_log ...", {}, Exception("audit unavailable"))
        ),
    )

    assert agent_chat._fail_orphaned_run(
        session, thread, now=datetime.now(timezone.utc), run_id="run-3", reason="RuntimeError: boom"
    )

    assert session.message.status == "failed"
    assert session.message.error == "El agente no pudo procesar este mensaje. Reinténtalo."
    assert thread.assistant_state["live"]["reason"] == "RuntimeError: boom"
    assert thread.assistant_state["live"]["status"] == "failed"


def test_resume_turn_never_releases_before_the_provider_call(monkeypatch):
    """S1 exception: the approved-write resume keeps its single transaction."""
    _planner_config(monkeypatch)
    session = SpySession()

    def create(**_kwargs):
        assert session.active, "resume must keep the turn's transaction open"
        session.events.append("provider")
        return _completion('{"kind":"respond","summary":"ok"}')

    monkeypatch.setattr(nodes, "_assistant_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    ))
    nodes.plan_llm({"content": "hello", "context": {"items": []}, "session": session,
                    "request_message_id": None, "resume": True})

    assert session.events == ["provider"]


def test_verification_releases_transaction_before_each_verifier_call(monkeypatch):
    """S1: the verifier is a provider caller too, and it runs inside verify_effects."""
    session = SpySession()

    def create(**_kwargs):
        assert not session.active, "verifier call began with an open transaction"
        session.events.append(f"provider-{len([e for e in session.events if e.startswith('provider')]) + 1}")
        if len([e for e in session.events if e.startswith("provider")]) == 1:
            session.active = True  # the read-only tool reads the database
            tool_call = SimpleNamespace(
                id="call-1", function=SimpleNamespace(name="list_project_files", arguments="{}")
            )
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=None, tool_calls=[tool_call])
            )])
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content='{"status":"confirmed","reason":"ok"}', tool_calls=[])
        )])

    monkeypatch.setattr(nodes, "_assistant_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    ))
    monkeypatch.setattr(nodes, "execute_tool", lambda *args, **kwargs: {"result": []})
    nodes.verify_effects({
        "session": session, "thread_id": 1, "run_id": "r1",
        "tool_results": [{"tool": "memory.update", "result": {}}],
        "verify_requested": True,
        "plan": {"success_criterion": "the record exists"},
        "evidence": [],
    })

    assert session.events == ["commit", "provider-1", "commit", "provider-2"]


def test_failed_run_reason_redacts_repr_escaped_operator_content():
    from app.services.agent_chat import _failed_run_reason

    operator = "failed on line1\npayroll ACME"
    reason = _failed_run_reason(RuntimeError(repr(operator)), operator)

    assert "ACME" not in reason
    assert reason.startswith("RuntimeError:")


def test_failed_run_reason_redacts_operator_content_and_structured_payloads():
    from app.services.agent_chat import _failed_run_reason

    reason = _failed_run_reason(RuntimeError('failed for "private operator message"'), "private operator message")
    payload_reason = _failed_run_reason(RuntimeError('{"token":"secret"}'))

    assert "private operator message" not in reason
    assert "secret" not in payload_reason
    assert reason.startswith("RuntimeError:")
    assert payload_reason.startswith("RuntimeError:")


def test_releasing_logs_slow_node_name_and_elapsed_milliseconds(monkeypatch, caplog):
    import logging
    from app.chat.assistant import graph

    monkeypatch.setattr(graph, "SLOW_ASSISTANT_NODE_SECONDS", 0)
    wrapped = graph._releasing(lambda _state: {"status": "ok"}, release=False)
    with caplog.at_level(logging.WARNING, logger="app.chat.assistant.graph"):
        assert wrapped({}) == {"status": "ok"}

    assert "Slow assistant node <lambda> took" in caplog.text
    assert "ms" in caplog.text
