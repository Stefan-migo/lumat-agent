"""Receive node — first-contact open greeting (CM-1).

Deterministic (no LLM): on the first turn the bot opens with the Lumat greeting.
The greeting adapts to whether the customer already stated their need: a bare
greeting gets the full greeting (identifies itself and asks how it can help),
while a first message that already says what they need gets the short greeting —
identifies itself but drops the redundant "¿En qué te puedo ayudar?". Either way
`run_conversation` fuses the greeting with the turn's answer into a single
message. Media-only turns receive an acknowledgement that the file was saved as
evidence. Other turns leave the answer to downstream nodes, so the flow resumes
from stored state, never from scratch (CM-1 repeat).
"""

from __future__ import annotations

import re
import unicodedata

from app.chat.nodes.handoff_gate import is_media_evidence
from app.chat.state import GREETING_HEADER, GREETING_SHORT_HEADER, ConversationState
from app.db import session_scope
from app.services.settings import get_message

EVIDENCE_ACK = "Recibí tu archivo, lo guardé para el técnico."

# Bare first-turn greetings (normalized: lower-case, accents stripped, every run
# of non-alphanumerics collapsed to a single space).
GREETING_TOKENS = frozenset(
    {
        "hola",
        "buenas",
        "hola buenas",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
        "hey",
    }
)


def _normalized_inbound(state: ConversationState) -> str:
    """The latest inbound text, normalized for greeting matching."""
    inbound = next(
        (message for message in reversed(state.window) if message.get("direction") == "inbound"),
        None,
    )
    text = unicodedata.normalize("NFD", (inbound.get("text") or "").casefold()) if inbound else ""
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def is_greeting_only(state: ConversationState) -> bool:
    """True when the first turn is a bare greeting (no need stated)."""
    return _normalized_inbound(state) in GREETING_TOKENS


def has_content(state: ConversationState) -> bool:
    """True when the inbound text states something beyond a bare greeting.

    Media-only turns (no text) have no content: the file is evidence, not a
    stated need, so they keep the full greeting.
    """
    return bool(_normalized_inbound(state)) and not is_greeting_only(state)


def _first_turn_header(session, state: ConversationState) -> str:
    key = "greeting_short" if has_content(state) else "greeting"
    default = GREETING_SHORT_HEADER if key == "greeting_short" else GREETING_HEADER
    return get_message(session, key, default)


def receive(state: ConversationState) -> dict:
    """Handle the incoming message at the start of the graph run.

    `state.turn` counts inbound messages (1 = first contact). The first turn
    sets `first_turn_greeting` (fused into one message by `run_conversation`);
    media receives an evidence acknowledgement while normal turns continue to
    downstream nodes.
    """
    updates: dict = {}
    if state.turn <= 1:
        with session_scope() as session:
            updates["first_turn_greeting"] = _first_turn_header(session, state)
    message = state.window[-1] if state.window else None
    if is_media_evidence(message):
        updates["replies"] = [EVIDENCE_ACK]
    return updates
