"""Behavioral unit coverage for deterministic response guards."""

import pytest

from app.chat.nodes.respond import (
    _affirms_excluded_appliance_repair,
    _claims_out_of_catalogue_scope,
    _gas_manipulation_instruction,
)


@pytest.mark.parametrize(
    "answer",
    [
        "Revisa que la llave de gas esté abierta.",
        "Corta el gas.",
        "Abre el gas.",
        "Cierra el gas.",
        "Corta el gas y ventila.",
        "Corta el gas antes de que llegue el técnico.",
        "Ante olor a gas: ventila, corta el gas y llama al 132.",
        "abre la válvula de gas",
        "Abre el medidor de gas.",
        "Cierra el paso de gas.",
        "gira la llave de gas",
        "revisa el paso de gas",
        "Si hueles gas, corta el suministro.",
        "confirma que la llave de gas esté abierta",
        "confirme que la válvula de gas esté abierta",
        "Enciende el calefón para ver si hay gas.",
        "Fíjate si la cocina enciende normal (para descartar que falte gas).",
    ],
)
def test_only_explicit_gas_hardware_and_appliance_directives_are_guarded(answer):
    assert _gas_manipulation_instruction(answer), (
        f"narrow gas instruction escaped the detector: {answer!r}"
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Cierra el suministro de gas solo si puedes hacerlo de forma segura.",
        "fijate si el gas esta habilitado",
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
        "Revisa si el calefón enciende.",
        "Revisa si la estufa enciende.",
        "Prueba con la cocina.",
        "Prueba con un fósforo si hay fuga de gas.",
        "Prueba con un fósforo si hay fuga.",
        "Revisa la presión del gas.",
        "Revisa que la llave de paso de agua esté abierta y que el gas esté habilitado.",
        "Cierra la llave azul y abre el agua.",
        "Sí, reparamos lavadoras.",
        "Revisa el modelo de la caldera y me dices.",
        "Revisa la garantía de la caldera.",
        "Revisa cuándo fue la última mantención de la caldera.",
        "Mira el código de error en el visor del calefont.",
        "Verifica si la estufa es a gas o eléctrica.",
        "Mira la etiqueta de la cocina para el modelo.",
        "Fíjate el número de serie de la caldera.",
        "Revisa tu boleta de gas y me cuentas.",
        "Mira la boleta del gas para el número de cliente.",
        "Verifica la dirección en la boleta de gas.",
        "La presión del sistema de calefacción presenta una baja después del trabajo previo con gas.",
    ],
)
def test_everything_outside_the_narrow_gas_families_is_not_guarded(answer):
    assert not _gas_manipulation_instruction(answer), (
        f"non-narrow sentence was still classified as a gas instruction: {answer!r}"
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Sí, reparamos lavadoras.",
        "Reparamos su refrigerador.",
    ],
)
def test_excluded_appliance_claims_remain_detectable_for_observation(answer):
    assert _affirms_excluded_appliance_repair(answer), (
        f"excluded-appliance claim was not identified for observation: {answer!r}"
    )


# S1 (odd/tasks/verdad-alcance.md): scope is the closed list in
# docs/kb/lumat-servicios.md. The two measured claims below are verbatim from
# `real-vocabulario-impreciso` and `real-consulta-otros-equipos` (both scored 0.00
# with a hard fail).
#
# The rewrite is deliberately narrow. `f9e29596b` fixed the same class of defect
# the other way round: a guard that replaced answers deleted a correct one, and
# the owner's decision there was "replace only what was measured, observe the
# rest". So only the two families the corpus measured are rewritten; every other
# out-of-catalogue appliance keeps the persona and the judge as its instruments.
@pytest.mark.parametrize(
    "answer",
    [
        "Sí, lo vemos: trabajamos con quemadores de cocina a gas, con técnicos autorizados SEC.",
        "Sí, también trabajamos con bomba de calor de piscina.",
        "Trabajamos con quemadores de cocina a gas.",
        "Nos dedicamos a bombas de calor de piscina.",
    ],
)
def test_out_of_catalogue_scope_claims_are_guarded(answer):
    assert _claims_out_of_catalogue_scope(answer), (
        f"out-of-catalogue scope claim escaped the guard: {answer!r}"
    )


# A refusal names the same words as the claim it refuses. Replacing it would
# delete the correct answer — the exact incident `f9e29596b` records.
@pytest.mark.parametrize(
    "answer",
    [
        "No trabajamos con bomba de calor de piscina",
        "No trabajamos con quemadores de cocina.",
        "Lamentablemente no trabajamos con bombas de calor de piscina.",
        "Eso no lo hacemos: no reparamos quemadores de cocina.",
    ],
)
def test_a_refusal_of_an_out_of_catalogue_service_is_not_rewritten(answer):
    assert not _claims_out_of_catalogue_scope(answer), (
        f"a correct refusal was still guarded: {answer!r}"
    )


# The same guard must stay silent on everything the KB does authorize: the
# in-catalogue appliances, the people Lumat works with, and the maintenance
# phrasing that legitimately names a burner or a gas network. A guard that fires
# here replaces a correct answer, which is worse than the defect it fixes.
@pytest.mark.parametrize(
    "answer",
    [
        "Sí, trabajamos con aire acondicionado.",
        "Trabajamos con técnicos autorizados SEC.",
        "Reparamos calderas y calefont.",
        "Hacemos instalaciones y reemplazos de gasfitería.",
        "Trabajamos con redes de gas y filtraciones de agua.",
        "Hacemos mantención de calefont y revisión de quemadores.",
        "La mantención de caldera incluye revisión del sistema de combustión.",
        "Fíjate si la cocina enciende normal (para descartar que falte gas).",
        "Ofrecemos una visita técnica para revisar calefactores eléctricos.",
        "Cubrimos ductos y trabajos eléctricos.",
        # Measured neither: they stay with the persona and the judge, never with
        # a rewrite (`f9e29596b`).
        "Reparamos hornos y microondas.",
        "Hacemos lavaplatos y campanas.",
        "Sí, reparamos lavadoras.",
        "Reparamos su refrigerador.",
    ],
)
def test_in_catalogue_scope_and_service_phrases_are_not_guarded(answer):
    assert not _claims_out_of_catalogue_scope(answer), (
        f"in-catalogue statement was still guarded: {answer!r}"
    )
