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
