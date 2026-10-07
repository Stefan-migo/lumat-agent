"""Isolated verifier runner contract."""

import json
from types import SimpleNamespace

import pytest

from app.chat.assistant.verification import (
    VerificationResult,
    build_verifier_messages,
    run_verification,
)


class FakeClient:
    def __init__(self, content, tool_calls=None, follow_up=None):
        self.calls = []
        self.responses = [SimpleNamespace(content=content, tool_calls=tool_calls or [])]
        if follow_up is not None:
            self.responses.append(SimpleNamespace(content=follow_up, tool_calls=[]))
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=self.responses.pop(0))])


def response(status, reason="checked"):
    return json.dumps({"status": status, "reason": reason})


@pytest.mark.parametrize("status", ["confirmed", "failed", "unverifiable"])
def test_verdict_contract(status):
    client = FakeClient(response(status))
    result = run_verification(criterion="Visible in list", steps=[], evidence=[], client=client)
    assert result == VerificationResult(status=status, reason="checked")
    assert len(client.calls) == 1


def test_missing_criterion_skips_model():
    client = FakeClient(response("confirmed"))
    assert run_verification(criterion="  ", steps=[], evidence=[], client=client).reason == "no-observable-criterion"
    assert not client.calls


def test_messages_only_contain_verification_inputs():
    messages = build_verifier_messages(
        "criterion-only", [{"tool": "project.list", "arguments": {"needle": "step-only"}}],
        [{"detail": "evidence-only"}],
    )
    serialized = json.dumps(messages)
    assert "criterion-only" in serialized and "step-only" in serialized and "evidence-only" in serialized
    for secret in ("parent-secret", "thread-secret", "memory-secret"):
        assert secret not in serialized


def test_write_attempt_is_refused_without_dispatch():
    call = SimpleNamespace(function=SimpleNamespace(name="memory.update", arguments='{}'))
    client = FakeClient("", [call])
    dispatched = []
    result = run_verification(criterion="Updated", steps=[], evidence=[], client=client,
                              tool_executor=lambda *args: dispatched.append(args))
    assert result.status == "failed"
    assert not dispatched


def test_more_than_two_tool_steps_is_refused():
    calls = [SimpleNamespace(function=SimpleNamespace(name="project.list", arguments="{}")) for _ in range(3)]
    client = FakeClient("", calls)
    dispatched = []
    result = run_verification(criterion="Project listed", steps=[], evidence=[], client=client,
                              tool_executor=lambda *args: dispatched.append(args))
    assert result.status in {"failed", "unverifiable"}
    assert not dispatched


def test_malformed_output_degrades_to_unverifiable():
    result = run_verification(criterion="Done", steps=[], evidence=[], client=FakeClient("not json"))
    assert result.status == "unverifiable"


def test_read_only_call_is_followed_by_final_verdict_with_result():
    call = SimpleNamespace(id="call-1", type="function",
                           function=SimpleNamespace(name="project.list", arguments="{}"))
    client = FakeClient("", [call], follow_up=response("confirmed", "found"))
    dispatched = []

    def execute(name, arguments):
        dispatched.append((name, arguments))
        return {"projects": ["demo"]}

    result = run_verification(criterion="Project exists", steps=[], evidence=[], client=client,
                              tool_executor=execute)
    assert result == VerificationResult(status="confirmed", reason="found")
    assert dispatched == [("project.list", {})]
    assert len(client.calls) == 2
    assert "demo" in json.dumps(client.calls[1]["messages"])


def test_read_only_call_without_executor_is_not_dispatched():
    call = SimpleNamespace(id="call-1", type="function",
                           function=SimpleNamespace(name="project.list", arguments="{}"))
    result = run_verification(criterion="Project exists", steps=[], evidence=[],
                              client=FakeClient("", [call]))
    assert result.status == "unverifiable"
    assert result.reason == "tool-executor-unavailable"


def test_configured_model_is_used(monkeypatch):
    from app.services import llm

    monkeypatch.setattr(llm, "get_settings", lambda: SimpleNamespace(assistant_chat_model="configured"))
    client = FakeClient(response("confirmed"))
    run_verification(criterion="Done", steps=[], evidence=[], client=client)
    assert client.calls[0]["model"] == "configured"
