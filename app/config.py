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
    # Chat is multi-provider (D3 change): DeepSeek (default) or OpenRouter,
    # both OpenAI chat-completions-compatible — only base_url + model + key
    # change. Both keys are optional at the Settings level; the ACTIVE
    # provider's key is required and enforced in llm.openai_client()
    # (fail-fast at use time). CHAT_MODEL is provider-appropriate by default.
    chat_provider: str = "deepseek"  # "deepseek" | "openrouter"
    deepseek_api_key: str | None = None
    openrouter_api_key: str | None = None
    chat_model: str = "deepseek-chat"
    assistant_chat_provider: str = "openrouter"
    assistant_chat_model: str = "google/gemini-2.5-flash"

    # Local embeddings (fastembed, ONNX Runtime — no API key, no token
    # billing). Multilingual model, 384 dims (db/migrations/008_local_embeddings.sql).
    embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embed_dims: int = 384

    meta_access_token: str  # Meta Cloud API permanent token
    meta_phone_number_id: str  # WhatsApp Business Phone Number ID

    app_version: str = "0.1.0"

    # Media downloads (design Webhook Pipeline: media -> media/ volume)
    media_dir: str = "media"

    # Panel (design D7; AP-1): secret used to SIGN the Starlette session
    # cookie. Required at boot — an unsigned session cookie would be
    # forgeable. SH-2: env-only, never in the repo.
    panel_session_secret: str

    # Memoria (design "fines de detalle fino"; S3 close observations).
    # Product values pending sanity before merge (open design question), so
    # they ship as env-configurable constants with the design defaults.
    obs_recur_window_days: int = 30   # recurrencia window (OBS_RECUR_WINDOW)
    obs_recur_count: int = 2          # closes per topic_key to raise recurrencia
    obs_no_reply_hours: int = 24      # inbound w/o bot reply -> sin_respuesta


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance (cleared in tests via cache_clear)."""
    return Settings()
