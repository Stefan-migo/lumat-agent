"""classify_intent node (CM-3, HH-3 partial, SH-4 partial).

LLM classification with SH-4 input-as-data:
- system prompt = static template (never contains user text)
- user text ONLY inside the <user_input>...</user_input> slot
- deterministic injection pattern set checked BEFORE any LLM call; on match
  the conversation escalates and NO tool/LLM call happens (SH-4: "never
  execute")
- LLM may also flag injection -> same escalation, no further action
- unknown intent increments `unknown_count`; at 2 the conversation escalates
  (HH-3 "Two failed comprehension attempts")
- an SS-1 `always_escalate` scope rule for the classified category escalates
  (HH-3 trigger 5, T4.4 — evaluated here, where the category is known; the
  handoff gate owns the pre-LLM triggers)
- case classification (service/priority/status) is stored on the case row
  (CM-3) through the formal cases service (T4.4)
"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy import func, select

from app.chat.state import ConversationState
from app.db import session_scope
from app.models import ConversationEvent
from app.services import prompts
from app.services.audit import record_audit
from app.services.cases import get_or_create_case
from app.services.costs import record_llm_cost
from app.services.llm import CHAT_MODEL, openai_client
from app.services.settings import get_scope_mode

logger = logging.getLogger(__name__)

# SH-4 detection patterns (design Security section): treated as data, logged,
# conversation escalated — never executed. Spanish + English variants.
_INJECTION_PATTERNS = (
    r"ignora tus instrucciones",
    r"ignor[ae] las instrucciones",
    r"olvida tus instrucciones",
    r"act[uú]a como",
    r"act as if",
    r"ignore your instructions",
    r"reveal (other|otros)",
    r"otros clientes",
    r"contrase[nñ]a",
    r"password",
    r"system prompt",
    r"admin(istrador)?",
)
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def is_injection(text: str) -> bool:
    """Deterministic SH-4 pattern check over the raw user text."""
    return bool(_INJECTION_RE.search(text))


def _current_text(state: ConversationState) -> str:
    return state.window[-1]["text"] if state.window else ""


def _llm_classify(text: str, message_id: int) -> dict:
    """Call gpt-4o-mini with input-as-data (SH-4); returns the parsed JSON.

    Records the token cost on the current message (D6 via costs.py).
    """
    client = openai_client()
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": prompts.load("personas/classify.md")},
            {
                "role": "user",
                "content": prompts.render("prompts/classify.md", user_input=text),
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
    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)
    return {
        "intent": parsed.get("intent") or "unknown",
        "service": parsed.get("service"),
        "priority": parsed.get("priority"),
        "status": parsed.get("status"),
        "injection": bool(parsed.get("injection")),
    }


def _store_classification(session, state: ConversationState, result: dict) -> dict:
    case = get_or_create_case(session, state.conversation_id, state.customer_id)
    case.service = result.get("service")
    case.priority = result.get("priority")
    case.status = result.get("status")
    return {
        "case": {
            "id": case.id,
            "service": case.service,
            "priority": case.priority,
            "status": case.status,
        }
    }


def _record_unknown_intent(session, state: ConversationState, cause: str) -> int:
    """Persist one unknown-intent attempt; returns the NEW total (HH-3)."""
    session.add(
        ConversationEvent(
            conversation_id=state.conversation_id,
            event="unknown_intent",
            cause=cause,
            actor="rule",
        )
    )
    session.flush()
    total = session.scalar(
        select(func.count(ConversationEvent.id)).where(
            ConversationEvent.conversation_id == state.conversation_id,
            ConversationEvent.event == "unknown_intent",
        )
    )
    return int(total or 0)


def classify_intent(state: ConversationState) -> dict:
    """Classify the current message; sets intent/case/unknown/escalate flags."""
    text = _current_text(state)
    if not text:
        return {}

    # SH-4: deterministic detection runs first and NEVER calls the LLM.
    if is_injection(text):
        logger.warning("injection pattern detected in conversation %s", state.conversation_id)
        with session_scope() as session:
            record_audit(
                session,
                actor="system",
                action="conversation.injection_detected",
                entity="conversation",
                entity_id=str(state.conversation_id),
                after={"reason": "deterministic_pattern"},
            )
        return {
            "intent": "injection",
            "escalate": True,
            "escalate_reason": "injection_detected",
        }

    try:
        result = _llm_classify(text, message_id=state.window[-1]["id"] if state.window else 0)
    except Exception:
        logger.exception("LLM classify failed for conversation %s", state.conversation_id)
        result = {"intent": "unknown"}

    if result.get("injection"):
        logger.warning("LLM flagged injection in conversation %s", state.conversation_id)
        with session_scope() as session:
            record_audit(
                session,
                actor="system",
                action="conversation.injection_detected",
                entity="conversation",
                entity_id=str(state.conversation_id),
                after={"reason": "llm_flag"},
            )
        return {
            "intent": "injection",
            "escalate": True,
            "escalate_reason": "injection_detected",
        }

    if result["intent"] == "unknown":
        with session_scope() as session:
            unknown_count = _record_unknown_intent(session, state, text)
        return {
            "intent": "unknown",
            "unknown_count": unknown_count,
            "escalate": unknown_count >= 2,
            "escalate_reason": "unknown_intent_twice" if unknown_count >= 2 else None,
        }

    with session_scope() as session:
        case_update = _store_classification(session, state, result)
        # HH-3 trigger 5 (T4.4): an SS-1 `always_escalate` category escalates
        # regardless of the answer path. Evaluated here, where the category is
        # known — the handoff gate owns the pre-LLM triggers.
        if get_scope_mode(session, result["intent"]) == "always_escalate":
            return {
                "intent": result["intent"],
                "escalate": True,
                "escalate_reason": "scope_always_escalate",
                **case_update,
            }
    return {"intent": result["intent"], **case_update}
