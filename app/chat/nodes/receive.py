"""Receive node — first-contact open greeting (CM-1) and greeting answers.

Deterministic (no LLM): on the first turn the bot opens with the Lumat greeting.
The greeting adapts to whether the customer already stated their need: a bare
greeting gets the full greeting (identifies itself and asks how it can help),
while a first message that already says what they need gets the short greeting —
identifies itself but drops the redundant "¿En qué te puedo ayudar?". Either way
`run_conversation` fuses the greeting with the turn's answer into a single
message. Media-only turns receive an acknowledgement that the file was saved as
evidence. Other turns leave the answer to downstream nodes, so the flow resumes
from stored state, never from scratch (CM-1 repeat).

A greeting on any later turn is answered with the same configured greeting and
never reaches classification: a saludo is not a comprehension failure (S1 of
`odd/tasks/chatbot-backlog.md`).
"""

from __future__ import annotations

import re
import unicodedata

from app.chat.nodes.handoff_gate import is_media_evidence
from app.chat.state import GREETING_HEADER, GREETING_SHORT_HEADER, ConversationState
from app.db import session_scope
from app.services.settings import get_message

EVIDENCE_ACK = "Recibí tu archivo, lo guardé para el técnico."

# Greeting words (normalized: lower-case, accents stripped, every run of
# non-alphanumerics collapsed to a single space). Recognition is by word instead
# of an exact whole-message match: production sent "Hola buenas tardes",
# "hola como va?" and "Alo?" and each one was counted as `unknown_intent`.
GREETING_WORDS = frozenset(
    {"hola", "holi", "buenas", "buenos", "buen", "saludos", "hey", "alo"}
)
# Day parts and social filler that may ride along with a greeting word without
# turning it into content. They never make a greeting on their own.
GREETING_FILLERS = frozenset(
    {
        "dia",
        "dias",
        "tarde",
        "tardes",
        "noche",
        "noches",
        "que",
        "tal",
        "como",
        "va",
        "van",
        "estas",
        "esta",
        "estan",
        "andas",
        "todo",
        "bien",
        "espero",
        "disculpa",
        "disculpe",
        "perdon",
        "oye",
        "senor",
        "senora",
        "senorita",
        "amigo",
        "amiga",
    }
)
# A greeting is short by nature. The cap keeps a long message that happens to
# open with one (`"hola " + rambling`) out of the greeting path.
_MAX_GREETING_LENGTH = 40


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
    """True when the message is only a greeting, whatever its variant.

    Every word must be a greeting word or greeting filler, and at least one must
    be a greeting word, so `"hola buenas tardes"` and `"hola como va?"` count
    while `"hola mundo"` and `"buenas necesito una visita"` stay content.
    """
    text = _normalized_inbound(state)
    if not text or len(text) > _MAX_GREETING_LENGTH:
        return False
    tokens = text.split()
    if not any(token in GREETING_WORDS for token in tokens):
        return False
    return all(token in GREETING_WORDS or token in GREETING_FILLERS for token in tokens)


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
    elif is_greeting_only(state):
        # S1: greeting the bot again is answered, not classified. The greeting
        # never increments `unknown_intent` nor counts as an attempt.
        with session_scope() as session:
            updates["replies"] = [get_message(session, "greeting", GREETING_HEADER)]
    message = state.window[-1] if state.window else None
    if is_media_evidence(message):
        updates["replies"] = [EVIDENCE_ACK]
    return updates
