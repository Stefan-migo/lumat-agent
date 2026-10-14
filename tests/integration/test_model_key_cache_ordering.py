import base64

from app.config import get_settings
from app.db import session_scope
from app.services import model_secrets


def test_write_does_not_leave_a_read_during_commit_window_cached(monkeypatch):
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"0" * 32).decode())
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-test")
    get_settings.cache_clear()

    with session_scope() as session:
        model_secrets.clear_model_api_key(session, "test-admin")
    model_secrets.invalidate_model_key_cache()
    assert model_secrets.resolve_model_api_key() == "sk-env-test"

    with session_scope() as session:
        model_secrets.set_model_api_key(session, "sk-new", "test-admin")
        # Simulate a same-process read after invalidation but before this write commits.
        assert model_secrets.resolve_model_api_key() == "sk-env-test"
        session.commit()

    # Mirrors the settings route: invalidate only after the write commits.
    model_secrets.invalidate_model_key_cache()
    assert model_secrets.resolve_model_api_key() == "sk-new"
