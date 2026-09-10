"""Contracts for bounded assistant context and durable state."""

from app.chat.assistant.state import (
    ASSISTANT_STATE_KEYS,
    COMPACTION_RETENTION_TOKENS,
    COMPACTION_THRESHOLD_TOKENS,
    INJECTION_TOKEN_BUDGET,
    SESSION_WINDOW_TOKENS,
    estimate_tokens,
)
from app.config import Settings


def test_estimate_tokens_uses_utf8_bytes_and_ceiling():
    assert estimate_tokens("á") == 1
    assert estimate_tokens("🙂") == 1
    assert estimate_tokens("a" * 5) == 2


def test_assistant_state_adds_only_optional_harness_contract_keys():
    assert ASSISTANT_STATE_KEYS == {
        "context_meta",
        "planner",
        "guardrails",
        "compaction",
        "extension_hooks",
    }


def test_harness_budget_defaults_are_resolved():
    assert INJECTION_TOKEN_BUDGET == 4_000
    assert SESSION_WINDOW_TOKENS == 8_000
    assert COMPACTION_THRESHOLD_TOKENS == 4_000
    assert COMPACTION_RETENTION_TOKENS == 2_000

    settings = Settings(
        app_secret="secret",
        verify_token="verify",
        database_url="postgresql+psycopg://app:app@localhost/lumat",
        meta_access_token="meta",
        meta_phone_number_id="phone",
        panel_session_secret="panel",
    )
    assert settings.assistant_context_injection_budget == 4_000
    assert settings.assistant_session_window_tokens == 8_000
    assert settings.assistant_compaction_threshold_tokens == 4_000
    assert settings.assistant_compaction_retention_tokens == 2_000
