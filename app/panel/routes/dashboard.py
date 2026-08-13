"""Panel home — dashboard KPIs (T5.5; AP-8).

GET /panel/ renders contacts / motivos / derived cases / visit requests as
SQL COUNT aggregates over the configured time window (settings
`kpi.window_days`, default 7). No chart library (AP-8: "simple
counters/time-window aggregates"): the KPI grid is pure Jinja2 numbers.

- contacts: distinct conversations with an inbound message in the window
- motivos: cases grouped by service, created in the window
- derivados: cases escalated in the window (escalated_at)
- solicitudes de visita: cases with service 'visita', created in the window
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from app.models import Case, Message, MessageDirection
from app.panel.deps import get_db, require_user, templates
from app.services.settings import get_setting

router = APIRouter(tags=["panel-dashboard"])


def compute_kpis(session, window_days: int) -> dict:
    """AP-8: the four KPI values as SQL counts over the window."""
    start = datetime.now(timezone.utc) - timedelta(days=window_days)

    contacts = session.scalar(
        select(func.count(func.distinct(Message.conversation_id))).where(
            Message.direction == MessageDirection.INBOUND,
            Message.created_at >= start,
        )
    )
    motivos = session.execute(
        select(Case.service, func.count().label("n"))
        .where(Case.created_at >= start)
        .group_by(Case.service)
        .order_by(func.count().desc(), Case.service)
    ).all()
    derived = session.scalar(
        select(func.count()).select_from(Case).where(Case.escalated_at >= start)
    )
    visits = session.scalar(
        select(func.count()).select_from(Case).where(
            Case.service == "visita", Case.created_at >= start
        )
    )
    return {
        "contacts": contacts or 0,
        "motivos": [(service, count) for service, count in motivos],
        "derived": derived or 0,
        "visit_requests": visits or 0,
        "window_days": window_days,
        "window_start": start.date().isoformat(),
    }


@router.get("/")
def panel_home(
    request: Request,
    session=Depends(get_db),
    current=Depends(require_user),
):
    window_days = int(get_setting(session, "kpi.window_days", default=7))
    kpis = compute_kpis(session, window_days)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"current_user": current, "kpis": kpis},
    )
