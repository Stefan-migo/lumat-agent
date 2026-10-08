"""Application configuration.

Settings are read from environment variables ONLY (no .env file loading):
all secrets live in server environment variables (design SH-2). The committed
`infra/.env.example` (T1.3) documents the required names for local/Compose use.

Any missing required variable raises a clear pydantic ValidationError at boot,
which is the intended "missing env -> clear boot error" behavior (T0.2).
"""

from functools import lru_cache
from pathlib import Path
import tomllib

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PYPROJECT_PATH = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _read_app_version() -> str:
    # Keep the deployed version tied to the package metadata used for releases.
    with PYPROJECT_PATH.open("rb") as pyproject:
        return tomllib.load(pyproject)["project"]["version"]


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
    brave_search_api_key: str | None = None
    assistant_attachment_max_bytes: int = 5 * 1024 * 1024
    assistant_attachment_max_count: int = 10
    assistant_attachment_max_context_chars: int = 20_000
    assistant_attachment_max_image_bytes: int = 5 * 1024 * 1024
    assistant_attachment_expiry_days: int = 30
    assistant_attachment_allowed_types: list[str] = ["pdf", "csv", "txt", "image"]
    project_file_max_bytes: int = 20 * 1024 * 1024
    project_file_allowed_types: list[str] = ["pdf", "csv", "txt", "md", "docx", "xlsx", "image"]
    assistant_context_injection_budget: int = 4_000
    assistant_session_window_tokens: int = 8_000
    assistant_compaction_threshold_tokens: int = 4_000
    assistant_compaction_retention_tokens: int = 2_000

    # Local embeddings (fastembed, ONNX Runtime — no API key, no token
    # billing). Multilingual model, 384 dims (db/migrations/008_local_embeddings.sql).
    embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embed_dims: int = 384
    # Preload the ONNX model at boot so no operator turn pays the load (and, on a
    # cold cache, the download). The suite forces it off: every lifespan start
    # would otherwise load the real model and poison the `get_embedder` fake.
    embed_prewarm: bool = True

    meta_access_token: str  # Meta Cloud API permanent token
    meta_phone_number_id: str  # WhatsApp Business Phone Number ID

    app_version: str = Field(default_factory=_read_app_version)
    git_sha: str = "unknown"

    # Media downloads (design Webhook Pipeline: media -> media/ volume)
    media_dir: str = "media"

    # Panel (design D7; AP-1): secret used to SIGN the Starlette session
    # cookie. Required at boot — an unsigned session cookie would be
    # forgeable. SH-2: env-only, never in the repo.
    panel_session_secret: str

    # Panel (AP-1): bcrypt work factor for panel password hashes. 12 is the
    # production value and MUST stay the default; the test harness lowers it
    # (tests/conftest.py) because bcrypt's cost dominates the auth/user/seed
    # suites. Safe to lower there: the factor is a work factor, not a format,
    # and verify_password reads the cost back out of each stored hash.
    #
    # The bounds are bcrypt's own: gensalt accepts 4..31 and raises ValueError
    # outside it. Without them an out-of-range env value boots fine and then
    # fails every hash_password call at runtime (user creation, password reset,
    # db/seed.sh); with them it fails at boot, where a bad value belongs.
    panel_bcrypt_rounds: int = Field(default=12, ge=4, le=31)

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
