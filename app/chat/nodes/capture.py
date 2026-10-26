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
from app.chat.nodes.replies import render_reply
from app.chat.state import ConversationState
from app.db import session_scope
from app.models import Conversation, Customer
from app.services.customers import (
    promote_captured_equipment,
    record_consent,
    update_captured_data,
)
from app.services.settings import (
    REPLY_TEXT_DEFAULTS,
    comuna_cubierta,
    get_capture_ack,
    get_capture_questions,
    get_capture_preventive_keywords,
    get_conduct,
    get_coverage_communes,
    get_reply_texts,
)

logger = logging.getLogger(__name__)

# CM-2 field order. V4 §A3/A7 (odd/tasks/chatbot-cerebro-max-v4.md, T10)
# reorders it: the technical need comes first and identity/admin data only when
# the visit is actually being booked. The old order started with name/email,
# which turned every reported fault into an interrogation. S11: this list is the
# shipped default and the capture model — the effective sequence is
# `chat.conduct.orden`.
CAPTURE_FIELDS: list[tuple[str, str]] = [
    ("failure", "Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?"),
    ("equipment", "¿Qué equipo es? Si sabes la marca y el modelo, mejor."),
    ("comuna", "¿En qué comuna te encuentras?"),
    ("availability", "¿Qué días y horarios te acomodan para la visita?"),
    ("name", "¿Cuál es tu nombre?"),
    ("email", "¿Cuál es tu correo electrónico?"),
    ("address", "¿Cuál es tu dirección?"),
]

# S14: how many times a field may be asked before the flow offers a derivation.
# The second ask is the reformulation; a third one would just repeat the same
# text again, so the turn escalates instead.
MAX_ASKS_PER_FIELD = 2

# S15: the closed-list derivation rule for a comuna outside `coverage.communes`.
COVERAGE_DERIVATION = "cobertura"
EXTRACTABLE_FIELDS = frozenset(field for field, _ in CAPTURE_FIELDS)
# S11: the shipped order and the capture model. `chat.conduct.orden` is the
# effective sequence; this list is its default and the fields the validators
# accept. Only the wording is configurable under `capture.questions` (S7).
CAPTURE_FIELD_ORDER = [field for field, _ in CAPTURE_FIELDS]
_FIELD_QUESTIONS = dict(CAPTURE_FIELDS)

# S18: short owner-facing labels for the panel's capture-order editor. The field
# names are code identifiers; the owner reorders labels, never identifiers.
CAPTURE_FIELD_LABELS: dict[str, str] = {
    "failure": "Problema",
    "equipment": "Equipo",
    "comuna": "Comuna",
    "availability": "Disponibilidad",
    "name": "Nombre",
    "email": "Correo",
    "address": "Dirección",
}

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

# Shipped wording of the capture steps (S8). The node answers with the configured
# text from settings (`reply.texts`); these aliases are the defaults that tests
# and `scripts/kb_fidelity.py` assert.
EVIDENCE_QUESTION = REPLY_TEXT_DEFAULTS["capture_evidence"]
CONSENT_QUESTION = REPLY_TEXT_DEFAULTS["capture_consent"]

# ponytail: the flow no longer emits this text (completion replies go through
# `summary`); it stays only as a classifier fixture in scripts/kb_fidelity.py.
# Delete it when that fixture stops using it.
COMPLETION_REPLY = (
    "Gracias, tu solicitud quedó registrada. Un técnico la revisará y te "
    "contactaremos para coordinar la visita."
)

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
    """True/False only for an exact allowlisted answer; otherwise unclear."""
    normalized = _normalize(value)
    if normalized in {_normalize(word) for word in _YES_WORDS}:
        return True
    if normalized in {_normalize(word) for word in _NO_WORDS}:
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


def _missing_fields(captured: dict, order: list[str]) -> list[str]:
    """Data fields of `order` not yet captured (a skip is stored, so not missing).

    `order` is the effective sequence from `chat.conduct.orden` (S11); a field
    the owner dropped from it is never asked.
    """
    skipped = set(captured.get("_skipped") or [])
    return [field for field in order if field not in captured and field not in skipped]


def _field_questions(session) -> dict[str, str]:
    """Configured wording per field, falling back to the built-in text (S7)."""
    return {**_FIELD_QUESTIONS, **get_capture_questions(session)}


def _render_capture_ack(session, captured: dict) -> str:
    """Render configured acknowledgement using only captured non-sensitive facts.

    An acknowledgement marks a transition; repeating the same sentence before
    every later question turns it back into the tic this feature removes, so the
    last one used is remembered and an identical replay is suppressed.
    """
    text = get_capture_ack(session)
    facts = {
        "nombre": captured.get("name"),
        "comuna": captured.get("comuna"),
        "equipo": captured.get("equipment") or captured.get("equipment_type"),
        "problema": captured.get("failure"),
        "disponibilidad": captured.get("availability"),
    }
    available = {key: value for key, value in facts.items() if isinstance(value, str) and value and value != "unknown"}
    if not available or not any(re.search(r"{{\s*" + key + r"\s*}}", text) for key in available):
        return ""
    rendered = re.sub(
        r"{{\s*(\w+)\s*}}",
        lambda match: available.get(match.group(1), ""),
        text,
    )
    if rendered.strip() == (captured.get("_acked") or "").strip():
        return ""
    captured["_acked"] = rendered.strip()
    return rendered


def _ask_text(fields: list[str], questions: dict[str, str]) -> str:
    """One message grouping 2-3 field questions, natural language, no list."""
    return " ".join(questions[field] for field in fields)


def _merge_extracted(
    captured: dict, extracted: dict | None, pending: list[str], state: ConversationState,
    communes: list[str],
) -> None:
    """Merge validated values from this turn, restricted to its pending batch."""
    prior_texts = {
        item.get("text") for item in state.window[:-1]
        if item.get("direction", "inbound") == "inbound" and item.get("text")
    }
    current_text = _current_text(state)
    for field, value in (extracted or {}).items():
        if field not in pending or field not in EXTRACTABLE_FIELDS or not isinstance(value, str):
            continue
        value = value.strip()
        if not value or captured.get(field):
            continue
        if field == "comuna":
            captured[field] = value if comuna_cubierta(communes, value) else "unknown"
        elif field == "email":
            if re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", value):
                captured[field] = value
        elif field in {"failure", "address"}:
            if value != current_text and value not in prior_texts:
                captured[field] = value
        else:
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
    pending = captured.get("_pending")

    if pending == "consent":
        # CI-3: the explicit consent step runs AFTER every data field, before
        # booking. A deviation on this step re-asks it instead of answering it.
        if state.capture_paused:
            with session_scope() as session:
                consent = render_reply(get_reply_texts(session), "capture_consent")
            return {"capture_paused": False, "replies": [consent]}
        answer = _current_text(state)
        consent = None if is_skip(answer) else _answer_consent(answer)
        if consent is True:
            captured["consent"] = answer
            captured.pop("_pending", None)
            with session_scope() as session:
                _apply_consent_and_customer(session, state, captured)
                _persist_captured(session, state, captured)
            return _ask_next(captured, state)
        if consent is False:
            captured.pop("email", None)
            captured.pop("address", None)
            captured["consent"] = "no"
            captured.pop("_pending", None)
            with session_scope() as session:
                texts = get_reply_texts(session)
                _persist_captured(session, state, captured)
                reply = render_reply(texts, "capture_consent_refused")
            return _derive_with_reply(captured, "consent_declined", reply)
        with session_scope() as session:
            texts = get_reply_texts(session)
            asked = dict(captured.get("_asked") or {})
            if asked.get("consent", 0) == 0 and "consent" not in captured:
                captured["consent"] = "unknown"
            if asked.get("consent", 0) >= MAX_ASKS_PER_FIELD:
                captured.pop("_pending", None)
                _persist_captured(session, state, captured)
                reply = render_reply(texts, "capture_consent_unclear")
                return _derive_with_reply(captured, "consent_unclear", reply)
            asked["consent"] = asked.get("consent", 0) + 1
            captured["_asked"] = asked
            captured["_pending"] = "consent"
            _persist_captured(session, state, captured)
            reply = render_reply(texts, "capture_consent_unclear")
        return {"captured": captured, "replies": [reply]}

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

    # An answer turn merges only validated fields the extractor assigned within
    # the asked batch. Skip answers retain the explicit unknown sentinel.
    with session_scope() as session:
        _merge_extracted(
            captured, state.extracted, pending, state, get_coverage_communes(session)
        )
    if not any(field in captured for field in pending):
        if is_skip(_current_text(state)):
            target = pending[0]
            if target not in captured:
                captured[target] = "unknown"
        else:
            return _reask_pending(captured, pending, state)

    captured.pop("_pending", None)
    return _ask_next(captured, state)


def _reask_pending(captured: dict, pending: list[str], state: ConversationState) -> dict:
    """Repeat the unanswered batch once, then offer its existing derivation."""
    asked = dict(captured.get("_asked") or {})
    if any(asked.get(field, 0) >= MAX_ASKS_PER_FIELD for field in pending):
        captured.pop("_pending", None)
        return _derive(captured, "campo_sin_respuesta")

    for field in pending:
        asked[field] = asked.get(field, 0) + 1
    captured["_asked"] = asked
    captured["_pending"] = pending
    with session_scope() as session:
        ask = _ask_text(pending, _field_questions(session))
        ack = _render_capture_ack(session, captured)
        if ack:
            ask = f"{ack}{ask}"
        _persist_captured(session, state, captured)
    return {"captured": captured, "replies": [ask]}


def _out_of_coverage(
    captured: dict, communes: list[str], derivaciones: list[str]
) -> bool:
    """True when the captured comuna is outside coverage and the rule is on (S15)."""
    if COVERAGE_DERIVATION not in derivaciones:
        return False
    comuna = captured.get("comuna")
    if not comuna or comuna == "unknown":
        return False
    return not comuna_cubierta(communes, comuna)


def _derive_with_reply(captured: dict, reason: str, reply: str) -> dict:
    """Send the capture to handoff while preserving its customer-facing reply."""
    return {**_derive(captured, reason), "replies": [reply]}


def _derive(captured: dict, reason: str) -> dict:
    """Send the capture to the handoff node with a reason (S14/S15)."""
    return {
        "captured": captured,
        "next_step": "handoff",
        "escalate": True,
        "escalate_reason": reason,
    }


def _ask_batch(missing: list[str], max_preguntas: int) -> list[str]:
    """Leading missing fields for this message (S14).

    Diagnostic fields go one at a time — a fault is what the customer has to
    describe first — and the booking data follows `chat.conduct`
    (`max_preguntas_por_mensaje`, 1 or 2).
    """
    limit = 1 if missing[0] in _DIAGNOSIS_FIELDS else max_preguntas
    return missing[:limit]


def _exhausted(captured: dict, batch: list[str]) -> bool:
    """True when a field of the batch was already asked the maximum times (S14)."""
    asked = captured.get("_asked") or {}
    return any(asked.get(field, 0) >= MAX_ASKS_PER_FIELD for field in batch)


def _ask_next(captured: dict, state: ConversationState, *, clear_paused: bool = False) -> dict:
    """Ask the next missing fields, or the consent step when none remain."""
    with session_scope() as session:
        conduct = get_conduct(session)
        if _out_of_coverage(
            captured, get_coverage_communes(session), conduct["derivaciones"]
        ):
            # S15: an out-of-coverage comuna is not rejected; an advisor takes it.
            captured.pop("_pending", None)
            _persist_captured(session, state, captured)
            return _derive(captured, COVERAGE_DERIVATION)
        preventive = {
            _normalize(keyword)
            for keyword in get_capture_preventive_keywords(session)
            if _normalize(keyword)
        }
        current = _normalize(_current_text(state))
        if "failure" not in captured and any(word in current for word in preventive):
            skipped = list(captured.get("_skipped") or [])
            if "failure" not in skipped:
                skipped.append("failure")
            captured["_skipped"] = skipped

        missing = _missing_fields(captured, conduct["orden"])
        if not missing:
            if _answer_consent(captured.get("consent", "")) is True:
                _persist_captured(session, state, captured)
                return {"captured": captured, "next_step": "booking"}
            captured["_pending"] = "consent"
            asked = dict(captured.get("_asked") or {})
            asked["consent"] = asked.get("consent", 0) + 1
            captured["_asked"] = asked
            _persist_captured(session, state, captured)
            consent = render_reply(get_reply_texts(session), "capture_consent")
            return {"captured": captured, "replies": [consent]}

        first_personal = next(
            (field for field in conduct["orden"] if field in {"email", "address"} and field not in captured),
            None,
        )
        batch = _ask_batch(missing, conduct["max_preguntas_por_mensaje"])
        if first_personal in batch and "consent" not in captured:
            captured["_pending"] = "consent"
            asked = dict(captured.get("_asked") or {})
            asked["consent"] = asked.get("consent", 0) + 1
            captured["_asked"] = asked
            _persist_captured(session, state, captured)
            consent = render_reply(get_reply_texts(session), "capture_consent")
            return {"captured": captured, "replies": [consent]}
        if _exhausted(captured, batch):
            # S14: asked twice without an answer — offer a derivation instead of
            # a third identical question. The handoff node owns the reply and
            # the takeover; `_after_capture` routes there.
            captured.pop("_pending", None)
            _persist_captured(session, state, captured)
            return _derive(captured, "campo_sin_respuesta")

        captured["_pending"] = batch
        asked = dict(captured.get("_asked") or {})
        for field in batch:
            asked[field] = asked.get(field, 0) + 1
        captured["_asked"] = asked
        texts = get_reply_texts(session)
        ack = _render_capture_ack(session, captured)
        ask = _ask_text(batch, _field_questions(session))
        if ack:
            ask = f"{ack}{ask}"
        label = _EQUIPMENT_LABELS.get(captured.get("equipment_type") or "")
        if batch == ["failure"] and label:
            ask = f"Entiendo, es un problema con tu {label}. {ask}"
        if len(missing) <= len(batch) and not captured.get("_evidence_asked"):
            ask = f"{ask} {render_reply(texts, 'capture_evidence')}"
            captured["_evidence_asked"] = True
        _persist_captured(session, state, captured)
    updates: dict = {"captured": captured, "replies": [ask]}
    if clear_paused:
        updates["capture_paused"] = False
    return updates
