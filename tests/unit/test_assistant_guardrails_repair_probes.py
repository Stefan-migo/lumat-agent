"""Guardrails repair probes: clamp width, permission boundary, one repair per turn (S3/S4/S5)."""

import dataclasses
import json
from types import SimpleNamespace

import pytest

from app.chat.assistant.graph import run_assistant
from app.chat.assistant.tools import registry as reg

SAFE = "No pude planificar esa solicitud de forma segura. Inténtalo nuevamente."


def _plan(tool="read_project_file", arguments=None, follow_up=False):
    return json.dumps({
        "kind": "tool", "tool": tool,
        "arguments": {"file_id": 3} if arguments is None else arguments,
        "summary": "s", "requires_approval": False, "follow_up": follow_up,
    })


class _Client:
    def __init__(self, replies, *, raise_on=()):
        self.replies, self.calls, self.raise_on = list(replies), [], set(raise_on)

    def create(self, **kw):
        self.calls.append(kw)
        if kw.get("stream"):
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))])]
        if len(self.calls) - 1 in self.raise_on:
            raise RuntimeError("provider down")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.replies.pop(0)))])

    @property
    def planner_calls(self):
        return [c for c in self.calls if not c.get("stream")]

    @property
    def stream_calls(self):
        return [c for c in self.calls if c.get("stream")]


@pytest.fixture
def read_hits(monkeypatch):
    hits = []

    def fake(session, args, **_kw):
        hits.append(args.model_dump())
        return {"kind": "text", "chars": 1, "offset": args.offset, "next_offset": None,
                "truncated": False, "text": "x"}

    definition = reg.TOOL_REGISTRY["read_project_file"]
    monkeypatch.setitem(reg.TOOL_REGISTRY, "read_project_file", dataclasses.replace(definition, handler=fake))
    return hits


def _run(monkeypatch, client):
    monkeypatch.setattr(
        "app.chat.assistant.nodes._assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=client.create))),
    )
    return run_assistant(
        thread_id=7, user_id=1, content="Read file", run_id="probe",
        on_token=lambda _t: None, actor_role="admin",
    )


@pytest.mark.parametrize("raw", ["6000", " 6000 ", None, 10**30, 6000.0])
def test_S3_every_page_over_the_ceiling_clamps_and_executes(monkeypatch, read_hits, raw):
    client = _Client([_plan(arguments={"file_id": 3, "limit": raw})])
    final = _run(monkeypatch, client)
    assert read_hits == [{"file_id": 3, "offset": 0, "limit": 3890}]
    assert final["guardrails"]["decision"] == "execute"
    assert len(client.planner_calls) == 1


def test_S5_unwhitelisted_plan_never_executes_after_repair(monkeypatch, read_hits):
    client = _Client([_plan(tool="not.allowed", arguments={})] * 2)
    final = _run(monkeypatch, client)
    assert read_hits == []
    assert final["response"] == SAFE
    assert len(client.planner_calls) == 2
    assert client.stream_calls == []


def test_S5_write_plan_pauses_without_a_repair_call(monkeypatch, read_hits):
    client = _Client([_plan(tool="project_file.save", arguments={"filename": "a.txt", "content": "hello"})])
    final = _run(monkeypatch, client)
    assert final["status"] == "approval_pending"
    assert len(client.planner_calls) == 1


@pytest.mark.parametrize("second,stage", [
    ("not json at all", "parse"),
    (json.dumps({"kind": "tool", "tool": "read_project_file", "arguments": {"file_id": 3}, "bogus": 1}), "validation"),
])
def test_S4_an_unusable_repair_ends_on_the_exact_fallback(monkeypatch, read_hits, second, stage):
    client = _Client([_plan(arguments={"file_id": 0}), second])
    final = _run(monkeypatch, client)
    assert final["response"] == SAFE
    assert final["planner"]["failure"]["stage"] == stage
    assert len(client.planner_calls) == 2
    assert client.stream_calls == []


def test_S4_a_provider_failure_in_the_repair_is_paid_once_and_terminal(monkeypatch, read_hits):
    client = _Client([_plan(arguments={"file_id": 0})], raise_on=(1,))
    final = _run(monkeypatch, client)
    assert final["response"] == SAFE
    assert final["planner"]["failure"]["stage"] == "provider"
    assert len(client.planner_calls) == 2
    assert client.stream_calls == []


def test_S4_one_repair_per_turn_survives_a_follow_up_plan(monkeypatch, read_hits):
    client = _Client([
        _plan(tool="not.allowed", arguments={}),
        _plan(arguments={"file_id": 3, "limit": 120}, follow_up=True),
        _plan(tool="not.allowed", arguments={}),
    ])
    final = _run(monkeypatch, client)
    assert read_hits == [{"file_id": 3, "offset": 0, "limit": 120}]
    # plan, repair, follow-up plan; the second rejection gets no second repair.
    assert len(client.planner_calls) == 3
    assert final["response"] == SAFE


def test_S5_a_semantic_listing_limit_still_fails_guardrails_after_repair(monkeypatch, read_hits):
    plan = _plan(tool="customers.search", arguments={"limit": 999})
    client = _Client([plan, plan])
    final = _run(monkeypatch, client)
    assert final["response"] == SAFE
    assert final["guardrails"]["decision"] == "fallback"
    assert len(client.planner_calls) == 2
    # The repair turn is told the bound it broke, not only that something was invalid: a rejection
    # the model cannot read is a rejection it cannot correct.
    prompt = client.planner_calls[1]["messages"][-1]["content"]
    assert "arguments_valid=false" in prompt
    assert "less than or equal to" in prompt


def test_S4_repair_prompt_shows_the_rejected_plan_never_the_fallback(monkeypatch, read_hits):
    client = _Client([_plan(arguments={"file_id": 0, "limit": 6000})])
    _run(monkeypatch, client)
    messages = client.planner_calls[1]["messages"]
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert json.loads(messages[2]["content"])["arguments"] == {"file_id": 0, "limit": 6000}
    assert 'Previous plan: {"kind":"tool","tool":"read_project_file"' in messages[-1]["content"]
    assert SAFE not in messages[-1]["content"]
    assert "whitelisted=true" in messages[-1]["content"] and "arguments_valid=false" in messages[-1]["content"]
