"""capture node — progressive structured data capture (CM-2).

Each turn the classifier extracts any capturable fields present in the free
text (CI-3b); the node merges them and asks the next MISSING fields in one
natural-language message (no numbered list).

Order (V4 §A3/A7, `odd/tasks/chatbot-cerebro-max-v4.md` T10): failure,
equipment, comuna, availability, name, email, address. The diagnostic fields
are asked ONE at a time; the 2–3 field bundle is reserved for booking data.
Identity and address come last, when the visit is actually being booked —
the old order started with name/email and turned every reported fault into an
interrogation. A purely social message mid-capture is answered, never stored as
a field answer (T03/T04).

Evidence is an optional ask; received media is case evidence. A skip answer
(no sé / no tengo / ...) marks the field `unknown` and continues without
blocking (CM-2).

CI-3: consent is NOT a data field. Once every field is captured the flow asks
for consent as its own explicit step before booking; a positive answer writes
the captured name/email/comuna/address + consent onto the customer record
(CR-6) and sends the flow to booking.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from app.chat.nodes.handoff_gate import is_media_evidence
from app.chat.state import ConversationState
from app.db import session_scope
from app.models import Conversation, Customer
from app.services.customers import (
    promote_captured_equipment,
    record_consent,
    update_captured_data,
)

logger = logging.getLogger(__name__)

# CM-2 field order. V4 §A3/A7 (odd/tasks/chatbot-cerebro-max-v4.md, T10)
# reorders it: the technical need comes first and identity/admin data only when
# the visit is actually being booked. The old order started with name/email,
# which turned every reported fault into an interrogation.
CAPTURE_FIELDS: list[tuple[str, str]] = [
    ("failure", "Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?"),
    ("equipment", "¿Qué equipo es? Si sabes la marca y el modelo, mejor."),
    ("comuna", "¿En qué comuna te encuentras?"),
    ("availability", "¿Qué días y horarios te acomodan para la visita?"),
    ("name", "¿Cuál es tu nombre?"),
    ("email", "¿Cuál es tu correo electrónico?"),
    ("address", "¿Cuál es tu dirección?"),
]

EVIDENCE_QUESTION = "¿Tienes algo más para pasarle al técnico? (una foto, un audio…)"

# CI-3: consent is an explicit step of its own, before booking. It is never a
# data field and never extracted from free text (PII).
CONSENT_QUESTION = "¿Autorizas que guardemos tus datos para gestionar tu solicitud? Responde sí o no."

# CI-3b: ask up to this many questions per message.
MAX_ASKS = 3
EXTRACTABLE_FIELDS = frozenset(field for field, _ in CAPTURE_FIELDS)
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

# V4 §A3/D3: a social message mid-capture is a greeting, not a field answer.
# Storing it would write "Hola, ¿cómo estás?" as the customer's name, and
# re-listing the pending fields would turn a greeting into a form.
_SOCIAL_ONLY = frozenset(
    {
        "hola",
        "holaa",
        "holaaa",
        "holaaaa",
        "buenas",
        "hola buenas",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
        "hey",
        "como estas",
        "como esta",
        "que tal",
        "todo bien",
        "hola como estas",
        "hola que tal",
        "como andas",
    }
)
_SOCIAL_REPLY = "¡Hola! Todo bien, gracias. Cuando quieras seguimos con lo de tu equipo."

# V4 §A3: the diagnostic fields are asked one at a time; the bundled ask is for
# booking data (location, availability, identity) once the need is understood.
_DIAGNOSIS_FIELDS = frozenset({"failure", "equipment"})
_EQUIPMENT_LABELS = {
    "calefont": "calefont",
    "caldera": "caldera",
    "calefaccion": "sistema de calefacción",
}


def _normalize(text: str) -> str:
    """Lower-case, accent-folded, non-alphanumerics collapsed to one space."""
    folded = unicodedata.normalize("NFD", (text or "").casefold())
    folded = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def is_social_only(text: str) -> bool:
    """True when the whole message is a greeting or a social question."""
    return _normalize(text) in _SOCIAL_ONLY


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
    return (state.window[-1].get("text") or "") if state.window else ""


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
    if state.intent in {"calefont", "caldera", "calefaccion"}:
        # V4 §E1 T07: a new fault replaces the equipment context instead of
        # leaving the earlier appliance frozen in the record.
        captured["equipment_type"] = state.intent
    message = state.window[-1] if state.window else None
    if is_media_evidence(message):
        return _ask_next(captured, state)
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

    if isinstance(pending, list) and is_social_only(_current_text(state)):
        # Answer the greeting without consuming it as a field answer and without
        # re-listing the pending fields; the next turn resumes the batch.
        return {"replies": [_SOCIAL_REPLY]}

    if state.capture_paused:
        # CI-2/CI-3b: a deviation was answered; resume without storing its text.
        captured.pop("_pending", None)
        return _ask_next(captured, state, clear_paused=True)

    if pending is None:
        # First capture turn: the current message is the intent, not an answer.
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

    # V4 §A1/A3: one useful question per turn while diagnosing; two or three
    # together only when the customer is already closing the booking.
    limit = 1 if missing[0] in _DIAGNOSIS_FIELDS else MAX_ASKS
    batch = missing[:limit]
    captured["_pending"] = batch
    ask = _ask_text(batch)
    label = _EQUIPMENT_LABELS.get(captured.get("equipment_type") or "")
    if batch == ["failure"] and label:
        ask = f"Entiendo, es un problema con tu {label}. {ask}"
    if len(missing) <= MAX_ASKS and not captured.get("_evidence_asked"):
        ask = f"{ask} {EVIDENCE_QUESTION}"
        captured["_evidence_asked"] = True
    with session_scope() as session:
        _persist_captured(session, state, captured)
    updates: dict = {"captured": captured, "replies": [ask]}
    if clear_paused:
        updates["capture_paused"] = False
    return updates
