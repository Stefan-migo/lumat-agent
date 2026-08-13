"""cost_gate node (SS-3; design: deterministic gate before any LLM).

Runs on EVERY inbound message after `emergency_gate` and before
`handoff_gate` — deterministic, zero LLM cost. It computes the
per-conversation and UTC-day spend states from the DB (costs.py) and stores
the combined mode on the state:

- "normal"        -> the flow continues unchanged
- "conservative"  -> the flow continues (LLM still allowed) but `respond`
  answers briefly (short-reply mode; the flag lives on ConversationState)
- "blocked"       -> no LLM anywhere: the router escalates to the handoff
  node, which skips its summary LLM call (handoff.py) and replies the
  deterministic HANDOFF_REPLY canned fallback (SS-3 — the existing no-LLM
  reply family; no fake-answer generator)

Owner alerts fire here, once per scope+threshold crossing, audit-deduped
(`costs.maybe_alert_owner`): 80% -> conservative alert, 100% -> block
alert. Ordering vs `emergency_gate`: SAFETY FIRST — a strong emergency hit
routes to the emergency protocol before this gate ever runs, so a gas leak
during a budget block still gets the safety protocol (and the emergency
path never calls the LLM anyway).
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.chat.state import ConversationState
from app.db import session_scope
from app.services import costs


def cost_gate(state: ConversationState) -> dict:
    """Evaluate spend states, alert the owner on crossings, flag cost_mode."""
    with session_scope() as session:
        conv_percent, conv_mode = costs.conversation_cost_state(
            session, state.conversation_id
        )
        day_percent, day_mode = costs.daily_cost_state(session)
        costs.maybe_alert_owner(
            session,
            scope="conversation",
            entity_id=str(state.conversation_id),
            percent=conv_percent,
            spend=costs.conversation_spend(session, state.conversation_id),
        )
        costs.maybe_alert_owner(
            session,
            scope="daily",
            entity_id=str(datetime.now(timezone.utc).date()),
            percent=day_percent,
            spend=costs.daily_spend(session),
        )
        mode = costs.combined_cost_mode(conv_mode, day_mode)

    result = {"cost_mode": mode}
    if mode == "blocked":
        result["escalate"] = True
        # Label the deriva bundle: daily block applies to every conversation
        # of the day; conversation block is specific to this conversation.
        result["escalate_reason"] = (
            "cost_daily_limit" if day_mode == "blocked" else "cost_conversation_limit"
        )
    return result
