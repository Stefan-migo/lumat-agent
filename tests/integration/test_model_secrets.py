import base64

from sqlalchemy import select

from app.config import get_settings
from app.db import session_scope
from app.models import AuditLog
from app.services import model_secrets
from app.services.llm import openai_client


def test_panel_key_drives_both_deepseek_consumers_and_is_redacted(monkeypatch):
    secret = "sk-panel-test"
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"0" * 32).decode())
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    get_settings.cache_clear()
    with session_scope() as session:
        model_secrets.set_model_api_key(session, secret, "test-admin")
    model_secrets.invalidate_model_key_cache()

    # Both consumers call the same client factory: omitted provider is the
    # WhatsApp chat's chat_provider; explicit DeepSeek is the panel assistant.
    assert openai_client().api_key == secret
    assert openai_client("deepseek").api_key == secret
    assert openai_client("openrouter").api_key == "sk-openrouter-test"

    with session_scope() as session:
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "model_api_key.set")
        )
        assert audit is not None
        assert secret not in repr((audit.before, audit.after, audit.entity_id))

    with session_scope() as session:
        model_secrets.clear_model_api_key(session, "test-admin")
    model_secrets.invalidate_model_key_cache()
    assert openai_client("deepseek").api_key == "sk-test"
