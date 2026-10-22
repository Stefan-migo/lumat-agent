"""Deterministic detector for explicit requests to speak with a human."""

from __future__ import annotations

import unicodedata

_HUMAN_ROLES = frozenset(
    {
        "persona",
        "personas",
        "humano",
        "humana",
        "humanos",
        "asesor",
        "asesora",
        "ejecutivo",
        "ejecutiva",
        "encargado",
        "encargada",
        "jefe",
        "jefa",
        "dueno",
        "duena",
        "operador",
        "operadora",
        "alguien",
        "vendedor",
        "vendedora",
    }
)

# Measured: "quiero hablar con un técnico" requests a person, but "necesito una
# visita técnica" describes a service need, so technical roles qualify only with
# a contact form and never with a generic request verb.
_CONTACT_ONLY_ROLES = frozenset({"tecnico", "tecnica", "tecnicos", "tecnicas"})
_CONTACT_FORMS = frozenset(
    {
        "hablar",
        "hablame",
        "comunicar",
        "comunicarme",
        "comunicarte",
        "comuniquenme",
        "comunicame",
        "pasar",
        "pasarme",
        "pasarte",
        "pasame",
        "pasas",
        "transferir",
        "transferirme",
        "transfiereme",
        "derivar",
        "derivarme",
        "deriva",
        "atender",
        "atienda",
        "atiendame",
        "contactar",
        "contacten",
        "llamar",
        "llamarme",
        "llamame",
    }
)
_REQUEST_VERBS = frozenset(
    {"quiero", "necesito", "prefiero", "deseo", "quisiera", "puedo", "podrias"}
)
_NEGATIONS = frozenset({"no", "nunca", "tampoco", "jamas", "ni"})


def _normalize(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFD", text)
    unaccented = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    folded = unaccented.casefold()
    return "".join(char if char.isalnum() else " " for char in folded).split()


def _is_negated(tokens: list[str], index: int) -> bool:
    return any(token in _NEGATIONS for token in tokens[max(0, index - 2) : index])


def _has_preceding_form(
    tokens: list[str], index: int, forms: frozenset[str]
) -> bool:
    return any(
        tokens[previous] in forms and not _is_negated(tokens, previous)
        for previous in range(max(0, index - 3), index)
    )


def is_human_request(text: str) -> bool:
    """Return whether normalized text deterministically requests a human."""
    tokens = _normalize(text)
    if not tokens:
        return False

    normalized = " ".join(tokens)
    phrases = ("atencion humana", "persona real", "humano real")
    if any(phrase in normalized for phrase in phrases):
        return True

    if all(token in _HUMAN_ROLES | _CONTACT_ONLY_ROLES for token in tokens):
        # A bare menu label is a selection, not a sentence: "persona",
        # "operador", and the compound "asesor humano" the old gate matched as a
        # phrase. Requiring a contact form instead would lose that recall.
        return True

    for index, token in enumerate(tokens):
        if token in _HUMAN_ROLES | _CONTACT_ONLY_ROLES:
            if _has_preceding_form(tokens, index, _CONTACT_FORMS):
                return True
            if token in _HUMAN_ROLES and _has_preceding_form(
                tokens, index, _REQUEST_VERBS
            ):
                return True

    return False
