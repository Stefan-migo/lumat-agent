"""summary node — conversation summary at completion/escalation (CM-5).

Generates a concise summary (customer, issue, captured data, classification,
outcome) with gpt-4o-mini, stores it on the conversation AND the case, and
records the LLM cost on the current message (D6 via T3.6 costs). On escalation
it also tells the customer a human will take over (the full handoff bundle +
state transition land in T4.4).
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.chat.state import ConversationState
from app.db import session_scope
from app.models import Case, Conversation, Customer
from app.services.costs import record_llm_cost
from app.services.llm import CHAT_MODEL, openai_client

logger = logging.getLogger(__name__)

ESCALATION_REPLY = "Un asesor revisará tu caso y te contactará a la brevedad."

SYSTEM_PROMPT = (
    "Eres el asistente de Lumat. Genera un resumen breve y conciso de la "
    "conversación con el cliente, en español: cliente (nombre o teléfono), "
    "motivo/equipo, datos capturados, clasificación del caso y siguiente paso. "
    "Responde SOLO con el resumen, sin preámbulo."
)


def _summary_context(state: ConversationState, customer: Customer) -> str:
    name = customer.name if customer else None
    return (
        f"Cliente: {name or state.phone} (telefono {state.phone})\n"
        f"Conversacion {state.conversation_id}, turno {state.turn}\n"
        f"Intencion: {state.intent}\n"
        f"Clasificacion del caso: {state.case or {}}\n"
        f"Datos capturados: {state.captured or {}}\n"
        f"Escalada: {state.escalate} ({state.escalate_reason or '-'})"
    )


def summary(state: ConversationState) -> dict:
    """Generate + persist the summary; reply on escalation (CM-5)."""
    with session_scope() as session:
        customer = session.get(Customer, state.customer_id)
        context = _summary_context(state, customer)

    client = openai_client()
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        temperature=0,
    )
    summary_text = response.choices[0].message.content or ""
    summary_text = summary_text.strip()

    with session_scope() as session:
        conv = session.get(Conversation, state.conversation_id)
        if conv is not None:
            conv.summary = summary_text
        case = session.scalar(
            select(Case)
            .where(Case.conversation_id == state.conversation_id)
            .order_by(Case.id.desc())
            .limit(1)
        )
        if case is not None:
            case.summary = summary_text
        record_llm_cost(
            session,
            message_id=state.window[-1]["id"] if state.window else 0,
            model=CHAT_MODEL,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

    replies = [ESCALATION_REPLY] if state.escalate else []
    return {"summary": summary_text, "replies": replies}
