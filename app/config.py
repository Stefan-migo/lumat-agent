"""Application configuration.

Settings are read from environment variables ONLY (no .env file loading):
all secrets live in server environment variables (design SH-2). The committed
`infra/.env.example` (T1.3) documents the required names for local/Compose use.

Any missing required variable raises a clear pydantic ValidationError at boot,
which is the intended "missing env -> clear boot error" behavior (T0.2).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-only application settings (design: app/config.py, D3, SH-2)."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # WhatsApp webhook (specs WH-1, WH-2)
    app_secret: str  # HMAC secret used to verify X-Hub-Signature-256
    verify_token: str  # hub.verify_token for the GET verify handshake

    # Data layer (used from T1.x onwards; required now so boot is fail-fast)
    database_url: str  # SQLAlchemy URL for PostgreSQL + pgvector

    # External providers (design D3)
    openai_api_key: str  # chat gpt-4o-mini + embeddings text-embedding-3-small
    meta_access_token: str  # Meta Cloud API permanent token
    meta_phone_number_id: str  # WhatsApp Business Phone Number ID

    app_version: str = "0.1.0"

    # Media downloads (design Webhook Pipeline: media -> media/ volume)
    media_dir: str = "media"

    # Panel (design D7; AP-1): secret used to SIGN the Starlette session
    # cookie. Required at boot — an unsigned session cookie would be
    # forgeable. SH-2: env-only, never in the repo.
    panel_session_secret: str


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance (cleared in tests via cache_clear)."""
    return Settings()
