"""Behavioral unit coverage for deterministic response guards."""

import pytest

from app.chat.nodes.respond import (
    _affirms_excluded_appliance_repair,
    _gas_manipulation_instruction,
)


@pytest.mark.parametrize(
    "answer",
    [
        "Enciende el calefón para ver si hay gas.",
        "Revisa si el calefón enciende.",
        "Revisa si la estufa enciende.",
        "Prueba con un fósforo si hay fuga de gas.",
        "Revisa la presión del gas.",
        "Abre el medidor de gas.",
        "Cierra el paso de gas.",
        "Abre el gas.",
        "gira la llave de gas",
        "revisa el paso de gas",
    ],
)
def test_customer_gas_manipulation_forms_are_guarded(answer):
    assert _gas_manipulation_instruction(answer), (
        f"unsafe gas instruction escaped the detector: {answer!r}"
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Sí, reparamos refrigerador.",
        "Reparamos su refrigerador.",
    ],
)
def test_singular_excluded_appliance_repair_claims_are_guarded(answer):
    assert _affirms_excluded_appliance_repair(answer), (
        f"singular excluded-appliance repair claim escaped the detector: {answer!r}"
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Cierra el suministro de gas solo si puedes hacerlo de forma segura.",
        "Ante olor a gas, abre puertas y ventanas para ventilar.",
        "Ante olor a gas, no abra la llave ni pruebe artefactos.",
        "La mantención incluye revisar la llave de gas.",
        "Revisar la llave de gas es parte de la mantención.",
        "El lavado de red considera revisar la llave de gas.",
    ],
)
def test_safety_and_descriptive_gas_text_is_not_an_instruction(answer):
    assert not _gas_manipulation_instruction(answer), (
        f"safe or descriptive gas text was classified as an instruction: {answer!r}"
    )


def test_guard_replaces_only_the_offending_sentence_and_preserves_safety_prose():
    answer = (
        "Ante olor a gas, ventila el lugar y llama a Bomberos 132. "
        "Abre el medidor de gas."
    )

    guarded = respond_guards_replace_for_test(answer)

    assert guarded.startswith("Ante olor a gas, ventila el lugar y llama a Bomberos 132.")
    assert "Abre el medidor de gas." not in guarded


def respond_guards_replace_for_test(answer):
    """Exercise the public sentence-replacement helper without a DB or model."""
    from app.chat.nodes.respond import _replace_gas_instruction_sentences

    return _replace_gas_instruction_sentences(
        answer, "No manipules la llave ni la línea de gas."
    )[0]
