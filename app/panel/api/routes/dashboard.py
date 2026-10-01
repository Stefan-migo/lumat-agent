"""Panel JSON API dashboard (B2/T2.1; PDW-API, PDW-AUTH-1, D4).

GET /panel/api/kpis -> the same `compute_kpis` dict the Jinja dashboard
renders (contacts / motivos / derived / visit_requests / window_days /
window_start), so the SPA mirrors the template view exactly. No new
business logic: the route reads the configured `kpi.window_days` setting
and delegates to the shared `compute_kpis` function (design: routes/*
--delegates_to--> services/*; dashboard.py --computes--> compute_kpis()).

Auth is the JSON-401 dependency (D4): unauthenticated calls get 401
{"detail":"unauthorized"}, never a 302 to the HTML login page (PDW-AUTH-1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_dashboard_user
from app.panel.deps import get_db
from app.services.dashboard import compute_kpis, today_projection
from app.services.settings import get_setting

router = APIRouter(tags=["panel-api-dashboard"])


@router.get("/kpis")
def kpis(
    window_days: int | None = Query(default=None, ge=1, le=31),
    session: Session = Depends(get_db),
    current: User = Depends(require_dashboard_user),
) -> dict:
    """Dashboard KPI counts over the requested or configured window (AP-8)."""
    configured_window_days = int(get_setting(session, "kpi.window_days", default=7))
    return compute_kpis(session, window_days if window_days is not None else configured_window_days)


@router.get("/dashboard/today")
def today(
    timezone: str,
    session: Session = Depends(get_db),
    current: User = Depends(require_dashboard_user),
) -> dict:
    return today_projection(session, timezone)
