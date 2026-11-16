"""Pure, bounded address parsing and validation against the offline street master."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.services.callejero import lookup_street, normalize_street

AddressState = Literal["validada", "sin_numeracion", "dudosa", "no_encontrada", "sin_referencia"]

_MAX_ADDRESS_LENGTH = 4000
_NUMBER_AT_END = re.compile(r"(?:\s+|\s*#\s*)(\d{1,6})\s*$")
# A real address often carries its unit after the number ("Irarrázaval 40 depto
# 502"). Reading that trailing 502 as the street number turns a true address into
# `no_encontrada` — the validator would claim the street does not exist. The unit
# clause is therefore matched first, and only when it follows an explicit number:
# a street literally named "Pasaje La Torre 5" keeps its own number.
_UNIT = r"(?:depto|dpto|departamento|depa|block|bloque|torre|oficina|piso|casa|sitio|parcela|lote|unidad|uh)"
_NUMBER_THEN_UNITS_AT_END = re.compile(
    rf"^(?P<street>.*?)\s+(?P<number>\d{{1,6}})\s*(?:,\s*|\s+)(?:{_UNIT}\b\.?\s*[\w-]*\s*(?:,\s*|\s+)?)+$",
    re.IGNORECASE,
)
_STREET_PREFIX = re.compile(
    r"^\s*(calle|c\.?|cl\.?|avenida|av\.?|avda\.?|avd\.?|"
    r"pasillo|pasaje|pje\.?|psje\.?|psj\.?|camino|cam\.?|ruta|rta\.?)"
    r"(?:\s+|\s*\.\s*)(.+?)\s*$",
    re.IGNORECASE,
)
_PREFIXES = {
    "C": "CALLE",
    "CL": "CALLE",
    "CALLE": "CALLE",
    "AV": "AVENIDA",
    "AVDA": "AVENIDA",
    "AVD": "AVENIDA",
    "AVENIDA": "AVENIDA",
    "PJE": "PASAJE",
    "PSJE": "PASAJE",
    "PSJ": "PASAJE",
    "PASAJE": "PASAJE",
    "PASILLO": "PASILLO",
    "CAM": "CAMINO",
    "CAMINO": "CAMINO",
    "RTA": "RUTA",
    "RUTA": "RUTA",
}


@dataclass(frozen=True)
class AddressValidationResult:
    state: AddressState
    normalized_address: str | None
    street_name: str | None
    reason: str


def _unparseable() -> AddressValidationResult:
    return AddressValidationResult("dudosa", None, None, "unparseable")


def _parse_address(text: str) -> tuple[str, int] | None:
    with_units = _NUMBER_THEN_UNITS_AT_END.match(text)
    if with_units is not None:
        number = int(with_units.group("number"))
        street_text = with_units.group("street").strip(" \t,;#")
    else:
        number_match = _NUMBER_AT_END.search(text)
        if number_match is None:
            return None
        number = int(number_match.group(1))
        street_text = text[: number_match.start()].strip(" \t,;#")
    prefix = _STREET_PREFIX.match(street_text)
    if prefix is None:
        return None
    raw_type, name = prefix.groups()
    name = name.strip(" \t,;#")
    if not name:
        return None
    canonical_type = _PREFIXES[normalize_street(raw_type)]
    street = f"{canonical_type} {name}"
    return street, number


def _strip_trailing_commune(text: str, commune: str) -> str:
    """Drop the commune the customer repeats at the end, exact match only.

    The commune is already captured and validated separately, and people write
    "Irarrázaval 40 depto 502, Ñuñoa" anyway. Removing only the supplied commune
    keeps the strip from eating a street name that merely looks like one.
    """
    wanted = normalize_street(commune)
    if not wanted:
        return text
    tail = re.search(r"[,;]\s*(?P<tail>[^,;]+?)\s*$", text)
    if tail is None or normalize_street(tail.group("tail")) != wanted:
        return text
    return text[: tail.start()].strip(" \t,;")


def validate_address(text: str, commune: str) -> AddressValidationResult:
    """Validate address text using only the supplied commune and local extract.

    This function does not open sessions or perform network I/O and returns a
    result for malformed, non-string, or oversized input rather than raising.
    """
    if not isinstance(text, str) or not isinstance(commune, str) or len(text) > _MAX_ADDRESS_LENGTH:
        return _unparseable()
    parsed = _parse_address(_strip_trailing_commune(text.strip(), commune))
    if parsed is None:
        return _unparseable()
    street, number = parsed
    lookup = lookup_street(commune, street, number)
    normalized_street = lookup.street_name or normalize_street(street)
    normalized_address = f"{normalize_street(normalized_street)} {number}"
    if lookup.state == "commune_not_covered":
        return AddressValidationResult("sin_referencia", normalized_address, None, "commune_not_covered")
    if lookup.state == "street_not_found":
        return AddressValidationResult("no_encontrada", normalized_address, None, "street_not_found")
    if lookup.state == "no_numbering":
        reason = "street_fuzzy_match" if lookup.matched_by == "fuzzy" else "street_has_no_numbering"
        return AddressValidationResult("sin_numeracion", normalized_address, lookup.street_name, reason)
    if lookup.state == "outside_range":
        reason = "street_fuzzy_match" if lookup.matched_by == "fuzzy" else "number_outside_ranges"
        return AddressValidationResult("dudosa", normalized_address, lookup.street_name, reason)
    reason = "street_fuzzy_match" if lookup.matched_by == "fuzzy" else "number_in_range"
    return AddressValidationResult("validada", normalized_address, lookup.street_name, reason)
