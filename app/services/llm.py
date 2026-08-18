"""LLM client factory (multi-provider chat; OpenAI-compatible protocol).

DeepSeek (default) and OpenRouter both speak the OpenAI chat-completions
protocol — only base_url + model + api_key change (design D3 change). A fresh
httpx client per call so tests can intercept every request with respx (create
the client inside the mocked context). At H1 scale (tens of conversations/day)
per-call client creation is negligible; a module-level cached client would pin
the transport at first use and make tests flaky.
"""

from __future__ import annotations

import httpx
from openai import OpenAI

from app.config import get_settings

LLM_TIMEOUT_SECONDS = 60.0

# chat_completions-compatible base URLs per provider (deepseek default).
# DeepSeek serves /chat/completions directly at api.deepseek.com; OpenRouter
# under /api/v1. Both accept the OpenAI SDK with only base_url changed.
PROVIDER_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openrouter": "https://openrouter.ai/api/v1",
}

CHAT_MODEL = get_settings().chat_model


def openai_client() -> OpenAI:
    """Return a chat-completions client for the ACTIVE provider (env, SH-2).

    Raises a clear error when the active provider's key is missing (fail-fast:
    Settings keeps both keys optional, the key is only required once a chat
    call is actually made).
    """
    settings = get_settings()
    provider = settings.chat_provider
    if provider not in PROVIDER_BASE_URLS:
        raise RuntimeError(
            f"unsupported CHAT_PROVIDER {provider!r} "
            "(expected 'deepseek' or 'openrouter')"
        )
    key = settings.deepseek_api_key if provider == "deepseek" else settings.openrouter_api_key
    if not key:
        raise RuntimeError(
            f"{provider.upper()}_API_KEY is required when CHAT_PROVIDER={provider}"
        )
    return OpenAI(
        api_key=key,
        base_url=PROVIDER_BASE_URLS[provider],
        http_client=httpx.Client(timeout=LLM_TIMEOUT_SECONDS),
    )
