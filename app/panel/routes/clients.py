"""Clients panel views (T5.2; AP-3, CR-3, CR-4, CR-5).

GET  /panel/clients?q=            -> list/search (name, phone — AP-3)
GET  /panel/clients/{id}          -> ficha: history (CR-5) + notes (CR-4)
POST /panel/clients/{id}/state    -> lifecycle state change (CR-3, audited)
POST /panel/clients/{id}/notes    -> add internal staff note (CR-4)

All routes require login (require_user); state changes and notes are audited
(CR-3/SH-5) and invalid CR-3 transitions are rejected with a flash error.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.models import CustomerState
from app.panel.deps import flash, get_db, pop_flash, require_user, templates
from app.services import customers

router = APIRouter(tags=["panel-clients"])


def _customer_or_404(session, customer_id: int):
    customer = session.get(customers.Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return customer


@router.get("/clients")
def clients_list(
    request: Request,
    q: str | None = None,
    session=Depends(get_db),
    current=Depends(require_user),
):
    found = customers.search_customers(session, q)
    return templates.TemplateResponse(
        request,
        "clients/list.html",
        {"current_user": current, "customers": found, "query": q or ""},
    )


@router.get("/clients/{customer_id}")
def client_ficha(
    request: Request,
    customer_id: int,
    session=Depends(get_db),
    current=Depends(require_user),
):
    customer = _customer_or_404(session, customer_id)
    return templates.TemplateResponse(
        request,
        "clients/ficha.html",
        {
            "current_user": current,
            "customer": customer,
            "history": customers.customer_history(session, customer_id),
            "notes": customers.list_notes(session, customer_id),
            "states": [s.value for s in CustomerState],
            "flash": pop_flash(request),
        },
    )


@router.post("/clients/{customer_id}/state")
def client_state_change(
    request: Request,
    customer_id: int,
    state: str = Form(...),
    session=Depends(get_db),
    current=Depends(require_user),
):
    customer = _customer_or_404(session, customer_id)
    try:
        customers.set_customer_state(
            session, customer, CustomerState(state), actor=current.username
        )
    except (customers.InvalidStateTransition, ValueError) as exc:
        flash(request, f"Invalid state change: {exc}")
    else:
        flash(request, f"State changed to {customer.state.value}")
    return RedirectResponse(f"/panel/clients/{customer_id}", status_code=303)


@router.post("/clients/{customer_id}/notes")
def client_add_note(
    request: Request,
    customer_id: int,
    note: str = Form(...),
    session=Depends(get_db),
    current=Depends(require_user),
):
    _customer_or_404(session, customer_id)
    note = note.strip()
    if note:
        customers.add_note(session, customer_id, note, actor=current.username)
        flash(request, "Note added")
    return RedirectResponse(f"/panel/clients/{customer_id}", status_code=303)
