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
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.chat.state import ConversationState, conversation_transcript
from app.db import session_scope
from app.models import KbVisibility, Message
from app.services import kb, prompts
from app.services.costs import record_llm_cost
from app.services.llm import CHAT_MODEL, openai_client
from app.services.settings import (
    MESSAGE_DEFAULTS,
    TARIFA_LABELS,
    get_hours_timezone,
    get_message,
    get_persona_texts,
    get_message_templates,
    get_tarifa_precios,
    get_tone_directive,
    tarifa_vigente,
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
    """Render the preset message the classifier picked.

    None when it is not stored, or when one of its slots resolves empty: S9
    forbids sending an incomplete text ("Hola , atendemos de ."), so the preset is
    skipped and the regular answer path takes the turn.
    """
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
    values = _slot_values(state, prompts.placeholders(text))
    if "" in values.values():
        return None
    return prompts.render_text(text, **values)


def _current_text(state: ConversationState) -> str:
    return state.window[-1]["text"] if state.window else ""


def retrieval_queries(state: ConversationState) -> list[str]:
    """KB query strings for this turn, most conservative first (KB-2).

    The customer's text is tried first so every turn that already finds a chunk
    answers exactly as before; the classifier's normalized `service` is the
    fallback for a miss. Measured on the seeded customer KB with the real
    embedder: "me dieron tu contacto para una mantencion de caldera" scores
    0.2686 raw — below `DEFAULT_MIN_SIM` — against 0.6070 as `service`, so the
    polite filler was the whole difference between answering and handing off.
    The raw text keeps the first slot because it carries the aspect the customer
    asked about (garantía, plazo): "tienen garantia por la mantencion?" scores
    0.510 raw against 0.341 as `service`.

    `state.case` is refreshed by `classify_intent` on every classified turn; an
    `unknown` turn writes no case, so a `service` there belongs to an earlier
    topic and must not steer this turn's retrieval.
    """
    text = _current_text(state)
    queries = [text] if text else []
    if state.intent in (None, "unknown"):
        return queries
    service = (getattr(state, "case", None) or {}).get("service")
    if isinstance(service, str):
        service = service.strip()
        if service and service.casefold() not in {query.casefold() for query in queries}:
            queries.append(service)
    return queries


def retrieve_chunks(session, state: ConversationState) -> list[dict]:
    """First non-empty KB retrieval across `retrieval_queries` (no LLM spend).

    A miss on the customer text costs one more local embed + pgvector query,
    never a model call: the fallback exists so a wording problem cannot become a
    human handoff while the KB holds the answer.
    """
    for query in retrieval_queries(state):
        chunks = kb.retrieve(
            session,
            query,
            top_k=kb.DEFAULT_TOP_K,
            min_sim=kb.DEFAULT_MIN_SIM,
            # Customer chat may use customer-audience documents only.
            audience=KbVisibility.CUSTOMER,
            global_only=True,
        )
        if chunks:
            return chunks
    return []


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


def build_tarifario_block(vigente: dict[str, int]) -> str:
    """Render the prices in force for the prompt's <tarifario> block.

    Only the current amount per service: no season names, no comparison with
    another date, nothing for a service the owner did not price.
    """
    lines = [
        f"{TARIFA_LABELS.get(service, service)}: ${valor:,.0f}".replace(",", ".")
        for service, valor in vigente.items()
    ]
    return "\n".join(lines)


def _tarifario_context() -> tuple[str, str]:
    """Today's date and the current-price block, in the configured timezone."""
    with session_scope() as session:
        timezone_name = get_hours_timezone(session)
        tarifa = get_tarifa_precios(session)
    hoy = datetime.now(ZoneInfo(timezone_name))
    return hoy.strftime("%Y-%m-%d"), build_tarifario_block(
        tarifa_vigente(tarifa, hoy.date())
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
        # S12: one read per turn, same session as the tone directive.
        persona = get_persona_texts(session)
    system = prompts.load(
        "personas/orchestrator.md", override=persona.get("personas/orchestrator.md")
    ) + (
        prompts.load(
            "personas/orchestrator_brief.md",
            override=persona.get("personas/orchestrator_brief.md"),
        )
        if brief
        else ""
    ) + f"\n{tone_directive}"
    memory_block = f"\n<memory>{memory_context}</memory>" if memory_context else ""
    fecha, tarifario = _tarifario_context()
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
                    fecha=fecha,
                    tarifario=tarifario,
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

    # T5/D13: a preset message the classifier picked answers this turn, ahead of
    # the clarification and KB paths.
    template_reply = _render_template_reply(state)
    if template_reply is not None:
        return {"replies": [template_reply]}

    if state.intent == "unknown":
        # Deterministic path — no LLM spend (design Cost Guardrails).
        if state.turn <= 1:
            # CM-1: avoid a clarification immediately after the first-contact
            # greeting; there is no prior bot instruction to clarify.
            return {}
        message_key = "cannot_understand_offer" if state.unknown_count >= 2 else "clarification"
        fallback = MESSAGE_DEFAULTS[message_key]
        with session_scope() as session:
            reply = get_message(session, message_key, fallback)
        return {"replies": [reply]}

    with session_scope() as session:
        try:
            chunks = retrieve_chunks(session, state)
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
