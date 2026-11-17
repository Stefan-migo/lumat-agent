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
        "Corta el gas.",
        "corta el gas y ventila",
        "Corta el gas antes de que llegue el técnico.",
        "Ante olor a gas: ventila, corta el gas y llama al 132.",
        "Si hueles gas, corta el suministro.",
        "Verifica si el calefont enciende.",
        "Mira si la cocina enciende.",
        "Haz la prueba con la cocina.",
        "Prueba con un fósforo si hay fuga.",
        "Prueba encender el calefactor.",
        "Prueba encender el quemador.",
        "abre la llave azul",
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
        "Si puedes hacerlo de forma segura, cierra la llave de gas.",
        "abre la llave de paso del agua",
        "Revisa si hay fuga de agua en el lavadero.",
        "Revisa la presión del agua.",
        "Revisa el medidor de agua.",
        "Revisa la filtración de agua del desagüe.",
        "Corta el agua antes de que siga saliendo.",
    ],
)
def test_safety_and_descriptive_gas_text_is_not_an_instruction(answer):
    assert not _gas_manipulation_instruction(answer), (
        f"safe or descriptive gas text was classified as an instruction: {answer!r}"
    )


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (
            "Ante olor a gas, ventila el lugar y llama a Bomberos 132. "
            "Abre el medidor de gas.",
            "Ante olor a gas, ventila el lugar y llama a Bomberos 132. "
            "No manipules la llave ni la línea de gas.",
        ),
        (
            "Ventila el lugar; abre la llave de gas; llama a Bomberos 132.",
            "Ventila el lugar; No manipules la llave ni la línea de gas.; "
            "llama a Bomberos 132.",
        ),
    ],
)
def test_guard_replaces_only_the_offending_sentence_and_preserves_safety_prose(
    answer, expected
):
    assert respond_guards_replace_for_test(answer) == expected


def respond_guards_replace_for_test(answer):
    """Exercise the public sentence-replacement helper without a DB or model."""
    from app.chat.nodes.respond import _replace_gas_instruction_sentences

    return _replace_gas_instruction_sentences(
        answer, "No manipules la llave ni la línea de gas."
    )[0]
