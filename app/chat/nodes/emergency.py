"""emergency node (EM-2, EM-3, EM-5; T4.2).

Runs ONLY via the emergency gate (never from route): a strong hit runs the
full deterministic safety protocol; a weak hit escalates to a human. No LLM
on either path — the gate exists precisely to keep the safety path free of
model calls (design D4: no LLM validation on emergency).

Strong hit (EM-3):
- abandons capture (EM-2): the reply is the safety protocol, never the next
  capture question
- delivers settings `emergency.safety_instructions` + `emergency.contacts` +
  `emergency.notify_message` (approved safety steps, contacts, technician-
  notified confirmation; the actual owner/technician notification lands in
  T4.3)
- flags the case row (emergency, status=escalado, escalated_at) through the
  minimal get-or-create bridge (the full cases service is T4.4)
- conversation.state -> human (HH-1 state model; the deriva bundle lands in
  T4.4)
- audit entry (SH-5) + operador-visible conversation_event

Weak hit (EM-5): escalate to a human, never silently ignore — deterministic
escalation reply + conversation.state -> human + escalation event.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.chat.nodes.classify_intent import _get_or_create_case
from app.chat.state import ConversationState
from app.db import session_scope
from app.models import (
    Conversation,
    ConversationEvent,
    ConversationState as ConversationStateEnum,
)
from app.services.audit import record_audit
from app.services.settings import (
    DEFAULT_EMERGENCY_CONTACTS,
    DEFAULT_EMERGENCY_NOTIFY_MESSAGE,
    DEFAULT_SAFETY_INSTRUCTIONS,
    get_setting,
)

logger = logging.getLogger(__name__)

# EM-5 weak-hit reply: a human takes over (mirrors summary.ESCALATION_REPLY).
WEAK_HIT_REPLY = (
    "Tu mensaje puede indicar una situación de riesgo. Un asesor de Lumat "
    "revisará tu caso y te contactará a la brevedad."
)


def _protocol_replies(session) -> list[str]:
    """EM-3: safety instructions + contacts + technician-notified blocks."""
    instructions = get_setting(
        session, "emergency.safety_instructions", default=DEFAULT_SAFETY_INSTRUCTIONS
    )
    contacts = get_setting(
        session, "emergency.contacts", default=DEFAULT_EMERGENCY_CONTACTS
    )
    notify = get_setting(
        session, "emergency.notify_message", default=DEFAULT_EMERGENCY_NOTIFY_MESSAGE
    )
    safety_reply = "INSTRUCCIONES DE SEGURIDAD:\n" + "\n".join(
        f"- {step}" for step in instructions
    )
    contacts_reply = "CONTACTOS DE EMERGENCIA:\n" + "\n".join(
        f"- {contact}" for contact in contacts
    )
    return [safety_reply, contacts_reply, notify]


def emergency(state: ConversationState) -> dict:
    """Run the safety protocol (strong hit) or escalate (weak hit)."""
    strong = state.emergency_hit == "strong"

    with session_scope() as session:
        conversation = session.get(Conversation, state.conversation_id)
        if conversation is not None:
            conversation.state = ConversationStateEnum.HUMAN
        if strong:
            case = _get_or_create_case(session, state)
            case.emergency = True
            case.status = "escalado"
            case.escalated_at = datetime.now(timezone.utc)
            session.add(
                ConversationEvent(
                    conversation_id=state.conversation_id,
                    event="emergency",
                    cause="strong_hit",
                )
            )
            record_audit(
                session,
                actor="system",
                action="conversation.emergency_detected",
                entity="conversation",
                entity_id=str(state.conversation_id),
                after={"hit": "strong"},
            )
            replies = _protocol_replies(session)
        else:
            session.add(
                ConversationEvent(
                    conversation_id=state.conversation_id,
                    event="escalation",
                    cause="emergency_weak_hit",
                )
            )
            replies = [WEAK_HIT_REPLY]

    if strong:
        return {
            "emergency": True,
            "escalate": True,
            "escalate_reason": "emergency",
            "replies": replies,
        }
    return {"escalate": True, "escalate_reason": "emergency_weak_hit", "replies": replies}
