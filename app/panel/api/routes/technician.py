from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import Case, Customer, User
from app.panel.api.deps import require_tecnico
from app.panel.api.serializers import (
    to_technician_appointment_detail_dict,
    to_technician_appointment_dict,
)
from app.panel.deps import get_db
from app.services import scheduling

router = APIRouter(tags=["panel-api-technician"])


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
