"""Cases panel view (T5.3; HH-4, AP-5, EM-4 ack).

GET  /panel/cases                  -> pending/escalated list (HH-4)
POST /panel/cases/{id}/update      -> state change + responsible assign (AP-5, audited)
POST /panel/cases/{id}/ack         -> emergency ack button (EM-4, audited)

The ack button writes the same columns as the reply-keyword ack (T4.3:
acknowledged_at/ack_by + `case.acknowledged` audit) — no new mechanism.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.models import User
from app.panel.deps import flash, get_db, require_user, templates
from app.services import cases as cases_service
from app.services.notify import acknowledge_case

router = APIRouter(tags=["panel-cases"])


def _case_or_404(session, case_id: int):
    case = session.get(cases_service.Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")
    return case


@router.get("/cases")
def cases_list(
    request: Request,
    session=Depends(get_db),
    current=Depends(require_user),
):
    rows = cases_service.list_open_cases(session)
    users = list(session.scalars(select(User).order_by(User.username)))
    return templates.TemplateResponse(
        request,
        "cases/list.html",
        {
            "current_user": current,
            "cases": rows,  # (Case, Customer) tuples
            "users": users,
        },
    )


@router.post("/cases/{case_id}/update")
def case_update(
    request: Request,
    case_id: int,
    status: str = Form(...),
    responsible_id: str = Form(""),
    session=Depends(get_db),
    current=Depends(require_user),
):
    case = _case_or_404(session, case_id)
    responsible = int(responsible_id) if responsible_id.strip() else None
    cases_service.update_case(
        session,
        case,
        status=status,
        responsible_id=responsible,
        actor=current.username,
    )
    flash(request, f"Case #{case_id} updated")
    return RedirectResponse("/panel/cases", status_code=303)


@router.post("/cases/{case_id}/ack")
def case_ack(
    request: Request,
    case_id: int,
    session=Depends(get_db),
    current=Depends(require_user),
):
    case = _case_or_404(session, case_id)
    if acknowledge_case(session, case, actor=current.username):
        flash(request, f"Emergency case #{case_id} acknowledged")
    return RedirectResponse("/panel/cases", status_code=303)
