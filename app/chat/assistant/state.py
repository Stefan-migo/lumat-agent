"""Durable state contract for the panel assistant, separate from WhatsApp."""

from __future__ import annotations

from collections.abc import Callable
from math import ceil
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

INJECTION_TOKEN_BUDGET = 4_000
SESSION_WINDOW_TOKENS = 8_000
COMPACTION_THRESHOLD_TOKENS = 4_000
COMPACTION_RETENTION_TOKENS = 2_000

ASSISTANT_STATE_KEYS = {
    "context_meta",
    "planner",
    "guardrails",
    "compaction",
    "extension_hooks",
}


def estimate_tokens(text: str) -> int:
    """Estimate tokens deterministically from UTF-8 bytes, rounded upward."""
    return ceil(len(text.encode("utf-8")) / 4)


class PlannerOutput(BaseModel):
    """The only planner shape accepted at the assistant trust boundary."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool", "respond", "complex"]
    classification: Literal["normal", "sdb"] = "normal"
    tool: str | None = None
    arguments: dict = Field(default_factory=dict)
    summary: str = Field(min_length=1, max_length=200)
    requires_approval: bool = False

    @model_validator(mode="after")
    def require_tool_for_tool_kind(self) -> "PlannerOutput":
        if self.kind == "tool" and not self.tool:
            raise ValueError("tool is required when kind is tool")
        if self.kind != "tool" and self.tool is not None:
            raise ValueError("tool is only allowed when kind is tool")
        return self


class SDBTrigger(BaseModel):
    """Strict input contract for planner and authenticated admin signals."""

    model_config = ConfigDict(extra="forbid")

    classification: Literal["normal", "sdb"] = "normal"
    sdb_requested: bool | None = None
    actor_role: str | None = None


class AssistantState(TypedDict, total=False):
    request_message_id: int
    thread_id: int
    run_id: str
    user_id: int
    content: str
    plan: dict
    approval: dict | None
    tool_result: dict | None
    evidence: list[dict]
    status: str
    response: str | None
    error: str | None
    on_token: Callable[[str], None] | None
    session: object
    actor: str
    attachments: list[object]
    context: dict
    context_meta: dict
    projection_evidence: dict
    planner: dict
    planner_output: dict
    guardrails: dict
    compaction: dict
    extension_hooks: dict
    legacy_compat: bool
    cost_mode: Literal["normal", "conservative", "blocked"]
    cost_directive: str
    sdb_trigger: Literal["classified", "admin"] | None
    sdb_phase: Literal["CLARIFY", "SPEC", "PLAN", "APPROVE", "EXECUTE", "VERIFY", "DELIVER"]
    sdb_route: Literal["normal", "sdb"]
    sdb_rejection: str | None
    sdb_scope: dict
    sdb_spec: dict
    sdb_tasks: list[dict]
    sdb_result: dict
    verification: dict


def normalize_sdb_trigger(signal: object) -> dict[str, str | None]:
    """Normalize the two trusted SDB entry signals, rejecting ambiguity."""
    try:
        trigger = SDBTrigger.model_validate(signal)
    except (TypeError, ValidationError):
        return {"route": "normal", "reason": "malformed-signal"}
    classification = trigger.classification
    requested = trigger.sdb_requested
    role = trigger.actor_role
    if classification not in {"normal", "sdb"}:
        return {"route": "normal", "reason": "malformed-classification"}
    if classification == "sdb" and requested is False:
        return {"route": "normal", "reason": "conflicting-trigger"}
    if requested is True and role != "admin":
        return {"route": "normal", "reason": "unauthorized-request"}
    if classification == "sdb":
        return {"route": "sdb", "trigger": "classified", "phase": "CLARIFY"}
    if requested is True:
        return {"route": "sdb", "trigger": "admin", "phase": "CLARIFY"}
    return {"route": "normal", "reason": None}
