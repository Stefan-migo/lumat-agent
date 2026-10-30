"""Shared matching and canonicalization for the configured service catalogue."""

from __future__ import annotations

import re
import unicodedata

from app.services.settings import (
    TARIFA_LABELS,
    get_service_durations,
    get_tarifa_precios,
)


_PREVENTIVE_CATALOGUE_WORDS = (
    "mantencion", "mantenimiento", "lavado", "limpieza", "preventiva", "revision",
)


def _normalize(text: str) -> str:
    """Lower-case, accent-folded, non-alphanumerics collapsed to one space."""
    folded = unicodedata.normalize("NFD", (text or "").casefold())
    folded = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def _edit_distance_at_most_one(left: str, right: str) -> bool:
    """Match one-word typos with a bounded Levenshtein distance of one."""
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, start=1):
        current = [row]
        for column, right_char in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (left_char != right_char),
            ))
        if min(current) > 1:
            return False
        previous = current
    return previous[-1] <= 1


def _matches_catalogue_phrase(text: str, phrase: str) -> bool:
    words = _normalize(phrase.replace("_", " ")).split()
    tokens = _normalize(text).split()
    if not words:
        return False
    for start, token in enumerate(tokens):
        if not _edit_distance_at_most_one(token, words[0]):
            continue
        cursor = start + 1
        for word in words[1:]:
            match_at = next(
                (
                    index for index in range(cursor, min(cursor + 3, len(tokens)))
                    if _edit_distance_at_most_one(tokens[index], word)
                ),
                None,
            )
            if match_at is None:
                break
            cursor = match_at + 1
        else:
            return True
    return False


def _catalogue_services(session) -> list[str]:
    """Configured service names from booking durations and the tariff."""
    return list(dict.fromkeys([*get_service_durations(session), *get_tarifa_precios(session)]))


def _preventive_services(session) -> list[str]:
    """The configured services whose own name says preventive.

    Keep A5's original source set: duration keys, tariff keys, and the display
    labels. The shared matcher must not change which preventive requests capture
    recognizes.
    """
    services = [
        *get_service_durations(session),
        *get_tarifa_precios(session),
        *TARIFA_LABELS.values(),
    ]
    return [
        service
        for service in services
        if any(
            word in _normalize(str(service).replace("_", " "))
            for word in _PREVENTIVE_CATALOGUE_WORDS
        )
    ]


def canonical_service(session, value: str) -> str:
    """Resolve a classifier service to a catalogue label safe for retrieval.

    Preventive labels are selected only when the supplied value expresses that
    preventive service. A device noun alone therefore resolves to the generic
    repair visit rather than a similarly-named maintenance service.

    An unresolvable value comes back unchanged, so the classifier's own fallback
    query survives a tree with no catalogue. Dropping it would answer less than
    before the normalization existed, which is a regression the KB fallback tests
    pin.
    """
    catalogue = _catalogue_services(session)
    normalized = _normalize(value)
    if catalogue and normalized and not re.search(
        r"\bno\s+(?:quiero|necesito|busco|solicito)\b", normalized
    ):
        preventive = next(
            (
                service for service in _preventive_services(session)
                if _matches_catalogue_phrase(value, service)
            ),
            None,
        )
        if preventive is not None:
            return TARIFA_LABELS.get(preventive, preventive)

    generic_visit = next(
        (
            service for service in catalogue
            if "visita" in _normalize(service.replace("_", " ")).split()
        ),
        None,
    )
    return TARIFA_LABELS.get(generic_visit, generic_visit) if generic_visit else value
