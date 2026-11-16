"""Offline lookup against the vendored official Chilean street master."""

from __future__ import annotations

import gzip
import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_MASTER_PATH = Path(__file__).resolve().parents[1] / "data" / "callejero" / "maestro.json.gz"
_MIN_FUZZY_LENGTH = 5
_MAX_LOOKUP_NAME_LENGTH = 256


@dataclass(frozen=True)
class StreetLookup:
    """Outcome of a street lookup, independent of chat or persistence state."""

    state: str
    street_name: str | None = None
    matched_by: str | None = None


def normalize_street(name: str) -> str:
    """Uppercase, accent-free, single-spaced street key.

    Keep this byte-identical to ``scripts/build_callejero.py:normalize_street``:
    the extractor and runtime must agree or every lookup can silently miss.
    """
    folded = unicodedata.normalize("NFD", name)
    plain = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    cleaned = plain.upper().replace(".", " ").replace(",", " ")
    return " ".join(cleaned.split())


@lru_cache(maxsize=1)
def _load_master() -> dict[str, Any]:
    with gzip.open(_MASTER_PATH, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["streets"]


def _canonical_key(value: str) -> str:
    """Normalize common street-type abbreviations to the extract's spelling."""
    key = normalize_street(value)
    for short, full in (
        ("AVDA ", "AVENIDA "),
        ("AVD ", "AVENIDA "),
        ("AV ", "AVENIDA "),
        ("PJE ", "PASAJE "),
        ("PSJE ", "PASAJE "),
        ("PSJ ", "PASAJE "),
        ("C ", "CALLE "),
        ("CL ", "CALLE "),
        ("CAM ", "CAMINO "),
        ("RTA ", "RUTA "),
    ):
        if key.startswith(short):
            return full + key[len(short):]
    return key


def _distance_at_most(left: str, right: str, limit: int = 2) -> int | None:
    """Bounded Levenshtein distance using O(min(n, m)) memory."""
    if abs(len(left) - len(right)) > limit:
        return None
    if len(left) > len(right):
        left, right = right, left
    previous = list(range(len(left) + 1))
    for row, right_char in enumerate(right, start=1):
        current = [row]
        row_min = row
        for column, left_char in enumerate(left, start=1):
            cost = 0 if left_char == right_char else 1
            value = min(
                current[column - 1] + 1,
                previous[column] + 1,
                previous[column - 1] + cost,
            )
            current.append(value)
            row_min = min(row_min, value)
        if row_min > limit:
            return None
        previous = current
    return previous[-1] if previous[-1] <= limit else None


def _fuzzy_name_length(key: str) -> int:
    words = key.split()
    if len(words) > 1 and words[0] in {"AVENIDA", "CALLE", "PASAJE", "PASILLO", "CAMINO", "RUTA"}:
        return len(" ".join(words[1:]))
    return len(key)


def _resolve_street(streets: dict[str, dict[str, Any]], key: str) -> tuple[dict[str, Any] | None, str | None]:
    exact = streets.get(key)
    if exact is not None:
        return exact, "exact"
    if _fuzzy_name_length(key) < _MIN_FUZZY_LENGTH or len(key) > _MAX_LOOKUP_NAME_LENGTH:
        return None, None

    best_distance = 3
    best: dict[str, Any] | None = None
    tied = False
    for candidate_key, entry in streets.items():
        if _fuzzy_name_length(candidate_key) < _MIN_FUZZY_LENGTH:
            continue
        distance = _distance_at_most(key, candidate_key)
        if distance is None:
            continue
        if distance < best_distance:
            best_distance = distance
            best = entry
            tied = False
        elif distance == best_distance:
            tied = True
    if best is None or tied:
        return None, None
    return best, "fuzzy"


def _contains_number(ranges: list[list[int]], number: int) -> bool:
    for start, end in ranges:
        if start <= number <= end and (start % 2 != end % 2 or number % 2 == start % 2):
            return True
    return False


def lookup_street(commune: str, street: str, number: int | None) -> StreetLookup:
    """Check a street and house number in one commune of the offline master.

    States are ``found_in_range``, ``outside_range``, ``no_numbering``,
    ``street_not_found`` and ``commune_not_covered``. Fuzzy correction is
    limited to Levenshtein distance two, only for names at least five
    characters long, and only when the closest candidate is unique.
    """
    if not isinstance(commune, str) or not isinstance(street, str):
        return StreetLookup("street_not_found")
    if len(street) > _MAX_LOOKUP_NAME_LENGTH:
        return StreetLookup("street_not_found")
    commune_key = normalize_street(commune)
    streets = next(
        (items for name, items in _load_master().items() if normalize_street(name) == commune_key),
        None,
    )
    if streets is None:
        return StreetLookup("commune_not_covered")

    key = _canonical_key(street)
    if not key:
        return StreetLookup("street_not_found")
    entry, matched_by = _resolve_street(streets, key)
    if entry is None:
        return StreetLookup("street_not_found")
    name = entry.get("name")
    ranges = entry.get("ranges") or []
    if not ranges:
        return StreetLookup("no_numbering", name, matched_by)
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        return StreetLookup("outside_range", name, matched_by)
    if _contains_number(ranges, number):
        return StreetLookup("found_in_range", name, matched_by)
    return StreetLookup("outside_range", name, matched_by)
