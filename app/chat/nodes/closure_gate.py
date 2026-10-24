"""Deterministic customer-chat closure and business-hours gate."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from app.chat.state import ConversationState
from app.services.settings import (
    MESSAGE_DEFAULTS,
    get_hours_schedule,
    get_hours_timezone,
    get_message,
    is_open_at,
)
from app.db import session_scope


CLOSING_TOKENS = frozenset({
    # Explicit closures only. Acknowledgements used to live here too ("gracias",
    # "ok", "listo", "perfecto"...) because a bare one reached classification,
    # incremented the unknown-intent count and could be answered with the menu
    # clarification. That reason is gone: courtesy now has its own classifier
    # category and its own configurable reply (S3), so the gate stops answering
    # "ok" to an instruction with a goodbye.
    "adios", "bye", "chao", "chau", "hasta", "luego", "nos", "pronto", "vemos",
})
_CLOSING_PHRASES = ("eso fue todo",)
_WORD_PATTERN = re.compile(r"\b\w+\b", re.UNICODE)


def _fold(text: str) -> str:
    """Casefold and drop diacritics, so `adiós` matches `adios`.

    Measured: without this, the correctly accented spelling of a word already
    in the set was not recognised, and `chao` -- the common Chilean spelling --
    was not in the set at all.
    """
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text.casefold())
        if not unicodedata.combining(char)
    )


def is_farewell(text: str) -> bool:
    """Return whether text is only a short customer closing formula."""
    folded = _fold(text).strip()
    if not folded or len(folded) > 40 or "?" in folded:
        return False
    matched_phrase = False
    for phrase in _CLOSING_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", folded):
            matched_phrase = True
            folded = re.sub(rf"\b{re.escape(phrase)}\b", " ", folded)
    tokens = _WORD_PATTERN.findall(folded)
    if not tokens:
        # A bare "eso fue todo" is a closing on its own; it used to ride on the
        # acknowledgement that followed it, and acknowledgements are no longer
        # closing tokens (S3).
        return matched_phrase
    return all(token in CLOSING_TOKENS for token in tokens)


def closure_gate(state: ConversationState) -> dict:
    """Reply to farewells or closed-hours messages before normal flow."""
    if "_pending" in (state.captured or {}):
        return {}

    message = state.window[-1] if state.window else {}
    text = message.get("text") or ""
    with session_scope() as session:
        if is_farewell(text):
            return {
                "replies": [
                    get_message(session, "farewell", MESSAGE_DEFAULTS["farewell"])
                ]
            }

        if not is_open_at(
            schedule=get_hours_schedule(session),
            timezone_name=get_hours_timezone(session),
            now=datetime.now(timezone.utc),
        ):
            return {
                "replies": [
                    get_message(
                        session,
                        "out_of_hours",
                        MESSAGE_DEFAULTS["out_of_hours"],
                    )
                ]
            }
    return {}
