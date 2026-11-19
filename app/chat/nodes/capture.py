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
from datetime import date, datetime, timedelta, timezone

from app.chat.nodes.handoff_gate import is_media_evidence
from app.chat.phrasing import facts as phrase_facts
from app.chat.phrasing import phrase
from app.chat.nodes.replies import render_reply
from app.chat.state import ConversationState
from app.chat.slot_window import resolve_window
from app.chat.service_catalogue import (
    _PREVENTIVE_CATALOGUE_WORDS,
    _matches_catalogue_phrase,
    _normalize,
    _preventive_services,
)
from app.db import session_scope
from app.models import Conversation, Customer
from app.services.address_validation import validate_address
from app.services.cases import is_emergency_case
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
    get_capture_quote_keywords,
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
    "no te voy a dar mi correo",
    "desconozco",
)

# S6: an explicit refusal names the datum it refuses. The generic skip above
# marks the field the bot just asked, which is wrong when the customer answers a
# different question out of turn: the email stayed pending and was asked again
# later (measured on `complejo-no-quiere-email`, capture order vs. script).
_REFUSAL_FIELDS: tuple[tuple[str, str], ...] = (
    ("no te voy a dar mi correo", "email"),
)
_YES_WORDS = (
    "si", "sí", "yes", "ok", "oka", "claro", "dale",
)
# S7 (chatbot-realismo-conversacional): the explicit first-person verbs are what a
# customer says when they decide. They are accepted inside a short sentence, which
# is what production #23 never got. The bare affirmatives above are accepted only
# when the whole message is just that, because a false positive here writes
# personal data without consent — the risk runs one way, so the rule is
# asymmetric on purpose.
_CONSENT_VERBS = ("autorizo", "autorizar", "consiento", "acepto", "confirmo")
# An explicit refusal phrase is a decision, not confusion: matching only the
# bare "no" made "no autorizo" fall into the unclear path and the customer
# was asked again (replay T9, conversation #26).
_NO_WORDS = (
    "no", "nope", "negativo", "no autorizo", "no quiero", "no acepto",
    "prefiero no", "no gracias",
)

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


def is_social_only(text: str) -> bool:
    """True when the whole message is a greeting or a social question."""
    return _normalize(text) in _SOCIAL_ONLY


def is_skip(text: str) -> bool:
    return any(word in text.lower() for word in _SKIP_WORDS)


def refused_field(text: str) -> str | None:
    """The capture field an explicit refusal names, if it names one (S6)."""
    normalized = _normalize(text)
    if not normalized:
        return None
    for phrase, field in _REFUSAL_FIELDS:
        if _normalize(phrase) in normalized:
            return field
    return None


def _answer_consent(value: str) -> bool | None:
    """Resolve a consent answer; a negation, a doubt or a question is never consent.

    S7: production asked again after "no se que marca es realmente el calefont. si
    autorizo" because only an exact allowlisted word counted. The old exact match
    was safe but deaf; this keeps the safety (nothing is inferred from prose) and
    adds the two shapes a real customer uses: an explicit consent verb inside a
    short sentence, and a bare affirmative that is the whole message.
    """
    normalized = _normalize(value)
    if not normalized:
        return None
    if normalized in {_normalize(word) for word in _NO_WORDS}:
        return False
    if len(normalized) > 120 or len(normalized.split()) > 20:
        return None
    if re.search(r"\bno\s+(?:autorizo|autorizar|acepto|consiento|doy)\b", normalized):
        return False
    # Thinking out loud is not deciding, and a question is never an answer.
    if re.search(r"\bno\s+se\s+si\b", normalized) or _looks_like_question(value):
        return None
    verbs = "|".join(re.escape(_normalize(word)) for word in _CONSENT_VERBS)
    if re.search(rf"\b(?:{verbs})\b", normalized):
        return True
    bare = {_normalize(word) for word in _YES_WORDS}
    if len(normalized.split()) <= 3 and any(word in bare for word in normalized.split()):
        return True
    return None


def _current_text(state: ConversationState) -> str:
    return (state.window[-1].get("text") or "") if state.window else ""


def _persist_captured(session, state: ConversationState, captured: dict) -> None:
    conv = session.get(Conversation, state.conversation_id)
    if conv is not None:
        conv.captured_data = captured
    # S1 canvas: consent is asked BEFORE email/address, so a single ficha write at
    # the consent step would leave the customer record missing every field captured
    # after it (CI functional flows caught exactly that). The sync is idempotent.
    # S3: a consent already on record enables the same write, otherwise skipping the
    # question would book a visit and drop the address the customer just gave.
    if (
        _answer_consent(captured.get("consent", "")) is True
        or captured.get("_consent_previously_granted")
    ):
        _sync_customer_fields(session, state, captured)


def _sync_customer_fields(session, state: ConversationState, captured: dict) -> None:
    """CR-6: write captured identification/location on the ficha (idempotent)."""
    customer = session.get(Customer, state.customer_id)
    if customer is None:
        return
    clean = {k: v for k, v in captured.items() if v not in ("unknown", None)}
    prior_address = customer.address
    update_captured_data(
        session,
        customer,
        name=clean.get("name"),
        email=clean.get("email"),
        comuna=clean.get("comuna"),
        address=(
            clean.get("address")
            if clean.get("direccion_estado") in {
                "validada", "sin_numeracion", "dudosa", "no_encontrada",
                "sin_referencia", "cliente",
            }
            else None
        ),
    )
    if clean.get("direccion_estado"):
        changed_outcome = (
            prior_address != clean.get("address")
            or customer.direccion_estado != clean["direccion_estado"]
            or customer.direccion_fuente != clean["direccion_fuente"]
            or customer.direccion_validada_at is None
        )
        customer.direccion_estado = clean["direccion_estado"]
        customer.direccion_fuente = clean["direccion_fuente"]
        if changed_outcome:
            customer.direccion_validada_at = datetime.now(timezone.utc)
    promote_captured_equipment(session, customer, state.conversation_id, clean)


def _apply_consent_and_customer(session, state: ConversationState, captured: dict) -> None:
    """CR-6: write the ficha and record the consent decision once."""
    _sync_customer_fields(session, state, captured)
    customer = session.get(Customer, state.customer_id)
    if customer is None:
        return
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

    S1 (chatbot-realismo-conversacional): it also thanks for something only once
    something has been asked. Production turn 285 opened the capture with
    "Gracias Stefan. Stefan, cuéntame qué pasa con la caldera…" — the customer had
    given nothing yet, and the name arrived twice in one message. The trigger is a
    fact the flow already tracks: a field is on record as asked.
    """
    if not captured.get("_asked"):
        return ""
    text = get_capture_ack(session)
    facts = {
        "nombre": captured.get("name"),
        "comuna": captured.get("comuna"),
        "equipo": captured.get("equipment") or captured.get("equipment_type"),
        "problema": captured.get("failure"),
        "disponibilidad": captured.get("availability"),
    }
    available = {key: value for key, value in facts.items() if isinstance(value, str) and value and value != "unknown"}
    declared = set(re.findall(r"{{\s*(\w+)\s*}}", text))
    # S1: a text with no placeholders is renderable on its own ("Entiendo. ").
    # Requiring an interpolated fact made "Gracias {{nombre}}. " the only shape the
    # acknowledgement could ever take, so the shipped default could not be a plain
    # phrase until this guard stopped demanding a fact.
    if declared and not declared <= set(available):
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


_INTERROGATIVES = (
    "que ", "qué ", "cuanto", "cuánto", "como ", "cómo ", "cual", "cuál",
    "donde", "dónde", "cuando", "cuándo", "por que", "por qué", "quien", "quién",
)


def _looks_like_question(text: str) -> bool:
    """True for a question, which is never a preventive request."""
    stripped = (text or "").strip()
    if "?" in stripped:
        return True
    return _normalize(stripped).startswith(tuple(_normalize(word) for word in _INTERROGATIVES))


# Shared catalogue matcher; capture keeps its local request guards and explicit
# `capture.preventive_keywords` override below.
def _is_preventive_request(session, text: str, overrides: list[str]) -> bool:
    normalized = _normalize(text)
    if re.search(r"\bno\s+(?:quiero|necesito|busco|solicito)\b", normalized):
        return False
    if any(_normalize(keyword) in normalized for keyword in overrides):
        return True
    return any(
        _matches_catalogue_phrase(text, service)
        for service in _preventive_services(session)
    )


def _is_quote_request(text: str, overrides: list[str]) -> bool:
    """True when the customer declares they want an evaluation or a quote.

    A refusal is not a request ("no necesito cotización"), and questions never
    reach here: the caller drops them, because "¿cuánto cuesta la evaluación?"
    is a price question answered by `respond` (S2).
    """
    normalized = _normalize(text)
    if re.search(r"\bno\s+(?:quiero|necesito|busco|solicito)\b", normalized):
        return False
    # "No tengo presupuesto ahora" declares the absence of one, so acknowledging
    # a quote request would tell the customer the opposite of what they said.
    if re.search(r"\b(?:no|sin)\s+(?:tengo|tener|tenemos|hay)\s+(?:presupuesto|plata|lucas)", normalized):
        return False
    return any(_normalize(keyword) in normalized for keyword in overrides)


def _phrase_reply(session, texts: dict[str, str], key: str, captured: dict, *, pending) -> str:
    """Render one capture reply and optionally rephrase it (S5).

    At most one model call per message: the acknowledgement and the evidence
    hint travel inside the same message as the question, so they stay in the
    template. Phrasing each fragment separately tripled the per-turn cost
    without changing a word the customer reads.
    """
    return phrase(
        session, key, render_reply(texts, key),
        facts=_offered_facts(captured, pending), pending=pending,
    )


def _offered_facts(captured: dict, pending) -> dict:
    """The facts the rewrite may name, marking them as used (S1, agenda-horarios).

    `phrasing.facts` stays pure: it decides WHICH one fact is still fresh. The
    node remembers it here, on the captured payload it is already rewriting, so
    the next question cannot name it again.
    """
    offered = phrase_facts(captured, pending)
    named = [key for key in offered if key != "pending"]
    if named:
        used = [str(key) for key in (captured.get("_facts_used") or ())]
        captured["_facts_used"] = used + [key for key in named if key not in used]
    return offered


def _phrase_question(session, captured: dict, fields: list[str], questions: dict[str, str]) -> str:
    """Render the ask for `fields`, optionally rephrased; the batch is the machine's."""
    rendered = _ask_text(fields, questions)
    return phrase(
        session, "capture_question", rendered,
        facts=_offered_facts(captured, fields), pending=fields,
    )


def _looks_like_prose(text: str) -> bool:
    """True for a long or multi-sentence turn, the shape corruption imitates."""
    stripped = (text or "").strip()
    if len(stripped) > 80:
        return True
    return len(re.findall(r"[.!?](?:\s|$)", stripped)) >= 2


def _merge_extracted(
    captured: dict, extracted: dict | None, pending: list[str], state: ConversationState,
    communes: list[str],
) -> None:
    """Merge any validated extracted value, even when another field was asked."""
    prior_texts = {
        item.get("text") for item in state.window[:-1]
        if item.get("direction", "inbound") == "inbound" and item.get("text")
    }
    current_text = _current_text(state)
    current_pending = captured.get("_pending") or []
    if isinstance(current_pending, str):
        current_pending = [current_pending]
    skipped = set(captured.get("_skipped") or [])
    for field, value in (extracted or {}).items():
        if field not in EXTRACTABLE_FIELDS or not isinstance(value, str):
            continue
        if field in skipped:
            # The preventive decision outranks the extractor: a maintenance request
            # must not be recorded as the fault it was explicitly not.
            continue
        value = value.strip()
        if not value or captured.get(field):
            continue
        # No field may echo a PROSE turn: a multi-sentence message copied into a
        # field is extraction corruption ("Soy Braulio, me dieron este numero...").
        # A terse answer legitimately equals the whole message ("tengo un calefont
        # que no calienta" fills `failure`), and rejecting those starved the flow —
        # CI functional flows asked the same question twice and then derived.
        if (
            _looks_like_prose(current_text)
            and _normalize(value) == _normalize(current_text)
        ):
            continue
        if field == "comuna":
            # Coverage is decided by `_out_of_coverage`, never here: dropping an
            # out-of-coverage commune made that rule unreachable, so the bot
            # re-asked instead of deriving `handoff:cobertura` (S15 regression).
            captured[field] = value
        elif field == "email":
            if re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", value):
                captured[field] = value
        elif field == "name":
            # A refusal is not a name ("no autorizo" answered the name question in
            # the replay). `is_skip` alone misses it: its words are matched
            # anywhere, so a negation prefix is the narrower guard here — adding
            # "no " to `is_skip` would turn "no enciende" into a skipped answer
            # for the failure field.
            if (
                len(value) <= 80
                and len(value.split()) <= 4  # a name is a name, not a sentence
                and "?" not in value
                and not is_skip(value)
                and not _normalize(value).startswith("no ")
                and all(char.isalpha() or char.isspace() for char in value)
            ):
                captured[field] = value
        elif field in {"failure", "address"}:
            repeated_pending_address = (
                field == "address"
                and field in current_pending
                and _normalize(value) == _normalize(current_text)
            )
            if value not in prior_texts or repeated_pending_address:
                captured[field] = value
        else:
            captured[field] = value


def _validate_address_candidate(captured: dict, state: ConversationState) -> dict | None:
    """Validate a newly captured address, deferring only until comuna is known."""
    candidate = captured.get("address")
    candidate_is_new = not state.captured.get("address")
    candidate_was_deferred = bool(captured.get("_address_pending_validation"))
    if (
        not isinstance(candidate, str)
        or not candidate
        or not (candidate_is_new or candidate_was_deferred)
    ):
        return None
    if captured.get("comuna") in (None, "", "unknown"):
        # An out-of-order extraction can precede the commune. Keep it only as a
        # conversation candidate (never a ficha address), then validate it once
        # the customer has supplied the commune.
        captured["_address_pending_validation"] = True
        return None

    captured.pop("_address_pending_validation", None)
    outcome = validate_address(candidate, captured["comuna"])
    if outcome.state in {"validada", "sin_numeracion"}:
        captured["direccion_estado"] = outcome.state
        captured["direccion_fuente"] = "callejero"
        return None
    if (
        outcome.state == "sin_referencia"
        and (captured.get("_asked") or {}).get("address", 0) < MAX_ASKS_PER_FIELD
    ):
        # The master cannot speak for this commune. Persist that uncertainty
        # without treating the typed address as trusted or replacing an older
        # address; the customer still gets the normal reformulation.
        captured.pop("address", None)
        # The master had no reference for this candidate, so it cannot change the
        # outcome attached to a different address already stored on the ficha.
        with session_scope() as session:
            customer = session.get(Customer, state.customer_id)
            stored_address = customer.address if customer is not None else None
            stored_comuna = customer.comuna if customer is not None else None
        if stored_address and (
            stored_address != candidate or stored_comuna != captured.get("comuna")
        ):
            captured.pop("direccion_estado", None)
            captured.pop("direccion_fuente", None)
        else:
            captured["direccion_estado"] = "sin_referencia"
            captured["direccion_fuente"] = "cliente"
        captured["_pending"] = ["address"]
        return _reask_pending(captured, ["address"], state)
    if (captured.get("_asked") or {}).get("address", 0) >= MAX_ASKS_PER_FIELD:
        # After the pin offer the customer's own description wins. It is a
        # deliberate, persisted fallback rather than a hard rejection.
        captured["direccion_estado"] = "cliente"
        captured["direccion_fuente"] = "cliente"
        return None

    captured.pop("address", None)
    captured.pop("direccion_estado", None)
    captured.pop("direccion_fuente", None)
    captured["_pending"] = ["address"]
    return _reask_pending(captured, ["address"], state)


def capture(state: ConversationState) -> dict:
    """Merge this turn's extraction and ask the next missing fields (CI-3b)."""
    captured = dict(state.captured)
    with session_scope() as session:
        if is_emergency_case(session, state.conversation_id):
            # The emergency node already delivered the safety protocol. On a later
            # capture turn, reuse the normal handoff route; never resume the form.
            return _derive(captured, "emergency")
    if state.intent in {"calefont", "caldera", "calefaccion"}:
        # V4 §E1 T07: a new fault replaces the equipment context instead of
        # leaving the earlier appliance frozen in the record.
        captured["equipment_type"] = state.intent
    message = state.window[-1] if state.window else None
    if is_media_evidence(message):
        return _ask_next(captured, state)
    # A QUESTION is not a request: "¿cuánto cuesta la revisión anual?" is a price
    # question, not a maintenance order, and reading the keyword out of it
    # silently marked `failure` as skipped (S14/S16 integration tests). Both
    # declarations below read only the non-question inbound text.
    declared = " ".join(
        item.get("text") or ""
        for item in state.window
        if item.get("direction", "inbound") == "inbound"
        and not _looks_like_question(item.get("text") or "")
    )
    normalized_window = _normalize(declared)
    # S4: evaluate the preventive intent once against the entire inbound window,
    # before any path can ask or re-ask the failure field.
    if "failure" not in captured:
        with session_scope() as session:
            preventive_keywords = get_capture_preventive_keywords(session)
            is_preventive = _is_preventive_request(
                session, normalized_window, preventive_keywords
            )
        if is_preventive:
            captured["_preventive_request"] = True
            skipped = list(captured.get("_skipped") or [])
            if "failure" not in skipped:
                skipped.append("failure")
            captured["_skipped"] = skipped
    # Residual 8 of #833: evaluated OUTSIDE the `failure` guard above, because a
    # customer who declares "una nueva evaluación y cotización" and then reports
    # the symptom still wants the evaluation — dropping it there would be wrong
    # (S4).
    with session_scope() as session:
        quote_keywords = get_capture_quote_keywords(session)
        is_quote = _is_quote_request(normalized_window, quote_keywords)
    if is_quote:
        captured["_quote_request"] = True
    # Extraction is merged on EVERY turn, including the first one, which is where
    # the customer states the problem ("tengo un calefont que no calienta" fills
    # `failure` and the next question is the equipment). Validators decide what is
    # accepted; the merge no longer waits for an "answer turn".
    with session_scope() as session:
        _merge_extracted(
            captured, state.extracted, [], state, get_coverage_communes(session)
        )
    if "failure" in captured:
        captured.pop("_preventive_request", None)
    pending = captured.get("_pending")
    if pending == "confirm_contact":
        return _answer_contact_confirmation(captured, state)
    refused = refused_field(_current_text(state))
    if refused is not None and refused not in captured:
        # S6: honour the refusal for the field it names, then keep the capture
        # going. The turn is not an answer to whatever field was pending, so it is
        # not consumed as one; the flow resumes with the next ask.
        captured[refused] = "unknown"
        skipped = list(captured.get("_skipped") or [])
        if refused not in skipped:
            skipped.append(refused)
        captured["_skipped"] = skipped
        if not state.extracted:
            captured.pop("_pending", None)
            return _ask_next(captured, state)
    if isinstance(pending, str) and pending != "consent":
        # A stored one-field batch can arrive as a bare string ("name"); it means
        # the batch of that field, not its letters. Iterating it character by
        # character asked for fields called "n" and re-asked forever (the ingest
        # ack test caught it as an unmocked LLM call).
        pending = [pending]

    # Validate classifier-extracted candidates now. Terse pending-field answers
    # are merged below and pass through the same gate there.
    address_result = _validate_address_candidate(captured, state)
    if address_result is not None:
        return address_result

    if isinstance(pending, list) and "failure" in (captured.get("_skipped") or []):
        pending = [field for field in pending if field != "failure"]
        if pending:
            captured["_pending"] = pending
        else:
            captured.pop("_pending", None)
            return _ask_next(captured, state)

    if pending == "consent":
        # CI-3: the explicit consent step runs AFTER every data field, before
        # booking. A deviation on this step re-asks it instead of answering it.
        if state.capture_paused:
            with session_scope() as session:
                consent = _phrase_reply(session, get_reply_texts(session), "capture_consent", captured, pending=["consent"])
            return {"capture_paused": False, "replies": [consent]}
        answer = _current_text(state)
        consent = _answer_consent(answer)
        if consent is True:
            captured["consent"] = answer
            captured.pop("_pending", None)
            with session_scope() as session:
                _apply_consent_and_customer(session, state, captured)
                _persist_captured(session, state, captured)
            # Consent is the last step: the data is complete, so the flow goes
            # straight to booking. Routing through `_ask_next` re-ran the coverage
            # check and derived for a commune that was already accepted.
            return {"captured": captured, "next_step": "booking"}
        if consent is False:
            captured.pop("email", None)
            captured.pop("address", None)
            captured["consent"] = "no"
            captured.pop("_pending", None)
            with session_scope() as session:
                texts = get_reply_texts(session)
                _persist_captured(session, state, captured)
                reply = _phrase_reply(session, texts, "capture_consent_refused", captured, pending=["consent"])
            return _derive_with_reply(captured, "consent_declined", reply)
        with session_scope() as session:
            texts = get_reply_texts(session)
            asked = dict(captured.get("_asked") or {})
            if asked.get("consent", 0) == 0 and "consent" not in captured:
                captured["consent"] = "unknown"
            if asked.get("consent", 0) >= MAX_ASKS_PER_FIELD:
                captured.pop("_pending", None)
                _persist_captured(session, state, captured)
                reply = _phrase_reply(session, texts, "capture_consent_unclear", captured, pending=["consent"])
                return _derive_with_reply(captured, "consent_unclear", reply)
            asked["consent"] = asked.get("consent", 0) + 1
            captured["_asked"] = asked
            captured["_pending"] = "consent"
            _persist_captured(session, state, captured)
            reply = _phrase_reply(session, texts, "capture_consent_unclear", captured, pending=["consent"])
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

    # Skip answers retain the explicit unknown sentinel.
    if pending and not any(field in captured for field in pending):
        answer = _current_text(state)
        if is_skip(answer):
            target = pending[0]
            if target not in captured:
                captured[target] = "unknown"
        elif (
            not state.extracted
            and not _looks_like_prose(answer)
            and not _looks_like_question(answer)
        ):
            # S2: a TERSE answer that the extractor missed belongs to the field we
            # just asked — the customer answered, the model simply did not label it
            # ("Ñuñoa", "Juan Perez"). It goes back through the same per-field
            # validators, so a commune outside coverage or a refusal still fails;
            # only PROSE is refused outright, which is where the corruption came
            # from ("Soy Braulio, me dieron este numero...").
            with session_scope() as session:
                _merge_extracted(
                    captured, {pending[0]: answer}, [], state,
                    get_coverage_communes(session),
                )
            if pending[0] not in captured:
                return _reask_pending(captured, pending, state)
            if pending[0] == "address":
                address_result = _validate_address_candidate(captured, state)
                if address_result is not None:
                    return address_result
        else:
            return _reask_pending(captured, pending, state)

    captured.pop("_pending", None)
    return _ask_next(captured, state)


def _address_reask_question(question: str, *, offer_pin: bool) -> str:
    """Reuse the configured address ask, adding the WhatsApp pin offer on retry."""
    if not offer_pin:
        return question
    return (
        question.rstrip().removesuffix("?")
        + " o, si te es más fácil, puedes enviarme tu ubicación con el pin de WhatsApp?"
    )


def _reask_pending(captured: dict, pending: list[str], state: ConversationState) -> dict:
    """Repeat the unanswered batch once, then offer its existing derivation."""
    with session_scope() as session:
        conduct = get_conduct(session)
        if _out_of_coverage(
            captured, get_coverage_communes(session), conduct["derivaciones"]
        ):
            # S5/T5a: the coverage rule outranks an exhausted pending field. It used
            # to live only in `_ask_next`, which this path never reaches, so a
            # customer outside coverage whose last field went unanswered was
            # derived as `campo_sin_respuesta` -- the measured behaviour on
            # `super-burst-contradiccion`, with `comuna: Providencia` captured.
            captured.pop("_pending", None)
            _persist_captured(session, state, captured)
            return _derive(captured, COVERAGE_DERIVATION)
    asked = dict(captured.get("_asked") or {})
    if any(asked.get(field, 0) >= MAX_ASKS_PER_FIELD for field in pending):
        captured.pop("_pending", None)
        return _derive(captured, "campo_sin_respuesta")

    for field in pending:
        asked[field] = asked.get(field, 0) + 1
    captured["_asked"] = asked
    captured["_pending"] = pending
    with session_scope() as session:
        ask = _render_capture_question(
            session, captured, pending, state.extracted,
            current_text=_current_text(state),
        )
        if pending == ["address"]:
            ask = _address_reask_question(
                ask, offer_pin=asked.get("address", 0) >= MAX_ASKS_PER_FIELD
            )
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


def _render_capture_question(
    session,
    captured: dict,
    batch: list[str],
    just_extracted: dict | None = None,
    *,
    current_text: str = "",
) -> str:
    """The customer-facing question for a batch of fields.

    One renderer for both ask paths. They used to render separately, and the copy
    in `_reask_pending` was missing the equipment label, so a customer who
    corrected "no era calefont, es una caldera" was asked a generic question and
    no reply ever said "caldera" (T5b, gate G6 on `super-burst-contradiccion`).

    Ack priority is the existing preventive acknowledgement, then S3's just-
    delivered availability acknowledgement, S5's later hold clause, the existing
    quote acknowledgement, and finally the base acknowledgement.
    """
    ask = _phrase_question(session, captured, batch, _field_questions(session))
    label = _EQUIPMENT_LABELS.get(captured.get("equipment_type") or "")
    if batch == ["failure"] and label and label.casefold() not in ask.casefold():
        # T5b: the rewritten question can already name the equipment (as in the
        # measured reply), so adding its label beside the configured ack repeats
        # both the greeting and the appliance. Use one equipment-aware ack here.
        equipment_ack = f"Entiendo, es un problema con tu {label}. "
        if equipment_ack.strip() == (captured.get("_acked") or "").strip():
            ack = ""
        else:
            captured["_acked"] = equipment_ack.strip()
            ack = equipment_ack
    else:
        ack = _render_capture_ack(session, captured)
    preventive_ack = ""
    if captured.get("_preventive_request"):
        equipment = captured.get("equipment")
        if not isinstance(equipment, str) or not equipment.strip() or equipment == "unknown":
            equipment = "tu equipo"
        preventive_ack = render_reply(
            get_reply_texts(session),
            "capture_preventive_ack",
            equipo=label or equipment,
        )
        if preventive_ack.strip() == (captured.get("_preventive_acked") or "").strip():
            preventive_ack = ""
        else:
            captured["_preventive_acked"] = preventive_ack.strip()
    # Residual 8 of #833: the evaluation/quote request is named once too, in the
    # turn the preventive acknowledgement leaves free — it keeps the turn it
    # already had, and this one waits instead of overwriting it. The marker is
    # written only when the text actually reaches the customer: marking it while
    # the preventive ack holds the turn swallowed the sentence (measured on
    # conversation 299 of the `captura-eval` run).
    availability_ack = ""
    # S3 (agenda-respeta-horario): only the turn that delivered the constraint
    # names it back. `just_extracted` is this turn's extraction, so an older
    # availability never turns a re-ask into a tic.
    delivered = (just_extracted or {}).get("availability")
    if isinstance(delivered, str) and delivered.strip():
        candidate = render_reply(
            get_reply_texts(session),
            "capture_availability_ack",
            disponibilidad=captured.get("availability") or delivered.strip(),
        )
        if candidate.strip() != (captured.get("_availability_acked") or "").strip():
            availability_ack = candidate
    availability_hold_ack = ""
    availability = captured.get("availability")
    if (
        isinstance(availability, str)
        and availability.strip()
        and availability != "unknown"
        and not (isinstance(delivered, str) and delivered.strip())
        and resolve_window(current_text, today=date.today()) is not None
    ):
        availability_hold_ack = render_reply(
            get_reply_texts(session),
            "capture_availability_hold",
            disponibilidad=availability.strip(),
        )
    quote_ack = ""
    if captured.get("_quote_request"):
        candidate = render_reply(get_reply_texts(session), "capture_quote_ack")
        if candidate.strip() != (captured.get("_quote_acked") or "").strip():
            quote_ack = candidate
    ack = _pick_ack(
        captured, ack, preventive_ack, quote_ack,
        availability_ack=availability_ack,
        availability_hold_ack=availability_hold_ack,
    )
    return f"{ack}{ask}"


def _pick_ack(
    captured: dict,
    base_ack: str,
    preventive_ack: str,
    quote_ack: str,
    *,
    availability_ack: str = "",
    availability_hold_ack: str = "",
) -> str:
    """Which acknowledgement speaks, and what the customer actually receives.

    `base_ack` is the turn's own acknowledgement — the equipment acknowledgement or
    the configured `capture_ack` — and it is the fallback: passing only the two
    optional ones dropped every "Entiendo…" from the capture replies, which the
    full suite caught and the narrowed runs did not.

    The preventive ack keeps the turn it already had and the evaluation/quote one
    waits for the next. S3's acknowledgement wins over S5's hold clause so the
    freshly delivered preference is not repeated; the hold clause in turn wins
    over the generic base ack. Markers are written only for text returned to the
    customer.
    """
    if preventive_ack:
        return preventive_ack
    if availability_ack:
        # The customer just told us when they are reachable: naming it beats a
        # generic "Entiendo." when only one acknowledgement fits the turn.
        captured["_availability_acked"] = availability_ack.strip()
        return availability_ack
    if availability_hold_ack:
        return availability_hold_ack
    if not quote_ack:
        return base_ack
    captured["_quote_acked"] = quote_ack.strip()
    return quote_ack


# S3: the three fields a returning customer should not have to retype. `name` is
# deliberately absent: the greeting already used it, and a wrong name is cheaper to
# carry than a wrong address.
_STORED_CONTACT_FIELDS = ("comuna", "email", "address")
# One year, the owner's decision: an annual maintenance customer should not repeat
# their address, and `customers` has no `updated_at`, so the only timestamp to age
# against is the ficha's creation. The failure direction is deliberately
# conservative: an older record falls back to asking.
_STORED_CONTACT_MAX_AGE = timedelta(days=365)


def _stored_contact(session, state: ConversationState) -> dict[str, str]:
    """S3: contact data the customer already gave, while it is still trusted."""
    customer = session.get(Customer, state.customer_id)
    if customer is None:
        return {}
    created_at = getattr(customer, "created_at", None)
    if created_at is not None:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created_at > _STORED_CONTACT_MAX_AGE:
            return {}
    values = {field: getattr(customer, field, None) for field in _STORED_CONTACT_FIELDS}
    stored = {
        field: value.strip()
        for field, value in values.items()
        if isinstance(value, str) and value.strip()
    }
    # The confirmation sentence names all three, so a partial record asks normally
    # instead of reading "Tengo tu comuna y …, con correo tu correo".
    return stored if len(stored) == len(_STORED_CONTACT_FIELDS) else {}


def _offer_stored_contact(session, state: ConversationState, captured: dict) -> str | None:
    """Seed the captured contact from the ficha and ask for one confirmation (S3)."""
    stored = _stored_contact(session, state)
    if not stored or any(captured.get(field) for field in _STORED_CONTACT_FIELDS):
        return None
    captured.update(stored)
    captured["_seeded_contact"] = list(_STORED_CONTACT_FIELDS)
    captured["_contact_offered"] = True
    captured["_pending"] = "confirm_contact"
    return render_reply(
        get_reply_texts(session),
        "capture_confirm_contact",
        comuna=captured["comuna"],
        direccion=captured["address"],
        email=captured["email"],
    )


def _is_affirmative(text: str) -> bool:
    """A short yes for a confirmation; the same asymmetry consent uses."""
    normalized = _normalize(text)
    if not normalized or _looks_like_question(text):
        return False
    if re.search(r"\bno\b", normalized) and not re.search(
        r"\bno\s+(?:cambio|cambió|nada)\b", normalized
    ):
        return False
    bare = {_normalize(word) for word in _YES_WORDS}
    return any(word in bare for word in normalized.split())


def _answer_contact_confirmation(captured: dict, state: ConversationState) -> dict:
    """Handle the single confirmation: keep the seeded values, or drop what changed."""
    seeded = list(captured.pop("_seeded_contact", []) or [])
    captured.pop("_pending", None)
    if not _is_affirmative(_current_text(state)):
        # A correction, not an approval: whatever the extractor read this turn stays,
        # everything else the customer did not confirm is asked again.
        for field in seeded:
            if not state.extracted.get(field):
                captured.pop(field, None)
    return _ask_next(captured, state)


def _customer_already_consented(session, state: ConversationState) -> bool:
    """S3: consent is a property of the customer, not of the conversation.

    Production #23 turn 301 asked a customer whose consent had been recorded on
    2026-10-27: the flow only ever looked at `captured["consent"]`, so every new
    conversation started the consent step from zero. The ficha is the source.
    """
    customer = session.get(Customer, state.customer_id)
    return bool(customer is not None and customer.consent_status)


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
        missing = _missing_fields(captured, conduct["orden"])
        contact_missing = [
            field for field in missing if field in _STORED_CONTACT_FIELDS
        ]
        if (
            contact_missing
            and len(contact_missing) == len(missing)
            and not captured.get("_contact_offered")
        ):
            offer = _offer_stored_contact(session, state, captured)
            if offer is not None:
                _persist_captured(session, state, captured)
                return {"captured": captured, "replies": [offer]}
        if not missing:
            if _answer_consent(captured.get("consent", "")) is True:
                _persist_captured(session, state, captured)
                return {"captured": captured, "next_step": "booking"}
            if _customer_already_consented(session, state):
                # S3: silent skip, decided by the owner. The marker keeps the trace
                # honest for the panel: nobody asked in this conversation.
                captured.pop("_pending", None)
                captured["_consent_previously_granted"] = True
                _persist_captured(session, state, captured)
                return {"captured": captured, "next_step": "booking"}
            captured["_pending"] = "consent"
            asked = dict(captured.get("_asked") or {})
            asked["consent"] = asked.get("consent", 0) + 1
            captured["_asked"] = asked
            _persist_captured(session, state, captured)
            consent = _phrase_reply(session, get_reply_texts(session), "capture_consent", captured, pending=["consent"])
            return {"captured": captured, "replies": [consent]}

        batch = _ask_batch(missing, conduct["max_preguntas_por_mensaje"])
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
        ask = _render_capture_question(
            session, captured, batch, state.extracted,
            current_text=_current_text(state),
        )
        _persist_captured(session, state, captured)
    updates: dict = {"captured": captured, "replies": [ask]}
    if clear_paused:
        updates["capture_paused"] = False
    return updates
