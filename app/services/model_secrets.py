"""Storage and hot resolution for model-provider credentials."""

from time import monotonic

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import session_scope
from app.models import PanelSecret
from app.services import crypto
from app.services.audit import record_audit

MODEL_API_KEY = "deepseek_api_key"
CACHE_TTL_SECONDS = 45
_cached_key: str | None = None
_cache_expires_at = 0.0
# Bumped on every write/invalidation. A read only publishes its result when the
# generation is unchanged, so a concurrent set/clear is never overwritten by an
# in-flight read that started before it.
_cache_generation = 0


def _mask(key: str) -> str:
    return "…" + key[-4:] if len(key) >= 4 else "…"


def model_api_key_status(session: Session) -> dict[str, bool | str]:
    row = session.scalar(select(PanelSecret).where(PanelSecret.key == MODEL_API_KEY))
    if row:
        key = crypto.decrypt(row.ciphertext, row.nonce)
        return {"configured": True, "source": "panel", "masked": _mask(key)}
    key = get_settings().deepseek_api_key
    if key:
        return {"configured": True, "source": "env", "masked": _mask(key)}
    return {"configured": False, "source": "none", "masked": ""}


def get_model_api_key(session: Session) -> str | None:
    row = session.scalar(select(PanelSecret).where(PanelSecret.key == MODEL_API_KEY))
    return crypto.decrypt(row.ciphertext, row.nonce) if row else get_settings().deepseek_api_key


def set_model_api_key(
    session: Session,
    key: str,
    actor: str,
    *,
    updated_by: int | None = None,
) -> None:
    ciphertext, nonce = crypto.encrypt(key)
    session.execute(
        insert(PanelSecret)
        .values(key=MODEL_API_KEY, ciphertext=ciphertext, nonce=nonce, updated_by=updated_by)
        .on_conflict_do_update(
            index_elements=[PanelSecret.key],
            set_={
                "ciphertext": ciphertext,
                "nonce": nonce,
                "updated_by": updated_by,
                "updated_at": func.now(),
            },
        )
    )
    record_audit(
        session,
        actor=actor,
        action="model_api_key.set",
        entity="panel_secret",
        entity_id=MODEL_API_KEY,
        after={"source": "panel"},
    )
    invalidate_model_key_cache()


def clear_model_api_key(session: Session, actor: str) -> None:
    session.execute(delete(PanelSecret).where(PanelSecret.key == MODEL_API_KEY))
    record_audit(
        session,
        actor=actor,
        action="model_api_key.clear",
        entity="panel_secret",
        entity_id=MODEL_API_KEY,
        after={"source": "env" if get_settings().deepseek_api_key else "none"},
    )
    invalidate_model_key_cache()


def resolve_model_api_key() -> str | None:
    global _cached_key, _cache_expires_at, _cache_generation
    now = monotonic()
    if now < _cache_expires_at:
        return _cached_key
    generation = _cache_generation
    with session_scope() as session:
        key = get_model_api_key(session)
    # Publish only if no write invalidated the cache while we were reading;
    # otherwise this read could re-cache a value a concurrent set/clear dropped.
    if generation == _cache_generation:
        _cached_key = key
        _cache_expires_at = now + CACHE_TTL_SECONDS
    return key


def invalidate_model_key_cache() -> None:
    global _cache_expires_at, _cache_generation
    _cache_expires_at = 0.0
    _cache_generation += 1
