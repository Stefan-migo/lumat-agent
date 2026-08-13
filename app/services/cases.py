"""Cases service (HH-2 deriva; design: app/services/cases.py).

Formal replacement for the T3.4 minimal get-or-create bridge
(`classify_intent._get_or_create_case`, ponytail debt): one place owns the
case row lifecycle and the deriva bundle.

- `get_or_create_case` — the conversation's latest case, creating a bare row
  when none exists (classification writes service/priority/status; the
  handoff node escalates it).
- `build_deriva_bundle` — HH-2 snapshot: full conversation history, summary,
  customer ficha data, captured fields and escalation context. The panel
  (HH-4/T5.3) renders the bundle without re-joining live rows, so the case
  stays self-contained even after the conversation/customer evolve.
- `create_handoff_case` — escalate the case: summary + status + escalated_at
  + the bundle snapshot (HH-2 "Handoff bundle complete").

All functions take an explicit session; the caller commits (matches
app/services/customers.py / audit.py style).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.state import ConversationState
from app.models import Case, Customer, Message


def get_or_create_case(session: Session, conversation_id: int, customer_id: int) -> Case:
    """Return the conversation's latest case, creating a bare one if needed."""
    case = session.scalar(
        select(Case)
        .where(Case.conversation_id == conversation_id)
        .order_by(Case.id.desc())
        .limit(1)
    )
    if case is None:
        case = Case(conversation_id=conversation_id, customer_id=customer_id)
        session.add(case)
        session.flush()
    return case


def build_deriva_bundle(
    session: Session,
    state: ConversationState,
    *,
    summary_text: str | None,
    reason: str,
) -> dict:
    """HH-2 snapshot: history + summary + customer ficha + captured fields."""
    messages = session.scalars(
        select(Message)
        .where(Message.conversation_id == state.conversation_id)
        .order_by(Message.id)
    ).all()
    customer = session.get(Customer, state.customer_id)
    history = [
        {
            "direction": m.direction.value,
            "msg_type": m.msg_type.value,
            "text": m.text,
            "media_url": m.media_url,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
    return {
        "history": history,
        "summary": summary_text,
        "customer": {
            "id": customer.id if customer else None,
            "name": customer.name if customer else None,
            "phone_e164": customer.phone_e164 if customer else state.phone,
            "email": customer.email if customer else None,
            "comuna": customer.comuna if customer else None,
            "address": customer.address if customer else None,
        },
        "captured": dict(state.captured or {}),
        "emergency": {"hit": state.emergency_hit, "flag": state.emergency},
        "escalate_reason": reason,
        "conversation_id": state.conversation_id,
        "customer_id": state.customer_id,
    }


def create_handoff_case(
    session: Session,
    state: ConversationState,
    *,
    summary_text: str | None,
    reason: str,
) -> Case:
    """Escalate the conversation's case with the deriva bundle (HH-2)."""
    case = get_or_create_case(session, state.conversation_id, state.customer_id)
    case.summary = summary_text
    case.status = "escalado"
    case.escalated_at = datetime.now(timezone.utc)
    case.bundle = build_deriva_bundle(
        session, state, summary_text=summary_text, reason=reason
    )
    session.flush()
    return case
