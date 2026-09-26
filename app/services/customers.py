"""Customer records service (CR-1..CR-6; design: app/services/customers.py).

One ficha per person, deduplicated by normalized E.164 phone (CR-2):

- CR-1: auto-ficha — unknown phone -> customer row created (state `nuevo`)
- CR-2: get-or-create by E.164; `+56 9...` / `+569...` / `9...` collapse
- CR-3: lifecycle states (customer_state enum) with transition validation;
        every change audited (actor, before/after)
- CR-4: internal staff notes (author + timestamp), staff-only table
- CR-5: history query (conversations / cases / messages, chronological)
- CR-6: captured data (name/email/comuna/address) + consent on the ficha

All functions take an explicit session; the caller commits (matches
app/services/audit.py style).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Case,
    Conversation,
    Customer,
    CustomerNote,
    CustomerState,
    Message,
    Appointment,
)
from app.services.audit import record_audit

# CR-3 lifecycle. Every customer moves through these states; a transition not
# listed is invalid and is REJECTED (spec scenario: nuevo -> postventa).
# postventa/cancelado are terminal; postventa is reachable only from finalizado.
CUSTOMER_STATE_TRANSITIONS: dict[CustomerState, set[CustomerState]] = {
    CustomerState.NUEVO: {
        CustomerState.CONTACTADO,
        CustomerState.PENDIENTE,
        CustomerState.AGENDADO,
        CustomerState.EN_EVALUACION,
        CustomerState.CANCELADO,
    },
    CustomerState.CONTACTADO: {
        CustomerState.PENDIENTE,
        CustomerState.AGENDADO,
        CustomerState.EN_EVALUACION,
        CustomerState.FINALIZADO,
        CustomerState.CANCELADO,
    },
    CustomerState.PENDIENTE: {
        CustomerState.AGENDADO,
        CustomerState.EN_EVALUACION,
        CustomerState.FINALIZADO,
        CustomerState.CANCELADO,
    },
    CustomerState.AGENDADO: {
        CustomerState.EN_EVALUACION,
        CustomerState.FINALIZADO,
        CustomerState.CANCELADO,
    },
    CustomerState.EN_EVALUACION: {
        CustomerState.AGENDADO,
        CustomerState.FINALIZADO,
        CustomerState.CANCELADO,
    },
    CustomerState.FINALIZADO: {CustomerState.POSTVENTA, CustomerState.CANCELADO},
    CustomerState.CANCELADO: set(),
    CustomerState.POSTVENTA: set(),
}


class InvalidStateTransition(ValueError):
    """Raised when a customer state change violates the CR-3 lifecycle."""


# ---------------------------------------------------------------------------
# E.164 normalization (canonical location; ingest.py re-exports)
# ---------------------------------------------------------------------------


def normalize_phone_e164(wa_id: str) -> str:
    """Normalize a WhatsApp wa_id to E.164 (CR-2 dedup basis).

    Handles: full international "+56912345678", digits-only "56912345678",
    Chilean local mobile "912345678" (9XXXXXXXX -> +56 9...), and stray
    spaces/dashes. Unknown shapes fall back to a best-effort "+<digits>".
    """
    digits = re.sub(r"\D", "", wa_id or "")
    if not digits:
        return ""
    if digits.startswith("9") and len(digits) == 9:
        return "+56" + digits
    if digits.startswith("56") and len(digits) == 11:
        return "+" + digits
    return "+" + digits


# ---------------------------------------------------------------------------
# CR-1 / CR-2 — get-or-create by phone
# ---------------------------------------------------------------------------


def get_or_create_customer(session: Session, phone: str) -> Customer:
    """Return the ficha for `phone`, creating it on first contact (CR-1/CR-2).

    The phone is normalized to E.164 first, so any format of the same number
    hits the same UNIQUE(phone_e164) row — duplicates are impossible (CR-2).
    """
    phone_e164 = normalize_phone_e164(phone)
    if not phone_e164:
        raise ValueError("phone cannot be normalized to E.164")
    customer = session.scalar(select(Customer).where(Customer.phone_e164 == phone_e164))
    if customer is None:
        customer = Customer(phone_e164=phone_e164, state=CustomerState.NUEVO)
        session.add(customer)
        session.flush()
        record_audit(
            session,
            actor="system",
            action="customer.auto_created",
            entity="customer",
            entity_id=str(customer.id),
            after={"phone_e164": phone_e164, "channel": "whatsapp"},
        )
    elif customer.archived_at is not None:
        archived_at = customer.archived_at
        customer.archived_at = None
        record_audit(
            session,
            actor="system",
            action="customer.auto_unarchived",
            entity="customer",
            entity_id=str(customer.id),
            before={"archived_at": archived_at.isoformat()},
            after={"archived_at": None},
        )
    return customer


# ---------------------------------------------------------------------------
# CR-3 — lifecycle transitions (validated + audited)
# ---------------------------------------------------------------------------


def set_customer_state(
    session: Session,
    customer: Customer,
    new_state: CustomerState,
    *,
    actor: str = "system",
    reason: str | None = None,
) -> Customer:
    """Transition a customer to `new_state`; reject invalid CR-3 transitions.

    Records who changed it and when (audit_log before/after snapshot). The
    caller commits.
    """
    if new_state not in CUSTOMER_STATE_TRANSITIONS[customer.state]:
        raise InvalidStateTransition(
            f"invalid customer transition {customer.state.value} -> {new_state.value}"
            + (f" ({reason})" if reason else "")
        )
    before = {"state": customer.state.value}
    customer.state = new_state
    record_audit(
        session,
        actor=actor,
        action="customer.state_change",
        entity="customer",
        entity_id=str(customer.id),
        before=before,
        after={"state": new_state.value},
    )
    return customer


# ---------------------------------------------------------------------------
# CR-4 — internal notes (staff only)
# ---------------------------------------------------------------------------


def add_note(session: Session, customer_id: int, note: str, actor: str) -> CustomerNote:
    """Store an internal staff note on a customer ficha (author + timestamp)."""
    entry = CustomerNote(customer_id=customer_id, note=note, author=actor)
    session.add(entry)
    session.flush()
    return entry


def list_notes(session: Session, customer_id: int) -> list[CustomerNote]:
    """Internal notes in chronological order (CR-4 panel view)."""
    return list(
        session.scalars(
            select(CustomerNote)
            .where(CustomerNote.customer_id == customer_id)
            .order_by(CustomerNote.created_at, CustomerNote.id)
        )
    )


# ---------------------------------------------------------------------------
# AP-3 — clients list / search (panel)
# ---------------------------------------------------------------------------


def search_customers(
    session: Session,
    query: str | None = None,
    limit: int = 100,
    *,
    include_archived: bool = False,
) -> list[Customer]:
    """List customers, optionally filtered by name or phone (AP-3).

    `query` matches case-insensitively against the name, or as a digit
    substring against the E.164 phone ("3333" finds +56933334444). No query
    -> newest-first list. Used by the panel clients view.
    """
    statement = select(Customer).order_by(Customer.created_at.desc(), Customer.id.desc())
    if not include_archived:
        statement = statement.where(Customer.archived_at.is_(None))
    q = (query or "").strip()
    if q:
        digits = "".join(ch for ch in q if ch.isdigit())
        name_clause = Customer.name.ilike(f"%{q}%")
        if digits:
            statement = statement.where(
                name_clause | Customer.phone_e164.contains(digits)
            )
        else:
            statement = statement.where(name_clause)
    return list(session.scalars(statement.limit(limit)))


def archive_customer(session: Session, customer: Customer, *, actor: str) -> Customer:
    """Archive a customer record once, retaining its first archive timestamp."""
    if customer.archived_at is None:
        customer.archived_at = datetime.now(timezone.utc)
        record_audit(
            session,
            actor=actor,
            action="customer.archived",
            entity="customer",
            entity_id=str(customer.id),
            before={"archived_at": None},
            after={"archived_at": customer.archived_at.isoformat()},
        )
    return customer


def unarchive_customer(session: Session, customer: Customer, *, actor: str) -> Customer:
    """Restore a customer record once; an active record is left unchanged."""
    if customer.archived_at is not None:
        archived_at = customer.archived_at
        customer.archived_at = None
        record_audit(
            session,
            actor=actor,
            action="customer.unarchived",
            entity="customer",
            entity_id=str(customer.id),
            before={"archived_at": archived_at.isoformat()},
            after={"archived_at": None},
        )
    return customer


# ---------------------------------------------------------------------------
# CR-5 — full history (ficha view)
# ---------------------------------------------------------------------------


def customer_history(
    session: Session, customer_id: int, messages_limit: int | None = None
) -> dict:
    """Complete linked history: conversations, cases, messages (CR-5).

    Returns dicts (not ORM objects) so the panel can render plain data.
    Messages are flattened across all the customer's conversations and sorted
    chronologically.
    """
    # Local import: a top-level `customers -> cases` import cycles through
    # `app.chat.state` (which imports `get_or_create_customer` from this module).
    from app.services.cases import case_is_open

    conversations = session.scalars(
        select(Conversation)
        .where(Conversation.customer_id == customer_id)
        .order_by(Conversation.created_at, Conversation.id)
    ).all()
    cases = session.scalars(
        select(Case)
        .where(Case.customer_id == customer_id)
        .order_by(Case.id)
    ).all()
    messages_total = session.scalar(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.customer_id == customer_id)
    )
    messages_query = (
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.customer_id == customer_id)
    )
    if messages_limit is not None and messages_limit > 0:
        messages = list(
            session.scalars(
                messages_query.order_by(Message.created_at.desc(), Message.id.desc())
                .limit(messages_limit)
            )
        )
        messages.reverse()
    else:
        messages = list(
            session.scalars(messages_query.order_by(Message.created_at, Message.id))
        )
    appointments = session.scalars(
        select(Appointment)
        .where(Appointment.customer_id == customer_id)
        .order_by(Appointment.starts_at, Appointment.id)
    ).all()
    return {
        "conversations": [
            {
                "id": c.id,
                "state": c.state.value,
                "summary": c.summary,
                "created_at": c.created_at,
                "closed_at": c.closed_at,
            }
            for c in conversations
        ],
        "cases": [
            {
                "id": ca.id,
                "conversation_id": ca.conversation_id,
                "customer_id": ca.customer_id,
                "created_at": ca.created_at,
                "service": ca.service,
                "priority": ca.priority,
                "status": ca.status,
                "summary": ca.summary,
                "emergency": ca.emergency,
                "responsible_id": ca.responsible_id,
                "escalated_at": ca.escalated_at,
                "closed_at": ca.closed_at,
                "acknowledged_at": ca.acknowledged_at,
                "ack_by": ca.ack_by,
                "is_open": case_is_open(ca),
            }
            for ca in cases
        ],
        "messages": [
            {
                "id": m.id,
                "conversation_id": m.conversation_id,
                "direction": m.direction.value,
                "msg_type": m.msg_type.value,
                "text": m.text,
                "media_url": m.media_url,
                "created_at": m.created_at,
            }
            for m in messages
        ],
        "messages_total": messages_total,
        "appointments": [
            {
                "id": a.id,
                "case_id": a.case_id,
                "service": a.service,
                "technician_id": a.technician_id,
                "local_start": a.local_start,
                "timezone": a.timezone,
                "starts_at": a.starts_at,
                "ends_at": a.ends_at,
                "status": a.status.value,
                "calendar_status": a.calendar_sync.status if a.calendar_sync else None,
                "calendar_error": a.calendar_sync.error if a.calendar_sync else None,
            }
            for a in appointments
        ],
    }


# ---------------------------------------------------------------------------
# CR-6 — captured data + consent on the ficha
# ---------------------------------------------------------------------------


def update_captured_data(
    session: Session,
    customer: Customer,
    *,
    name: str | None = None,
    email: str | None = None,
    comuna: str | None = None,
    address: str | None = None,
) -> Customer:
    """Persist conversation-captured personal/contact data (CR-6, CM-2)."""
    if name is not None:
        customer.name = name
    if email is not None:
        customer.email = email
    if comuna is not None:
        customer.comuna = comuna
    if address is not None:
        customer.address = address
    return customer


def record_consent(
    session: Session,
    customer: Customer,
    *,
    consent: bool,
    consent_at: datetime | None = None,
) -> Customer:
    """Record consent acceptance/withdrawal for data storage + service use."""
    customer.consent_status = consent
    if consent:
        customer.consent_at = consent_at or datetime.now(timezone.utc)
    else:
        customer.consent_at = None
    return customer
