from __future__ import annotations

from app.services.callejero import lookup_street, normalize_street
from scripts.build_callejero import normalize_street as producer_normalize_street


def test_service_normalizer_matches_extract_producer_byte_for_byte() -> None:
    value = "  Avenida   Irarrázábal, Ñuñoa. "
    expected = "AVENIDA IRARRAZABAL NUNOA"

    assert normalize_street(value) == expected
    assert producer_normalize_street(value) == expected
    assert normalize_street(value) == producer_normalize_street(value)


def test_lookup_finds_real_range_and_respects_its_parity() -> None:
    found = lookup_street("Ñuñoa", "AV. IRARRAZAVAL", 40)
    wrong_parity = lookup_street("Ñuñoa", "Avenida Irarrázaval", 65)

    assert found.state == "found_in_range"
    assert found.street_name == "AVENIDA IRARRAZAVAL"
    assert found.matched_by == "exact"
    assert wrong_parity.state == "outside_range"


def test_lookup_finds_street_without_numbering() -> None:
    found = lookup_street("Ñuñoa", "Avenida Italia", 123)

    assert found.state == "no_numbering"
    assert found.street_name == "AVENIDA ITALIA"


def test_lookup_distinguishes_missing_street_from_uncovered_commune() -> None:
    missing = lookup_street("Ñuñoa", "Calle Inventada", 123)
    uncovered = lookup_street("Colina", "Avenida Irarrázaval", 123)

    assert missing.state == "street_not_found"
    assert uncovered.state == "commune_not_covered"


def test_lookup_corrects_a_bounded_typo_but_not_a_short_name() -> None:
    typo = lookup_street("Ñuñoa", "AV. IRARAZAVAL", 40)
    short_typo = lookup_street("Ñuñoa", "AV. ITAL", 123)

    assert typo.state == "found_in_range"
    assert typo.street_name == "AVENIDA IRARRAZAVAL"
    assert typo.matched_by == "fuzzy"
    assert short_typo.state == "street_not_found"


def test_lookup_is_safe_for_junk_and_oversized_inputs() -> None:
    for street in (None, "", "x" * 4000):
        result = lookup_street("Ñuñoa", street, 1)
        assert result.state == "street_not_found"
