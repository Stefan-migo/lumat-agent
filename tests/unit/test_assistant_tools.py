from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace

import pytest

from app.chat.assistant.tools.registry import (
    AUTONOMOUS_WRITE_ALLOWLIST,
    MAX_ITEMS,
    CapabilitiesArgs,
    MemoryArgs,
    MemoryDeleteArgs,
    MemorySearchArgs,
    MemoryUpdateArgs,
    MemoryWriteArgs,
    ProjectArchiveArgs,
    ProjectCreateArgs,
    ProjectMergeArgs,
    ProjectRenameArgs,
    RuleArgs,
    ToolValidationError,
    TOOL_REGISTRY,
    ToolDefinition,
    _assistant_capabilities,
    execute_tool,
    get_tool,
    tool_schemas,
)
from app.services.prompts import load_assistant_config
from app.chat.assistant.state import SDBTask
from app.chat.assistant.approval import consume_approval, issue_approval, validate_execution
from app.services.projects import ProjectCandidate, ProjectResult
from app.services import tukulpan as memory
from app.chat.assistant.tools.search import BraveSearch, DuckDuckGoSearch, SearchFailure
import httpx
import respx


def test_registry_exposes_typed_bounded_tools():
    schemas = tool_schemas()
    assert "customers.search" in schemas
    assert schemas["customers.search"]["type"] == "object"
    assert get_tool("customers.search").read_only is True
    assert get_tool("automation.create_rule").read_only is False


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"customer_id": 0},
        {"customer_id": 1, "limit": MAX_ITEMS + 1},
        {"customer_id": 1, "unexpected": True},
    ],
)
def test_operational_history_args_reject_invalid_input(payload):
    with pytest.raises(ValueError):
        get_tool("customers.operational_history").args_model.model_validate(payload)


def test_operational_history_projects_bounded_service_results(monkeypatch):
    tool = get_tool("customers.operational_history")

    case_fields = {
        "id": 3, "service": "repair", "priority": "high", "status": "closed",
        "summary": "Completed", "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "closed_at": None, "customer_id": 99, "internal": "excluded",
    }
    appointment_fields = {
        "id": 4, "service": "inspection", "status": "completed",
        "starts_at": datetime(2025, 1, 2, tzinfo=timezone.utc),
        "ends_at": datetime(2025, 1, 2, 1, tzinfo=timezone.utc),
        "local_start": "2025-01-02T10:00", "timezone": "America/Santiago",
        "customer_id": 99, "message_text": "excluded", "media_url": "excluded",
    }
    case_rows = [SimpleNamespace(**case_fields) for _ in range(3)]
    appointment_rows = [SimpleNamespace(**appointment_fields) for _ in range(3)]
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.cases.list_cases_for_customer",
        lambda session, customer_id, limit: calls.append(("cases", customer_id, limit)) or case_rows,
    )
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.scheduling.list_for_customer",
        lambda session, customer_id: calls.append(("appointments", customer_id)) or appointment_rows,
    )

    result = tool.handler(SimpleNamespace(), tool.args_model(customer_id=7, limit=2))

    assert calls == [("cases", 7, 2), ("appointments", 7)]
    assert len(result["cases"]) == len(result["appointments"]) == 2
    assert set(result) == {"cases", "appointments"}
    assert set(result["cases"][0]) == {
        "id", "service", "priority", "status", "summary", "created_at", "closed_at"
    }
    assert set(result["appointments"][0]) == {
        "id", "service", "status", "starts_at", "ends_at", "local_start", "timezone"
    }
    assert result["cases"][0]["created_at"] == "2025-01-01T00:00:00+00:00"
    assert result["cases"][0]["closed_at"] is None
    assert result["appointments"][0]["starts_at"] == "2025-01-02T00:00:00+00:00"
    forbidden = {"customer_id", "name", "phone", "email", "address", "comuna", "consent",
                 "message_text", "media_url", "customer_notes"}
    assert not forbidden.intersection(result["cases"][0])
    assert not forbidden.intersection(result["appointments"][0])


@pytest.mark.parametrize("tool_name", ["customers.search", "customers.list"])
def test_customer_search_tools_project_only_public_fields(monkeypatch, tool_name):
    customer = SimpleNamespace(
        id=7, name="Example", state="nuevo", phone_e164="+56912345678",
        email="private@example.test", address="Private address", comuna="Private comuna",
        consent_status=True, consent_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.customers.search_customers",
        lambda *_args: [customer],
    )

    result = execute_tool(SimpleNamespace(), tool_name, {})["result"]

    assert set(result[0]) == {"id", "name", "state"}
    forbidden = {"phone_e164", "email", "address", "comuna", "consent_status", "consent_at"}
    assert not forbidden.intersection(result[0])


def test_registry_exposes_the_single_url_reader_as_a_read_only_tool():
    schemas = tool_schemas()
    assert "web.fetch" in schemas
    assert schemas["web.fetch"]["required"] == ["url"]
    assert get_tool("web.fetch").read_only is True


def test_capabilities_args_forbids_fields():
    with pytest.raises(ValueError):
        CapabilitiesArgs.model_validate({"unexpected": True})


def test_assistant_capabilities_reports_every_whitelisted_tool_without_truncation(monkeypatch):
    whitelist = [*load_assistant_config().tools_whitelist, "assistant.test-extra"]
    monkeypatch.setitem(
        TOOL_REGISTRY,
        "assistant.test-extra",
        ToolDefinition(
            "assistant.test-extra",
            CapabilitiesArgs,
            True,
            lambda _session, _args: {},
            "Test-only capability.",
        ),
    )
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(tools_whitelist=whitelist),
    )
    result = _assistant_capabilities(SimpleNamespace(), CapabilitiesArgs())
    names = [line.split(" — ", 1)[0] for line in result["capabilities"].splitlines()]

    assert result["tool_count"] == len(whitelist)
    assert result["tool_count"] > MAX_ITEMS
    assert names == whitelist
    assert len(names) == len(whitelist)


def test_assistant_capabilities_excludes_non_whitelisted_registry_entry(monkeypatch):
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda: SimpleNamespace(tools_whitelist=["customers.search"]),
    )

    result = _assistant_capabilities(SimpleNamespace(), CapabilitiesArgs())

    assert result["tool_count"] == 1
    assert "customers.search" in result["capabilities"]
    assert "project.list" not in result["capabilities"]


def test_memory_kpis_is_not_a_registered_tool():
    assert "memory.kpis" not in TOOL_REGISTRY
    assert "dashboard.summary" in TOOL_REGISTRY


def test_appointments_list_is_not_a_registered_tool():
    assert "appointments.list" not in TOOL_REGISTRY
    assert "appointments.upcoming" in TOOL_REGISTRY


def test_no_handler_is_shared_across_tool_domains():
    handler_domains = {}
    for name, definition in TOOL_REGISTRY.items():
        handler_domains.setdefault(definition.handler, set()).add(name.split(".", 1)[0])

    assert all(len(domains) == 1 for domains in handler_domains.values())


def test_memory_args_reject_unknown_scope_and_expose_canonical_scope_schema():
    with pytest.raises(ValueError):
        MemoryArgs.model_validate({"scope": "banana", "entity_id": "whatever"})

    assert sorted(MemoryArgs.model_json_schema()["discriminator"]["mapping"]) == [
        "customer", "own"
    ]


def test_memory_scope_entity_is_conditional_and_legacy_axes_are_forbidden():
    assert MemoryArgs.model_validate({"scope": "own"}).root.entity_id is None

    with pytest.raises(ValueError):
        MemoryArgs.model_validate({"scope": "own", "entity_id": "thread:7"})
    with pytest.raises(ValueError):
        MemoryArgs.model_validate({"scope": "customer"})
    with pytest.raises(ValueError):
        MemoryArgs.model_validate({"scope": "agent"})
    with pytest.raises(ValueError):
        MemoryArgs.model_validate({"scope": "panel"})


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


@respx.mock
def test_web_search_returns_bounded_provider_neutral_evidence():
    route = respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "T" * 2_000,
                            "url": "https://example.test/result",
                            "description": "S" * 2_000,
                        }
                        for _ in range(8)
                    ]
                }
            },
        )
    )

    results = BraveSearch(api_key="test-key").search("safe query", limit=99)

    assert route.called
    assert len(results) == 5
    assert set(results[0]) == {"title", "url", "snippet"}
    assert len(results[0]["title"]) <= 100
    assert len(results[0]["snippet"]) <= 200
    assert len(json.dumps(results)) < 4_000


@respx.mock
def test_web_search_sanitizes_html_and_entities_in_text_fields():
    respx.get("https://api.search.brave.com/res/v1/web/search").respond(
        200,
        json={
            "web": {
                "results": [
                    {
                        "title": "<em>Calefont</em> &amp; Chile",
                        "url": "https://example.test/result",
                        "description": "<strong>entre $90.000 y $280.000</strong> &amp; más",
                    }
                ]
            }
        },
    )

    result = BraveSearch(api_key="test-key").search("safe query")[0]

    assert "<" not in result["title"]
    assert ">" not in result["title"]
    assert "<" not in result["snippet"]
    assert ">" not in result["snippet"]
    assert result["title"] == "Calefont & Chile"
    assert result["snippet"] == "entre $90.000 y $280.000 & más"


@pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
@respx.mock
def test_web_search_provider_failures_are_explicit(status, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    respx.get("https://api.search.brave.com/res/v1/web/search").respond(status)

    with pytest.raises(SearchFailure):
        BraveSearch(api_key="test-key").search("safe query")


def _search_hit() -> dict:
    return {
        "web": {
            "results": [
                {
                    "title": "Calefont",
                    "url": "https://example.test/result",
                    "description": "un resultado",
                }
            ]
        }
    }


@respx.mock
def test_web_search_rate_limit_waits_and_retries_once(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    route = respx.get("https://api.search.brave.com/res/v1/web/search")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "1"}),
        httpx.Response(200, json=_search_hit()),
    ]

    results = BraveSearch(api_key="test-key").search("safe query")

    assert len(route.calls) == 2
    assert slept == [1.0]
    assert results[0]["url"] == "https://example.test/result"


@respx.mock
def test_web_search_rate_limit_wait_is_capped(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    route = respx.get("https://api.search.brave.com/res/v1/web/search")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "99"}),
        httpx.Response(200, json=_search_hit()),
    ]

    BraveSearch(api_key="test-key").search("safe query")

    assert len(route.calls) == 2
    assert slept == [2.0]


@respx.mock
def test_web_search_rate_limit_without_header_uses_the_default_wait(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    route = respx.get("https://api.search.brave.com/res/v1/web/search")
    route.side_effect = [
        httpx.Response(429),
        httpx.Response(200, json=_search_hit()),
    ]

    BraveSearch(api_key="test-key").search("safe query")

    assert len(route.calls) == 2
    assert slept == [1.0]


@respx.mock
def test_web_search_rate_limit_that_persists_fails_after_one_retry(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    route = respx.get("https://api.search.brave.com/res/v1/web/search")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "1"}),
        httpx.Response(429, headers={"Retry-After": "1"}),
    ]

    with pytest.raises(SearchFailure, match="rate-limited"):
        BraveSearch(api_key="test-key").search("safe query")

    assert len(route.calls) == 2
    assert slept == [1.0]


@respx.mock
def test_web_search_non_rate_limit_failure_does_not_retry(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    route = respx.get("https://api.search.brave.com/res/v1/web/search").respond(500)

    with pytest.raises(SearchFailure):
        BraveSearch(api_key="test-key").search("safe query")

    assert len(route.calls) == 1
    assert slept == []


@respx.mock
def test_web_search_challenge_timeout_and_malformed_payload_are_failures():
    respx.get("https://api.search.brave.com/res/v1/web/search").respond(
        202, content=b"<html><body>challenge</body></html>"
    )
    with pytest.raises(SearchFailure):
        BraveSearch(api_key="test-key").search("safe query")

    respx.get("https://api.search.brave.com/res/v1/web/search").respond(
        200, content=b"not json"
    )
    with pytest.raises(SearchFailure):
        BraveSearch(api_key="test-key").search("safe query")

    respx.get("https://api.search.brave.com/res/v1/web/search").respond(200, json={"web": {}})
    with pytest.raises(SearchFailure):
        BraveSearch(api_key="test-key").search("safe query")


@respx.mock
def test_web_search_timeout_is_explicit():
    respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        side_effect=httpx.ReadTimeout("timed out")
    )

    with pytest.raises(SearchFailure):
        BraveSearch(api_key="test-key").search("safe query")


@respx.mock
def test_web_search_empty_results_are_the_only_empty_success():
    route = respx.get("https://api.search.brave.com/res/v1/web/search").respond(
        200, json={"web": {"results": []}}
    )

    assert BraveSearch(api_key="test-key").search("safe query") == []
    assert route.calls[0].request.headers["X-Subscription-Token"] == "test-key"


def test_web_search_missing_api_key_fails_fast(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.tools.search.get_settings",
        lambda: SimpleNamespace(brave_search_api_key=" "),
    )

    with pytest.raises(SearchFailure, match="BRAVE_SEARCH_API_KEY"):
        BraveSearch().search("safe query")


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


def test_own_memory_read_uses_trusted_thread_and_agent_axes_and_fails_closed(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.list_for_entity",
        lambda *args, **kwargs: calls.append(kwargs) or [],
    )

    result = execute_tool(
        SimpleNamespace(), "memory.read", {"scope": "own"}, trusted_thread_id=7
    )
    assert result["status"] == "completed"
    assert calls == [
        {"scope": "panel", "entity_id": "thread:7", "proyecto": "default"},
        {"scope": "agent", "entity_id": "agent:default", "proyecto": "default"},
    ]

    with pytest.raises(ToolValidationError, match="positive trusted thread id"):
        execute_tool(SimpleNamespace(), "memory.read", {"scope": "own"})
    with pytest.raises(ToolValidationError, match="positive trusted thread id"):
        execute_tool(
            SimpleNamespace(), "memory.search", {"scope": "own", "query": "launch"}
        )


def test_memory_search_uses_own_axes_and_bounds_content(monkeypatch):
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
        "memory.search", {"query": "launch", "scope": "own", "limit": 1},
        trusted_thread_id=7,
    )

    assert result["status"] == "completed"
    assert len(result["result"][0]["contenido"]) == 2_000
    assert [kwargs for _args, kwargs in calls] == [
        {"scope": "panel", "entity_id": "thread:7", "proyecto": "default", "top_k": 1},
        {"scope": "agent", "entity_id": "agent:default", "proyecto": "default", "top_k": 1},
    ]
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "memory.search", {"query": "x", "scope": "own", "entity_id": "customer:7"})


def test_memory_write_derives_visibility_target_and_keeps_thread_override(monkeypatch):
    assert AUTONOMOUS_WRITE_ALLOWLIST == frozenset({"memory.write", "memory.update", "memory.delete"})
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
    monkeypatch.setattr("app.chat.assistant.tools.registry.relations.judge_memory_relations", lambda *args: [])
    args = {
        "titulo": "Decision",
        "contenido": "Use the panel",
        "topic_key": "agent:decision",
        "tipo": "decision",
    }

    first = execute_tool(session, "memory.write", args, trusted_thread_id=7)
    second = execute_tool(session, "memory.write", args, trusted_thread_id=7)

    assert first["result"] == {"written": True, "id": 4, "topic_key": "agent:decision"}
    assert second["result"] == first["result"]
    assert all(call["scope"] == "agent" and call["entity_id"] == "agent:default" for call in calls)

    execute_tool(
        session,
        "memory.write",
        {**args, "visibility": "thread"},
        trusted_thread_id=7,
    )
    assert calls[-1]["scope"] == "panel"
    assert calls[-1]["entity_id"] == "thread:7"


def test_memory_correction_args_are_bounded_and_require_a_patch():
    assert MemoryUpdateArgs.model_json_schema()["properties"].keys() == {
        "id", "titulo", "contenido", "tipo"
    }
    assert MemoryDeleteArgs.model_json_schema()["properties"].keys() == {"id"}
    with pytest.raises(ValueError):
        MemoryUpdateArgs.model_validate({"id": 1})
    with pytest.raises(ValueError):
        MemoryUpdateArgs.model_validate({"id": 1, "scope": "agent", "titulo": "x"})
    with pytest.raises(ValueError):
        MemoryDeleteArgs.model_validate({"id": 0})
    with pytest.raises(ValueError):
        MemoryDeleteArgs.model_validate({"id": 1, "topic_key": "agent:x"})


@pytest.mark.parametrize(
    "row_kwargs",
    [
        {"proyecto": "default", "producer": memory.MemoryProducer.AGENT, "topic_key": "agent:x", "scope": "panel", "entity_id": "thread:8"},
        {"proyecto": "default", "producer": memory.MemoryProducer.AGENT, "topic_key": "agent:x", "scope": "agent", "entity_id": "agent:default"},
    ],
)
def test_memory_correction_owned_axes_are_accepted(monkeypatch, row_kwargs):
    from app.chat.assistant.tools.registry import _owned_agent_memory_or_raise

    row = SimpleNamespace(id=4, **row_kwargs)
    session = SimpleNamespace(get=lambda _model, _id: row)
    assert _owned_agent_memory_or_raise(session, 4, trusted_thread_id=8, proyecto="default") is row


@pytest.mark.parametrize(
    "row_kwargs",
    [
        {"proyecto": "default", "producer": memory.MemoryProducer.USER, "topic_key": "agent:x", "scope": "agent", "entity_id": "agent:default"},
        {"proyecto": "default", "producer": memory.MemoryProducer.SYSTEM, "topic_key": "system:x", "scope": "agent", "entity_id": "agent:default"},
        {"proyecto": "default", "producer": memory.MemoryProducer.AGENT, "topic_key": "agent:x", "scope": "panel", "entity_id": "thread:9"},
        {"proyecto": "other", "producer": memory.MemoryProducer.AGENT, "topic_key": "agent:x", "scope": "agent", "entity_id": "agent:other"},
    ],
)
def test_memory_correction_rejects_rows_outside_agent_ownership(row_kwargs):
    from app.chat.assistant.tools.registry import _owned_agent_memory_or_raise

    row = SimpleNamespace(id=4, **row_kwargs)
    session = SimpleNamespace(get=lambda _model, _id: row)
    with pytest.raises(ToolValidationError):
        _owned_agent_memory_or_raise(session, 4, trusted_thread_id=8, proyecto="default")


def test_memory_correction_update_and_delete_are_autonomous(monkeypatch):
    assert AUTONOMOUS_WRITE_ALLOWLIST == frozenset({"memory.write", "memory.update", "memory.delete"})
    row = SimpleNamespace(id=4, proyecto="default", producer=memory.MemoryProducer.AGENT, topic_key="agent:x", scope="agent", entity_id="agent:default")

    class Savepoint:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    session = SimpleNamespace(begin_nested=lambda: Savepoint(), get=lambda _model, _id: row)
    monkeypatch.setattr("app.chat.assistant.tools.registry.memory.update", lambda *_args, **_kwargs: row)
    monkeypatch.setattr("app.chat.assistant.tools.registry.memory.delete", lambda *_args, **_kwargs: row)
    assert execute_tool(session, "memory.update", {"id": 4, "titulo": "Fixed"}, trusted_thread_id=8)["result"] == {"updated": True, "id": 4}
    assert execute_tool(session, "memory.delete", {"id": 4}, trusted_thread_id=8)["result"] == {"deleted": True, "id": 4}


def test_memory_service_update_reembeds_only_changed_content(monkeypatch):
    row = SimpleNamespace(
        contenido="Old", titulo="Old title", tipo=memory.MemoryType.DECISION,
        embedding=[0.0], normalized_hash="old", review_after=None,
    )
    session = SimpleNamespace(get=lambda _model, _id: row, flush=lambda: None)
    embedded = []
    monkeypatch.setattr("app.services.tukulpan._embed", lambda texts: embedded.append(texts) or [[1.0]])

    memory.update(session, 1, titulo="New title")
    assert embedded == []
    memory.update(session, 1, contenido="New content")
    assert embedded == [["New content"]]
    assert row.embedding == [1.0]
    assert row.normalized_hash == memory._normalized_hash("New content")


def test_memory_service_update_rejects_missing_id():
    session = SimpleNamespace(get=lambda _model, _id: None)

    with pytest.raises(ValueError, match="memory 1 not found"):
        memory.update(session, 1, titulo="Missing")


def test_memory_service_update_propagates_embedding_failure(monkeypatch):
    row = SimpleNamespace(
        contenido="Old", titulo="Old title", tipo=memory.MemoryType.DECISION,
        embedding=[0.0], normalized_hash="old", review_after=None,
    )
    session = SimpleNamespace(get=lambda _model, _id: row, flush=lambda: None)
    monkeypatch.setattr(
        "app.services.tukulpan._embed",
        lambda _texts: (_ for _ in ()).throw(RuntimeError("embedder unavailable")),
    )

    with pytest.raises(RuntimeError, match="embedder unavailable"):
        memory.update(session, 1, contenido="New content")


def test_memory_service_update_recomputes_review_after_when_tipo_becomes_decaying():
    row = SimpleNamespace(
        contenido="Content", titulo="Title", tipo=memory.MemoryType.DECISION,
        embedding=[0.0], normalized_hash="hash", review_after=None,
    )
    session = SimpleNamespace(get=lambda _model, _id: row, flush=lambda: None)

    memory.update(session, 1, tipo=memory.MemoryType.SUMMARY)

    assert row.review_after is not None


def test_memory_service_update_clears_review_after_when_tipo_becomes_non_decaying():
    row = SimpleNamespace(
        contenido="Content", titulo="Title", tipo=memory.MemoryType.SUMMARY,
        embedding=[0.0], normalized_hash="hash", review_after=memory._review_after(memory.MemoryType.SUMMARY),
    )
    session = SimpleNamespace(get=lambda _model, _id: row, flush=lambda: None)

    memory.update(session, 1, tipo=memory.MemoryType.DECISION)

    assert row.review_after is None


def test_memory_service_update_title_only_keeps_review_after():
    review_after = memory._review_after(memory.MemoryType.SUMMARY)
    row = SimpleNamespace(
        contenido="Content", titulo="Title", tipo=memory.MemoryType.SUMMARY,
        embedding=[0.0], normalized_hash="hash", review_after=review_after,
    )
    session = SimpleNamespace(get=lambda _model, _id: row, flush=lambda: None)

    memory.update(session, 1, titulo="New title")

    assert row.review_after == review_after


def test_memory_write_global_visibility_uses_canonical_agent_axis(monkeypatch):
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
    monkeypatch.setattr("app.chat.assistant.tools.registry.relations.judge_memory_relations", lambda *args: [])

    result = execute_tool(
        session,
        "memory.write",
        {
            "titulo": "Project fact",
            "contenido": "Reuse this",
            "topic_key": "agent:fact",
            "tipo": "decision",
            "visibility": "global",
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
    args = {
        "titulo": "Discovery",
        "contenido": "Fact",
        "topic_key": "agent:fact",
        "tipo": "discovery",
    }
    with pytest.raises(ToolValidationError):
        execute_tool(session, "memory.write", args)

    result = execute_tool(session, "memory.write", args, trusted_thread_id=7)
    assert result["result"]["written"] is False
    assert result["result"]["degraded_reason"] == "Memory write unavailable"
    assert "embedding unavailable" not in result["result"]["degraded_reason"]


def test_memory_update_degradation_does_not_leak_raw_exception(monkeypatch):
    from app.chat.assistant.tools.registry import _update_memory

    class Savepoint:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    raw_error = "private update backend details"
    row = SimpleNamespace(
        id=4, proyecto="default", producer=memory.MemoryProducer.AGENT,
        topic_key="agent:fact", scope="agent", entity_id="agent:default",
    )
    session = SimpleNamespace(begin_nested=lambda: Savepoint(), get=lambda _model, _id: row)
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.update",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError(raw_error)),
    )

    result = _update_memory(
        session,
        MemoryUpdateArgs(id=4, titulo="Updated"),
        trusted_thread_id=7,
    )

    assert result == {"updated": False, "degraded_reason": "Memory update unavailable"}
    assert raw_error not in result["degraded_reason"]


def test_memory_delete_degradation_does_not_leak_raw_exception(monkeypatch):
    from app.chat.assistant.tools.registry import _delete_memory

    class Savepoint:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    raw_error = "private delete backend details"
    row = SimpleNamespace(
        id=4, proyecto="default", producer=memory.MemoryProducer.AGENT,
        topic_key="agent:fact", scope="agent", entity_id="agent:default",
    )
    session = SimpleNamespace(begin_nested=lambda: Savepoint(), get=lambda _model, _id: row)
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.memory.delete",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError(raw_error)),
    )

    result = _delete_memory(
        session,
        MemoryDeleteArgs(id=4),
        trusted_thread_id=7,
    )

    assert result == {"deleted": False, "degraded_reason": "Memory delete unavailable"}
    assert raw_error not in result["degraded_reason"]


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
