import base64

import httpx
import respx
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


def test_real_chatbot_and_assistant_consumers_send_the_panel_key(monkeypatch):
    """Covers the consumers' client-selection seams, not every node call site; catches a factory-level bypass."""
    secret = "sk-panel-consumer-test"
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"0" * 32).decode())
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-fallback")
    monkeypatch.setenv("ASSISTANT_CHAT_PROVIDER", "deepseek")
    get_settings.cache_clear()
    with session_scope() as session:
        model_secrets.set_model_api_key(session, secret, "test-admin")
    model_secrets.invalidate_model_key_cache()

    response = {
        "id": "cmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "deepseek-chat",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }
    with respx.mock(base_url="https://api.deepseek.com") as router:
        route = router.post("/chat/completions").mock(return_value=httpx.Response(200, json=response))

        from app.chat.graph import run_internal_conversation
        from app.chat.assistant.nodes import _assistant_client

        run_internal_conversation(None, None, "hello")
        _assistant_client().chat.completions.create(
            model="deepseek-chat", messages=[{"role": "user", "content": "hello"}]
        )

        assert len(route.calls) == 2
        assert all(call.request.headers["authorization"] == f"Bearer {secret}" for call in route.calls)
