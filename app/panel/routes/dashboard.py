"""Panel home route (GET /panel/) — placeholder until the real dashboard
lands in T5.5 (KPIs = SQL counts over the settings time window, AP-8).

The route exists from T5.1 so the panel has a protected landing page and the
`require_user` dependency is exercised end-to-end by the auth tests.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.panel.deps import require_user, templates

router = APIRouter(tags=["panel-dashboard"])


@router.get("/")
def panel_home(request: Request, current=Depends(require_user)):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"current_user": current, "kpis": None},
    )
