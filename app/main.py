"""LumatAgent API application factory (design: app/main.py).

`app = create_app()` at module level so `uvicorn app.main:app` boots directly.
Settings are validated at import time: missing required env vars fail fast with
a clear error instead of starting a half-configured server.

Startup (lifespan) runs the webhook recovery sweep: messages persisted as
`received` before a crash are reprocessed (design Webhook Pipeline — crash
recovery via FOR UPDATE SKIP LOCKED).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.panel.routes import panel_router
from app.webhook.ingest import reset_stale_processing, sweep_received
from app.webhook.router import router as webhook_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup sweep: reprocess messages stuck in `received` (crash recovery).

    Rows left `processing` by a hard crash are reset to `received` first
    (single worker: nothing can be actively processing at boot).
    """
    try:
        reset_stale_processing()
        sweep_received()
    except Exception:
        logger.exception("startup webhook sweep failed")
    yield


def create_app() -> FastAPI:
    settings = get_settings()  # raises pydantic ValidationError when env is missing

    app = FastAPI(title="LumatAgent API", version=settings.app_version, lifespan=lifespan)

    # AP-1: signed-cookie session for the panel (design D7). 12 h lifetime;
    # the payload is signed with panel_session_secret (SH-2: env-only).
    # same_site=lax keeps the cookie off cross-site requests; https_only stays
    # False because nginx terminates TLS in front of the API container.
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.panel_session_secret,
        session_cookie="session",
        max_age=12 * 60 * 60,
        same_site="lax",
        https_only=False,
    )

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        return {"status": "ok", "version": settings.app_version}

    app.include_router(webhook_router)
    app.include_router(panel_router)
    return app


app = create_app()
