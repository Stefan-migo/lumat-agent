"""Durable state contract for the panel assistant, separate from WhatsApp."""

from __future__ import annotations

from collections.abc import Callable
from math import ceil
from typing import TypedDict

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


class AssistantState(TypedDict, total=False):
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
    planner: dict
    guardrails: dict
    compaction: dict
    extension_hooks: dict
