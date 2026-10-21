"""Date-resolved tariff (S2): a date yields exactly one price per service.

The prompt only ever sees the prices in force on the day the customer writes,
so the model cannot compare seasons or quote a stale figure.
"""

from datetime import date

import pytest

from app.services.settings import (
    DEFAULT_TARIFA_PRECIOS,
    TARIFA_SERVICES,
    tarifa_vigente,
)


def test_march_resolves_the_high_season():
    assert tarifa_vigente(DEFAULT_TARIFA_PRECIOS, date(2026, 3, 15)) == {
        "visita_tecnica": 30000,
        "mantencion_calefont": 50000,
        "mantencion_caldera": 80000,
        "lavado_red": 140000,
    }


def test_december_resolves_the_low_season():
    assert tarifa_vigente(DEFAULT_TARIFA_PRECIOS, date(2026, 12, 15)) == {
        "visita_tecnica": 30000,
        "mantencion_calefont": 40000,
        "mantencion_caldera": 60000,
        "lavado_red": 120000,
    }


@pytest.mark.parametrize(
    ("day", "calefont"),
    [
        # Boundaries of the wrap-around range 11..2.
        (date(2026, 10, 31), 50000),
        (date(2026, 11, 1), 40000),
        (date(2026, 2, 28), 40000),
        (date(2026, 3, 1), 50000),
        (date(2026, 1, 1), 40000),
    ],
)
def test_month_boundaries_flip_the_price_exactly_once(day, calefont):
    assert tarifa_vigente(DEFAULT_TARIFA_PRECIOS, day)["mantencion_calefont"] == calefont


def test_every_month_resolves_every_service():
    for month in range(1, 13):
        vigente = tarifa_vigente(DEFAULT_TARIFA_PRECIOS, date(2026, month, 1))
        assert set(vigente) == set(TARIFA_SERVICES)
        assert all(isinstance(valor, int) and valor > 0 for valor in vigente.values())


def test_a_service_without_ranges_is_omitted_instead_of_invented():
    tarifa = {"visita_tecnica": [{"desde_mes": 1, "hasta_mes": 12, "valor": 30000}]}

    assert tarifa_vigente(tarifa, date(2026, 6, 1)) == {"visita_tecnica": 30000}


def test_empty_tariff_resolves_to_nothing():
    assert tarifa_vigente({}, date(2026, 6, 1)) == {}
