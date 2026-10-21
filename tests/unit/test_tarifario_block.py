"""The `<tarifario>` prompt block (S2): current prices only, no season words."""

import pytest

from app.chat.nodes.respond import build_tarifario_block

VIGENTE = {
    "visita_tecnica": 30000,
    "mantencion_calefont": 50000,
    "mantencion_caldera": 80000,
    "lavado_red": 140000,
}


def test_block_lists_each_service_with_its_current_price():
    block = build_tarifario_block(VIGENTE)

    assert "Visita técnica: $30.000" in block
    assert "Mantención de calefont: $50.000" in block
    assert "Mantención de caldera: $80.000" in block
    assert "Lavado de red: $140.000" in block


def test_block_is_empty_when_no_price_is_in_force():
    assert build_tarifario_block({}) == ""


@pytest.mark.parametrize("word", ["temporada", "temporada alta", "temporada baja", "invierno", "verano"])
def test_block_never_names_a_season(word):
    assert word not in build_tarifario_block(VIGENTE).lower()


def test_block_omits_services_without_a_price():
    block = build_tarifario_block({"visita_tecnica": 30000})

    assert "Visita técnica" in block
    assert "calefont" not in block


class _FakeSession:
    def __init__(self, values):
        self.values = values

    def get(self, model, key):
        if key in self.values:
            return type("Setting", (), {"value": self.values[key]})()
        return None


def test_tarifario_context_uses_the_configured_timezone_and_the_current_date(monkeypatch):
    import contextlib
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.chat.nodes import respond as respond_node
    from app.services.settings import DEFAULT_TARIFA_PRECIOS, tarifa_vigente

    values = {"hours.timezone": "UTC", "tarifa.precios": DEFAULT_TARIFA_PRECIOS}
    monkeypatch.setattr(
        respond_node, "session_scope", lambda: contextlib.nullcontext(_FakeSession(values))
    )

    fecha, block = respond_node._tarifario_context()
    hoy = datetime.now(ZoneInfo("UTC")).date()

    assert fecha == hoy.strftime("%Y-%m-%d")
    assert block == respond_node.build_tarifario_block(tarifa_vigente(DEFAULT_TARIFA_PRECIOS, hoy))
    assert len(block.splitlines()) == 4
