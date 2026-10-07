"""OpenSpec scenarios for retained SDB verification and assistant graph contracts."""

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from app.chat.assistant.graph import build_assistant_graph
from app.chat.assistant.nodes import sdb_deliver, sdb_verify
from app.chat.assistant.state import SDBTask


def test_graph_has_no_sdb_phase_nodes_and_preserves_normal_path():
    graph = build_assistant_graph()

    assert not any(name.startswith("sdb_") for name in graph.nodes)
    assert all(name in graph.nodes for name in (
        "plan_llm", "guardrails", "execute_tool", "tool_loop_head",
        "verify_effects", "respond_stream",
    ))


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("unknown.tool", {}),
        ("automation.create_rule", {"name": "unsafe"}),
        ("conversations.search", {"query": 42, "limit": 10}),
    ],
)
def test_invalid_sdb_task_is_rejected_before_approval_and_execution(monkeypatch, tool, arguments):
    executed = False

    def fail_if_called(*args, **kwargs):
        nonlocal executed
        executed = True

    monkeypatch.setattr("app.chat.assistant.tools.registry.execute_tool", fail_if_called)
    task = {
        "id": "task-invalid",
        "scope": {"entities": ["service history"], "request": "service history"},
        "summary": "Read history",
        "verifiable_output": "rows",
        "tool": tool,
        "arguments": arguments,
    }

    with pytest.raises(ValueError):
        SDBTask.model_validate(task)
    assert executed is False


def test_verify_requires_ordered_tool_and_mutation_evidence():
    task = {"id": "task-1", "tool": "conversations.search"}
    state = {"sdb_tasks": [task], "sdb_result": {"results": [{
        "task_id": "task-1", "order": 0, "tool": "conversations.search",
        "status": "completed", "result": {"rows": ["bounded"]},
        "evidence": {"tool": "conversations.search", "rows": 1},
    }]}}

    verified = sdb_verify(state)

    assert verified["verification"]["status"] == "passed"
    assert verified["verification"]["results"][0]["evidence"] == {
        "tool": "conversations.search", "rows": 1
    }


def test_verify_rejects_matching_ids_when_mutation_evidence_is_missing():
    state = {
        "sdb_tasks": [{"id": "task-1", "tool": "project.rename"}],
        "sdb_result": {"results": [{
            "task_id": "task-1", "order": 0, "tool": "project.rename",
            "status": "completed", "result": None, "evidence": {},
        }]},
    }

    verified = sdb_verify(state)

    assert verified["verification"]["status"] == "failed"
    assert verified["verification"]["mismatches"][0]["field"] == "mutation_evidence"


def test_verify_accepts_completed_empty_read_result():
    state = {
        "sdb_tasks": [{"id": "task-1", "tool": "conversations.search"}],
        "sdb_result": {"results": [{
            "task_id": "task-1", "order": 0, "tool": "conversations.search",
            "status": "completed", "read_only": True, "result": [], "evidence": {},
        }]},
    }

    verified = sdb_verify(state)

    assert verified["verification"]["status"] == "passed"
    assert verified["verification"]["results"][0]["result"] == []


def test_deliver_rejects_uncommitted_verified_results():
    delivered = sdb_deliver({
        "verification": {"status": "passed", "task_ids": ["task-1"]},
        "sdb_result": {"durable_commit": False},
    })

    assert delivered["status"] == "failed"
    assert delivered["evidence"][0]["reason"] == "durable commit not confirmed"


def test_db_commit_uncertainty_is_bounded_without_retry(monkeypatch):
    from app.panel import deps

    class Session:
        commits = 0
        rollbacks = 0

        def commit(self):
            self.commits += 1
            raise ConnectionError("database connection lost")

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            pass

    session = Session()
    monkeypatch.setattr(deps, "SessionLocal", lambda: session)
    database = deps.get_db()
    next(database)

    with pytest.raises(HTTPException) as caught:
        next(database)

    assert caught.value.status_code == 500
    assert "recovery" in caught.value.detail
    assert session.commits == 1
    assert session.rollbacks == 1


def test_db_preserves_request_validation_errors(monkeypatch):
    from app.panel import deps

    class Session:
        rollbacks = 0
        closes = 0

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            self.closes += 1

    session = Session()
    monkeypatch.setattr(deps, "SessionLocal", lambda: session)
    database = deps.get_db()
    next(database)
    validation_error = RequestValidationError([{"loc": ("body",), "msg": "invalid", "type": "value_error"}])

    with pytest.raises(RequestValidationError) as caught:
        database.throw(validation_error)

    assert caught.value is validation_error
    assert session.rollbacks == 1
    assert session.closes == 1
