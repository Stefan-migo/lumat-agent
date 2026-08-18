"""Panel JSON API clients (B2/T2.2; PDW-API, PDW-API-3, D4).

Thin JSON wrappers over `app/services/customers.py` — no new business
logic, audits preserved (SH-5):

- GET  /clients?q=            -> {"clients": [...], "query": q} (search,
                                 cap 100)
- GET  /clients/{id}          -> {"customer", "history", "notes", "states"}
- POST /clients/{id}/state    -> {"ok", "state"} (CR-3 transition validated,
                                 audited with the actor)
- POST /clients/{id}/notes    -> {"ok", "note"} (empty note rejected 400,
                                 audited)

All errors are JSON {"detail": ...} (PDW-API-3): 401 from the JSON-401 dep
(D4, PDW-AUTH-1), 404 for a missing customer, 400 for an invalid CR-3
transition or an empty note. No redirects, no CORS (D1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import CustomerState, User
from app.panel.api.deps import require_user_json
from app.panel.api.serializers import to_customer_dict, to_note_dict
from app.panel.deps import get_db
from app.services import customers
from app.services.audit import record_audit

router = APIRouter(tags=["panel-api-clients"])


class StateBody(BaseModel):
    state: str


class NoteBody(BaseModel):
    note: str


def _customer_or_404(session: Session, customer_id: int) -> customers.Customer:
    customer = session.get(customers.Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return customer


@router.get("/clients")
def clients_list(
    q: str | None = None,
    session: Session = Depends(get_db),
    current: User = Depends(require_user_json),
) -> dict:
    """Search/list customers (AP-3), wrapped and capped at 100."""
    found = customers.search_customers(session, q, limit=100)
    return {"clients": [to_customer_dict(c) for c in found], "query": q or ""}


@router.get("/clients/{customer_id}")
def client_ficha(
    customer_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_user_json),
) -> dict:
    """Full ficha: customer + history (CR-5) + notes (CR-4) + lifecycle."""
    customer = _customer_or_404(session, customer_id)
    return {
        "customer": to_customer_dict(customer),
        "history": customers.customer_history(session, customer_id),
        "notes": [
            to_note_dict(n) for n in customers.list_notes(session, customer_id)
        ],
        "states": [s.value for s in CustomerState],
    }


@router.post("/clients/{customer_id}/state")
def client_state_change(
    customer_id: int,
    body: StateBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_user_json),
) -> dict:
    """CR-3 lifecycle transition, validated and audited with the actor."""
    customer = _customer_or_404(session, customer_id)
    try:
        customers.set_customer_state(
            session, customer, CustomerState(body.state), actor=current.username
        )
    except (customers.InvalidStateTransition, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    session.commit()
    return {"ok": True, "state": customer.state.value}


@router.post("/clients/{customer_id}/notes")
def client_add_note(
    customer_id: int,
    body: NoteBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_user_json),
) -> dict:
    """CR-4 internal staff note; audited with the actor (SH-5)."""
    _customer_or_404(session, customer_id)
    note = body.note.strip()
    if not note:
        raise HTTPException(status_code=400, detail="note cannot be empty")
    entry = customers.add_note(session, customer_id, note, actor=current.username)
    record_audit(
        session,
        actor=current.username,
        action="customer.note_added",
        entity="customer",
        entity_id=str(customer_id),
        after={"note": note},
    )
    session.commit()
    return {"ok": True, "note": to_note_dict(entry)}
