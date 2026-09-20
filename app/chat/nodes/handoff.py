"""handoff node — deriva bundle + human takeover (HH-1, HH-2, HH-3; T4.4).

Reached from every escalation trigger (handoff_gate pre-LLM triggers,
emergency weak hit, classify/route post-classification escalations — 2x
unknown, injection, SS-1 always_escalate, KB miss). On handoff:

- generates the CM-5 summary (LLM; a failure never blocks the escalation —
  the bundle uses a deterministic captured-data fallback)
- builds the HH-2 deriva bundle (history + summary + customer + captured)
  onto the case row via app/services/cases.py
- transitions the conversation bot -> human through the single auditable
  `set_conversation_state` helper (HH-1 state_change event)
- records the escalation trigger event (operador-visible) + an audit entry
- replies that a human will take over; the customer never repeats info (HH-2)

During `human` the webhook keeps persisting messages (HH-5); the bot never
runs again for the conversation (ingest boundary, no panel reply in H1).
"""

from __future__ import annotations

import logging

from app.chat.nodes.summary import compose_fallback_summary, generate_summary
from app.chat.state import ConversationState, set_conversation_state
from app.db import session_scope
from app.models import (
    Conversation,
    ConversationState as ConversationStateEnum,
    Customer,
)
from app.services.audit import record_audit
from app.services.cases import create_handoff_case
from app.services.realtime import record_activity

logger = logging.getLogger(__name__)

# H1 handoff reply: a human takes over (same wording the escalation summary
# used pre-T4.4, so the customer-facing message is unchanged).
HANDOFF_REPLY = "Un asesor revisará tu caso y te contactará a la brevedad."


def _escalate_reason(state: ConversationState) -> str:
    """Label the escalation: post-classification reason > gate trigger."""
    return state.escalate_reason or state.handoff_reason or "handoff"


def handoff(state: ConversationState) -> dict:
    """Escalate to a human: deriva bundle + state -> human + reply + audit."""
    reason = _escalate_reason(state)

    with session_scope() as session:
        customer = session.get(Customer, state.customer_id)
    if state.cost_mode == "blocked":
        # SS-3: under a cost block NO LLM runs anywhere — the escalation
        # summary is skipped and the reply is the deterministic HANDOFF_REPLY
        # canned fallback.
        summary_text = compose_fallback_summary(state)
    else:
        try:
            summary_text = generate_summary(state, customer)
        except Exception:
            logger.exception(
                "summary generation failed for handoff of conversation %s",
                state.conversation_id,
            )
            summary_text = compose_fallback_summary(state)

    with session_scope() as session:
        conversation = session.get(Conversation, state.conversation_id)
        case = create_handoff_case(
            session, state, summary_text=summary_text, reason=reason
        )
        if conversation is not None:
            set_conversation_state(
                session,
                conversation,
                ConversationStateEnum.HUMAN,
                cause=f"handoff:{reason}",
                actor="rule",
            )
        record_activity(
            session,
            state.conversation_id,
            "escalation",
            cause=f"handoff:{reason}",
            actor="rule",
        )
        record_audit(
            session,
            actor="rule",
            action="conversation.handoff",
            entity="conversation",
            entity_id=str(state.conversation_id),
            after={"reason": reason, "case_id": case.id},
        )

    return {
        "escalate": True,
        "escalate_reason": reason,
        "summary": summary_text,
        "replies": [HANDOFF_REPLY],
    }
