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

from app.chat.nodes.replies import render_reply
from app.chat.nodes.summary import compose_fallback_summary, generate_summary
from app.chat.state import ConversationState, set_conversation_state
from app.db import session_scope
from app.models import (
    Conversation,
    ConversationState as ConversationStateEnum,
    Customer,
)
from app.services import prompts
from app.services.audit import record_audit
from app.services.cases import create_handoff_case
from app.services.realtime import record_activity
from app.services.settings import REPLY_TEXT_DEFAULTS, get_reply_texts

logger = logging.getLogger(__name__)

# The shipped generic handoff wording, used by every reason that has no text of
# its own (and as the fallback when a derivation text cannot be filled). This
# alias is the default the tests assert.
HANDOFF_REPLY = REPLY_TEXT_DEFAULTS["handoff"]

# S4: the five escalation reasons whose wording the customer reads. Every other
# reason (injection, emergency, cost limits, KB misses, unclear bookings…) keeps
# the generic `handoff` text, so a reason added later never ships copy nobody
# reviewed. The keys are `reply.texts` entries, editable from the panel.
DERIVATION_REPLY_KEYS: dict[str, str] = {
    "cobertura": "handoff_cobertura",
    "persona": "handoff_persona",
    "unknown_intent_thrice": "handoff_unknown_intent_thrice",
    "campo_sin_respuesta": "handoff_campo_sin_respuesta",
    "booking_unavailable": "handoff_booking_unavailable",
}


def _escalate_reason(state: ConversationState) -> str:
    """Label the escalation: post-classification reason > gate trigger."""
    return state.escalate_reason or state.handoff_reason or "handoff"


def derivation_reply(
    texts: dict[str, str], reason: str, captured: dict | None = None
) -> str:
    """The text the customer reads for this escalation reason (S4).

    Only the slot the chosen text declares is filled, and the coverage text falls
    back to the generic one when the captured comuna is missing: `render_text` is
    strict, so an unfilled `{{comuna}}` would otherwise reach the customer as
    literal braces or break the escalation.
    """
    key = DERIVATION_REPLY_KEYS.get(reason, "handoff")
    values: dict[str, str] = {}
    if "comuna" in prompts.placeholders(texts[key]):
        comuna = (captured or {}).get("comuna")
        if not comuna or comuna == "unknown":
            return render_reply(texts, "handoff")
        values["comuna"] = comuna
    return render_reply(texts, key, **values)


def handoff(state: ConversationState) -> dict:
    """Escalate to a human: deriva bundle + state -> human + reply + audit."""
    reason = _escalate_reason(state)

    with session_scope() as session:
        customer = session.get(Customer, state.customer_id)
    if state.cost_mode == "blocked":
        # SS-3: under a cost block NO LLM runs anywhere — the escalation
        # summary is skipped and the reply is the deterministic `handoff` text
        # from settings.
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
        handoff_reply = derivation_reply(
            get_reply_texts(session), reason, state.captured
        )
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
        "replies": [handoff_reply],
    }
