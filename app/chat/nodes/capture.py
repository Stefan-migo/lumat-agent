"""capture node — progressive structured data capture (CM-2).

Each turn the classifier extracts any capturable fields present in the free
text (CI-3b); the node merges them and asks the next 2-3 MISSING fields in one
natural-language message (no numbered list), in the LumatRequest §1.5 order:
identification (name, email), location (comuna, address), equipment, failure,
evidence, availability. A skip answer (no sé / no tengo / ...) marks the field
`unknown` and continues without blocking (CM-2).

CI-3: consent is NOT a data field. Once every field is captured the flow asks
for consent as its own explicit step before booking; a positive answer writes
the captured name/email/comuna/address + consent onto the customer record
(CR-6) and sends the flow to booking.
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

# CM-2 field order (LumatRequest §1.5): (field, question to ask). Identification
# is name + email, then location, then the equipment/failure/availability block.
CAPTURE_FIELDS: list[tuple[str, str]] = [
    ("name", "¿Cuál es tu nombre?"),
    ("email", "¿Cuál es tu correo electrónico?"),
    ("comuna", "¿En qué comuna te encuentras?"),
    ("address", "¿Cuál es tu dirección?"),
    ("equipment", "¿Qué equipo tienes? (marca, modelo y años aproximados)"),
    ("failure", "Describe el problema: qué falla, desde cuándo y con qué frecuencia."),
    ("evidence", "¿Puedes enviar una foto o video del equipo y su pantalla? (si no, di 'no tengo')"),
    ("availability", "¿Qué días y horarios te acomodan para la visita?"),
]

# CI-3: consent is an explicit step of its own, before booking. It is never a
# data field and never extracted from free text (PII).
CONSENT_QUESTION = "¿Autorizas que guardemos tus datos para gestionar tu solicitud? Responde sí o no."

# CI-3b: ask up to this many questions per message. `evidence` is a media ask, so
# it is not an extracted free-text field.
MAX_ASKS = 3
EXTRACTABLE_FIELDS = frozenset(field for field, _ in CAPTURE_FIELDS if field != "evidence")
_FIELD_QUESTIONS = dict(CAPTURE_FIELDS)
_FIELD_ORDER = [field for field, _ in CAPTURE_FIELDS]

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
        email=clean.get("email"),
        comuna=clean.get("comuna"),
        address=clean.get("address"),
    )
    promote_captured_equipment(session, customer, state.conversation_id, clean)
    consent = _answer_consent(captured.get("consent", "unknown"))
    if consent is not None:
        record_consent(session, customer, consent=consent)


def _missing_fields(captured: dict) -> list[str]:
    """Data fields not yet captured (a skipped field is stored, so not missing)."""
    return [field for field in _FIELD_ORDER if field not in captured]


def _ask_text(fields: list[str]) -> str:
    """One message grouping 2-3 field questions, natural language, no list."""
    return " ".join(_FIELD_QUESTIONS[field] for field in fields)


def _merge_extracted(captured: dict, extracted: dict | None) -> None:
    """Fill captured fields from this turn's extraction (never overwrite/consent)."""
    for field, value in (extracted or {}).items():
        if field in EXTRACTABLE_FIELDS and value and not captured.get(field):
            captured[field] = value


def capture(state: ConversationState) -> dict:
    """Merge this turn's extraction and ask the next missing fields (CI-3b)."""
    captured = dict(state.captured)
    _merge_extracted(captured, state.extracted)
    pending = captured.get("_pending")

    if pending == "consent":
        # CI-3: the explicit consent step runs AFTER every data field, before
        # booking. A deviation on this step re-asks it instead of answering it.
        if state.capture_paused:
            return {"capture_paused": False, "replies": [CONSENT_QUESTION]}
        answer = _current_text(state)
        captured["consent"] = "unknown" if is_skip(answer) else answer
        captured.pop("_pending", None)
        with session_scope() as session:
            _apply_consent_and_customer(session, state, captured)
            _persist_captured(session, state, captured)
        return {"captured": captured, "next_step": "booking"}

    if state.capture_paused:
        # CI-2/CI-3b: a deviation was answered; resume without storing its text.
        captured.pop("_pending", None)
        return _ask_next(captured, state, clear_paused=True)

    if pending is None:
        # First capture turn: the current message is the intent, not an answer.
        if state.intent in {"calefont", "caldera", "calefaccion"}:
            captured["equipment_type"] = state.intent
        return _ask_next(captured, state)

    # An answer turn. Extraction already filled what it could. A single free-text
    # answer that extracted nothing is attributed to the first asked field still
    # missing — the batch we asked is always the leading missing fields in order.
    if not any(field in captured for field in pending):
        target = pending[0]
        if target not in captured:
            captured[target] = "unknown" if is_skip(_current_text(state)) else _current_text(state)

    captured.pop("_pending", None)
    return _ask_next(captured, state)


def _ask_next(captured: dict, state: ConversationState, *, clear_paused: bool = False) -> dict:
    """Ask the next 2-3 missing fields, or the consent step when none remain."""
    missing = _missing_fields(captured)
    if not missing:
        captured["_pending"] = "consent"
        with session_scope() as session:
            _persist_captured(session, state, captured)
        return {"captured": captured, "replies": [CONSENT_QUESTION]}

    batch = missing[:MAX_ASKS]
    captured["_pending"] = batch
    with session_scope() as session:
        _persist_captured(session, state, captured)
    updates: dict = {"captured": captured, "replies": [_ask_text(batch)]}
    if clear_paused:
        updates["capture_paused"] = False
    return updates
