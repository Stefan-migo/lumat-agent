"""OpenAI client factory (D3: gpt-4o-mini chat, text-embedding-3-small).

A fresh httpx client per call so tests can intercept every request with respx
(create the client inside the mocked context). At H1 scale (tens of
conversations/day) per-call client creation is negligible; the alternative —
a module-level cached client — would pin the transport at first use and make
tests flaky.
"""

from __future__ import annotations

import httpx
from openai import OpenAI

from app.config import get_settings

LLM_TIMEOUT_SECONDS = 60.0

CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"


def openai_client() -> OpenAI:
    """Return a configured OpenAI client (key from env, SH-2)."""
    return OpenAI(
        api_key=get_settings().openai_api_key,
        http_client=httpx.Client(timeout=LLM_TIMEOUT_SECONDS),
    )
