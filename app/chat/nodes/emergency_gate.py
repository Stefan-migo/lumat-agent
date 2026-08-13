"""emergency_gate node (EM-1, EM-2, EM-5; design: gate before any LLM).

Deterministic keyword detection that runs on EVERY inbound message BEFORE any
LLM call, including mid-capture turns (EM-2 interrupt): the graph routes the
gate first and only then falls into the `_flow_start` conditional, so a
capture sub-flow never re-classifies past an emergency.

Reads the SS-2 keyword list from settings on every run and classifies the raw
message text (EM-1 "Keyword configured" applies on the very next message):

- "strong" -> the emergency node runs the full safety protocol (EM-3), no LLM
- "weak"   -> the emergency node escalates to a human (EM-5, never ignore)
- None     -> normal flow continues (greeting / capture / classify)

Per-run read + compile (ponytail: ~14 short keywords compile in microseconds
and there is no cache to invalidate; a shared cache would need a settings-
change invalidation hook for zero measurable gain).
"""

from __future__ import annotations

from app.chat.state import ConversationState
from app.db import session_scope
from app.services.emergency import classify_emergency, compile_keywords
from app.services.settings import get_emergency_keywords


def _current_text(state: ConversationState) -> str:
    return state.window[-1]["text"] if state.window else ""


def emergency_gate(state: ConversationState) -> dict:
    """Classify the current message; store `emergency_hit` for the router."""
    text = _current_text(state)
    if not text:
        return {"emergency_hit": None}
    with session_scope() as session:
        pattern = compile_keywords(get_emergency_keywords(session))
    return {"emergency_hit": classify_emergency(text, pattern)}
