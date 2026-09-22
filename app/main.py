"""LumatAgent API application factory (design: app/main.py).

`app = create_app()` at module level so `uvicorn app.main:app` boots directly.
Settings are validated at import time: missing required env vars fail fast with
a clear error instead of starting a half-configured server.

Startup (lifespan) runs the crash-recovery sweeps: webhook messages persisted as
`received` before a crash are reprocessed (design Webhook Pipeline — crash
recovery via FOR UPDATE SKIP LOCKED), and panel assistant runs orphaned by the
same crash are failed so the operator gets their Retry action back.
"""

import logging
import threading
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.db import SessionLocal
from app.panel.routes import panel_router
from app.services.agent_chat import reap_orphaned_runs
from app.webhook.ingest import reset_stale_processing, sweep_received
from app.webhook.router import router as webhook_router
from app.ops.sweep import run as run_notification_sweep

logger = logging.getLogger(__name__)


def _prewarm_embedder() -> None:
    """Load the local embedding model before anyone needs it.

    Runs off the boot path on purpose: with a cold fastembed cache this call
    downloads ~240MB, and boot must not wait minutes for it. Failure is logged
    and swallowed — an unavailable model degrades the turns that need it, it
    must not stop the API from serving.
    """
    try:
        from app.services import kb

        kb.get_embedder()
        logger.info("embedder prewarm complete")
    except Exception:
        logger.exception("embedder prewarm failed")


def start_embedder_prewarm() -> threading.Thread | None:
    """Start the embedder prewarm on a daemon thread; None when disabled.

    Daemon so a download in flight never holds up shutdown.
    """
    if not get_settings().embed_prewarm:
        return None
    thread = threading.Thread(target=_prewarm_embedder, name="embedder-prewarm", daemon=True)
    thread.start()
    return thread


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup sweeps: recover messages stuck in `received`, fail orphaned runs.

    Rows left `processing` by a hard crash are reset to `received` first
    (single worker: nothing can be actively processing at boot) — the same
    reasoning that lets the assistant-run sweep treat a `running` live state as
    proof of orphanhood.

    They are independent recoveries, so each gets its own `try`: one failing
    (the notification sweep reaches the database and outbound channels) must not
    skip the rest, and the log names the sweep that broke.
    """
    for name, sweep in (
        ("reset_stale_processing", reset_stale_processing),
        ("sweep_received", sweep_received),
        ("notification_sweep", run_notification_sweep),
        ("reap_orphaned_runs", partial(reap_orphaned_runs, SessionLocal)),
    ):
        try:
            sweep()
        except Exception:
            logger.exception("startup sweep %s failed", name)
    # Prewarm off the boot path: a cold download can take minutes, so it must
    # not delay or replace the recovery sweeps above.
    start_embedder_prewarm()
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
        return {"status": "ok", "version": settings.app_version, "commit": settings.git_sha}

    app.include_router(webhook_router)
    app.include_router(panel_router)
    return app


app = create_app()
