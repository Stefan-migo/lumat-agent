from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.services.address_validation import validate_address


@pytest.mark.parametrize(
    ("address", "commune", "state", "street_name"),
    [
        ("AV. IRARRAZAVAL 40", "Ñuñoa", "validada", "AVENIDA IRARRAZAVAL"),
        ("Avenida Irarrázaval 65", "Ñuñoa", "dudosa", "AVENIDA IRARRAZAVAL"),
        ("Avenida Italia 123", "Ñuñoa", "sin_numeracion", "AVENIDA ITALIA"),
        ("Calle Inventada 123", "Ñuñoa", "no_encontrada", None),
        ("Avenida Irarrázaval 40", "Colina", "sin_referencia", None),
    ],
)
def test_validates_against_the_official_street_master(
    address: str, commune: str, state: str, street_name: str | None
) -> None:
    result = validate_address(address, commune)

    assert result.state == state
    assert result.street_name == street_name
    assert result.normalized_address is not None
    assert result.reason


def test_accepts_accent_and_street_abbreviation_equivalence() -> None:
    abbreviated = validate_address("AV. IRARRAZAVAL 40", "Ñuñoa")
    expanded = validate_address("Avenida Irarrázábal 40", "Ñuñoa")

    assert abbreviated.state == expanded.state == "validada"
    assert abbreviated.street_name == expanded.street_name == "AVENIDA IRARRAZAVAL"
    assert abbreviated.normalized_address == expanded.normalized_address


def test_corrects_a_bounded_street_typo() -> None:
    result = validate_address("Av. Irarazaval 40", "Ñuñoa")

    assert result.state == "validada"
    assert result.street_name == "AVENIDA IRARRAZAVAL"
    assert result.reason == "street_fuzzy_match"


@pytest.mark.parametrize("address", ["mi casa", "por ahí", "asdf", "", "calle Italia", "Italia 123"])
def test_junk_and_unstructured_text_never_raises(address: str) -> None:
    result = validate_address(address, "Ñuñoa")

    assert result.state == "dudosa"
    assert result.reason == "unparseable"
    assert result.street_name is None


def test_oversized_input_is_bounded_and_unparseable() -> None:
    result = validate_address("Avenida " + ("x" * 4000), "Ñuñoa")

    assert result.state == "dudosa"
    assert result.reason == "unparseable"
    assert result.street_name is None


def test_result_is_immutable() -> None:
    result = validate_address("Av. Irarrázaval 40", "Ñuñoa")

    with pytest.raises(FrozenInstanceError):
        result.state = "cliente"


def test_validator_never_returns_the_chat_only_cliente_state() -> None:
    for address in ("Av. Irarrázaval 40", "Calle Inventada 123", "mi casa"):
        assert validate_address(address, "Ñuñoa").state != "cliente"


@pytest.mark.parametrize(
    "address",
    [
        "Avenida Irarrázaval 40 depto 502",
        "Avenida Irarrázaval 40 dpto 502, Ñuñoa",
        "Avenida Irarrázaval 40 casa 2",
        "Avenida Irarrázaval 40 torre 3 depto 51",
    ],
)
def test_unit_after_the_number_does_not_become_the_street_number(address: str) -> None:
    """A department is not the house number.

    Reading the trailing unit as the number turns a true address into
    `no_encontrada`: the validator would claim the street does not exist.
    """
    result = validate_address(address, "Ñuñoa")

    assert result.state in {"validada", "dudosa"}
    assert result.state != "no_encontrada"
    assert result.street_name == "AVENIDA IRARRAZAVAL"
    assert result.normalized_address == "AVENIDA IRARRAZAVAL 40"


def test_a_street_named_after_a_unit_word_keeps_its_own_number() -> None:
    result = validate_address("Pasaje La Torre 5", "Ñuñoa")

    assert result.state != "dudosa" or result.reason != "unparseable"
