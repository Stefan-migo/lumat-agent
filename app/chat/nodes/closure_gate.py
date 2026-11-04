"""Deterministic customer-chat closure and business-hours gate."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from app.chat.state import ConvState, ConversationState, set_conversation_state
from app.services.settings import (
    MESSAGE_DEFAULTS,
    get_hours_closure_enabled,
    get_hours_schedule,
    get_hours_timezone,
    get_message,
    is_open_at,
)
from app.db import session_scope
from app.models import Conversation


CLOSING_TOKENS = frozenset({
    # Explicit closures only. Acknowledgements used to live here too ("gracias",
    # "ok", "listo", "perfecto"...) because a bare one reached classification,
    # incremented the unknown-intent count and could be answered with the menu
    # clarification. That reason is gone: courtesy now has its own classifier
    # category and its own configurable reply (S3), so the gate stops answering
    # "ok" to an instruction with a goodbye.
    "adios", "bye", "chao", "chau", "hasta", "luego", "nos", "pronto", "vemos",
})
# T3/S3: "eso era todo" is how this customer actually closes, and the judge caught
# the gate answering it with a sales question («¿En qué más te puedo ayudar?»).
# These stay phrases and not tokens: `eso`, `era` and `todo` are ordinary words,
# and a token match would close "el calefont era viejo" too. `is_farewell`
# requires the phrase to be the whole message, which is what keeps that out.
# Stored folded, like the text they are matched against.
# T3: words that may sit around an explicit closing phrase without cancelling it.
# Deliberately NOT part of CLOSING_TOKENS: an acknowledgement on its own is not a
# farewell (S3), it only stops being an obstacle when a real closing is present.
# Measured: "dale, muchas gracias, eso era todo" was answered with another sales
# question.
_COURTESY_TOKENS = frozenset({
    # "no" belongs here and not in CLOSING_TOKENS: a refusal cancels a closing when
    # it is the whole message, and must not cancel one when it merely precedes it.
    # Measured (conversación #53): "no, eso seria todo gracias" was not a farewell,
    # fell to smalltalk and the bot answered "Con gusto. ¿Te puedo ayudar en algo
    # más?" three times to a customer who was leaving.
    "no", "nop",
    "dale", "bueno", "ya", "ok", "oka", "listo", "perfecto", "gracias",
    "muchas", "mil", "genial", "excelente", "amable", "saludos", "cordial",
    "que", "tengas", "buen", "dia", "nuevament",
    # Temporal qualifiers do not add content after an explicit closing phrase.
    "por", "ahora", "ahorita", "momento", "el",
})
_CLOSING_PHRASES = (
    "eso fue todo",
    "eso era todo",
    "eso es todo",
    "eso seria todo",
    "nada mas",
)
_WORD_PATTERN = re.compile(r"\b\w+\b", re.UNICODE)
# A refusal is the whole message, not a sentence that opens with "no".
# "No tengo agua caliente" is a complaint and must never count towards closing;
# "No gracias" and a drawn-out "Noooooooooo" do (collapsed below, porque el
# cliente insistente escribe la negativa con letras repetidas).
_REFUSAL_OPENERS = frozenset({"no", "nop", "nada", "ninguno", "ninguna"})
_REPEATED_LETTERS = re.compile(r"(.)\1{2,}")


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
    """Return whether text is a customer closing formula with no other content."""
    folded = _fold(text).strip()
    if not folded or "?" in folded:
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
    if matched_phrase and all(token in _COURTESY_TOKENS for token in tokens):
        # Courtesy around an explicit closing must not cancel it -- but courtesy
        # alone still must not close, and neither must content that happens to
        # follow the phrase ("eso era todo lo que necesitaba saber del precio").
        return True
    return all(token in CLOSING_TOKENS for token in tokens)


def _is_refusal(text: str) -> bool:
    """Return whether text is a refusal on its own, with nothing else to answer.

    Measured (conversación #25): the customer refused four times in a row and the
    bot asked "¿Te puedo ayudar en algo más?" after each one until he wrote "Chao".
    A refusal followed by real content ("no, el calefont era viejo") answers
    something and stays out of the closing count.
    """
    folded = _REPEATED_LETTERS.sub(r"\1", _fold(text or "")).strip()
    tokens = _WORD_PATTERN.findall(folded)
    if not tokens or tokens[0] not in _REFUSAL_OPENERS:
        return False
    return all(token in _COURTESY_TOKENS for token in tokens[1:])


def closure_gate(state: ConversationState) -> dict:
    """Reply to farewells or closed-hours messages before normal flow."""
    if "_pending" in (state.captured or {}):
        return {}

    message = state.window[-1] if state.window else {}
    text = message.get("text") or ""
    with session_scope() as session:
        should_close_after_refusals = False
        if message.get("direction") == "inbound" and _is_refusal(text):
            current_index = len(state.window) - 1
            previous_inbound_index = next(
                (
                    index
                    for index in range(current_index - 1, -1, -1)
                    if state.window[index].get("direction") == "inbound"
                ),
                None,
            )
            if previous_inbound_index is not None:
                between = state.window[previous_inbound_index + 1 : current_index]
                previous_inbound = state.window[previous_inbound_index]
                should_close_after_refusals = (
                    _is_refusal(previous_inbound.get("text") or "")
                    and any(
                        entry.get("direction") == "outbound"
                        and (entry.get("text") or "").strip().endswith("?")
                        for entry in between
                    )
                )

        if is_farewell(text) or should_close_after_refusals:
            # Owner decision (conversación #53): a clear goodbye closes the
            # conversation, not only the turn. The state stayed `bot` and the owner
            # saw a thread that never finished; closing also stops the bot from
            # answering it again (HH-1) and opens a fresh one on the next message.
            conversation = session.get(Conversation, state.conversation_id)
            if conversation is not None:
                set_conversation_state(
                    session, conversation, ConvState.CLOSED, cause="farewell", actor="bot"
                )
            return {
                "replies": [
                    get_message(session, "farewell", MESSAGE_DEFAULTS["farewell"])
                ]
            }

        if get_hours_closure_enabled(session) and not is_open_at(
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
