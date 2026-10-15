from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import AppointmentStatus, Case, Customer, TechnicianVisitState, User
from app.panel.api.deps import require_tecnico
from app.panel.api.serializers import (
    to_technician_appointment_detail_dict,
    to_technician_appointment_dict,
)
from app.panel.deps import get_db
from app.services import scheduling, visit_actions, visit_state

router = APIRouter(tags=["panel-api-technician"])


class TechnicianCloseBody(BaseModel):
    outcome: Literal["completed", "no_show"]
    reason: str | None = None


def _owned_appointment(
    session: Session, appointment_id: int, current: User, *, for_update: bool = False
) -> scheduling.Appointment:
    """The technician's own appointment, or 404.

    A missing id and another technician's visit are indistinguishable: both are
    404, so the routes cannot be used to probe which appointment ids exist.
    `for_update` locks the row for the field quick actions, so two rapid clicks
    serialize on the cooldown read (S7)."""
    appointment = session.get(
        scheduling.Appointment, appointment_id, with_for_update=for_update
    )
    if appointment is None or appointment.technician_id != current.id:
        raise HTTPException(status_code=404, detail="appointment not found")
    return appointment


def _quick_action(
    session: Session, appointment_id: int, current: User, state: TechnicianVisitState
) -> dict:
    """Record a field quick action and notify the customer (S5-S8).

    The response carries the new state and when a resend becomes available, and
    never the customer phone (S8) — the number is resolved server-side."""
    appointment = _owned_appointment(session, appointment_id, current, for_update=True)
    try:
        visit_actions.notify_customer(
            session, appointment, state=state, actor=current.username
        )
    except visit_actions.ResendCooldown as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "resend_cooldown",
                "message": str(exc),
                "retry_after_seconds": exc.retry_after_seconds,
            },
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except visit_state.VisitStateUnavailable as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "visit_state_unavailable", "message": str(exc)},
        ) from exc
    except visit_actions.VisitNotificationFailed as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "notification_failed", "message": str(exc)},
        ) from exc
    received_at = appointment.technician_state_at or datetime.now(timezone.utc)
    body = {
        "ok": True,
        "technician_state": appointment.technician_state.value,
        "resend_available_at": (received_at + visit_actions.RESEND_COOLDOWN).isoformat(),
    }
    session.commit()
    return body


@router.get("/technician/agenda")
def technician_agenda(
    session: Session = Depends(get_db), current: User = Depends(require_tecnico)
) -> dict:
    rows = scheduling.list_for_technician(session, current.id)
    return {"appointments": [to_technician_appointment_dict(appointment, customer=customer, case=case) for appointment, customer, case in rows]}


@router.get("/technician/appointments/{appointment_id}")
def technician_appointment(
    appointment_id: int, session: Session = Depends(get_db), current: User = Depends(require_tecnico)
) -> dict:
    """Read one of the technician's own visits (S2), with the field state and the
    per-action resend cooldown (S5/S7)."""
    appointment = _owned_appointment(session, appointment_id, current)
    customer = session.get(Customer, appointment.customer_id)
    case = session.get(Case, appointment.case_id)
    now = datetime.now(timezone.utc)
    resend_available_at = {
        state: visit_actions.resend_available_at(session, appointment.id, state, now=now)
        for state in TechnicianVisitState
    }
    return to_technician_appointment_detail_dict(
        appointment, customer=customer, case=case, resend_available_at=resend_available_at
    )


@router.post("/technician/appointments/{appointment_id}/close")
def technician_close_appointment(
    appointment_id: int, body: TechnicianCloseBody, session: Session = Depends(get_db), current: User = Depends(require_tecnico)
) -> dict:
    """Close one of the technician's own visits as `completed` or `no_show` (S4).

    `scheduling.close` records both the appointment history and the append-only
    audit entry; the response carries no payload, so no history or conversation
    data can leak back to the technician."""
    appointment = _owned_appointment(session, appointment_id, current)
    try:
        scheduling.close(session, appointment, outcome=AppointmentStatus(body.outcome), actor=current.username, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "invalid_lifecycle", "message": str(exc)}) from exc
    session.commit()
    return {"ok": True}


@router.post("/technician/appointments/{appointment_id}/en_route")
def technician_en_route(
    appointment_id: int, session: Session = Depends(get_db), current: User = Depends(require_tecnico)
) -> dict:
    """Tell the customer the technician is on the way (S5/S7/S8)."""
    return _quick_action(session, appointment_id, current, TechnicianVisitState.EN_ROUTE)


@router.post("/technician/appointments/{appointment_id}/arrived")
def technician_arrived(
    appointment_id: int, session: Session = Depends(get_db), current: User = Depends(require_tecnico)
) -> dict:
    """Tell the customer the technician arrived / is outside (S5/S7/S8)."""
    return _quick_action(session, appointment_id, current, TechnicianVisitState.ARRIVED)
