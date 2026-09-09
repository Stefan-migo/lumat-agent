"""Privacy-bounded technician panel API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_tecnico
from app.panel.api.serializers import to_technician_appointment_dict
from app.panel.deps import get_db
from app.services import scheduling

router = APIRouter(tags=["panel-api-technician"])


@router.get("/technician/agenda")
def technician_agenda(
    session: Session = Depends(get_db), current: User = Depends(require_tecnico)
) -> dict:
    rows = scheduling.list_for_technician(session, current.id)
    return {
        "appointments": [
            to_technician_appointment_dict(appointment, customer=customer, case=case)
            for appointment, customer, case in rows
        ]
    }
