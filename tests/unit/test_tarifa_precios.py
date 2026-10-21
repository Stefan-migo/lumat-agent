"""Tariff settings: shape, month coverage and validation (S1).

The tariff lives in settings with one or more month ranges per service. A range
must partition months 1-12 exactly once: no gaps, no overlaps, so a date always
resolves to exactly one price.
"""

import pytest

from app.services.settings import (
    DEFAULT_TARIFA_PRECIOS,
    TARIFA_PRECIOS_KEY,
    TARIFA_SERVICES,
    get_tarifa_precios,
    validate_tarifa_precios,
)


class FakeSession:
    def __init__(self, value=None):
        self.value = value

    def get(self, model, key):
        if self.value is not None:
            return type("Setting", (), {"value": self.value})()
        return None


def _months(precios):
    """Expand a service's ranges into the set of covered months."""
    months = set()
    for rango in precios:
        month = rango["desde_mes"]
        while True:
            months.add(month)
            if month == rango["hasta_mes"]:
                break
            month = month % 12 + 1
    return months


def test_default_tariff_covers_the_four_services():
    assert TARIFA_SERVICES == (
        "visita_tecnica",
        "mantencion_calefont",
        "mantencion_caldera",
        "lavado_red",
    )
    assert set(DEFAULT_TARIFA_PRECIOS) == set(TARIFA_SERVICES)
    for service in TARIFA_SERVICES:
        assert _months(DEFAULT_TARIFA_PRECIOS[service]) == set(range(1, 13))


def test_default_tariff_matches_the_agreed_figures():
    def valor(service, month):
        for rango in DEFAULT_TARIFA_PRECIOS[service]:
            if month in _months([rango]):
                return rango["valor"]
        raise AssertionError(f"{service} does not cover month {month}")

    assert valor("visita_tecnica", 6) == 30000
    assert valor("mantencion_calefont", 6) == 50000
    assert valor("mantencion_calefont", 12) == 40000
    assert valor("mantencion_caldera", 6) == 80000
    assert valor("mantencion_caldera", 1) == 60000
    assert valor("lavado_red", 6) == 140000
    assert valor("lavado_red", 2) == 120000


def test_default_tariff_is_valid():
    assert validate_tarifa_precios(DEFAULT_TARIFA_PRECIOS) == DEFAULT_TARIFA_PRECIOS


def test_get_tarifa_precios_returns_default_when_unset_or_malformed():
    assert get_tarifa_precios(FakeSession()) == DEFAULT_TARIFA_PRECIOS
    assert get_tarifa_precios(FakeSession({"invalid": "shape"})) == DEFAULT_TARIFA_PRECIOS


def test_get_tarifa_precios_returns_the_stored_value():
    stored = {
        "visita_tecnica": [{"desde_mes": 1, "hasta_mes": 12, "valor": 1}],
        "mantencion_calefont": [{"desde_mes": 1, "hasta_mes": 12, "valor": 2}],
        "mantencion_caldera": [{"desde_mes": 1, "hasta_mes": 12, "valor": 3}],
        "lavado_red": [{"desde_mes": 1, "hasta_mes": 12, "valor": 4}],
    }
    assert get_tarifa_precios(FakeSession(stored)) == stored


def test_key_is_stable():
    assert TARIFA_PRECIOS_KEY == "tarifa.precios"


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda value: value.pop("visita_tecnica"), id="missing-service"),
        pytest.param(
            lambda value: value.__setitem__("instalacion", value["visita_tecnica"]),
            id="unknown-service",
        ),
        pytest.param(
            lambda value: value.__setitem__("visita_tecnica", "30000"), id="not-a-list"
        ),
        pytest.param(
            lambda value: value["visita_tecnica"].__setitem__(0, {"desde_mes": 1, "hasta_mes": 12, "valor": 0}),
            id="non-positive-value",
        ),
        pytest.param(
            lambda value: value["visita_tecnica"].__setitem__(0, {"desde_mes": 1, "hasta_mes": 12, "valor": True}),
            id="bool-value",
        ),
        pytest.param(
            lambda value: value["visita_tecnica"].__setitem__(0, {"desde_mes": 0, "hasta_mes": 12, "valor": 1}),
            id="month-out-of-range",
        ),
        pytest.param(
            lambda value: value["visita_tecnica"].__setitem__(0, {"desde_mes": 1, "hasta_mes": 11, "valor": 1}),
            id="month-gap",
        ),
        pytest.param(
            lambda value: value["visita_tecnica"].append({"desde_mes": 6, "hasta_mes": 8, "valor": 2}),
            id="month-overlap",
        ),
        pytest.param(
            lambda value: value["visita_tecnica"].__setitem__(0, {"desde_mes": 1, "hasta_mes": 12}),
            id="missing-value",
        ),
    ],
)
def test_validate_tarifa_precios_rejects_malformed_configuration(mutate):
    value = {
        "visita_tecnica": [{"desde_mes": 1, "hasta_mes": 12, "valor": 30000}],
        "mantencion_calefont": [{"desde_mes": 1, "hasta_mes": 12, "valor": 50000}],
        "mantencion_caldera": [{"desde_mes": 1, "hasta_mes": 12, "valor": 80000}],
        "lavado_red": [{"desde_mes": 1, "hasta_mes": 12, "valor": 140000}],
    }
    mutate(value)

    with pytest.raises(ValueError):
        validate_tarifa_precios(value)


@pytest.mark.parametrize("value", [None, [], "tarifa", 30000])
def test_validate_tarifa_precios_rejects_non_objects(value):
    with pytest.raises(ValueError):
        validate_tarifa_precios(value)
