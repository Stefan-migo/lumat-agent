"""Panel JSON API package (design D4; PDW-API, PDW-AUTH).

Additive JSON layer under `/panel/api/*`, coexisting with the Jinja2 routes
(which stay as live fallback). Owns its JSON-401 dependencies in `deps.py`
(D4 — the SPA must never follow a 302 to the HTML login page, PDW-AUTH-1).
No CORS (D1): the SPA and the API share an origin in dev (Vite proxy) and
prod (nginx), so the same-origin session cookie is all the transport needs.
"""

from fastapi import APIRouter

from app.panel.api.routes import (
    auth,
    appointments,
    calendar_templates,
    notifications,
    cases,
    clients,
    conversations,
    dashboard,
    kb,
    settings,
    chat,
    advanced_dashboard,
    automation_rules,
)

# Per-domain sub-routers are included as they land, batch by batch.

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(appointments.router)
api_router.include_router(calendar_templates.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(clients.router)
api_router.include_router(conversations.router)
api_router.include_router(cases.router)
api_router.include_router(kb.router)
api_router.include_router(settings.router)
api_router.include_router(chat.router)
api_router.include_router(advanced_dashboard.router)
api_router.include_router(automation_rules.router)
