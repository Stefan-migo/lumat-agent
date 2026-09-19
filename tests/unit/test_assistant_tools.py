from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.chat.assistant.tools.registry import (
    AUTONOMOUS_WRITE_ALLOWLIST,
    MemoryArgs,
    MemorySearchArgs,
    MemoryWriteArgs,
    ProjectArchiveArgs,
    ProjectCreateArgs,
    ProjectMergeArgs,
    ProjectRenameArgs,
    RuleArgs,
    ToolValidationError,
    execute_tool,
    get_tool,
    tool_schemas,
)
from app.chat.assistant.state import SDBTask
from app.chat.assistant.approval import consume_approval, issue_approval, validate_execution
from app.services.projects import ProjectCandidate, ProjectResult
from app.chat.assistant.tools.search import DuckDuckGoSearch, SearchFailure


def test_registry_exposes_typed_bounded_tools():
    schemas = tool_schemas()
    assert "customers.search" in schemas
    assert schemas["customers.search"]["type"] == "object"
    assert get_tool("customers.search").read_only is True
    assert get_tool("automation.create_rule").read_only is False


def test_memory_args_reject_unknown_scope_and_expose_canonical_scope_schema():
    with pytest.raises(ValueError):
        MemoryArgs.model_validate({"scope": "banana", "entity_id": "whatever"})

    assert MemoryArgs.model_json_schema()["properties"]["scope"]["enum"] == [
        "panel", "customer", "agent"
    ]


def test_memory_scope_entity_is_conditional_and_panel_entity_is_forbidden():
    assert MemoryArgs.model_validate({"scope": "panel"}).entity_id is None

    with pytest.raises(ValueError, match="derived server-side"):
        MemoryArgs.model_validate({"scope": "panel", "entity_id": "thread:7"})
    with pytest.raises(ValueError):
        MemoryArgs.model_validate({"scope": "customer"})
    with pytest.raises(ValueError):
        MemoryArgs.model_validate({"scope": "agent"})


def test_project_tools_are_typed_bounded_and_classified():
    expected = {
        "project.list": True,
        "project.find": True,
        "project.create": False,
        "project.rename": False,
        "project.archive": False,
        "project.merge": False,
    }
    for name, read_only in expected.items():
        assert name in tool_schemas()
        assert get_tool(name).read_only is read_only
        assert get_tool(name).schema()["type"] == "object"

    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "project.find", {"query": "x" * 201})
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "project.merge", {"source": "a", "target": "b", "extra": "no"})


def test_project_whitelist_is_checked_at_execution_boundary(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.list",
        lambda *args, **kwargs: called.append(True),
    )

    with pytest.raises(ToolValidationError, match="not whitelisted"):
        execute_tool(SimpleNamespace(), "project.list", {}, whitelist={"customers.list"})
    assert called == []


def test_ambiguous_project_find_requires_approval_without_selecting_namespace(monkeypatch):
    candidate = ProjectCandidate("gas", "Gas", 0.91)
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.find",
        lambda *args, **kwargs: ProjectResult(None, [candidate], requires_approval=True),
    )

    result = execute_tool(SimpleNamespace(), "project.find", {"query": "gas service"})

    assert result["status"] == "approval_pending"
    assert result["result"]["project"] is None
    assert result["result"]["candidates"][0]["slug"] == "gas"
    assert result["approval"]["project_payload"]["operation"] == "find"


def _approved_project_plan(tool, arguments, decision):
    return {
        "tool": tool,
        "arguments": arguments,
        "project_payload": {
            "operation": tool.removeprefix("project."),
            "arguments": arguments,
            "decision": decision,
        },
    }


def test_approved_project_find_selects_candidate(monkeypatch):
    candidate = ProjectCandidate("gas", "Gas", 0.91)
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.find",
        lambda *args, **kwargs: ProjectResult(
            project=None, candidates=[candidate], requires_approval=True
        ) if kwargs.get("_approval") is None else ProjectResult(
            project="gas", candidates=[candidate], requires_approval=False
        ),
    )
    plan = _approved_project_plan("project.find", {"query": "gas service"}, {"selected_slug": "gas"})
    approval = issue_approval(plan)
    assert consume_approval(approval, approval["token"]) is True

    result = execute_tool(SimpleNamespace(), "project.find", plan["arguments"], approval=approval)

    assert result["status"] == "completed"
    assert result["result"]["project"] == "gas"
    assert result["result"]["requires_approval"] is False


def test_approved_project_create_reuses_candidate(monkeypatch):
    candidate = ProjectCandidate("gas", "Gas", 0.91)
    existing = SimpleNamespace(slug="gas")
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.create",
        lambda *args, **kwargs: existing if kwargs.get("_approval") else ProjectResult(None, [candidate], True),
    )
    plan = _approved_project_plan(
        "project.create",
        {"slug": "gas-new", "name": "Gas", "purpose": "gas service"},
        {"selected_slug": "gas"},
    )
    approval = issue_approval(plan)
    assert consume_approval(approval, approval["token"]) is True

    result = execute_tool(SimpleNamespace(), "project.create", plan["arguments"], approval=approval)

    assert result["status"] == "completed"
    assert result["result"]["slug"] == "gas"


def test_approved_project_create_creates_distinct_project(monkeypatch):
    created = SimpleNamespace(slug="gas-new")
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.create",
        lambda *args, **kwargs: created if kwargs.get("_approval") else ProjectResult(
            None, [ProjectCandidate("gas", "Gas", 0.91)], True
        ),
    )
    plan = _approved_project_plan(
        "project.create",
        {"slug": "gas-new", "name": "Gas New", "purpose": "gas service"},
        {"create_distinct": True},
    )
    approval = issue_approval(plan)
    assert consume_approval(approval, approval["token"]) is True

    result = execute_tool(SimpleNamespace(), "project.create", plan["arguments"], approval=approval)

    assert result["status"] == "completed"
    assert result["result"]["slug"] == "gas-new"


def test_project_approval_decision_is_required_and_replay_or_changes_select_nothing(monkeypatch):
    calls = []
    candidate = ProjectCandidate("gas", "Gas", 0.91)
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.find",
        lambda *args, **kwargs: calls.append(kwargs.get("_approval")) or ProjectResult(
            project=None, candidates=[candidate], requires_approval=kwargs.get("_approval") is None
        ),
    )
    arguments = {"query": "gas service"}
    plan = _approved_project_plan("project.find", arguments, {"selected_slug": "gas"})
    approval = issue_approval(plan)

    pending = execute_tool(SimpleNamespace(), "project.find", arguments)
    assert pending["status"] == "approval_pending"
    assert pending["result"]["project"] is None
    assert calls == [None]

    assert consume_approval(approval, approval["token"]) is True
    execute_tool(SimpleNamespace(), "project.find", arguments, approval=approval)
    assert calls[-1] is not None
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "project.find", {"query": "changed"}, approval=approval)
    assert len(calls) == 2
    assert consume_approval(approval, approval["token"]) is False

    expired = issue_approval(plan, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "project.find", arguments, approval=expired)


def test_project_mutation_requires_consumed_exact_non_expired_approval(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.rename",
        lambda *args, **kwargs: called.append(True),
    )
    arguments = {"project": "gas", "name": "Gas Service"}
    plan = {"tool": "project.rename", "arguments": arguments}
    approval = issue_approval(plan)

    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "project.rename", arguments, approval=approval)
    assert called == []

    assert consume_approval(approval, approval["token"]) is True
    assert validate_execution(plan, approval) is True
    execute_tool(SimpleNamespace(), "project.rename", arguments, approval=approval)
    assert called == [True]

    changed = {"project": "gas", "name": "Changed"}
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "project.rename", changed, approval=approval)
    assert called == [True]


def test_unknown_and_invalid_tools_are_rejected_before_execution():
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "not-a-tool", {})
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "customers.search", {"limit": 1000})


def test_write_requires_consumed_exact_approval(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.automation.create_rule",
        lambda *args, **kwargs: called.append((args, kwargs)),
    )
    args = {
        "name": "notify",
        "event_type": "case.created",
        "conditions": {},
        "channel": "email",
        "template_event": "case.created",
        "cooldown_seconds": 0,
    }
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "automation.create_rule", args)
    assert called == []
    approval = {
        "status": "consumed",
        "arguments_sha256": "wrong",
    }
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "automation.create_rule", args, approval=approval)
    assert called == []


def _sdb_approved_project(tool, arguments, decision=None):
    task = {
        "id": tool,
        "tool": tool,
        "arguments": arguments,
        "scope": {"proyecto": "default"},
    }
    if decision is not None:
        task["decision"] = decision
    approval = issue_approval({
        "sdb": {"phase": "EXECUTE", "spec": {"sha256": "spec"}, "tasks": [task]},
    })
    assert consume_approval(approval, approval["token"]) is True
    return approval, approval["sdb_bindings"][0], task


def test_sdb_project_create_uses_frozen_decision_and_real_execute_path(monkeypatch):
    called = []
    created = SimpleNamespace(slug="gas-new")
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.create",
        lambda *args, **kwargs: called.append(kwargs.get("_approval")) or created,
    )
    arguments = {"slug": "gas-new", "name": "Gas New", "purpose": "gas service"}
    approval, binding, task = _sdb_approved_project("project.create", arguments, {"create_distinct": True})

    result = execute_tool(
        SimpleNamespace(), task["tool"], arguments, approval=approval, task_binding=binding
    )

    assert result["status"] == "completed"
    assert result["result"]["slug"] == "gas-new"
    assert called
    assert binding["project_payload"]["decision"] == {"create_distinct": True}


@pytest.mark.parametrize("decision", [None, {"unexpected": True}, {"create_distinct": False}])
def test_sdb_project_create_rejects_missing_or_invalid_decision_without_mutation(monkeypatch, decision):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.create",
        lambda *args, **kwargs: called.append(True),
    )
    arguments = {"slug": "gas-new", "name": "Gas New", "purpose": "gas service"}
    approval, binding, task = _sdb_approved_project("project.create", arguments, decision)

    with pytest.raises(ToolValidationError, match="decision"):
        execute_tool(SimpleNamespace(), task["tool"], arguments, approval=approval, task_binding=binding)
    assert called == []


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("project.rename", {"project": "gas", "name": "Gas Service"}),
        ("project.archive", {"project": "gas"}),
        ("project.merge", {"source": "gas-old", "target": "gas"}),
    ],
)
def test_sdb_project_mutations_use_real_execute_path(monkeypatch, tool, arguments):
    called = []
    monkeypatch.setattr(
        f"app.chat.assistant.tools.registry.projects.{tool.removeprefix('project.')}",
        lambda *args, **kwargs: called.append(True) or SimpleNamespace(slug="gas"),
    )
    approval, binding, task = _sdb_approved_project(tool, arguments)

    result = execute_tool(SimpleNamespace(), tool, arguments, approval=approval, task_binding=binding)

    assert result["status"] == "completed"
    assert called == [True]


@pytest.mark.parametrize("field,value", [("tool", "project.archive"), ("arguments", {"project": "other"}), ("project_payload", {"operation": "create"})])
def test_sdb_project_binding_tampering_is_rejected_before_mutation(monkeypatch, field, value):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.rename",
        lambda *args, **kwargs: called.append(True),
    )
    arguments = {"project": "gas", "name": "Gas Service"}
    approval, binding, task = _sdb_approved_project("project.rename", arguments)
    tampered = {**binding, field: value}

    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), task["tool"], arguments, approval=approval, task_binding=tampered)
    assert called == []


def test_sdb_accepts_only_registered_typed_write_tasks():
    base = {"scope": {}, "summary": "write", "verifiable_output": "result"}
    for tool, arguments in (
        ("automation.create_rule", {"name": "n", "event_type": "e", "channel": "c", "template_event": "t", "cooldown_seconds": 0}),
        ("project.create", {"slug": "s", "name": "N", "purpose": "P"}),
        ("project.rename", {"project": "s", "name": "N"}),
        ("project.archive", {"project": "s"}),
        ("project.merge", {"source": "s", "target": "t"}),
    ):
        task = SDBTask.model_validate({**base, "id": tool, "tool": tool, "arguments": arguments})
        assert task.tool == tool

    with pytest.raises(ValueError, match="write-not-registered"):
        SDBTask.model_validate({**base, "id": "unknown", "tool": "project.destroy", "arguments": {"project": "s"}})


def test_write_argument_schemas_forbid_missing_and_extra_fields():
    with pytest.raises(ValueError):
        ProjectCreateArgs.model_validate({"slug": "s", "name": "N"})
    with pytest.raises(ValueError):
        ProjectRenameArgs.model_validate({"project": "s", "name": "N", "extra": 1})
    with pytest.raises(ValueError):
        ProjectArchiveArgs.model_validate({"project": "s", "extra": 1})
    with pytest.raises(ValueError):
        ProjectMergeArgs.model_validate({"source": "s", "target": "t", "extra": 1})
    with pytest.raises(ValueError):
        RuleArgs.model_validate({"name": "n", "event_type": "e", "channel": "c", "template_event": "t", "cooldown_seconds": -1})


def test_project_create_requires_exact_decision_payload(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.create",
        lambda *args, **kwargs: called.append(True),
    )
    args = {"slug": "s", "name": "N", "purpose": "P"}
    approval = issue_approval({
        "tool": "project.create",
        "arguments": args,
        "project_payload": {"operation": "create", "arguments": args, "decision": {"create_distinct": True}},
    })
    assert consume_approval(approval, approval["token"])
    execute_tool(SimpleNamespace(), "project.create", args, approval=approval)
    assert called == [True]

    bad = issue_approval({"tool": "project.create", "arguments": args, "project_payload": {"operation": "create", "arguments": args, "decision": {"unexpected": True}}})
    assert consume_approval(bad, bad["token"])
    with pytest.raises(ToolValidationError, match="decision"):
        execute_tool(SimpleNamespace(), "project.create", args, approval=bad)
    assert called == [True]


def test_write_handler_failure_is_preserved_as_error_evidence(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.automation.create_rule",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    args = {"name": "n", "event_type": "e", "conditions": {}, "channel": "c", "template_event": "t", "cooldown_seconds": 0}
    approval = issue_approval({"tool": "automation.create_rule", "arguments": args})
    assert consume_approval(approval, approval["token"])
    result = execute_tool(SimpleNamespace(), "automation.create_rule", args, approval=approval)
    assert result["status"] == "error"
    assert result["evidence"]["status"] == "error"


def test_web_search_is_bounded_and_failures_are_empty():
    html = "<html><body>" + "".join(
        f'<a class="result__a" href="https://example.test/{n}">{"x" * 2000}</a>'
        for n in range(8)
    ) + "</body></html>"

    class Client:
        def get(self, _url):
            return type("Response", (), {"text": html, "raise_for_status": lambda self: None})()

    results = DuckDuckGoSearch(Client()).search("safe query", limit=99)
    assert len(results) == 5
    assert all(len(result["title"]) <= 1000 for result in results)


def test_conversations_and_appointments_use_service_seams(monkeypatch):
    conversation = SimpleNamespace(id=1)
    appointment = SimpleNamespace(id=2, starts_at=datetime.now(timezone.utc) + timedelta(days=1))
    monkeypatch.setattr(
        "app.services.conversations.list_conversations",
        lambda session, query, limit: [conversation],
    )
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.scheduling.list_for_range",
        lambda *args, **kwargs: [(appointment, None, None, None, None)],
    )
    assert execute_tool(SimpleNamespace(), "conversations.search", {"query": "a"})["result"] == [{"id": 1}]
    assert execute_tool(SimpleNamespace(), "appointments.upcoming", {})["result"][0]["id"] == 2


def test_memory_read_is_bounded_and_uses_memory_service(monkeypatch):
    memories = [SimpleNamespace(id=index, topic_key="topic") for index in range(30)]
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.list_for_entity",
        lambda *args, **kwargs: memories,
    )
    result = execute_tool(
        SimpleNamespace(),
        "memory.read",
        {"scope": "customer", "entity_id": "42", "topic": "topic", "limit": 5},
    )
    assert result["status"] == "completed"
    assert len(result["result"]) == 5


def test_panel_memory_read_uses_trusted_thread_and_fails_closed(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.list_for_entity",
        lambda *args, **kwargs: calls.append(kwargs) or [],
    )

    result = execute_tool(
        SimpleNamespace(), "memory.read", {"scope": "panel"}, trusted_thread_id=7
    )
    assert result["status"] == "completed"
    assert calls == [{"scope": "panel", "entity_id": "thread:7"}]

    with pytest.raises(ToolValidationError, match="positive trusted thread id"):
        execute_tool(SimpleNamespace(), "memory.read", {"scope": "panel"})
    with pytest.raises(ToolValidationError, match="positive trusted thread id"):
        execute_tool(
            SimpleNamespace(), "memory.search", {"scope": "panel", "query": "launch"}
        )


def test_memory_search_is_scoped_and_bounds_content(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.hybrid_search",
        lambda *args, **kwargs: calls.append((args, kwargs)) or [{
            "id": 1,
            "scope": "panel",
            "entity_id": "thread:7",
            "contenido": "x" * 5000,
        }],
    )

    result = execute_tool(
        SimpleNamespace(),
        "memory.search", {"query": "launch", "scope": "panel", "limit": 1},
        trusted_thread_id=7,
    )

    assert result["status"] == "completed"
    assert len(result["result"][0]["contenido"]) == 2_000
    assert calls[0][1] == {"scope": "panel", "entity_id": "thread:7", "top_k": 1}
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "memory.search", {"query": "x", "scope": "panel", "entity_id": "customer:7"})


def test_memory_write_is_thread_anchored(monkeypatch):
    assert AUTONOMOUS_WRITE_ALLOWLIST == frozenset({"memory.write"})
    assert "scope" not in MemoryWriteArgs.model_json_schema()["properties"]
    assert "entity_id" not in MemoryWriteArgs.model_json_schema()["properties"]
    with pytest.raises(ValueError):
        MemoryWriteArgs.model_validate({"titulo": "x", "contenido": "y", "topic_key": "system:row"})

    class Savepoint:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    session = SimpleNamespace(begin_nested=lambda: Savepoint())
    row = SimpleNamespace(id=4)
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.upsert",
        lambda session, **kwargs: calls.append(kwargs) or row,
    )
    args = {"titulo": "Decision", "contenido": "Use the panel", "topic_key": "agent:decision"}

    first = execute_tool(session, "memory.write", args, trusted_thread_id=7)
    second = execute_tool(session, "memory.write", args, trusted_thread_id=7)

    assert first["result"] == {"written": True, "id": 4, "topic_key": "agent:decision"}
    assert second["result"] == first["result"]
    assert all(call["scope"] == "panel" and call["entity_id"] == "thread:7" for call in calls)


def test_memory_write_project_visibility_uses_canonical_agent_axis(monkeypatch):
    class Savepoint:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    session = SimpleNamespace(begin_nested=lambda: Savepoint())
    row = SimpleNamespace(id=5)
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.upsert",
        lambda session, **kwargs: calls.append(kwargs) or row,
    )

    result = execute_tool(
        session,
        "memory.write",
        {
            "titulo": "Project fact",
            "contenido": "Reuse this",
            "topic_key": "agent:fact",
            "visibility": "project",
        },
        trusted_thread_id=8,
    )

    assert result["result"] == {"written": True, "id": 5, "topic_key": "agent:fact"}
    assert calls[0]["scope"] == "agent"
    assert calls[0]["entity_id"] == "agent:default"
    assert calls[0]["proyecto"] == "default"
    assert calls[0]["producer"].value == "agent"
    assert calls[0]["origin_thread_id"] == "8"


def test_memory_write_degrades_and_fails_closed_without_trusted_thread(monkeypatch):
    class Savepoint:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    session = SimpleNamespace(begin_nested=lambda: Savepoint())
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.upsert",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("embedding unavailable")),
    )
    args = {"titulo": "Discovery", "contenido": "Fact", "topic_key": "agent:fact"}
    with pytest.raises(ToolValidationError):
        execute_tool(session, "memory.write", args)

    result = execute_tool(session, "memory.write", args, trusted_thread_id=7)
    assert result["result"]["written"] is False
    assert result["result"]["degraded_reason"] == "embedding unavailable"


def test_websearch_failure_is_error_evidence(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.websearch.search",
        lambda *args, **kwargs: (_ for _ in ()).throw(SearchFailure("timeout")),
    )
    result = execute_tool(SimpleNamespace(), "web.search", {"query": "status"})
    assert result["status"] == "error"
    assert result["evidence"]["status"] == "error"
    assert result["evidence"]["reason"] == "timeout"


def test_websearch_malformed_response_is_failure():
    class Client:
        def get(self, _url):
            return type(
                "Response",
                (),
                {
                    "text": "<html><body><a class='result__a' href='javascript:alert(1)'>unsafe</a></body></html>",
                    "raise_for_status": lambda self: None,
                },
            )()

    with pytest.raises(SearchFailure, match="unsafe"):
        DuckDuckGoSearch(Client()).search("unsafe")


def test_approval_failure_records_error_evidence_before_raising(monkeypatch):
    from app.chat.assistant.nodes import execute

    state = {
        "thread_id": 4,
        "run_id": "run-4",
        "plan": {"tool": "automation.create_rule", "arguments": {}, "requires_approval": True},
        "approval": None,
        "evidence": [],
        "session": SimpleNamespace(),
    }
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    with pytest.raises(PermissionError, match="approval") as caught:
        execute(state)
    assert state["evidence"][0]["status"] == "error"
    assert "approval" in state["evidence"][0]["detail"]
    assert caught.value.evidence[0]["status"] == "error"
