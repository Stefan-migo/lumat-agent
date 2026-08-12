"""LumatAgent API application factory (design: app/main.py).

`app = create_app()` at module level so `uvicorn app.main:app` boots directly.
Settings are validated at import time: missing required env vars fail fast with
a clear error instead of starting a half-configured server.
"""

from fastapi import FastAPI

from app.config import get_settings
from app.webhook.router import router as webhook_router


def create_app() -> FastAPI:
    settings = get_settings()  # raises pydantic ValidationError when env is missing

    app = FastAPI(title="LumatAgent API", version=settings.app_version)

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        return {"status": "ok", "version": settings.app_version}

    app.include_router(webhook_router)
    return app


app = create_app()
