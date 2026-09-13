"""Strict RED coverage for exact SDB approval and durable recovery."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.chat.assistant.approval import (
    canonical_sdb_digest,
    issue_approval,
    validate_approval,
    validate_execution,
)
from app.chat.assistant.recovery import claim_execution, resumable_sdb_tasks


def _sdb_plan(spec=None, tasks=None):
    return {
        "phase": "EXECUTE",
        "spec": spec or {"scope": {"entities": ["service history"]}, "sha256": "spec-1"},
        "tasks": tasks or [{"id": "task-1", "verifiable_output": "summary"}],
    }


def test_mutated_spec_after_approval_is_rejected_without_execution():
    plan = _sdb_plan()
    approval = issue_approval({"sdb": plan, "tool": None, "arguments": {}})
    mutated = _sdb_plan(spec={"scope": {"entities": ["billing"]}, "sha256": "spec-2"})

    assert validate_approval({"sdb": mutated, "tool": None, "arguments": {}}, approval, approval["token"]) is False
    assert validate_execution({"sdb": mutated, "tool": None, "arguments": {}}, {**approval, "status": "consumed"}) is False


def test_approval_binds_exact_canonical_phase_and_task_payload_and_expiry():
    plan = _sdb_plan()
    approval = issue_approval({"sdb": plan, "tool": None, "arguments": {}})
    altered = _sdb_plan(tasks=[{"id": "task-2", "verifiable_output": "summary"}])

    assert canonical_sdb_digest(plan) == approval["sdb_sha256"]
    assert validate_approval({"sdb": altered, "tool": None, "arguments": {}}, approval, approval["token"]) is False
    expired = issue_approval(
        {"sdb": plan, "tool": None, "arguments": {}},
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    assert validate_approval({"sdb": plan, "tool": None, "arguments": {}}, expired, expired["token"]) is False


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


def test_sdb_task_runner_never_fabricates_completed_results(monkeypatch):
    from app.services import agent_chat

    captured = []
    monkeypatch.setattr(agent_chat, "persist_sdb_state", lambda *args, **kwargs: captured.append(kwargs))
    thread = SimpleNamespace(
        id=1,
        current_plan={"sdb": {"tasks": [{"id": "task-1", "verifiable_output": "summary"}]}},
        assistant_state={"sdb": {"checkpoints": []}},
    )

    result = agent_chat._run_sdb_tasks(object(), thread, "run-1")

    assert result["status"] == "not-implemented"
    assert [item["status"] for item in result["results"]] == ["not-implemented"]
    assert all(entry["checkpoint"]["status"] != "completed" for entry in captured)


def test_sdb_task_runner_forwards_authorized_project_to_checkpoint(monkeypatch):
    from app.services import agent_chat

    captured = []
    monkeypatch.setattr(agent_chat, "persist_sdb_state", lambda *args, **kwargs: captured.append(kwargs))
    authorization = SimpleNamespace(slug="field-ops")
    thread = SimpleNamespace(
        id=1,
        current_plan={"sdb": {"tasks": [{"id": "task-1", "verifiable_output": "summary"}]}},
        assistant_state={"sdb": {"checkpoints": []}},
    )

    agent_chat._run_sdb_tasks(object(), thread, "run-1", authorization)

    assert captured[0]["authorization"] is authorization
