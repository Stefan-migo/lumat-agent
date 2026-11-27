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
import re
from datetime import date, datetime, timezone

from app.chat.nodes.capture import is_social_only
from app.chat.nodes.respond import asks_about_schedule, quotes_required, tariff_service
from app.chat.slot_window import resolve_window
from app.chat.state import ConversationState
from app.chat.visit_questions import (
    asks_about_booked_visit,
    asks_for_change,
    normalise as _normalise_visit_text,
)
from app.db import session_scope
from app.models import Conversation, Customer

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
    resume_capture: bool = False,
    quote_question: bool = False,
    day_selection: bool = False,
    change_request: bool = False,
    has_upcoming_visit: bool = True,
    booked_visit_question: bool = False,
) -> dict:
    """Pure (intent, flags) -> routing decision (AO-3, no LLM).

    Returns the state field updates (same shape the node returns):
    ``next_step`` is one of handoff | capture | research | respond; escalation
    flags ride along so the downstream node knows why it was chosen.
    ``question`` marks a message to answer before capture, including the opening
    turn when it carries a coverage or price signal; ``resume_capture`` marks
    that pendingless opening so capture follows the answer in the same turn.
    ``quote_question`` marks a turn that asks the price of work outside the
    published tariff (D8): it is answered, not turned into a diagnostic capture.
    ``change_request`` marks a turn that explicitly asks to move or cancel the
    visit (S12): it outranks ``question``, because "Quiero reagendar la visita es
    posible?" is a request whose surface happens to be interrogative.
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
    if booked_visit_question:
        # Measured conversation 50: a question about the visit the customer holds
        # is answered from her appointment rows, never from the free-agenda preview
        # (`availability_reply` outranked everything) and never as a capture field
        # (`day_selection` read «para el lunes» as a preference). The classifier
        # returns `consulta`, `reagendar_visita` or `solicitar_visita` for the same
        # sentence across runs, so the answer cannot depend on that label. A change
        # request never carries this flag (`asks_about_booked_visit` excludes it).
        return {"next_step": "respond"}
    if intent == "reagendar_visita" and change_request:
        # S2/S12: an explicit request to change the visit remains management,
        # even when no upcoming appointment is currently in the database.
        return {"next_step": "manage"}
    if intent == "reagendar_visita" and not has_upcoming_visit:
        # S4: with no visit to move, this is a visit request, and it outranks the
        # mid-capture question path on purpose. The hour the customer names is
        # named back by the capture acknowledgement (S3) and read by booking once
        # the capture finishes (owner decision L5). Measured twice: whenever this
        # branch runs the reply names the preference; whenever the same turn fell
        # through to `research` the customer KB had nothing to say about a time
        # preference and the reply was a kb_miss offer ("No tengo ese dato.
        # ¿Prefieres que te tome los datos…?"). The classifier flip-flops between
        # `solicitar_visita` and `reagendar_visita` for the same sentence across
        # runs, so routing must not depend on which label it picked this time:
        # `solicitar_visita` already lands in capture on its own.
        return {"next_step": "capture"}
    if intent == "smalltalk":
        # Mid-capture courtesy is answered by capture, which re-asks the pending
        # batch; without a pending field the configured social reply stays linear.
        return {"next_step": "capture" if mid_capture else "respond"}
    if mid_capture:
        if intent in {"cancelar_visita", "reagendar_visita"} and change_request:
            # S12 (chatbot-realismo-conversacional): asking to reschedule is a
            # request, not an answer. Production #23 turn 289 asked "Quiero
            # reagendar la visita es posible?" mid-capture and read "¿En qué
            # comuna te encuentras?" back — CI-2 used to fold these two intents
            # into the pending field, and the customer's own visit was never
            # offered. The explicit change verb is what makes it a request.
            return {"next_step": "manage"}
        if intent in RETRIEVAL_INTENTS or question:
            # Answer the deviation from KB, then resume the pending field (CI-2).
            # S1 (agenda-respeta-horario) put this ahead of visit management:
            # measured `real-dato-mas-pregunta` ("Yo creo qje no alcanza, y
            # mañana?") and `real-reagenda-familiar` ("Es factible que vengas un
            # dia pero a las.9 am") both classify as `reagendar_visita`, so the
            # old order sent a plain schedule question to `manage`, which had no
            # visit to move, handed off with `booking_unavailable` and left the
            # conversation owned by a human — the following turns got no reply.
            return {
                "next_step": "research",
                "active_sub_agent": RESEARCH_TRIAGE,
                "capture_paused": True,
            }
        if intent in {"cancelar_visita", "reagendar_visita"}:
            # No question in the turn: S12's plain request keeps its own path.
            return {"next_step": "manage"}
        # Remaining intents are field answers in CI-2.
        return {"next_step": "capture"}
    if intent in {"cancelar_visita", "reagendar_visita"}:
        return {"next_step": "manage"}
    if quote_question:
        # S2/D8: "cuanto cuesta cambiar la caldera" classified as `caldera` and
        # landed in capture, which answered "cuéntame qué pasa con el equipo" —
        # the price question was never answered and the quote step in `respond`
        # was unreachable for the eight measured works. Asking the price of that
        # work is a question, not a new fault to diagnose.
        return {"next_step": "respond"}
    if day_selection:
        return {"next_step": "capture"}
    if question:
        # S1: answer an interrogative capture-intent turn, or a pendingless
        # opening with a coverage/price signal. Pause either active capture or
        # that opening so research can resume the agenda in the same turn.
        decision = {
            "next_step": "research",
            "active_sub_agent": RESEARCH_TRIAGE,
        }
        if mid_capture or resume_capture:
            decision["capture_paused"] = True
        return decision
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


def _normalise_interrogative_text(text: str) -> str:
    """Case-fold and remove accents for explicit interrogative marker matching.

    Same fold `app.chat.visit_questions` uses, imported rather than reimplemented
    so the routing predicates and the answer match the customer's words the same
    way.
    """
    return _normalise_visit_text(text)


def asks_explicitly(text: str) -> bool:
    """True when a turn has explicit question punctuation or a question marker.

    `cuando` is intentionally excluded: it also appears in statements like
    "cuando llegue". Marker matching uses word boundaries so `pueden` cannot
    match as a substring of another word.

    `factible`, `podrias` and `podria` are the conditional-request shape (S1,
    agenda-respeta-horario): "Es factible que vengas un dia pero a las.9 am" is
    measured as `reagendar_visita` by the classifier and carries no "?", so
    without these markers it read as a field answer and the requested hour was
    never acknowledged. A statement that happens to use them is answered and the
    capture agenda resumes, so the failure mode is an extra answer, not a lost
    field.
    """
    if "?" in text or "¿" in text:
        return True
    normalized = _normalise_interrogative_text(text)
    return re.search(r"\b(?:cuanto|pueden|se\s+puede|factible|podrias|podria|sera)\b", normalized) is not None


def _is_question(state: ConversationState) -> bool:
    """A mid-capture message that asks something (S16, S4/T4, T1/S1).

    Social-only turns stay in capture. Explicit question punctuation or a
    question marker answers a question even when extraction also found a field;
    schedule/coverage terms remain the final fallback for the measured T4 shape.

    S1/D2 removed the old `not state.extracted` conjunction on purpose. It guarded
    the answer-phrased-as-a-question shape ("¿puede ser el sábado?"), and it cost
    every turn that brings data AND a question: 303 of 2.157 real customer
    messages (14%) were stored as a field answer and the question went
    unanswered. Extraction is already applied before this decision, so answering
    the question loses nothing — and the capture agenda resumes right after
    (`_after_research_triage`).
    """
    text = (state.window[-1].get("text") or "") if state.window else ""
    if is_social_only(text):
        return False
    if asks_explicitly(text):
        return True
    return asks_about_schedule(text)


def _has_pendingless_answer_signal(state: ConversationState) -> bool:
    """A first-turn place or published-price signal merits an answer first."""
    captured = state.captured or {}
    if "_pending" in captured or not state.window:
        return False
    text = state.window[-1].get("text") or ""
    normalized = _normalise_interrogative_text(text)
    if re.search(r"\b(?:vivo|vives|viven|estoy|estas|estamos)\s+en\b", normalized):
        return True
    return bool(
        re.search(r"\b(?:precio|precios|vale|cuesta|sale|tarifa|valor)\b", normalized)
        and tariff_service(text)
    )


def _is_quote_question(state: ConversationState) -> bool:
    """A turn that asks the price of work with no published tariff (S2/D8).

    Without this flag the classifier's device intent wins: "cuanto cuesta cambiar
    la caldera" comes back as `caldera`, capture asks what the equipment is doing,
    and the customer's price question is never answered.
    """
    if not _is_question(state):
        return False
    text = (state.window[-1].get("text") or "") if state.window else ""
    return quotes_required(text)


def _has_upcoming_visit(state: ConversationState) -> bool:
    """Read whether this customer has a booked future appointment.

    Missing conversation/customer records fail closed to the legacy routing,
    where visit management remains available.
    """
    if state.conversation_id is None or state.customer_id is None:
        return True

    from app.chat.nodes.manage import _appointment_query

    with session_scope() as session:
        conversation = session.get(Conversation, state.conversation_id)
        customer = session.get(Customer, state.customer_id)
        if (
            conversation is None
            or customer is None
            or conversation.customer_id != customer.id
        ):
            return True
        return session.scalar(
            _appointment_query(customer.id, datetime.now(timezone.utc)).limit(1)
        ) is not None


def orchestrate(state: ConversationState) -> dict:
    """Dispatch the classified intent to a sub-graph (or handoff/respond).

    Replaces the ``route`` node. Pure ``_dispatch`` decides the destination;
    this wrapper records the selected sub-agent on the state and returns the
    routing updates the graph consumes via ``_route_path``.
    """
    pendingless_answer_signal = _has_pendingless_answer_signal(state)
    text = (state.window[-1].get("text") or "") if state.window else ""
    booked_visit_question = asks_about_booked_visit(text)
    day_selection = (
        resolve_window(text, today=date.today()) is not None
        and not asks_explicitly(text)
        and not asks_for_change(text)
        # Naming a day is not choosing a slot when the day belongs to a visit the
        # customer already holds (measured conversation 50, turn 3).
        and not booked_visit_question
        and not _is_quote_question(state)
        and not is_social_only(text)
        and state.intent not in {"postventa", "valores"}
    )
    decision = _dispatch(
        state.intent or "",
        escalate=state.escalate,
        emergency=state.emergency,
        escalate_reason=state.escalate_reason,
        mid_capture="_pending" in (state.captured or {}),
        template_id=getattr(state, "template_id", None),
        question=_is_question(state) or pendingless_answer_signal,
        resume_capture=pendingless_answer_signal,
        quote_question=_is_quote_question(state),
        day_selection=day_selection,
        change_request=asks_for_change(
            (state.window[-1].get("text") or "") if state.window else ""
        ),
        has_upcoming_visit=_has_upcoming_visit(state),
        booked_visit_question=booked_visit_question,
    )
    if decision.get("active_sub_agent"):
        logger.info(
            "orchestrate: conversation %s dispatched to sub-agent %s",
            state.conversation_id,
            decision["active_sub_agent"],
        )
    return decision
