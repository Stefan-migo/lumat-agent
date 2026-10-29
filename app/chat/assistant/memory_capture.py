"""Deterministic memory capture gates for the panel assistant (MEM-13, S1-S5).

The runtime owns the *when*: a bounded set of gates computed from the finished
turn and the thread, never from the user's phrasing and never from the model's
mood. The model only produces the content of a candidate, under a strict schema.

Three reasons can fire, in this precedence:

1. ``compaction`` — the thread crossed its rotation threshold, so the part that
   lives only in the window today gets a durable record (S4).
2. ``durable_write`` — the turn executed a tool that changes business state, so
   the outcome itself is worth remembering (S3).
3. ``turns`` — every ``CAPTURE_TURN_INTERVAL`` user turns, so a long
   conversation leaves a trace even when nothing was written (S1, S3).

It never fires when the paid-call budget is blocked, when the thread is not
trusted, or once the per-thread daily budget is spent. A count that cannot be
read fails closed: this module decides whether to spend money, so an unknown
budget is "no".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chat.assistant.tools.registry import MemoryWriteArgs
from app.models import InternalChatMessage, Memory
from app.services.prompts import load


_CAPTURE_PROMPT = "prompts/assistant_memory_capture.md"
_MAX_TOOL_RESULTS = 3
_MAX_TOOL_RESULT_CHARS = 2000
_MAX_USER_REQUEST_CHARS = 4000
_MAX_PLAN_SUMMARY_CHARS = 2000
_MAX_FINAL_RESPONSE_CHARS = 3000

CAPTURE_TURN_INTERVAL = 4
CAPTURE_DAILY_LIMIT = 6

# The assistant's own messages carry this author; every other author is a human
# turn (the panel stamps the acting user's role, e.g. `admin` or `operador`).
ASSISTANT_AUTHOR = "agent"

CaptureReason = Literal["turns", "durable_write", "compaction"]


@dataclass(frozen=True)
class CaptureDecision:
    """One fired gate. The reason is recorded as capture evidence."""

    reason: CaptureReason


def _bounded_text(value: object, limit: int) -> str:
    if isinstance(value, str):
        return value[:limit]
    if value is None:
        return ""
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(value)
    return text[:limit]


def _capture_payload(
    *,
    user_request: object,
    plan_summary: object,
    tool_results: object,
    final_response: object,
) -> str:
    executed_tools = []
    if isinstance(tool_results, list):
        for entry in tool_results[:_MAX_TOOL_RESULTS]:
            if not isinstance(entry, dict):
                continue
            executed_tools.append(
                {
                    "tool": _bounded_text(entry.get("tool", ""), 120),
                    "result": _bounded_text(
                        entry.get("result", entry.get("output", "")),
                        _MAX_TOOL_RESULT_CHARS,
                    ),
                }
            )
    return json.dumps(
        {
            "user_request": _bounded_text(user_request, _MAX_USER_REQUEST_CHARS),
            "plan_summary": _bounded_text(plan_summary, _MAX_PLAN_SUMMARY_CHARS),
            "executed_tools": executed_tools,
            "final_response_excerpt": _bounded_text(final_response, _MAX_FINAL_RESPONSE_CHARS),
        },
        ensure_ascii=False,
    )


def _planner_call(messages: list[dict], state: Any, call_key: str) -> tuple[str, object, dict[str, str] | None]:
    """Resolve the paid planner seam lazily.

    `nodes` imports this module for the capture node, so importing the seam at
    module level would close the cycle at graph build time. Keeping the module
    attribute also gives tests one patch point that never touches `nodes`.
    """
    from app.chat.assistant.nodes import _planner_call as paid_planner_call

    return paid_planner_call(messages, state, call_key)


def extract_candidates(
    *,
    state: Any,
    user_request: object,
    plan_summary: object,
    tool_results: object,
    final_response: object,
) -> list[dict[str, Any]]:
    """Extract up to three strictly validated memory candidates from a finished turn."""
    messages = [
        {"role": "system", "content": load(_CAPTURE_PROMPT)},
        {
            "role": "user",
            "content": _capture_payload(
                user_request=user_request,
                plan_summary=plan_summary,
                tool_results=tool_results,
                final_response=final_response,
            ),
        },
    ]
    try:
        raw_text, _completion, error = _planner_call(messages, state, "memory_capture")
    except Exception:
        return []
    if error or not isinstance(raw_text, str):
        return []
    try:
        payload = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return []
    if not isinstance(payload, dict) or set(payload) != {"memories"}:
        return []
    items = payload["memories"]
    if not isinstance(items, list):
        return []
    candidates: list[dict[str, Any]] = []
    for item in items[:3]:
        try:
            validated = MemoryWriteArgs.model_validate(item)
        except (ValidationError, TypeError, ValueError):
            continue
        candidates.append(validated.model_dump())
    return candidates


def capture_decision(
    *,
    cost_allowed: bool,
    thread_id: object,
    turn_index: object,
    captures_today: object,
    durable_write: bool,
    compacted: bool,
) -> CaptureDecision | None:
    """Decide whether this finished turn earns a capture, and why.

    Pure: every input comes from the caller, so the rule is testable without a
    database and cannot drift with ambient state.
    """
    if not cost_allowed:
        return None
    if type(thread_id) is not int or thread_id <= 0:
        return None
    if type(turn_index) is not int or turn_index <= 0:
        return None
    if type(captures_today) is not int or captures_today >= CAPTURE_DAILY_LIMIT:
        return None
    if compacted:
        return CaptureDecision("compaction")
    if durable_write:
        return CaptureDecision("durable_write")
    if turn_index % CAPTURE_TURN_INTERVAL == 0:
        return CaptureDecision("turns")
    return None


def thread_turn_index(session: Session, thread_id: int) -> int:
    """How many human turns this thread holds so far (the current one included)."""
    return int(
        session.scalar(
            select(func.count(InternalChatMessage.id)).where(
                InternalChatMessage.thread_id == thread_id,
                InternalChatMessage.author != ASSISTANT_AUTHOR,
            )
        )
        or 0
    )


def captures_today(session: Session, thread_id: int, *, now: datetime | None = None) -> int:
    """Memories already written from this thread since UTC midnight.

    Agent-authored memories carry ``origin_thread_id`` (MEM-9), so the thread's
    own budget counts every capture it produced today — the agent's explicit
    writes and the runtime's captures alike.
    """
    start = datetime.combine((now or datetime.now(timezone.utc)).date(), time.min, timezone.utc)
    return int(
        session.scalar(
            select(func.count(Memory.id)).where(
                Memory.origin_thread_id == str(thread_id),
                Memory.created_at >= start,
            )
        )
        or 0
    )


def durable_write_in(tool_results: list[dict[str, Any]], autonomous: frozenset[str]) -> bool:
    """Whether any executed step changed business state.

    Read-only tools and the always-authorized writes (memory/artifact) are
    excluded: the agent's own memory write already recorded itself, so capturing
    again would spend a model call to duplicate it.
    """
    from app.chat.assistant.tools.registry import ToolValidationError, get_tool

    for entry in tool_results:
        name = entry.get("tool")
        if not isinstance(name, str) or entry.get("status") == "error":
            continue
        if name in autonomous:
            continue
        try:
            definition = get_tool(name)
        except ToolValidationError:
            continue
        if definition.write:
            return True
    return False


def should_capture(state: Any) -> CaptureDecision | None:
    """Evaluate the gates against one finished assistant turn."""
    from app.chat.assistant.tools.registry import AUTONOMOUS_WRITE_ALLOWLIST

    session = state.get("session")
    thread_id = state.get("thread_id")
    if session is None or type(thread_id) is not int or thread_id <= 0:
        return None
    try:
        turn_index = thread_turn_index(session, thread_id)
        captured = captures_today(session, thread_id)
    except Exception:  # a gate that cannot read its own budget never spends
        return None
    return capture_decision(
        cost_allowed=bool((state.get("guardrails") or {}).get("cost_allowed", True)),
        thread_id=thread_id,
        turn_index=turn_index,
        captures_today=captured,
        durable_write=durable_write_in(state.get("tool_results") or [], AUTONOMOUS_WRITE_ALLOWLIST),
        compacted=bool((state.get("compaction") or {}).get("rotated")),
    )
