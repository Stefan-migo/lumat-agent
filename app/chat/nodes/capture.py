"""capture node — progressive structured data capture (CM-2).

One field per turn, in the LumatRequest §1.5 order: identification, location,
equipment, failure, evidence, availability, consent. The answer to the
pending field is validated and stored on the conversation (`captured_data`,
persisted so the D2 per-message rebuild keeps it); a skip answer (no sé / no
tengo / ...) marks the field `unknown` and continues without blocking (CM-2).

Consent (CR-6): a positive consent answer writes the captured name/comuna/
address + consent onto the customer record. Completion replies with a
confirmation and sends the flow to the summary node (CM-5).
"""

from __future__ import annotations

import logging

from app.chat.state import ConversationState
from app.db import session_scope
from app.models import Conversation, Customer
from app.services.customers import (
    promote_captured_equipment,
    record_consent,
    update_captured_data,
)

logger = logging.getLogger(__name__)

# CM-2 field order (LumatRequest §1.5): (field, question to ask).
CAPTURE_FIELDS: list[tuple[str, str]] = [
    ("name", "¿Cuál es tu nombre?"),
    ("comuna", "¿En qué comuna te encuentras?"),
    ("address", "¿Cuál es tu dirección?"),
    ("equipment", "¿Qué equipo tienes? (marca, modelo y años aproximados)"),
    ("failure", "Describe el problema: qué falla, desde cuándo y con qué frecuencia."),
    ("evidence", "¿Puedes enviar una foto o video del equipo y su pantalla? (si no, di 'no tengo')"),
    ("availability", "¿Qué días y horarios te acomodan para la visita?"),
    ("consent", "¿Autorizas que guardemos tus datos para gestionar tu solicitud? Responde sí o no."),
]

COMPLETION_REPLY = (
    "Gracias, tu solicitud quedó registrada. Un técnico la revisará y te "
    "contactaremos para coordinar la visita."
)

# Skip answers -> field stored as "unknown", flow continues (CM-2).
_SKIP_WORDS = (
    "no se",
    "no sé",
    "no tengo",
    "no lo se",
    "skip",
    "saltar",
    "paso",
    "ninguno",
    "ninguna",
    "no aplica",
    "prefiero no responder",
    "desconozco",
)
_YES_WORDS = ("si", "sí", "yes", "ok", "claro", "confirmo", "acepto")
_NO_WORDS = ("no", "nope", "negativo")


def is_skip(text: str) -> bool:
    return any(word in text.lower() for word in _SKIP_WORDS)


def _answer_consent(value: str) -> bool | None:
    """True/False for an explicit consent answer; None when skipped."""
    if value == "unknown":
        return None
    lowered = value.lower()
    if any(word in lowered for word in _YES_WORDS):
        return True
    if any(word in lowered for word in _NO_WORDS):
        return False
    return None


def _current_text(state: ConversationState) -> str:
    return state.window[-1]["text"] if state.window else ""


def _persist_captured(session, state: ConversationState, captured: dict) -> None:
    conv = session.get(Conversation, state.conversation_id)
    if conv is not None:
        conv.captured_data = captured


def _apply_consent_and_customer(session, state: ConversationState, captured: dict) -> None:
    """CR-6: write captured identification/location + consent on the ficha."""
    customer = session.get(Customer, state.customer_id)
    if customer is None:
        return
    clean = {k: v for k, v in captured.items() if v not in ("unknown", None)}
    update_captured_data(
        session,
        customer,
        name=clean.get("name"),
        comuna=clean.get("comuna"),
        address=clean.get("address"),
    )
    promote_captured_equipment(session, customer, state.conversation_id, clean)
    consent = _answer_consent(captured.get("consent", "unknown"))
    if consent is not None:
        record_consent(session, customer, consent=consent)


def _next_field_after(pending: str) -> tuple[str, str] | None:
    for i, (field, question) in enumerate(CAPTURE_FIELDS):
        if field == pending and i + 1 < len(CAPTURE_FIELDS):
            return CAPTURE_FIELDS[i + 1]
    return None


def capture(state: ConversationState) -> dict:
    """Handle one capture turn: store the pending answer, ask the next field."""
    captured = dict(state.captured)
    pending = captured.get("_pending")

    if state.capture_paused and pending is not None:
        # CI-2: do not store deviation text as the pending value; re-ask and resume.
        question = dict(CAPTURE_FIELDS)[pending]
        return {"capture_paused": False, "replies": [question]}

    if pending is None:
        # First capture turn: the current message is the menu choice/intent,
        # not an answer. Ask the first field without storing anything.
        captured["_pending"] = CAPTURE_FIELDS[0][0]
        if state.intent in {"calefont", "caldera", "calefaccion"}:
            captured["equipment_type"] = state.intent
        with session_scope() as session:
            _persist_captured(session, state, captured)
        return {"captured": captured, "replies": [CAPTURE_FIELDS[0][1]]}

    answer = _current_text(state)
    value = "unknown" if is_skip(answer) else answer
    captured[pending] = value
    captured.pop("_pending", None)

    with session_scope() as session:
        if pending == "consent":
            _apply_consent_and_customer(session, state, captured)
        _persist_captured(session, state, captured)

    next_field = _next_field_after(pending)
    if next_field is None:
        return {"captured": captured, "next_step": "booking"}

    captured["_pending"] = next_field[0]
    with session_scope() as session:
        _persist_captured(session, state, captured)
    return {"captured": captured, "replies": [next_field[1]]}
