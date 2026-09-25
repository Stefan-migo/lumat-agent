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

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.chat.state import ConversationState
from app.models import Case, Customer, Message
from app.services.audit import record_audit
from app.services.events import publish_event

CLOSING_CASE_STATUSES = frozenset({"closed", "cerrado", "finalizado", "cancelado"})


def case_is_open_expr():
    """Canonical predicate for an open case, including NULL-status cases."""
    return and_(
        Case.closed_at.is_(None),
        or_(Case.status.is_(None), Case.status.not_in(CLOSING_CASE_STATUSES)),
    )


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
        publish_event(
            session, event_type="case.created", entity_type="case", entity_id=case.id,
            payload={"customer_id": customer_id, "conversation_id": conversation_id},
            dedupe_key=f"case:{case.id}:created",
        )
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
    publish_event(
        session, event_type="case.updated", entity_type="case", entity_id=case.id,
        payload={"customer_id": case.customer_id, "conversation_id": case.conversation_id, "status": case.status},
        dedupe_key=f"case:{case.id}:handoff",
    )
    return case


# ---------------------------------------------------------------------------
# Panel operations (T5.3; HH-4, AP-5)
# ---------------------------------------------------------------------------


def list_open_cases(session: Session, limit: int = 100) -> list[Case]:
    """HH-4: pending/escalated cases (open, not closed), escalated first.

    The panel needs the customer next to each case, so rows are joined with
    the customer record (the template renders name + phone).
    """
    return list(
        session.execute(
            select(Case, Customer)
            .join(Customer, Case.customer_id == Customer.id)
            .where(case_is_open_expr())
            .order_by(
                Case.escalated_at.desc().nulls_last(),
                Case.created_at.desc(),
                Case.id.desc(),
            )
            .limit(limit)
        ).all()
    )


_UNSET = object()  # sentinel: distinguish "keep" from "explicitly clear"


def update_case(
    session: Session,
    case: Case,
    *,
    status: str | None = None,
    responsible_id: int | None | object = _UNSET,
    actor: str = "system",
) -> Case:
    """AP-5: change case state and/or the responsible user; audited.

    `status=None` keeps the current value; `responsible_id=None` (explicit)
    CLEARS the assignment (the sentinel default means "keep"). Every change
    writes an audit snapshot (SH-5). The caller commits.
    """
    before = {"status": case.status, "responsible_id": case.responsible_id}
    if status is not None:
        was_closing = case.status in CLOSING_CASE_STATUSES
        is_closing = status in CLOSING_CASE_STATUSES
        case.status = status
        if is_closing and not was_closing and case.closed_at is None:
            case.closed_at = datetime.now(timezone.utc)
        elif was_closing and not is_closing:
            case.closed_at = None
    if responsible_id is not _UNSET:
        case.responsible_id = responsible_id
    record_audit(
        session,
        actor=actor,
        action="case.updated",
        entity="case",
        entity_id=str(case.id),
        before=before,
        after={"status": case.status, "responsible_id": case.responsible_id},
    )
    session.flush()
    publish_event(
        session, event_type="case.updated", entity_type="case", entity_id=case.id,
        payload={"status": case.status, "responsible_id": case.responsible_id},
        dedupe_key=f"case:{case.id}:updated:{case.status}:{case.responsible_id}",
    )
    return case
