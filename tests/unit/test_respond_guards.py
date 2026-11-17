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
        "confirma que la llave de gas esté abierta",
        "fijate si el gas esta habilitado",
    ],
)
def test_customer_gas_manipulation_forms_are_guarded(answer):
    assert _gas_manipulation_instruction(answer), (
        f"unsafe gas instruction escaped the detector: {answer!r}"
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Revisa que la llave de paso de agua esté abierta y que el gas esté habilitado.",
    ],
)
def test_mixed_water_and_gas_instructions_are_guarded(answer):
    assert _gas_manipulation_instruction(answer), (
        f"mixed water-and-gas instruction escaped the detector: {answer!r}"
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
        "Revisa el modelo de la caldera y me dices.",
        "Revisa la garantía de la caldera.",
        "Revisa cuándo fue la última mantención de la caldera.",
        "Mira el código de error en el visor del calefont.",
        "Verifica si la estufa es a gas o eléctrica.",
        "Mira la etiqueta de la cocina para el modelo.",
        "Fíjate el número de serie de la caldera.",
    ],
)
def test_appliance_administration_and_diagnostics_are_not_gas_instructions(answer):
    assert not _gas_manipulation_instruction(answer), (
        f"non-ignition appliance check was classified as an instruction: {answer!r}"
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Revisa tu boleta de gas y me cuentas.",
        "Mira la boleta del gas para el número de cliente.",
        "Verifica la dirección en la boleta de gas.",
    ],
)
def test_gas_word_with_administrative_checks_is_not_an_instruction(answer):
    assert not _gas_manipulation_instruction(answer), (
        f"administrative gas reference was classified as an instruction: {answer!r}"
    )


def test_blue_valve_signal_is_not_suppressed_by_water_context():
    answer = "Cierra la llave azul y abre el agua."
    assert _gas_manipulation_instruction(answer), (
        f"blue gas valve instruction escaped the detector: {answer!r}"
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Cierra el suministro de gas solo si puedes hacerlo de forma segura.",
        "Ante olor a gas, abre puertas y ventanas para ventilar.",
        "Ante olor a gas, no abra la llave ni pruebe artefactos.",
        "Ante olor a gas, no abra la llave ni pruebe artefactos. Ventila y llama al 132.",
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
