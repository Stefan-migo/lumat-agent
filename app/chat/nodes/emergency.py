"""emergency node (EM-2, EM-3; T4.2, weak path migrated in T4.4).

Runs ONLY via the emergency gate on a STRONG hit — the full deterministic
safety protocol. No LLM on this path (design D4: no LLM validation on
emergency). The weak hit no longer lands here: since T4.4 the gate routes
`weak` straight to the handoff node, so EM-5 escalation and every other
escalation share the same human/escalate flow (HH-2 deriva bundle + state ->
human). This node is the protocol, not the handoff.

Strong hit (EM-3):
- abandons capture (EM-2): the reply is the safety protocol, never the next
  capture question
- delivers settings `emergency.protocol` (approved safety steps, contacts and
  the technician-notified confirmation; the owner/technician notification fires
  below). The content is editable from the panel but is never the gate: a
  strong hit fires from `emergency.keywords` before any of this is read.
- flags the case row (emergency, status=escalado, escalated_at) through the
  cases service (T4.4)
- conversation.state -> human through `set_conversation_state` (HH-1:
  transition recorded with actor=system)
- audit entry (SH-5) + operador-visible conversation_event
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.chat.state import ConversationState, set_conversation_state
from app.db import session_scope
from app.models import (
    Conversation,
    ConversationEvent,
    ConversationState as ConversationStateEnum,
    Customer,
)
from app.services.audit import record_audit
from app.services.cases import set_case_status, get_or_create_case
from app.services.notify import send_emergency_notification
from app.services.notifications import notify_admins
from app.services.settings import get_emergency_protocol

logger = logging.getLogger(__name__)


def _protocol_replies(session) -> list[str]:
    """EM-3: safety instructions + contacts + technician-notified blocks."""
    protocol = get_emergency_protocol(session)
    instructions = protocol["safety_instructions"]
    contacts = protocol["contacts"]
    notify = protocol["notify_message"]
    safety_reply = "INSTRUCCIONES DE SEGURIDAD:\n" + "\n".join(
        f"- {step}" for step in instructions
    )
    contacts_reply = "CONTACTOS DE EMERGENCIA:\n" + "\n".join(
        f"- {contact}" for contact in contacts
    )
    return [safety_reply, contacts_reply, notify]


def emergency(state: ConversationState) -> dict:
    """Run the safety protocol (EM-3). The gate only routes strong hits here."""
    with session_scope() as session:
        conversation = session.get(Conversation, state.conversation_id)
        if conversation is not None:
            set_conversation_state(
                session,
                conversation,
                ConversationStateEnum.HUMAN,
                cause="emergency_strong_hit",
                actor="system",
            )
        case = get_or_create_case(session, state.conversation_id, state.customer_id)
        case.emergency = True
        set_case_status(case, "escalado")
        case.escalated_at = datetime.now(timezone.utc)
        session.add(
            ConversationEvent(
                conversation_id=state.conversation_id,
                event="emergency",
                cause="strong_hit",
                actor="system",
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
        # EM-4: notify the owner/technician (WhatsApp template, email
        # fallback). `send_emergency_notification` never raises and audits
        # its own attempts; the outer guard keeps a notification bug from
        # ever blocking the safety reply (EM-3). One notification per
        # emergency — a delivered one (notified_at set) is not re-sent;
        # a failed one (notified_at still None) retries on the next hit.
        if case.notified_at is None:
            try:
                customer = session.get(Customer, state.customer_id)
                context = state.window[-1]["text"] if state.window else ""
                send_emergency_notification(
                    session, case, customer, conversation, context=context
                )
                notify_admins(
                    session,
                    title="Emergencia detectada",
                    content=f"Se detectó una emergencia en el caso #{case.id}.",
                    source="emergencia",
                    source_id=case.id,
                    dedupe_key=f"emergencia:{case.id}",
                )
            except Exception:
                logger.exception(
                    "emergency notification failed for conversation %s",
                    state.conversation_id,
                )
        replies = _protocol_replies(session)

    return {
        "emergency": True,
        "escalate": True,
        "escalate_reason": "emergency",
        "replies": replies,
    }
