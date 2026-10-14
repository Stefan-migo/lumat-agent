"""respond node — KB-grounded answers + unresolved logging (CM-4, CM-6).

Only authorized KB content (retrieved via pgvector) can be answered: the LLM
receives chunks inside <kb> tags and the user text inside <user_input> (never
in the system prompt). The system prompt forbids inventing prices, guarantees,
definitive diagnoses or availability (CM-4). A KB miss (below min_sim) answers
"cannot answer reliably" deterministically (no LLM spend), logs the unresolved
question (CM-6: question + context + timestamp on the inbound message payload)
and escalates by default.

Unknown intents get a deterministic clarification (no LLM — deterministic
paths never call the LLM, design Cost Guardrails).
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.chat.state import ConversationState, conversation_transcript
from app.db import session_scope
from app.models import KbVisibility, Message
from app.services import kb, prompts
from app.services.costs import record_llm_cost
from app.services.llm import CHAT_MODEL, openai_client
from app.services.settings import (
    MESSAGE_DEFAULTS,
    get_message,
    get_message_templates,
    get_tone_directive,
)

logger = logging.getLogger(__name__)

CANNOT_ANSWER_REPLY = MESSAGE_DEFAULTS["cannot_answer"]
KB_UNAVAILABLE_REPLY = (
    "La base de conocimiento no está disponible en este momento. "
    "Un asesor de Lumat revisará tu consulta y te contactará."
)
CLARIFICATION_REPLY = MESSAGE_DEFAULTS["clarification"]

# T5/D8: preset-message slot vocabulary -> ConversationState sources. The system
# always fills them; a missing/"unknown" value renders as an empty string.
_SLOT_SOURCES = {
    "nombre": "name",
    "comuna": "comuna",
    "direccion": "address",
    "equipo": "equipment",
    "problema": "failure",
    "disponibilidad": "availability",
}


def _slot_values(state: ConversationState, slots: set[str]) -> dict[str, str]:
    """Fill the template's declared slots from captured/booking (D8/D13)."""
    captured = state.captured or {}
    booking = state.booking or {}
    values: dict[str, str] = {}
    for slot in slots:
        if slot == "visita":
            values[slot] = booking.get("label") or ""
            continue
        source = _SLOT_SOURCES.get(slot)
        raw = captured.get(source) if source else None
        values[slot] = "" if raw in (None, "unknown") else str(raw)
    return values


def _render_template_reply(state: ConversationState) -> str | None:
    """Render the preset message the classifier picked; None if it is not stored."""
    if not state.template_id:
        return None
    with session_scope() as session:
        templates = get_message_templates(session)
    template = next(
        (t for t in templates if isinstance(t, dict) and t.get("id") == state.template_id),
        None,
    )
    if template is None:
        return None
    text = template.get("text") or ""
    return prompts.render_text(text, **_slot_values(state, prompts.placeholders(text)))


def _current_text(state: ConversationState) -> str:
    return state.window[-1]["text"] if state.window else ""


def log_unresolved(session, message_id: int, context: str) -> None:
    """CM-6: mark an inbound message as unresolved (question+context+ts)."""
    message = session.get(Message, message_id)
    if message is None:
        return
    message.payload = {
        **(message.payload or {}),
        "unresolved": True,
        "unresolved_context": context,
    }


def list_unresolved_questions(session, limit: int = 100) -> list[Message]:
    """CM-6 query (no dedicated SQL view — filter by payload flag)."""
    return list(
        session.scalars(
            select(Message)
            .where(Message.payload["unresolved"].astext == "true")
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
    )


def _answer_from_kb(
    text: str,
    kb_text: str,
    message_id: int,
    brief: bool = False,
    memory_context: str = "",
    conversation: str = "(sin mensajes previos)",
    booking: str = "El cliente no tiene ninguna visita agendada.",
) -> str:
    """Grounded answer; records the LLM cost on the current message (D6).

    ``brief`` (SS-3 conservative mode) appends the one-line brevity directive
    to the system prompt so completion tokens — the expensive half of the
    gpt-4o-mini rate — shrink. ``memory_context`` (CM-7) is injected as a
    read-only <memory> block beside <kb> when the customer has stored memories.
    """
    client = openai_client()
    with session_scope() as session:
        tone_directive = get_tone_directive(session)
    system = prompts.load("personas/orchestrator.md") + (
        prompts.load("personas/orchestrator_brief.md") if brief else ""
    ) + f"\n{tone_directive}"
    memory_block = f"\n<memory>{memory_context}</memory>" if memory_context else ""
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": prompts.render(
                    "prompts/respond.md",
                    conversation=conversation,
                    booking=booking,
                    kb_text=kb_text + memory_block,
                    user_input=text,
                ),
            },
        ],
        temperature=0,
    )
    with session_scope() as session:
        record_llm_cost(
            session,
            message_id=message_id,
            model=CHAT_MODEL,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )
    with session_scope() as session:
        fallback = get_message(session, "cannot_answer", CANNOT_ANSWER_REPLY)
    return response.choices[0].message.content or fallback


def respond(state: ConversationState) -> dict:
    """Answer the current message: clarification / KB-grounded / cannot-answer."""
    text = _current_text(state)
    if not text:
        return {}

    if state.intent == "unknown":
        # Deterministic path — no LLM spend (design Cost Guardrails).
        if state.turn <= 1:
            # CM-1: avoid a clarification immediately after the first-contact
            # greeting; there is no prior bot instruction to clarify.
            return {}
        with session_scope() as session:
            clarification = get_message(session, "clarification", CLARIFICATION_REPLY)
        return {"replies": [clarification]}

    # T5/D13: a preset message the classifier picked pre-empts the KB path.
    template_reply = _render_template_reply(state)
    if template_reply is not None:
        return {"replies": [template_reply]}

    with session_scope() as session:
        try:
            chunks = kb.retrieve(
                session,
                text,
                top_k=kb.DEFAULT_TOP_K,
                min_sim=kb.DEFAULT_MIN_SIM,
                # Customer chat may use customer-audience documents only.
                audience=KbVisibility.CUSTOMER,
                global_only=True,
            )
        except Exception as error:
            # Unlike the panel this path records no evidence entry, so the log is
            # the only record of the outage: keep the traceback.
            logger.exception("Knowledge-base retrieval failed: %s", error)
            return {
                "replies": [KB_UNAVAILABLE_REPLY],
                "escalate": True,
                "escalate_reason": "kb_unavailable",
            }
        if not chunks:
            # CM-4: cannot answer reliably + CM-6 log + default escalation.
            log_unresolved(
                session,
                message_id=state.window[-1]["id"],
                context=f"intent={state.intent}",
            )
            return {
                "replies": [get_message(session, "cannot_answer", CANNOT_ANSWER_REPLY)],
                "escalate": True,
                "escalate_reason": "kb_miss",
            }
        kb_text = "\n".join(f"{i + 1}. {c['content']}" for i, c in enumerate(chunks))

    answer = _answer_from_kb(
        text,
        kb_text,
        message_id=state.window[-1]["id"],
        brief=state.cost_mode == "conservative",
        memory_context=state.memory_context,
        conversation=conversation_transcript(state.window),
        booking=(
            f"El cliente tiene una visita agendada: {state.booking['service']} "
            f"el {state.booking['label']} (estado {state.booking['status']})."
            if state.booking
            else "El cliente no tiene ninguna visita agendada."
        ),
    )
    return {"replies": [answer]}
