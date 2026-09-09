"""Panel JSON API cases (B3/T3.2; PDW-API, PDW-API-3, D4, D8).

Thin JSON wrappers over `app/services/cases.py` + `app/services/notify.py`:

- GET  /cases            -> {"cases": [...], "users": [{id,username}]}
                           open cases (HH-4, escalated first) with the
                           customer embedded per case (D8)
- POST /cases/{id}/update -> {"ok", "case"} (AP-5 status + nullable
                           responsible, audited with the actor)
- POST /cases/{id}/ack   -> {"ok", "case"} (EM-4 emergency ack, audited)

No new business logic; the mutation audits are the existing service calls
(SH-5). The /update route deliberately passes the `responsible_id` "keep vs
clear" sentinel through: omitting the field keeps the assignment, `null`
explicitly clears it (service `_UNSET` contract). Errors are JSON
{"detail": ...} (PDW-API-3): 401 from the JSON-401 dep (D4, PDW-AUTH-1), 404
for a missing case. No redirects, no CORS (D1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_operator_json
from app.panel.api.serializers import to_case_dict, to_customer_dict, to_user_dict
from app.panel.deps import get_db
from app.services import cases as cases_service
from app.services.notify import acknowledge_case

router = APIRouter(tags=["panel-api-cases"])

# Reuse the service's keep-vs-clear sentinel (app/services/cases.py): the body
# field defaults to it so "omitted" keeps the current assignment, while an
# explicit `null` clears it. Must be the SAME object instance the service
# checks with `is`, not a local copy.
_UNSET = cases_service._UNSET


class CaseUpdateBody(BaseModel):
    status: str | None = None
    responsible_id: int | None | object = _UNSET


def _case_or_404(session: Session, case_id: int) -> cases_service.Case:
    case = session.get(cases_service.Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")
    return case


@router.get("/cases")
def cases_list(
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """Open cases (escalated first) with customer embedded + users (D8)."""
    rows = cases_service.list_open_cases(session)  # list[tuple[Case, Customer]]
    users = session.scalars(select(User).order_by(User.username)).all()
    return {
        "cases": [
            {**to_case_dict(case), "customer": to_customer_dict(customer)}
            for case, customer in rows
        ],
        "users": [to_user_dict(u) for u in users],
    }


@router.post("/cases/{case_id}/update")
def case_update(
    case_id: int,
    body: CaseUpdateBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """AP-5: change case status and/or responsible; null clears assignment."""
    case = _case_or_404(session, case_id)
    cases_service.update_case(
        session,
        case,
        status=body.status,
        responsible_id=body.responsible_id,
        actor=current.username,
    )
    session.commit()
    return {"ok": True, "case": to_case_dict(case)}


@router.post("/cases/{case_id}/ack")
def case_ack(
    case_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """EM-4: acknowledge an emergency case from the panel (audited)."""
    case = _case_or_404(session, case_id)
    acknowledge_case(session, case, actor=current.username)
    session.commit()
    return {"ok": True, "case": to_case_dict(case)}
