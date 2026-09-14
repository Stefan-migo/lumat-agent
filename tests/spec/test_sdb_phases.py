"""OpenSpec scenarios for native SDB execution phases."""

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from app.chat.assistant.graph import _after_sdb_approve, build_assistant_graph
from app.chat.assistant.nodes import (
    sdb_approve,
    sdb_clarify,
    sdb_deliver,
    sdb_execute,
    sdb_plan,
    sdb_spec,
    sdb_verify,
    resolve_sdb_item,
)
from app.chat.assistant.state import SDBTask
from app.services.projects import _ProjectAuthorization


def _clarified_state():
    return sdb_clarify({
        "content": "Research the service history and summarize the findings.",
        "sdb_trigger": "classified",
        "sdb_route": "sdb",
    })


def _run(*nodes):
    state = _clarified_state()
    for node in nodes:
        state.update(node(state))
    return state


def test_native_nodes_run_in_declared_order_and_end_with_terminal_evidence():
    state = _run(sdb_spec, sdb_plan)
    state["sdb_result"] = {"results": [{
        "task_id": "task-1", "order": 0, "tool": "conversations.search", "status": "completed",
        "result": {"rows": ["bounded"]}, "evidence": {"rows": 1},
    }]}
    state.update(sdb_execute(state))
    state.update(sdb_verify(state))
    state.update(sdb_deliver(state))

    assert state["sdb_phase"] == "DELIVER"
    assert state["status"] == "completed"
    assert state["evidence"][-1]["route"] == "sdb"
    assert state["evidence"][-1]["phase"] == "DELIVER"
    assert state["evidence"][-1]["status"] == "completed"


def test_approve_halts_pending_without_auto_approval():
    result = sdb_approve({"sdb_phase": "PLAN", "sdb_tasks": []})

    assert result["approval"] == {"status": "pending"}
    assert result["status"] == "approval_pending"


def test_approval_route_requires_consumed_status():
    assert _after_sdb_approve({"approval": {"status": "pending"}}) == "__end__"
    assert _after_sdb_approve({"approval": {"status": "consumed"}}) == "sdb_execute"


def test_spec_freezes_scope_before_plan_and_rejects_expansion():
    state = _run(sdb_spec)
    frozen_scope = state["sdb_spec"]["scope"]

    state.update(sdb_plan(state))
    planned = state

    assert planned["sdb_spec"]["scope"] == frozen_scope
    assert planned["sdb_spec"]["scope_frozen"] is True
    assert all(task["scope"] == frozen_scope for task in planned["sdb_tasks"])


def test_scope_lookup_rejects_item_outside_frozen_scope():
    state = _run(sdb_spec, sdb_plan)

    result = resolve_sdb_item(state["sdb_spec"], "unapproved entity")

    assert result["status"] == "error"
    assert result["error"] == "scope-not-found"


def test_scope_lookup_distinguishes_absent_item_inside_frozen_scope():
    state = _run(sdb_spec, sdb_plan)

    result = resolve_sdb_item(state["sdb_spec"], "service history")

    assert result["status"] == "error"
    assert result["error"] == "not-exist"


def test_every_task_declares_one_verifiable_output():
    state = sdb_plan(sdb_spec(_clarified_state()))

    assert state["sdb_tasks"]
    assert all(task["verifiable_output"] for task in state["sdb_tasks"])
    assert all(len(task) <= 6 for task in state["sdb_tasks"])
    assert all(task["tool"] == "conversations.search" for task in state["sdb_tasks"])
    assert all(task["arguments"] == {"query": task["scope"]["request"], "limit": 10} for task in state["sdb_tasks"])
    assert all(isinstance(SDBTask.model_validate(task), SDBTask) for task in state["sdb_tasks"])


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


def test_sdb_artifacts_and_evidence_are_bounded():
    state = _run(sdb_spec, sdb_plan, sdb_execute, sdb_verify, sdb_deliver)

    assert len(str(state["sdb_spec"])) <= 8192
    assert len(str(state["sdb_result"])) <= 4096
    assert len(str(state["evidence"])) <= 4096


def test_execute_and_verify_do_not_fabricate_completion():
    state = _run(sdb_spec, sdb_plan, sdb_execute, sdb_verify)

    assert state["sdb_result"]["results"] == []
    assert state["verification"]["status"] == "failed"


def test_graph_exposes_native_phase_nodes_and_routes():
    graph = build_assistant_graph()

    assert all(name in graph.nodes for name in (
        "sdb_clarify", "sdb_spec", "sdb_plan", "sdb_approve",
        "sdb_execute", "sdb_verify", "sdb_deliver",
    ))


def test_authorized_project_is_frozen_in_sdb_scope_without_changing_phases():
    authorization = _ProjectAuthorization(slug="field-ops")
    state = {"content": "Research the service history and summarize the findings.", "project_authorization": authorization}
    state.update(sdb_clarify(state))
    state.update(sdb_spec(state))
    state.update(sdb_plan(state))

    assert state["sdb_scope"]["proyecto"] == "field-ops"
    assert state["sdb_spec"]["scope"]["proyecto"] == "field-ops"
    assert [state.update(node(state)) or state["sdb_phase"] for node in (sdb_execute, sdb_verify, sdb_deliver)] == [
        "EXECUTE", "VERIFY", "DELIVER"
    ]


def test_verify_requires_ordered_tool_and_mutation_evidence():
    state = _run(sdb_spec, sdb_plan)
    state["sdb_result"] = {"results": [{
        "task_id": "task-1", "order": 0, "tool": "conversations.search",
        "status": "completed", "result": {"rows": ["bounded"]},
        "evidence": {"tool": "conversations.search", "rows": 1},
    }]}

    verified = sdb_verify(state)

    assert verified["verification"]["status"] == "passed"
    assert verified["verification"]["results"][0]["evidence"] == {
        "tool": "conversations.search", "rows": 1
    }


def test_verify_rejects_matching_ids_when_mutation_evidence_is_missing():
    state = _run(sdb_spec, sdb_plan)
    state["sdb_tasks"][0]["tool"] = "project.rename"
    state["sdb_result"] = {"results": [{
        "task_id": "task-1", "order": 0, "tool": "project.rename",
        "status": "completed", "result": None, "evidence": {},
    }]}

    verified = sdb_verify(state)

    assert verified["verification"]["status"] == "failed"
    assert verified["verification"]["mismatches"][0]["field"] == "mutation_evidence"


def test_verify_accepts_completed_empty_read_result():
    state = _run(sdb_spec, sdb_plan)
    state["sdb_result"] = {"results": [{
        "task_id": "task-1", "order": 0, "tool": "conversations.search",
        "status": "completed", "read_only": True, "result": [], "evidence": {},
    }]}

    verified = sdb_verify(state)

    assert verified["verification"]["status"] == "passed"
    assert verified["verification"]["results"][0]["result"] == []


def test_deliver_rejects_uncommitted_verified_results():
    state = {
        "verification": {"status": "passed", "task_ids": ["task-1"]},
        "sdb_result": {"durable_commit": False},
    }

    delivered = sdb_deliver(state)

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
