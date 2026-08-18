"""Panel JSON API package (design D4; PDW-API, PDW-AUTH).

Additive JSON layer under `/panel/api/*`, coexisting with the Jinja2 routes
(which stay as live fallback). Owns its JSON-401 dependencies in `deps.py`
(D4 — the SPA must never follow a 302 to the HTML login page, PDW-AUTH-1).
No CORS (D1): the SPA and the API share an origin in dev (Vite proxy) and
prod (nginx), so the same-origin session cookie is all the transport needs.
"""

from fastapi import APIRouter

from app.panel.api.routes import auth

# Per-domain sub-routers (dashboard, clients, conversations, cases, kb,
# settings) are included as they land, batch by batch.

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
