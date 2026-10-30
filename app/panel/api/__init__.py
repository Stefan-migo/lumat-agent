"""Panel JSON API package (design D4; PDW-API, PDW-AUTH).

Additive JSON layer under `/panel/api/*`, coexisting with the Jinja2 routes
(which stay as live fallback). Owns its JSON-401 dependencies in `deps.py`
(D4 — the SPA must never follow a 302 to the HTML login page, PDW-AUTH-1).
No CORS (D1): the SPA and the API share an origin in dev (Vite proxy) and
prod (nginx), so the same-origin session cookie is all the transport needs.

Router assembly is deferred on purpose. Importing any submodule of this package
first executes this file, and building the router imports every route module,
which import services back. That made `import app.services.<anything>` fail
whenever the service imported a panel serializer at module level — twice in
production (`app.services.conversations`, `app.services.dashboard`). Keeping
this module's import surface free of routes ends the class: a serializer import
no longer drags the whole router graph behind it.
"""

from fastapi import APIRouter

_API_ROUTER: APIRouter | None = None


def build_api_router() -> APIRouter:
    """Assemble the panel JSON router, importing each domain sub-router here."""
    from app.panel.api.routes import (
        auth,
        appointments,
        calendar_templates,
        notifications,
        cases,
        clients,
        conversations,
        dashboard,
        analytics,
        kb,
        settings,
        chat,
        advanced_dashboard,
        automation_rules,
        automation_recipes,
        technician,
        users,
        projects,
        project_files,
        skills,
        assistant_memories,
    )

    router = APIRouter(prefix="/api")
    # Per-domain sub-routers are included as they land, batch by batch.
    router.include_router(auth.router)
    router.include_router(appointments.router)
    router.include_router(calendar_templates.router)
    router.include_router(notifications.router)
    router.include_router(dashboard.router)
    router.include_router(clients.router)
    router.include_router(conversations.router)
    router.include_router(cases.router)
    router.include_router(kb.router)
    router.include_router(settings.router)
    router.include_router(analytics.router)
    router.include_router(chat.router)
    router.include_router(advanced_dashboard.router)
    router.include_router(automation_rules.router)
    router.include_router(automation_recipes.router)
    router.include_router(technician.router)
    router.include_router(users.router)
    router.include_router(projects.router)
    router.include_router(project_files.router)
    router.include_router(skills.router)
    router.include_router(assistant_memories.router)
    return router


def __getattr__(name: str) -> APIRouter:
    """Build `api_router` on first access, so a submodule import never triggers it."""
    if name == "api_router":
        global _API_ROUTER
        if _API_ROUTER is None:
            _API_ROUTER = build_api_router()
        return _API_ROUTER
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
