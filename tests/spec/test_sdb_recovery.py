"""Strict RED coverage for exact SDB approval and durable recovery."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.chat.assistant.approval import (
    arguments_digest,
    canonical_sdb_digest,
    canonical_sdb_payload,
    consume_approval,
    issue_approval,
    validate_approval,
    validate_execution,
)
from app.chat.assistant.recovery import claim_execution, resumable_sdb_tasks


def _sdb_plan(spec=None, tasks=None):
    request = (spec or {"scope": {"entities": ["service history"]}, "sha256": "spec-1"})["scope"].get("request", "service history")
    return {
        "phase": "EXECUTE",
        "spec": spec or {"scope": {"entities": ["service history"]}, "sha256": "spec-1"},
        "tasks": tasks or [{"id": "task-1", "scope": {"entities": ["service history"], "request": request}, "summary": "Read history", "verifiable_output": "summary", "tool": "conversations.search", "arguments": {"query": request, "limit": 10}}],
    }


def test_mutated_spec_after_approval_is_rejected_without_execution():
    plan = _sdb_plan()
    approval = issue_approval({"sdb": plan, "tool": "conversations.search", "arguments": plan["tasks"][0]["arguments"]})
    mutated = _sdb_plan(spec={"scope": {"entities": ["billing"]}, "sha256": "spec-2"})

    assert validate_approval({"sdb": mutated, "tool": "conversations.search", "arguments": plan["tasks"][0]["arguments"]}, approval, approval["token"]) is False
    assert validate_execution({"sdb": mutated, "tool": "conversations.search", "arguments": plan["tasks"][0]["arguments"]}, {**approval, "status": "consumed"}) is False


def test_approval_binds_exact_canonical_phase_and_task_payload_and_expiry():
    plan = _sdb_plan()
    approval = issue_approval({"sdb": plan, "tool": "conversations.search", "arguments": plan["tasks"][0]["arguments"]})
    altered = _sdb_plan(tasks=[{"id": "task-2", "verifiable_output": "summary"}])

    assert canonical_sdb_digest(plan) == approval["sdb_sha256"]
    assert validate_approval({"sdb": altered, "tool": "conversations.search", "arguments": plan["tasks"][0]["arguments"]}, approval, approval["token"]) is False
    expired = issue_approval(
        {"sdb": plan, "tool": "conversations.search", "arguments": plan["tasks"][0]["arguments"]},
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    assert validate_approval({"sdb": plan, "tool": "conversations.search", "arguments": plan["tasks"][0]["arguments"]}, expired, expired["token"]) is False


class _AtomicClaimSession:
    def __init__(self):
        self.claimed = False

    def execute(self, statement, params):
        if self.claimed:
            return SimpleNamespace(scalar_one_or_none=lambda: None)
        self.claimed = True
        return SimpleNamespace(scalar_one_or_none=lambda: 1)

    def refresh(self, thread):
        thread.assistant_state = {**thread.assistant_state, "execution_status": "running"}


def test_active_run_claim_is_atomic_and_second_claim_cannot_duplicate():
    session = _AtomicClaimSession()
    thread = SimpleNamespace(id=7, active_run_id="run-1", assistant_state={"execution_status": "pending"})

    assert claim_execution(session, thread, active_run_id="run-1") is True
    assert claim_execution(session, thread, active_run_id="run-1") is False


def test_resume_uses_last_successful_checkpoint_without_repeating_tasks():
    tasks = [{"id": "task-1"}, {"id": "task-2"}, {"id": "task-3"}]
    checkpoints = [{"task_id": "task-1", "status": "completed"}, {"task_id": "task-2", "status": "completed"}]

    assert resumable_sdb_tasks(tasks, checkpoints) == [{"id": "task-3"}]

    assert resumable_sdb_tasks(tasks, [{"task_id": "task-1", "status": "failed"}]) == tasks


def test_canonical_sdb_digest_is_stable_and_bounded():
    first = _sdb_plan()
    second = {"tasks": first["tasks"], "spec": first["spec"], "phase": first["phase"]}

    assert canonical_sdb_digest(first) == canonical_sdb_digest(second)
    assert len(canonical_sdb_digest({"payload": "x" * 100_000})) == 64


def test_approval_freezes_every_ordered_binding_and_its_argument_hash():
    plan = _sdb_plan(tasks=[
        _sdb_plan()["tasks"][0],
        {**_sdb_plan()["tasks"][0], "id": "task-2", "arguments": {"query": "other", "limit": 10}},
    ])
    approval = issue_approval({"sdb": plan})

    assert approval["sdb_bindings"] == [
        {
            "order": 0,
            "task_id": "task-1",
            "tool": "conversations.search",
            "arguments": {"query": "service history", "limit": 10},
            "arguments_sha256": arguments_digest(
                "conversations.search", {"query": "service history", "limit": 10}, order=0, task_id="task-1"
            ),
        },
        {
            "order": 1,
            "task_id": "task-2",
            "tool": "conversations.search",
            "arguments": {"query": "other", "limit": 10},
            "arguments_sha256": arguments_digest(
                "conversations.search", {"query": "other", "limit": 10}, order=1, task_id="task-2"
            ),
        },
    ]
    assert canonical_sdb_payload(plan)["sdb_bindings"] == approval["sdb_bindings"]
    assert approval["sdb_sha256"] == canonical_sdb_digest({**plan, "sdb_bindings": approval["sdb_bindings"]})


def test_execution_rejects_binding_substitution_reorder_and_tamper():
    tasks = [_sdb_plan()["tasks"][0], {**_sdb_plan()["tasks"][0], "id": "task-2"}]
    sdb = _sdb_plan(tasks=tasks)
    approval = issue_approval({"sdb": sdb})
    assert consume_approval(approval, approval["token"]) is True

    for changed in (
        {**sdb, "tasks": list(reversed(tasks))},
        {**sdb, "tasks": [{**tasks[0], "id": "substituted"}, tasks[1]]},
        {**sdb, "tasks": [{**tasks[0], "arguments": {"query": "tampered", "limit": 10}}, tasks[1]]},
    ):
        assert validate_execution({"sdb": changed}, approval) is False


def test_sdb_task_runner_never_fabricates_completed_results(monkeypatch):
    from app.services import agent_chat

    captured = []
    monkeypatch.setattr(agent_chat, "persist_sdb_state", lambda *args, **kwargs: captured.append(kwargs))
    monkeypatch.setattr(agent_chat, "execute_tool", lambda *args, **kwargs: {"status": "completed", "result": {"rows": []}})
    thread = SimpleNamespace(
        id=1,
        current_plan={"sdb": {"tasks": [{"id": "task-1", "scope": {}, "summary": "read", "verifiable_output": "summary", "tool": "conversations.search", "arguments": {"query": "x", "limit": 10}}]}},
        assistant_state={"sdb": {"checkpoints": []}},
    )

    result = agent_chat._run_sdb_tasks(object(), thread, "run-1")

    assert result["status"] == "completed"
    assert [item["status"] for item in result["results"]] == ["completed"]
    assert captured[0]["checkpoint"]["status"] == "completed"


def test_sdb_task_runner_stops_after_first_failure(monkeypatch):
    from app.services import agent_chat

    captured = []
    monkeypatch.setattr(agent_chat, "persist_sdb_state", lambda *args, **kwargs: captured.append(kwargs))
    monkeypatch.setattr(agent_chat, "execute_tool", lambda *args, **kwargs: {"status": "error", "error": "read failed"})
    tasks = [{"id": f"task-{n}", "scope": {}, "summary": "read", "verifiable_output": "rows", "tool": "conversations.search", "arguments": {"query": "x", "limit": 10}} for n in (1, 2)]
    thread = SimpleNamespace(id=1, current_plan={"sdb": {"tasks": tasks}}, assistant_state={"sdb": {"checkpoints": []}})

    result = agent_chat._run_sdb_tasks(object(), thread, "run-1")

    assert result["status"] == "failed"
    assert [item["task_id"] for item in result["results"]] == ["task-1"]
    assert captured[0]["checkpoint"]["status"] == "failed"
    assert captured[0]["events"][0]["status"] == "failed"
    assert captured[0]["results"] == result["results"]


def test_sdb_failed_task_records_audit_and_never_streams_completed(monkeypatch):
    from app.services import agent_chat

    audits = []
    events = []
    monkeypatch.setattr(agent_chat, "record_audit", lambda *args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(
        agent_chat, "persist_sdb_state",
        lambda *args, **kwargs: events.extend(kwargs["events"]),
    )
    monkeypatch.setattr(agent_chat, "execute_tool", lambda *args, **kwargs: {"status": "error", "error": "read failed"})
    thread = SimpleNamespace(
        id=1,
        current_plan={"sdb": {"tasks": _sdb_plan()["tasks"]}},
        assistant_state={"sdb": {"checkpoints": []}},
    )

    result = agent_chat._run_sdb_tasks(SimpleNamespace(add=lambda entry: None), thread, "run-failed")

    assert result["status"] == "failed"
    assert result["results"][0]["status"] == "failed"
    assert events[0]["status"] == "failed"
    assert all(event["status"] != "completed" for event in events)
    assert audits[0]["action"] == "internal_chat.sdb_execution"


def test_sdb_timeout_and_exception_are_bounded_failed_attempts(monkeypatch):
    from app.chat.assistant.tools.registry import ToolExecutionError
    from app.services import agent_chat

    for failure in (TimeoutError("read timed out"), ToolExecutionError("read failed")):
        audits = []
        captured = []
        monkeypatch.setattr(agent_chat, "record_audit", lambda *args, **kwargs: audits.append(kwargs))
        monkeypatch.setattr(agent_chat, "persist_sdb_state", lambda *args, **kwargs: captured.append(kwargs))
        monkeypatch.setattr(
            agent_chat, "execute_tool",
            lambda *args, failure=failure, **kwargs: (_ for _ in ()).throw(failure),
        )
        thread = SimpleNamespace(
            id=1,
            current_plan={"sdb": {"tasks": _sdb_plan()["tasks"]}},
            assistant_state={"sdb": {"checkpoints": []}},
        )

        result = agent_chat._run_sdb_tasks(SimpleNamespace(add=lambda entry: None), thread, "run-failure")

        assert result["status"] == "failed"
        assert result["results"][0]["status"] == "failed"
        assert result["results"][0]["error"] in {"read timed out", "read failed"}
        assert len(audits) == len(captured) == 1


def test_sdb_gate_order_rejects_cost_before_project_capability(monkeypatch):
    from app.services import agent_chat

    calls = []
    monkeypatch.setattr(agent_chat, "persist_sdb_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_chat, "execute_tool", lambda *args, **kwargs: calls.append("dispatch"))
    task = _sdb_plan()["tasks"][0] | {"scope": {"proyecto": "field-ops"}}
    thread = SimpleNamespace(
        id=1,
        current_plan={"sdb": {"tasks": [task]}},
        assistant_state={"sdb": {"checkpoints": []}, "guardrails": {"cost_allowed": False}},
    )

    result = agent_chat._run_sdb_tasks(SimpleNamespace(add=lambda entry: None), thread, "run-blocked")

    assert result["status"] == "failed"
    assert result["results"][0]["error"] == "assistant cost limit blocks tool execution"
    assert calls == []


def test_sdb_missing_project_capability_fails_closed_without_tool(monkeypatch):
    from app.services import agent_chat

    captured = []
    monkeypatch.setattr(agent_chat, "persist_sdb_state", lambda *args, **kwargs: captured.append(kwargs))
    monkeypatch.setattr(agent_chat, "execute_tool", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("executed")))
    task = _sdb_plan()["tasks"][0] | {"scope": {"proyecto": "field-ops"}}
    thread = SimpleNamespace(
        id=1,
        current_plan={"sdb": {"tasks": [task]}},
        assistant_state={"sdb": {"checkpoints": []}},
    )

    result = agent_chat._run_sdb_tasks(SimpleNamespace(add=lambda entry: None), thread, "run-capability")

    assert result["status"] == "failed"
    assert result["results"][0]["error"] == "SDB project capability is unavailable"
    assert captured[0]["checkpoint"]["status"] == "failed"
    assert captured[0]["results"][0]["status"] == "failed"


def test_sdb_write_task_is_rejected_with_no_side_effect(monkeypatch):
    from app.services import agent_chat

    captured = []
    monkeypatch.setattr(agent_chat, "persist_sdb_state", lambda *args, **kwargs: captured.append(kwargs))
    monkeypatch.setattr(agent_chat, "execute_tool", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("executed")))
    task = _sdb_plan()["tasks"][0] | {
        "tool": "automation.create_rule",
        "arguments": {
            "name": "unsafe", "event_type": "message.received", "channel": "panel",
            "template_event": "unsafe", "cooldown_seconds": 0,
        },
    }
    thread = SimpleNamespace(
        id=1,
        current_plan={"sdb": {"tasks": [task]}},
        assistant_state={"sdb": {"checkpoints": []}},
    )

    result = agent_chat._run_sdb_tasks(SimpleNamespace(add=lambda entry: None), thread, "run-write")

    assert result["status"] == "failed"
    assert result["results"][0]["error"] == "SDB tasks must use read-only tools"
    assert captured[0]["checkpoint"]["status"] == "failed"


def test_sdb_task_runner_forwards_authorized_project_to_checkpoint(monkeypatch):
    from app.services import agent_chat

    captured = []
    monkeypatch.setattr(agent_chat, "persist_sdb_state", lambda *args, **kwargs: captured.append(kwargs))
    authorization = SimpleNamespace(slug="field-ops")
    thread = SimpleNamespace(
        id=1,
        current_plan={"sdb": {"tasks": [{"id": "task-1", "scope": {}, "summary": "read", "verifiable_output": "summary", "tool": "conversations.search", "arguments": {"query": "x", "limit": 10}}]}},
        assistant_state={"sdb": {"checkpoints": []}},
    )

    agent_chat._run_sdb_tasks(object(), thread, "run-1", authorization)

    assert captured[0]["authorization"] is authorization
