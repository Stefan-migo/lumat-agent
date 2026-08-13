"""Panel router aggregator (design D7: app/panel/routes).

All panel routes live under the /panel prefix and are enforced server-side by
`deps.require_user` / `deps.require_admin` (AP-2). Mounted in app/main.py
next to the webhook router.
"""

from fastapi import APIRouter

from app.panel.routes import auth, dashboard

panel_router = APIRouter(prefix="/panel", tags=["panel"])

panel_router.include_router(auth.router)
panel_router.include_router(dashboard.router)
