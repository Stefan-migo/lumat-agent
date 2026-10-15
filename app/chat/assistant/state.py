"""Durable state contract for the panel assistant, separate from WhatsApp."""

from __future__ import annotations

from collections.abc import Callable
from math import ceil
from copy import deepcopy
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

ASSISTANT_STATE_KEYS = {
    "context_meta",
    "planner",
    "guardrails",
    "compaction",
    "extension_hooks",
    "kb_chunks",
}


def estimate_tokens(text: str) -> int:
    """Estimate tokens deterministically from UTF-8 bytes, rounded upward."""
    return ceil(len(text.encode("utf-8")) / 4)


class PlannerOutput(BaseModel):
    """The only planner shape accepted at the assistant trust boundary."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool", "respond", "complex", "delegate"]
    tool: str | None = None
    sub_agent: str | None = None
    arguments: dict = Field(default_factory=dict)
    summary: str = Field(min_length=1, max_length=200)
    success_criterion: str | None = Field(default=None, min_length=1, max_length=300)
    requires_approval: bool = False
    follow_up: bool = False
    skills: list[str] = Field(default_factory=list)

    @field_validator("summary", mode="before")
    @classmethod
    def clamp_summary(cls, value: object) -> object:
        if isinstance(value, str):
            return value[:200]
        return value

    @field_validator("success_criterion", mode="before")
    @classmethod
    def require_non_empty_success_criterion(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("success_criterion must not be empty")
        return value

    @field_validator("arguments", mode="before")
    @classmethod
    def empty_arguments_for_null(cls, value: object) -> object:
        """An explicit null means no arguments; the model authors it for respond plans."""
        if value is None:
            return {}
        return value

    @model_validator(mode="after")
    def require_tool_for_tool_kind(self) -> "PlannerOutput":
        if self.kind == "tool" and not self.tool:
            raise ValueError("tool is required when kind is tool")
        if self.kind != "tool" and self.tool is not None:
            raise ValueError("tool is only allowed when kind is tool")
        if self.kind == "delegate" and not self.sub_agent:
            raise ValueError("sub_agent is required when kind is delegate")
        if self.kind != "delegate" and self.sub_agent is not None:
            raise ValueError("sub_agent is only allowed when kind is delegate")
        return self


class CortexNote(BaseModel):
    """One structured planning note captured with explicit user confirmation."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["objective", "risk", "next_step", "general"]
    content: str = Field(min_length=1)


class CortexDecision(BaseModel):
    """One structured planning decision captured with explicit user confirmation."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class CortexSession(BaseModel):
    """Validated thread-scoped Cortex state."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    status: Literal["active", "closed"]
    opened_at: str = Field(min_length=1)
    closed_at: str | None
    report_key: str | None
    decisions: list[CortexDecision] = Field(default_factory=list)
    notes: list[CortexNote] = Field(default_factory=list)


def validate_cortex_session(state: object) -> bool:
    """Return whether a state contains a complete, valid Cortex session."""
    if not isinstance(state, dict) or "cortex_session" not in state:
        return False
    try:
        CortexSession.model_validate(state["cortex_session"])
    except (TypeError, ValidationError):
        return False
    return True


def merge_assistant_state(current: dict, update: dict) -> dict:
    """Recursively merge nested state without replacing sibling mappings."""
    result = deepcopy(current)
    for key, value in update.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = merge_assistant_state(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


class AssistantState(TypedDict, total=False):
    request_message_id: int
    thread_id: int
    run_id: str
    user_id: int
    content: str
    plan: dict
    approval: dict | None
    tool_result: dict | None
    tool_results: list[dict]
    tool_steps: int
    delegation: dict
    cap_reached: bool
    evidence: list[dict]
    status: str
    response: str | None
    error: str | None
    on_token: Callable[[str], None] | None
    session: object
    effective: dict
    actor: str
    actor_role: str
    attachments: list[object]
    context: dict
    context_meta: dict
    projection_evidence: dict
    planner: dict
    planner_output: dict
    guardrails: dict
    compaction: dict
    extension_hooks: dict
    kb_chunks: list[dict]
    cortex_session: dict
    legacy_compat: bool
    resume: bool
    cost_mode: Literal["normal", "conservative", "blocked"]
    cost_directive: str
    project_authorization: object
    verification: dict
    verify_requested: bool
    sdb_requested: bool
