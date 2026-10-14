from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import AppointmentStatus, Case, Customer, User
from app.panel.api.deps import require_tecnico
from app.panel.api.serializers import (
    to_technician_appointment_detail_dict,
    to_technician_appointment_dict,
)
from app.panel.deps import get_db
from app.services import scheduling

router = APIRouter(tags=["panel-api-technician"])


class TechnicianCloseBody(BaseModel):
    outcome: Literal["completed", "no_show"]
    reason: str | None = None


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
    """Read one of the technician's own visits (S2). A missing id and another
    technician's visit are indistinguishable: both are 404, so the route cannot
    be used to probe which appointment ids exist."""
    appointment = session.get(scheduling.Appointment, appointment_id)
    if appointment is None or appointment.technician_id != current.id:
        raise HTTPException(status_code=404, detail="appointment not found")
    customer = session.get(Customer, appointment.customer_id)
    case = session.get(Case, appointment.case_id)
    return to_technician_appointment_detail_dict(appointment, customer=customer, case=case)


@router.post("/technician/appointments/{appointment_id}/close")
def technician_close_appointment(
    appointment_id: int, body: TechnicianCloseBody, session: Session = Depends(get_db), current: User = Depends(require_tecnico)
) -> dict:
    """Close one of the technician's own visits as `completed` or `no_show` (S4).

    Same 404 for a missing id and another technician's visit, so the route cannot
    probe ids. `scheduling.close` records both the appointment history and the
    append-only audit entry; the response carries no payload, so no history or
    conversation data can leak back to the technician."""
    appointment = session.get(scheduling.Appointment, appointment_id)
    if appointment is None or appointment.technician_id != current.id:
        raise HTTPException(status_code=404, detail="appointment not found")
    try:
        scheduling.close(session, appointment, outcome=AppointmentStatus(body.outcome), actor=current.username, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "invalid_lifecycle", "message": str(exc)}) from exc
    session.commit()
    return {"ok": True}
