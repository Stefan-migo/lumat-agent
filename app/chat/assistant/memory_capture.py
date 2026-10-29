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

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import InternalChatMessage, Memory

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
