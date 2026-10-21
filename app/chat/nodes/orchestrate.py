"""orchestrate node — deterministic dispatch to sub-graphs (H2 router, AO-3).

Sits after ``handoff_gate`` (clear path, AO-4) and replaces the old ``route``
node. It is a pure ``(intent, gate flags)`` dispatcher with NO LLM (D2/D3): it
picks the destination sub-graph by the design.md routing table and returns the
state updates that set the ``next_step`` and escalation/emergency flags plus
the selected sub-agent.

Today's ``route`` node semantics are preserved exactly (design table):
escalate flags -> handoff; persona/emergencia/injection -> handoff;
CAPTURE_INTENTS -> capture; RETRIEVAL_INTENTS -> research; unknown (1st,
no escalate) -> respond; anything else -> respond.

The tools whitelist (AO-6 / D5) is enforced "assert-in-dispatch": the
orchestrator only dispatches research_triage, whose ``tools_whitelist``
declares the sole slice-1 tool ``kb.retrieve``. ``is_tool_whitelisted`` is the
thin boundary check A sub-agent may only use the service calls its whitelist
allows; anything else is logged and the turn hands off. Both live here but are
pure/queryable so the routing table and whitelist boundary are unit-testable
without a DB or LLM.
"""

from __future__ import annotations

import logging

from app.chat.nodes.capture import is_social_only
from app.chat.state import ConversationState

logger = logging.getLogger(__name__)

# CM-3 route groups (design line 55-58, AO-3).
#
# `consulta` is the informational intent: a question ABOUT an appliance is answered
# from the KB, while a reported problem with one keeps starting the visit capture.
# Without it the appliance intents had nowhere to put a question, so "que tipos de
# calefont instalan" started the capture flow and asked for a name. See
# odd/tasks/classify-question-vs-problem.md.
CAPTURE_INTENTS = {"calefont", "caldera", "calefaccion", "solicitar_visita"}
RETRIEVAL_INTENTS = {"valores", "postventa", "consulta"}

# The destination sub-graph for KB intents (slice-1; the four other sub-agents
# are data-only this slice and have no runtime dispatch).
RESEARCH_TRIAGE = "research_triage"


def _dispatch(
    intent: str,
    *,
    escalate: bool = False,
    emergency: bool = False,
    escalate_reason: str | None = None,
    mid_capture: bool = False,
    template_id: str | None = None,
    question: bool = False,
) -> dict:
    """Pure (intent, flags) -> routing decision (AO-3, no LLM).

    Returns the state field updates (same shape the node returns):
    ``next_step`` is one of handoff | capture | research | respond; escalation
    flags ride along so the downstream node knows why it was chosen.
    ``question`` marks a mid-capture message that asks something (S16): it is
    answered and the pending field resumes, whatever intent the classifier gave.
    """
    # T4.4: any post-classification escalation (2x unknown, injection, SS-1
    # always_escalate) converges on handoff, reason preserved (route.py:25-30).
    if escalate:
        return {
            "next_step": "handoff",
            "escalate": True,
            "escalate_reason": escalate_reason,
        }

    intent = intent or ""

    if intent == "persona":
        return {"next_step": "handoff", "escalate": True, "escalate_reason": "persona"}
    if intent == "emergencia":
        return {
            "next_step": "handoff",
            "escalate": True,
            "escalate_reason": "emergencia",
            "emergency": True,
        }
    if intent == "injection":
        # SH-4: injection -> escalate (handoff), never a tool/LLM answer.
        return {
            "next_step": "handoff",
            "escalate": True,
            "escalate_reason": "injection_detected",
        }
    if mid_capture:
        if intent in RETRIEVAL_INTENTS or question:
            # Answer the deviation from KB, then resume the pending field (CI-2).
            return {
                "next_step": "research",
                "active_sub_agent": RESEARCH_TRIAGE,
                "capture_paused": True,
            }
        # Cancel/reschedule are intentionally treated as field answers in CI-2.
        return {"next_step": "capture"}
    if intent in {"cancelar_visita", "reagendar_visita"}:
        return {"next_step": "manage"}
    if intent in CAPTURE_INTENTS:
        return {"next_step": "capture"}
    if intent in RETRIEVAL_INTENTS:
        # T5: a preset the classifier picked answers the turn directly, so a KB
        # miss cannot hand it off. Capture/manage flows are not pre-empted.
        if template_id:
            return {"next_step": "respond"}
        # H2: KB intents dispatch to the research_triage sub-graph (was
        # route.py:43-44 kb_retrieve -> respond).
        return {"next_step": "research", "active_sub_agent": RESEARCH_TRIAGE}
    # unknown (1st time, no escalate) asks for clarification; anything else
    # is answered linearly. Both land on respond (route.py:45-50).
    return {"next_step": "respond"}


def is_tool_whitelisted(whitelist: tuple[str, ...] | list[str] | None, tool: str) -> bool:
    """AO-6 thin boundary: is ``tool`` within the sub-agent's whitelist?"""
    return bool(whitelist) and tool in whitelist


def _is_question(state: ConversationState) -> bool:
    """A mid-capture message that asks something (S16).

    A question mark is the deterministic signal the classifier contract honours.
    Two guards keep answers in the capture flow: extraction (an answer phrased as
    a question, "¿puede ser el sábado?") and the social set (a greeting like
    "Hola, ¿cómo estás?" is answered by capture, never sent to retrieval).
    """
    text = (state.window[-1].get("text") or "") if state.window else ""
    return "?" in text and not state.extracted and not is_social_only(text)


def orchestrate(state: ConversationState) -> dict:
    """Dispatch the classified intent to a sub-graph (or handoff/respond).

    Replaces the ``route`` node. Pure ``_dispatch`` decides the destination;
    this wrapper records the selected sub-agent on the state and returns the
    routing updates the graph consumes via ``_route_path``.
    """
    decision = _dispatch(
        state.intent or "",
        escalate=state.escalate,
        emergency=state.emergency,
        escalate_reason=state.escalate_reason,
        mid_capture="_pending" in (state.captured or {}),
        template_id=getattr(state, "template_id", None),
        question=_is_question(state),
    )
    if decision.get("active_sub_agent"):
        logger.info(
            "orchestrate: conversation %s dispatched to sub-agent %s",
            state.conversation_id,
            decision["active_sub_agent"],
        )
    return decision
