import pytest

from app.services import crypto


def test_encrypt_decrypt_round_trip(monkeypatch):
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")
    from app.config import get_settings

    get_settings.cache_clear()
    ciphertext, nonce = crypto.encrypt("sk-test")

    assert ciphertext != b"sk-test"
    assert len(nonce) == 12
    assert crypto.decrypt(ciphertext, nonce) == "sk-test"


def test_encrypt_without_encryption_key_has_clear_error(monkeypatch):
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="SETTINGS_ENCRYPTION_KEY"):
        crypto.encrypt("sk-test")


def test_openai_client_uses_resolved_model_key_for_both_deepseek_paths(monkeypatch):
    from app.config import get_settings
    from app.services import llm

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-test")
    get_settings.cache_clear()
    monkeypatch.setattr(llm, "resolve_model_api_key", lambda: "sk-panel-test")

    assert llm.openai_client().api_key == "sk-panel-test"
    assert llm.openai_client("deepseek").api_key == "sk-panel-test"


def test_openai_client_keeps_environment_fallback_and_openrouter_key(monkeypatch):
    from app.config import get_settings
    from app.services import llm

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    get_settings.cache_clear()
    monkeypatch.setattr(llm, "resolve_model_api_key", lambda: "sk-test")

    assert llm.openai_client("deepseek").api_key == "sk-test"
    assert llm.openai_client("openrouter").api_key == "sk-openrouter-test"


def test_openai_client_fails_clearly_when_deepseek_key_is_missing(monkeypatch):
    from app.config import get_settings
    from app.services import llm

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(llm, "resolve_model_api_key", lambda: None)

    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY is required"):
        llm.openai_client("deepseek")
