"""Allow-listed, typed assistant tools.

Tool handlers return plain bounded data and receive the request transaction
directly. They never call panel routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.chat.assistant.approval import validate_execution
from app.chat.assistant.tools import search as websearch
from app.models import Appointment, Case, Conversation, Customer
from app.services import automation, cases, customers, kb

MAX_ITEMS = 20


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
    return value


def _search_customers(session, args: SearchArgs):
    return customers.search_customers(session, args.query, args.limit)


def _search_conversations(session, args: QueryArgs):
    statement = select(Conversation).join(Customer, Customer.id == Conversation.customer_id)
    if args.query:
        statement = statement.where(
            Customer.name.ilike(f"%{args.query}%") | Conversation.wa_phone.contains(args.query)
        )
    return list(session.scalars(statement.order_by(Conversation.created_at.desc()).limit(args.limit)))


def _upcoming_appointments(session, args: AppointmentArgs):
    return list(session.scalars(
        select(Appointment)
        .where(Appointment.starts_at >= datetime.now(timezone.utc))
        .order_by(Appointment.starts_at, Appointment.id)
        .limit(args.limit)
    ))


def _open_cases(session, args: CasesArgs):
    return [case for case, _customer in cases.list_open_cases(session, args.limit)]


def _retrieve_kb(session, args: KbArgs):
    return kb.retrieve(session, args.query, top_k=args.top_k)


def _kpis(session, args: KpiArgs):
    # dashboard imports panel serializers; defer it to avoid loading the panel
    # router while the assistant registry is being imported.
    from app.services import dashboard

    return dashboard.compute_kpis(session, args.window_days)


def _create_rule(session, args: RuleArgs):
    return automation.create_rule(session, args.model_dump(), actor="assistant", executor_origin=True)


def _web_search(_session, args: WebSearchArgs):
    return websearch.search(args.query, limit=args.limit)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    args_model: type[BaseModel]
    read_only: bool
    handler: Callable[[Any, BaseModel], Any]

    @property
    def write(self) -> bool:
        return not self.read_only

    def schema(self) -> dict:
        return self.args_model.model_json_schema()


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "customers.search": ToolDefinition("customers.search", SearchArgs, True, _search_customers),
    "customers.list": ToolDefinition("customers.list", SearchArgs, True, _search_customers),
    "conversations.search": ToolDefinition("conversations.search", QueryArgs, True, _search_conversations),
    "conversations.list": ToolDefinition("conversations.list", QueryArgs, True, _search_conversations),
    "appointments.upcoming": ToolDefinition("appointments.upcoming", AppointmentArgs, True, _upcoming_appointments),
    "appointments.list": ToolDefinition("appointments.list", AppointmentArgs, True, _upcoming_appointments),
    "cases.list": ToolDefinition("cases.list", CasesArgs, True, _open_cases),
    "kb.retrieve": ToolDefinition("kb.retrieve", KbArgs, True, _retrieve_kb),
    "memory.kpis": ToolDefinition("memory.kpis", KpiArgs, True, _kpis),
    "dashboard.summary": ToolDefinition("dashboard.summary", KpiArgs, True, _kpis),
    "web.search": ToolDefinition("web.search", WebSearchArgs, True, _web_search),
    "automation.create_rule": ToolDefinition("automation.create_rule", RuleArgs, False, _create_rule),
}


def get_tool(name: str) -> ToolDefinition:
    try:
        return TOOL_REGISTRY[name]
    except KeyError as exc:
        raise ToolValidationError(f"unknown assistant tool: {name}") from exc


def tool_schemas() -> dict[str, dict]:
    return {name: definition.schema() for name, definition in TOOL_REGISTRY.items()}


def execute_tool(session, name: str, arguments: dict, *, approval: dict | None = None) -> dict:
    definition = get_tool(name)
    try:
        parsed = definition.args_model.model_validate(arguments)
    except Exception as exc:
        raise ToolValidationError(f"invalid arguments for {name}") from exc
    payload = {"tool": name, "arguments": parsed.model_dump()}
    if not definition.read_only and not approval:
        raise ToolValidationError("write tool requires consumed exact approval")
    if not definition.read_only and not validate_execution(payload, approval or {}):
        raise ToolValidationError("approval does not match exact tool arguments")
    try:
        result = _plain(definition.handler(session, parsed))
    except ToolValidationError:
        raise
    except Exception as exc:
        raise ToolExecutionError(f"{name} failed") from exc
    return {"tool": name, "status": "completed", "read_only": definition.read_only, "result": result}
