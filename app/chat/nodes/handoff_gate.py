"""handoff_gate node — deterministic pre-LLM escalation triggers (HH-3, T4.4).

Runs after the emergency gate and BEFORE any LLM call: the triggers below need
no classification, so a handoff never spends a model call. Everything that
fires here (and every post-classification escalation) converges on the
`handoff` node, which builds the deriva bundle (HH-2) and moves the
conversation to `human` (HH-1).

Deterministic triggers (HH-3):
1. menu "persona" — the customer asks to talk to a person ("hablar con una
   persona", "persona", "humano", "operador", ...)
3. media evidence — a photo/video/audio/document/sticker arrives for technical
   review (design: "media in normal flow -> handoff for review")
4. complaint/warranty — complaint/upset language (deterministic keyword list,
   module constant; the panel can tune it later via settings if needed)

Triggers 2 and 5 are evaluated AFTER classification (the gate cannot know an
intent it has not classified):
2. 2x unknown intent — classify_intent increments `unknown_count` (T3.4) and
   escalates on the second failure
5. SS-1 `always_escalate` scope — classify_intent checks `get_scope_mode` once
   the category is known

Both converge on the same `route` escalate path -> handoff node.

Note: the menu category names "Postventa/Garantía" are deliberately NOT in the
complaint list — selecting the category must reach the KB retrieval path; a
real complaint ("quiero hacer un reclamo") escalates.
"""

from __future__ import annotations

import re

from app.chat.state import ConversationState
from app.models import MessageType

# Trigger 1: person-request expressions (accent-insensitive via IGNORECASE).
_PERSONA_PATTERN = re.compile(
    r"\bpersona\b|\bhumano\b|\boperador\b|hablar con alguien|asesor humano",
    re.IGNORECASE,
)

# Trigger 3: media types treated as evidence requiring technical review.
# String values — the D2 state window stores `msg_type` as `m.msg_type.value`.
MEDIA_EVIDENCE_TYPES: frozenset[str] = frozenset(
    t.value for t in (MessageType.IMAGE, MessageType.VIDEO, MessageType.AUDIO, MessageType.DOCUMENT, MessageType.STICKER)
)

# Trigger 4: complaint/warranty/upset language. Module constant (HH-3 "nice to
# have" settings-configurable; a settings knob is the upgrade path).
_COMPLAINT_WORDS = (
    "reclamo",
    "reclamos",
    "queja",
    "quejas",
    "quejo",
    "molesto",
    "molesta",
    "enojado",
    "enojada",
    "devolver",
    "devolucion",
    "devolución",
    "reembolso",
    "defectuoso",
    "defectuosa",
    "estafa",
)
_COMPLAINT_PHRASES = ("mal servicio", "no me sirve", "no funciona lo que compre")
_COMPLAINT_PATTERN = re.compile(
    "|".join(
        [rf"\b{re.escape(w)}\b" for w in _COMPLAINT_WORDS]
        + [re.escape(p) for p in _COMPLAINT_PHRASES]
    ),
    re.IGNORECASE,
)


def _current_message(state: ConversationState) -> dict | None:
    return state.window[-1] if state.window else None


def evaluate_handoff(state: ConversationState) -> str | None:
    """Deterministic pre-LLM trigger evaluation; returns the reason or None."""
    message = _current_message(state)
    if message is None:
        return None
    if message.get("msg_type") in MEDIA_EVIDENCE_TYPES:
        return "media_evidence"
    text = message.get("text") or ""
    if _PERSONA_PATTERN.search(text):
        return "persona"
    if _COMPLAINT_PATTERN.search(text):
        return "complaint"
    return None


def handoff_gate(state: ConversationState) -> dict:
    """Store the deterministic trigger reason for the graph router."""
    return {"handoff_reason": evaluate_handoff(state)}
