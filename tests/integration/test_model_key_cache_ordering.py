import base64

from app.config import get_settings
from app.db import session_scope
from app.services import model_secrets


def test_write_does_not_invalidate_the_cache_before_commit(monkeypatch):
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"0" * 32).decode())
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-test")
    get_settings.cache_clear()

    reads = []
    real = model_secrets.get_model_api_key

    def counting(session):
        reads.append(1)
        return real(session)

    monkeypatch.setattr(model_secrets, "get_model_api_key", counting)

    with session_scope() as session:
        model_secrets.clear_model_api_key(session, "test-admin")
    model_secrets.invalidate_model_key_cache()
    assert model_secrets.resolve_model_api_key() == "sk-env-test"
    assert len(reads) == 1

    with session_scope() as session:
        model_secrets.set_model_api_key(session, "sk-new", "test-admin")
        # The cached fallback remains valid until the caller commits and invalidates.
        assert model_secrets.resolve_model_api_key() == "sk-env-test"
        assert len(reads) == 1, "the write invalidated the cache before commit"
        session.commit()

    # Mirrors the settings route: invalidate only after the write commits.
    model_secrets.invalidate_model_key_cache()
    assert model_secrets.resolve_model_api_key() == "sk-new"
