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
import unicodedata

from sqlalchemy import func, select

from app.chat.state import ConversationState, conversation_transcript
from app.chat.nodes.capture import EXTRACTABLE_FIELDS
from app.db import session_scope
from app.models import ConversationEvent
from app.services import prompts
from app.services.audit import record_audit
from app.services.cases import set_case_status, get_or_create_case
from app.services.costs import record_llm_cost
from app.services.llm import CHAT_MODEL, openai_client
from app.services.settings import get_message_templates, get_scope_mode
from app.services.realtime import record_activity

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


# V4 §A3: `persona` means an EXPLICIT request for a human. The model over-fires
# it on social questions ("¿cómo estás?"), which used to hand the conversation
# to a human and drop the customer's pending context. The intent only survives
# when the text actually asks for a person.
_HUMAN_REQUEST_PATTERNS = (
    r"hablar con (una |un )?(persona|humano|humana|ejecutiv\w*|asesor\w*|alguien)",
    r"comunic\w* con (una |un )?(persona|humano|ejecutiv\w*|asesor\w*)",
    r"pas\w* (con |a )?(una |un )?(persona|humano|ejecutiv\w*|asesor\w*)",
    r"(necesito|quiero|prefiero) (una |un )?(persona|humano|humana|ejecutiv\w*|asesor\w*)",
    r"atencion humana",
    r"persona real",
)
_HUMAN_REQUEST_RE = re.compile("|".join(_HUMAN_REQUEST_PATTERNS), re.IGNORECASE)


def is_explicit_human_request(text: str) -> bool:
    """True only when the message asks for a person in so many words."""
    folded = unicodedata.normalize("NFD", (text or "").casefold())
    folded = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    return bool(_HUMAN_REQUEST_RE.search(folded))


def _current_text(state: ConversationState) -> str:
    return state.window[-1]["text"] if state.window else ""


def _template_block(templates: list) -> str:
    """Render the preset-message catalog as an inert DATA block (D5/T6).

    Owner-authored text (untrusted) goes into the USER message wrapped in
    `<templates>...</templates>`, never the static system prompt (SH-4).
    """
    lines = [
        f"- id={template.get('id')}: {template.get('text')}"
        for template in templates
        if isinstance(template, dict) and template.get("id")
    ]
    return "\n".join(lines) if lines else "(sin respuestas prediseñadas)"


def _llm_classify(
    text: str, message_id: int, conversation: str = "(sin mensajes previos)"
) -> dict:
    """Call gpt-4o-mini with input-as-data (SH-4); returns the parsed JSON.

    Records the token cost on the current message (D6 via costs.py).
    """
    client = openai_client()
    with session_scope() as session:
        catalog = get_message_templates(session)
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": prompts.load("personas/classify.md")},
            {
                "role": "user",
                "content": prompts.render(
                    "prompts/classify.md",
                    conversation=conversation,
                    templates=_template_block(catalog),
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
    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)
    # The model was handed the catalog; only an offered id may survive (D13).
    offered = {t.get("id") for t in catalog if isinstance(t, dict)}
    picked = parsed.get("template_id")
    return {
        "intent": parsed.get("intent") or "unknown",
        "service": parsed.get("service"),
        "priority": parsed.get("priority"),
        "status": parsed.get("status"),
        "injection": bool(parsed.get("injection")),
        # CI-3b: same call also extracts any capture fields present in the text.
        "fields": parsed.get("fields") or {},
        # T4/D3: the preset-message id this turn selected (None when none fits).
        "template_id": picked if isinstance(picked, str) and picked in offered else None,
    }


def _extracted(result: dict) -> dict:
    """Keep only clean string values for known capturable fields (never consent)."""
    raw = result.get("fields") or {}
    return {
        field: value.strip()
        for field, value in raw.items()
        if field in EXTRACTABLE_FIELDS and isinstance(value, str) and value.strip()
    }


def _store_classification(session, state: ConversationState, result: dict) -> dict:
    case = get_or_create_case(session, state.conversation_id, state.customer_id)
    case.service = result.get("service")
    case.priority = result.get("priority")
    set_case_status(case, result.get("status"))
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
    mid_capture = "_pending" in (state.captured or {})
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
        result = _llm_classify(
            text,
            message_id=state.window[-1]["id"] if state.window else 0,
            conversation=conversation_transcript(state.window),
        )
    except Exception:
        logger.exception("LLM classify failed for conversation %s", state.conversation_id)
        result = {"intent": "unknown"}

    if result.get("intent") == "persona" and not is_explicit_human_request(text):
        # V4 §A3 / E1 T05: "¿cómo estás?" is not "quiero hablar con una persona".
        logger.info(
            "classify_intent: persona downgraded to unknown in conversation %s",
            state.conversation_id,
        )
        result = {**result, "intent": "unknown"}

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
        if mid_capture:
            # CM-2 field answers are not comprehension failures (HH-3).
            return {
                "intent": "unknown",
                "extracted": _extracted(result),
                "template_id": result.get("template_id"),
            }
        with session_scope() as session:
            unknown_count = _record_unknown_intent(session, state, text)
            record_activity(
                session,
                state.conversation_id,
                "classified",
                cause="intent:unknown",
                actor="bot",
            )
        return {
            "intent": "unknown",
            "unknown_count": unknown_count,
            "escalate": unknown_count >= 2,
            "escalate_reason": "unknown_intent_twice" if unknown_count >= 2 else None,
            "extracted": _extracted(result),
            "template_id": result.get("template_id"),
        }

    with session_scope() as session:
        case_update = _store_classification(session, state, result)
        record_activity(
            session,
            state.conversation_id,
            "classified",
            cause=f"intent:{result['intent']}",
            actor="bot",
        )
        # HH-3 trigger 5 (T4.4): an SS-1 `always_escalate` category escalates
        # regardless of the answer path. Evaluated here, where the category is
        # known — the handoff gate owns the pre-LLM triggers.
        if get_scope_mode(session, result["intent"]) == "always_escalate":
            return {
                "intent": result["intent"],
                "escalate": True,
                "escalate_reason": "scope_always_escalate",
                "extracted": _extracted(result),
                "template_id": result.get("template_id"),
                **case_update,
            }
    return {
        "intent": result["intent"],
        "extracted": _extracted(result),
        "template_id": result.get("template_id"),
        **case_update,
    }
