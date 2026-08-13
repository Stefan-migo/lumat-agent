"""route node — capture vs retrieval vs escalate paths (CM-3 flow).

Deterministic routing on the classified intent (no LLM):

- calefont/caldera/calefaccion/solicitar_visita -> capture sub-flow
- valores/postventa -> KB retrieval path
- persona -> handoff escalation (HH-3)
- emergencia -> emergency flag + escalation (full emergency node lands in T4.2;
  this sets the flags the design flow consumes)
- unknown already escalated by classify_intent (HH-3 2x counter)
"""

from __future__ import annotations

from app.chat.state import ConversationState

CAPTURE_INTENTS = {"calefont", "caldera", "calefaccion", "solicitar_visita"}
RETRIEVAL_INTENTS = {"valores", "postventa"}


def route(state: ConversationState) -> dict:
    """Decide the next step and set escalation/emergency flags."""
    intent = state.intent or ""

    if intent == "persona":
        return {"next_step": "escalate", "escalate": True, "escalate_reason": "persona"}
    if intent == "emergencia":
        return {"next_step": "escalate", "emergency": True, "escalate": True, "escalate_reason": "emergencia"}
    if intent == "injection":
        # SH-4: injection -> escalate (summary + human), never a tool/LLM answer
        return {"next_step": "escalate", "escalate": True, "escalate_reason": "injection_detected"}
    if intent in CAPTURE_INTENTS:
        return {"next_step": "capture"}
    if intent in RETRIEVAL_INTENTS:
        return {"next_step": "kb_retrieve"}
    if intent == "unknown":
        # classify_intent already set escalate at the 2nd failure (HH-3)
        if state.escalate:
            return {"next_step": "escalate"}
        return {"next_step": "respond"}  # ask for clarification
    return {"next_step": "respond"}
