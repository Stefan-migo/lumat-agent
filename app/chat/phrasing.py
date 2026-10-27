"""Hard-gated optional rewriting of the fixed capture reply catalog."""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from app.services import llm
from app.services.settings import get_conduct

logger = logging.getLogger(__name__)

PHRASEABLE_KEYS = frozenset({
    "capture_consent", "capture_consent_refused", "capture_consent_unclear",
    "capture_question",
})
_MAX_CHARS = 240
# Only the contact fields are guarded against being pulled forward before their
# turn. Every other field may appear as an already-captured fact inside the
# sentence ("tu caldera no enciende", "para coordinar la visita"), which is the
# whole point of the rewrite; a keyword table over all fields rejected exactly
# those sentences and made the feature dead code that still paid a model call.
_FORWARD_GUARDED = {
    "email": ("correo", "email"),
    "address": ("direccion", "domicilio", "calle"),
}


def facts(captured: dict[str, Any] | None = None, pending: Any = ()) -> dict[str, Any]:
    """Return only safe known capture facts plus the fields currently asked."""
    captured = captured or {}
    aliases = {
        "nombre": captured.get("name"), "comuna": captured.get("comuna"),
        "equipo": captured.get("equipment") or captured.get("equipment_type"),
        "problema": captured.get("failure"), "disponibilidad": captured.get("availability"),
    }
    safe = {key: value for key, value in aliases.items()
            if isinstance(value, str) and value and value != "unknown"}
    fields = pending if isinstance(pending, (list, tuple, set, frozenset)) else [pending]
    safe["pending"] = [str(field) for field in fields if field]
    return safe


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", _fold(text)))


def validate(draft: str, *, template: str, facts: dict[str, Any], pending: Any) -> bool:
    """Pure mechanical gate for shape, pending fields, and safe facts."""
    if not isinstance(draft, str) or not draft.strip() or len(draft) > _MAX_CHARS:
        return False
    # The machine decided which fields are asked; a rewrite may neither add nor
    # drop a question, so the count must match the template exactly. Combined
    # with the contact-field guard below, this is the decidable form of
    # "batch closed" — intent equivalence is S7's round-trip test, not a
    # mechanical comparison.
    if draft.count("?") != template.count("?"):
        return False
    if re.search(r"(?m)```|`|\[[^]]+\]\([^)]*\)|^\s*#{1,6}\s|[*_]{1,2}", draft):
        return False
    if re.search(r"(?m)^\s*[-+*]\s+", draft):
        return False
    if any(unicodedata.category(char) in {"So", "Sk"} for char in draft):
        return False

    numbers = set(re.findall(r"\d+(?:[.,:/-]\d+)*", draft))
    fact_values = [str(value) for value in facts.values() if isinstance(value, (str, int, float))]
    allowed_numbers = {number for value in fact_values
                       for number in re.findall(r"\d+(?:[.,:/-]\d+)*", value)}
    if numbers - allowed_numbers:
        return False
    folded = _fold(draft)
    normalized_facts = [_fold(value) for value in fact_values]
    currency_or_price = re.findall(r"(?:[$€£]\s?\d[\d.,]*|\b(?:precio|cuesta|cobramos|pesos?|dolares?)\b)", folded)
    if any(not any(match in value for value in normalized_facts) for match in currency_or_price):
        return False
    date_mentions = re.findall(
        r"\b(?:20\d{2}|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b",
        folded,
    )
    if any(not any(match in value for value in normalized_facts) for match in date_mentions):
        return False

    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", draft):
        return False
    # Sensitive values can be supplied to the pure validator by callers/tests,
    # but are never emitted by facts() and therefore never sent to the model.
    for key, value in facts.items():
        if key.casefold() in {"email", "address", "direccion", "dirección"} and isinstance(value, str) and value and value.casefold() in draft.casefold():
            return False

    pending_fields = pending if isinstance(pending, (list, tuple, set, frozenset)) else [pending]
    allowed_fields = {str(field) for field in pending_fields}
    draft_terms = _terms(draft)
    for field, keywords in _FORWARD_GUARDED.items():
        if field not in allowed_fields and draft_terms.intersection(_terms(" ".join(keywords))):
            return False
    return True


def rewrite(template: str, facts: dict[str, Any], pending: Any) -> str | None:
    """Ask once for a concise rewrite; every provider failure is a fallback."""
    try:
        response = llm.openai_client().chat.completions.create(
            model=llm.CHAT_MODEL,
            messages=[
                {"role": "system", "content": "Reescribe brevemente el texto en español. Conserva exactamente su intención y los campos preguntados. Usa solo los hechos autorizados. Devuelve únicamente el texto."},
                {"role": "user", "content": f"Plantilla: {template}\nHechos permitidos: {facts!r}\nCampos pendientes: {pending!r}"},
            ],
            temperature=0.1,
            timeout=4.0,
        )
        text = response.choices[0].message.content
        return text.strip() if isinstance(text, str) and text.strip() else None
    except Exception:
        return None


def phrase(session, key: str, rendered: str, *, facts: dict[str, Any], pending: Any) -> str:
    """Return template unless explicitly enabled and the candidate passes gate."""
    mode = get_conduct(session).get("redaccion", "plantilla")
    if key not in PHRASEABLE_KEYS or mode != "llm":
        logger.info("capture phrase key=%s mode=%s verdict=template", key, mode)
        return rendered
    verdict = "fallback"
    try:
        draft = rewrite(rendered, facts, pending)
        if draft is not None and validate(draft, template=rendered, facts=facts, pending=pending):
            verdict = "accepted"
            logger.info("capture phrase key=%s mode=%s verdict=%s", key, mode, verdict)
            return draft
    except Exception:
        pass
    logger.info("capture phrase key=%s mode=%s verdict=%s", key, mode, verdict)
    return rendered
