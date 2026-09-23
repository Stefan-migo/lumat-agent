"""Allow-listed, typed assistant tools.

Tool handlers return plain bounded data and receive the request transaction
directly. They never call panel routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from itertools import zip_longest
from typing import Annotated, Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator
from app.chat.assistant.approval import issue_approval, validate_execution
from app.chat.assistant.tools import search as websearch
from app.chat.assistant.tools.search import SearchFailure
from app.services import automation, cases, customers, kb, projects, relations, scheduling, tukulpan as memory

MAX_ITEMS = 20
SDB_WRITE_ALLOWLIST = frozenset({
    "automation.create_rule",
    "project.create",
    "project.rename",
    "project.archive",
    "project.merge",
})
AUTONOMOUS_WRITE_ALLOWLIST = frozenset({"memory.write", "memory.update", "memory.delete"})
MEMORY_SEARCH_CONTENT_LIMIT = 2_000
# The customer id shape is a contract value the planner cannot derive from prose.
_CUSTOMER_ENTITY_PATTERN = r"^(?:customer:\d+|\d+)$"


class ToolValidationError(ValueError):
    """The tool name, arguments, or approval was unsafe."""


class ToolExecutionError(RuntimeError):
    """A declared tool failed without authorizing another tool call."""


class SearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=10, ge=1, le=MAX_ITEMS)


class QueryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=10, ge=1, le=MAX_ITEMS)


class CapabilitiesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppointmentArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=10, ge=1, le=MAX_ITEMS)


class CasesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=10, ge=1, le=MAX_ITEMS)


class KbArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=5)


class KpiArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window_days: int = Field(default=7, ge=1, le=31)


class _MemoryReadBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str | None = Field(default=None, max_length=255)
    limit: int = Field(default=10, ge=1, le=MAX_ITEMS)


class _MemorySearchBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)


class _OwnMemoryArgs(_MemoryReadBase):
    scope: Literal["own"]
    entity_id: None = None


class _CustomerMemoryArgs(_MemoryReadBase):
    scope: Literal["customer"]
    entity_id: str = Field(min_length=1, max_length=100, pattern=_CUSTOMER_ENTITY_PATTERN)


class _OwnMemorySearchArgs(_MemorySearchBase):
    scope: Literal["own"]
    entity_id: None = None


class _CustomerMemorySearchArgs(_MemorySearchBase):
    scope: Literal["customer"]
    entity_id: str = Field(min_length=1, max_length=100, pattern=_CUSTOMER_ENTITY_PATTERN)


_MemoryRead = Annotated[
    _OwnMemoryArgs | _CustomerMemoryArgs,
    Field(discriminator="scope"),
]
_MemorySearch = Annotated[
    _OwnMemorySearchArgs | _CustomerMemorySearchArgs,
    Field(discriminator="scope"),
]


class MemoryArgs(RootModel[_MemoryRead]):
    """memory.read arguments. Own memory is the default thread/project union."""

    @model_validator(mode="before")
    @classmethod
    def default_scope(cls, value):
        if isinstance(value, dict) and "scope" not in value:
            return {**value, "scope": "own"}
        return value


class MemorySearchArgs(RootModel[_MemorySearch]):
    """memory.search arguments. Own memory is the default thread/project union."""

    @model_validator(mode="before")
    @classmethod
    def default_scope(cls, value):
        if isinstance(value, dict) and "scope" not in value:
            return {**value, "scope": "own"}
        return value


class MemoryWriteArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str = Field(min_length=1, max_length=200)
    contenido: str = Field(min_length=1, max_length=2000)
    topic_key: str = Field(min_length=1, max_length=200, pattern=r"^agent:")
    tipo: Literal["decision", "discovery", "pattern", "preference"]
    visibility: Literal["thread", "global"] = "global"


class MemoryUpdateArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int = Field(gt=0)
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    contenido: str | None = Field(default=None, min_length=1, max_length=2000)
    tipo: Literal["decision", "discovery", "pattern", "preference"] | None = None

    @model_validator(mode="after")
    def require_patch(self):
        if self.titulo is None and self.contenido is None and self.tipo is None:
            raise ValueError("memory.update requires at least one field")
        return self


class MemoryDeleteArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int = Field(gt=0)


class WebSearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=5)


class RuleArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    event_type: str
    conditions: dict[str, Any] = Field(default_factory=dict)
    channel: str
    template_event: str
    cooldown_seconds: int = Field(ge=0, le=2_592_000)


class ProjectListArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=MAX_ITEMS, ge=1, le=MAX_ITEMS)


class ProjectFindArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=200)


class ProjectCreateArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=500)


class ProjectRenameArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)


class ProjectArchiveArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project: str = Field(min_length=1, max_length=100)


class ProjectMergeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1, max_length=100)
    target: str = Field(min_length=1, max_length=100)


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in list(value.items())[:MAX_ITEMS]}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in list(value)[:MAX_ITEMS]]
    if hasattr(value, "__table__"):
        return {column.name: _plain(getattr(value, column.name)) for column in value.__table__.columns}
    if hasattr(value, "__dict__"):
        return {str(k): _plain(v) for k, v in list(vars(value).items())[:MAX_ITEMS] if not str(k).startswith("_")}
    return value


def _search_customers(session, args: SearchArgs):
    return customers.search_customers(session, args.query, args.limit)


def _search_conversations(session, args: QueryArgs):
    # The conversation service imports panel serializers; defer it to avoid
    # loading the panel router during assistant registry import.
    from app.services import conversations

    return conversations.list_conversations(session, args.query, args.limit)


def _upcoming_appointments(session, args: AppointmentArgs):
    now = datetime.now(timezone.utc)
    rows = scheduling.list_for_range(session, now.date(), now.date() + timedelta(days=30), "UTC")
    return [row[0] for row in rows if row[0].starts_at is not None and row[0].starts_at >= now][: args.limit]


def _open_cases(session, args: CasesArgs):
    return [case for case, _customer in cases.list_open_cases(session, args.limit)]


def _retrieve_kb(session, args: KbArgs):
    # The Lumat assistant is internal and deliberately reads the whole corpus, including internal documents.
    return kb.retrieve(session, args.query, top_k=args.top_k, audience=None)


def _kpis(session, args: KpiArgs):
    # dashboard imports panel serializers; defer it to avoid loading the panel
    # router while the assistant registry is being imported.
    from app.services import dashboard

    return dashboard.compute_kpis(session, args.window_days)


def _read_memory(session, args: MemoryArgs, *, trusted_thread_id: int | None, proyecto: str = "default"):
    parsed = args.root
    if parsed.scope == "own":
        if type(trusted_thread_id) is not int or trusted_thread_id <= 0:
            raise ToolValidationError("own memory read requires a positive trusted thread id")
        thread_rows = memory.list_for_entity(
            session, scope="panel", entity_id=memory.thread_memory_entity(trusted_thread_id), proyecto=proyecto
        )
        agent_rows = memory.list_for_entity(
            session, scope="agent", entity_id=memory.agent_memory_entity(proyecto), proyecto=proyecto
        )
        if parsed.topic:
            thread_rows = [row for row in thread_rows if row.topic_key == parsed.topic]
            agent_rows = [row for row in agent_rows if row.topic_key == parsed.topic]
        # Interleave both axes before truncating: a thread holding `limit` rows must not hide the
        # project axis (R3-own-read-limit).
        rows = [
            row for pair in zip_longest(thread_rows, agent_rows) for row in pair if row is not None
        ]
        return rows[: parsed.limit]
    entity_id = parsed.entity_id
    rows = memory.list_for_entity(session, scope=parsed.scope, entity_id=entity_id)
    if parsed.topic:
        rows = [row for row in rows if row.topic_key == parsed.topic]
    return rows[: parsed.limit]


def _search_memory(session, args: MemorySearchArgs, *, trusted_thread_id: int | None, proyecto: str = "default"):
    parsed = args.root
    if parsed.scope == "own":
        if type(trusted_thread_id) is not int or trusted_thread_id <= 0:
            raise ToolValidationError("own memory search requires a positive trusted thread id")
        rows = memory.hybrid_search(
            session,
            parsed.query,
            scope="panel",
            entity_id=memory.thread_memory_entity(trusted_thread_id),
            proyecto=proyecto,
            top_k=parsed.limit,
        ) + memory.hybrid_search(
            session,
            parsed.query,
            scope="agent",
            entity_id=memory.agent_memory_entity(proyecto),
            proyecto=proyecto,
            top_k=parsed.limit,
        )
        rows.sort(key=lambda row: row.get("score", 0), reverse=True)
        return [
            {**row, "contenido": row.get("contenido", "")[:MEMORY_SEARCH_CONTENT_LIMIT]}
            for row in rows[: parsed.limit]
        ]
    entity_id = parsed.entity_id
    rows = memory.hybrid_search(
        session,
        parsed.query,
        scope=parsed.scope,
        entity_id=entity_id,
        top_k=parsed.limit,
    )
    return [
        {**row, "contenido": row.get("contenido", "")[:MEMORY_SEARCH_CONTENT_LIMIT]}
        for row in rows
    ]


def _write_memory(session, args: MemoryWriteArgs, *, trusted_thread_id: int, proyecto: str = "default"):
    key = args.topic_key
    try:
        authorization = None if proyecto == memory.WRITABLE_PROYECTO else projects.agent_context(session, proyecto)
        scope, entity_id = memory.visibility_target(
            args.visibility, thread_id=trusted_thread_id, proyecto=proyecto
        )
        with session.begin_nested():
            row = memory.upsert(
                session,
                scope=scope,
                entity_id=entity_id,
                topic_key=key,
                proyecto=proyecto,
                tipo=memory.MemoryType(args.tipo),
                titulo=args.titulo,
                contenido=args.contenido,
                producer=memory.MemoryProducer.AGENT,
                origin_thread_id=str(trusted_thread_id),
                visibility=args.visibility,
                authorization=authorization,
            )
            relations.judge_memory_relations(session, row)
        return {"written": True, "id": row.id, "topic_key": key}
    except Exception as exc:
        return {"written": False, "degraded_reason": str(exc), "topic_key": key}


def _owned_agent_memory_or_raise(session, memory_id: int, *, trusted_thread_id: int, proyecto: str):
    row = session.get(memory.Memory, memory_id)
    if row is None:
        raise ToolValidationError(f"memory {memory_id} is not owned by the assistant")
    owned_axes = {
        ("panel", memory.thread_memory_entity(trusted_thread_id)),
        ("agent", memory.agent_memory_entity(proyecto)),
    }
    if (
        row.proyecto != proyecto
        or row.producer is not memory.MemoryProducer.AGENT
        or not row.topic_key.startswith("agent:")
        or (row.scope, row.entity_id) not in owned_axes
    ):
        raise ToolValidationError(f"memory {memory_id} is not owned by the assistant")
    return row


def _update_memory(session, args: MemoryUpdateArgs, *, trusted_thread_id: int, proyecto: str = "default"):
    _owned_agent_memory_or_raise(session, args.id, trusted_thread_id=trusted_thread_id, proyecto=proyecto)
    try:
        with session.begin_nested():
            row = memory.update(
                session,
                args.id,
                titulo=args.titulo,
                contenido=args.contenido,
                tipo=memory.MemoryType(args.tipo) if args.tipo is not None else None,
            )
        return {"updated": True, "id": row.id}
    except Exception as exc:
        return {"updated": False, "degraded_reason": str(exc)}


def _delete_memory(session, args: MemoryDeleteArgs, *, trusted_thread_id: int, proyecto: str = "default"):
    _owned_agent_memory_or_raise(session, args.id, trusted_thread_id=trusted_thread_id, proyecto=proyecto)
    try:
        with session.begin_nested():
            row = memory.delete(session, args.id)
        return {"deleted": True, "id": row.id}
    except Exception as exc:
        return {"deleted": False, "degraded_reason": str(exc)}


def _create_rule(session, args: RuleArgs):
    return automation.create_rule(session, args.model_dump(), actor="assistant", executor_origin=True)


def _web_search(_session, args: WebSearchArgs):
    return websearch.search(args.query, limit=args.limit)


def _project_list(session, args: ProjectListArgs):
    return projects.list(session)[: args.limit]


def _project_find(session, args: ProjectFindArgs, *, _approval=None):
    return projects.find(session, args.query, _approval=_approval)


def _project_create(session, args: ProjectCreateArgs, *, _approval=None):
    return projects.create(session, args.slug, args.name, args.purpose, _approval=_approval)


def _project_rename(session, args: ProjectRenameArgs):
    return projects.rename(session, args.project, args.name)


def _project_archive(session, args: ProjectArchiveArgs):
    return projects.archive(session, args.project)


def _project_merge(session, args: ProjectMergeArgs):
    return projects.merge(session, args.source, args.target)


def _assistant_capabilities(_session, _args: CapabilitiesArgs):
    from app.services.prompts import load_assistant_config

    whitelist = load_assistant_config().tools_whitelist
    lines = []
    for name in whitelist:
        definition = TOOL_REGISTRY[name]
        access = "read-only" if definition.read_only else "write"
        lines.append(f"{name} — {definition.description} ({access})")
    return {
        "tool_count": len(whitelist),
        "capabilities": "\n".join(lines),
    }


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    args_model: type[BaseModel]
    read_only: bool
    handler: Callable[[Any, BaseModel], Any]
    description: str

    @property
    def write(self) -> bool:
        return not self.read_only

    def schema(self) -> dict:
        return self.args_model.model_json_schema()


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "assistant.capabilities": ToolDefinition("assistant.capabilities", CapabilitiesArgs, True, _assistant_capabilities, "List the assistant's own available tools and their purpose."),
    "customers.search": ToolDefinition("customers.search", SearchArgs, True, _search_customers, "Search customer records."),
    "customers.list": ToolDefinition("customers.list", SearchArgs, True, _search_customers, "List customer records."),
    "conversations.search": ToolDefinition("conversations.search", QueryArgs, True, _search_conversations, "Search panel conversations."),
    "conversations.list": ToolDefinition("conversations.list", QueryArgs, True, _search_conversations, "List panel conversations."),
    "appointments.upcoming": ToolDefinition("appointments.upcoming", AppointmentArgs, True, _upcoming_appointments, "List upcoming appointments."),
    "cases.list": ToolDefinition("cases.list", CasesArgs, True, _open_cases, "List open cases."),
    "kb.retrieve": ToolDefinition("kb.retrieve", KbArgs, True, _retrieve_kb, "Retrieve grounded knowledge-base results."),
    "memory.read": ToolDefinition("memory.read", MemoryArgs, True, _read_memory, "Read scoped memory."),
    "memory.search": ToolDefinition("memory.search", MemorySearchArgs, True, _search_memory, "Search scoped memory."),
    "memory.write": ToolDefinition("memory.write", MemoryWriteArgs, False, _write_memory, "Write memory; global across threads by default."),
    "memory.update": ToolDefinition("memory.update", MemoryUpdateArgs, False, _update_memory, "Update an agent-authored memory."),
    "memory.delete": ToolDefinition("memory.delete", MemoryDeleteArgs, False, _delete_memory, "Delete an agent-authored memory."),
    "dashboard.summary": ToolDefinition("dashboard.summary", KpiArgs, True, _kpis, "Read the operational dashboard summary."),
    "web.search": ToolDefinition("web.search", WebSearchArgs, True, _web_search, "Search the bounded web adapter."),
    "automation.create_rule": ToolDefinition("automation.create_rule", RuleArgs, False, _create_rule, "Create an automation after approval."),
    "project.list": ToolDefinition("project.list", ProjectListArgs, True, _project_list, "List project namespaces."),
    "project.find": ToolDefinition("project.find", ProjectFindArgs, True, _project_find, "Find a project namespace."),
    "project.create": ToolDefinition("project.create", ProjectCreateArgs, False, _project_create, "Create a project namespace after approval."),
    "project.rename": ToolDefinition("project.rename", ProjectRenameArgs, False, _project_rename, "Rename a project after approval."),
    "project.archive": ToolDefinition("project.archive", ProjectArchiveArgs, False, _project_archive, "Archive a project after approval."),
    "project.merge": ToolDefinition("project.merge", ProjectMergeArgs, False, _project_merge, "Merge projects after approval."),
}


def get_tool(name: str) -> ToolDefinition:
    try:
        return TOOL_REGISTRY[name]
    except KeyError as exc:
        raise ToolValidationError(f"unknown assistant tool: {name}") from exc


def tool_schemas() -> dict[str, dict]:
    return {name: definition.schema() for name, definition in TOOL_REGISTRY.items()}


def execute_tool(
    session,
    name: str,
    arguments: dict,
    *,
    approval: dict | None = None,
    task_binding: dict | None = None,
    whitelist: set[str] | frozenset[str] | None = None,
    cost_allowed: bool = True,
    trusted_thread_id: int | None = None,
    proyecto: str = "default",
) -> dict:
    definition = get_tool(name)
    if whitelist is not None and name not in whitelist:
        raise ToolValidationError(f"tool is not whitelisted: {name}")
    autonomous_write = name in AUTONOMOUS_WRITE_ALLOWLIST
    if autonomous_write and (type(trusted_thread_id) is not int or trusted_thread_id <= 0):
        raise ToolValidationError("autonomous memory write requires a positive trusted thread id")
    if definition.write and not autonomous_write and name not in SDB_WRITE_ALLOWLIST:
        raise ToolValidationError("write-not-registered")
    if not cost_allowed:
        raise ToolValidationError("assistant cost limit blocks tool execution")
    try:
        parsed = definition.args_model.model_validate(arguments)
    except Exception as exc:
        raise ToolValidationError(f"invalid arguments for {name}") from exc
    payload = {"tool": name, "arguments": parsed.model_dump()}
    if task_binding is not None:
        payload["task_binding"] = task_binding
    if isinstance(approval, dict) and isinstance(approval.get("sdb_payload"), dict):
        payload["sdb"] = approval["sdb_payload"]
    project_approval = None
    if name.startswith("project.") and approval:
        project_payload = (
            task_binding.get("project_payload")
            if isinstance(task_binding, dict) and isinstance(task_binding.get("project_payload"), dict)
            else approval.get("project_payload")
        )
        if isinstance(project_payload, dict):
            payload["project_payload"] = project_payload
        if not validate_execution(payload, approval):
            raise ToolValidationError("approval does not match exact tool arguments")
        decision = project_payload.get("decision") if isinstance(project_payload, dict) else None
        if name == "project.create" and (
            not isinstance(project_payload, dict)
            or set(project_payload) != {"operation", "arguments", "decision"}
            or project_payload.get("operation") != "create"
            or project_payload.get("arguments") != parsed.model_dump()
            or not isinstance(decision, dict)
            or set(decision) not in ({"selected_slug"}, {"create_distinct"})
            or ("selected_slug" in decision and not isinstance(decision["selected_slug"], str))
            or ("create_distinct" in decision and decision["create_distinct"] is not True)
        ):
            raise ToolValidationError("project create approval is missing an explicit decision")
        if name in {"project.find", "project.create"} and not isinstance(decision, dict):
            raise ToolValidationError("project approval is missing an explicit decision")
        if name in {"project.find", "project.create"}:
            project_approval = projects._ApprovedProjectDecision(
                operation=name.removeprefix("project."), decision=decision
            )
    if not definition.read_only and not autonomous_write and not approval:
        raise ToolValidationError("write tool requires consumed exact approval")
    if not definition.read_only and not autonomous_write and not project_approval and not validate_execution(payload, approval or {}):
        raise ToolValidationError("approval does not match exact tool arguments")
    try:
        if name == "project.find":
            result = _plain(definition.handler(session, parsed, _approval=project_approval))
        elif name == "project.create":
            result = _plain(definition.handler(session, parsed, _approval=project_approval))
        elif name in {"memory.write", "memory.update", "memory.delete"}:
            result = _plain(
                definition.handler(
                    session, parsed, trusted_thread_id=trusted_thread_id, proyecto=proyecto
                )
            )
        elif name in {"memory.read", "memory.search"}:
            result = _plain(
                definition.handler(
                    session, parsed, trusted_thread_id=trusted_thread_id, proyecto=proyecto
                )
            )
        else:
            result = _plain(definition.handler(session, parsed))
    except SearchFailure as exc:
        return {
            "tool": name,
            "status": "error",
            "read_only": definition.read_only,
            "error": str(exc),
            "evidence": {"tool": name, "status": "error", "reason": str(exc)},
        }
    except ToolValidationError:
        raise
    except Exception as exc:
        return {
            "tool": name,
            "status": "error",
            "read_only": definition.read_only,
            "error": str(exc),
            "evidence": {"tool": name, "status": "error", "reason": str(exc)},
        }
    if isinstance(result, dict) and result.get("requires_approval"):
        plan = {"tool": name, "arguments": parsed.model_dump()}
        return {
            "tool": name,
            "status": "approval_pending",
            "read_only": definition.read_only,
            "result": result,
            "approval": issue_approval(plan),
        }
    return {"tool": name, "status": "completed", "read_only": definition.read_only, "result": result}
