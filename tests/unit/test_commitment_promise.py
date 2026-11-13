from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.commitments import is_promise, promise_due


@pytest.mark.parametrize(
    "text",
    [
        "le envío el detalle",
        "te envío",
        "mañana voy",
        "le confirmo en un rato",
        "le confirmo",
        "estoy cotizando",
        "lo dejo agendado",
        "te aviso",
        "le preparo",
        "me consigo",
        "coordino",
        "enviaré",
        "te contacto",
        "lo reviso y te digo",
    ],
)
def test_measured_promise_shapes_are_recognized(text):
    assert is_promise(text)


@pytest.mark.parametrize("text", ["no calienta la casa", "te molesto con una pregunta"])
def test_non_promises_are_not_recognized(text):
    assert not is_promise(text)


def test_promise_matching_ignores_accents_and_case():
    assert is_promise("LE ENVIO el DETALLE")
    assert is_promise("Le preparó el informe")


def test_word_boundary_prevents_aviso_matching_inside_avisos():
    assert not is_promise("avisos enviados a todos")


def test_manana_uses_business_local_date_across_utc_midnight():
    now = datetime(2026, 11, 2, 23, 30, tzinfo=ZoneInfo("America/Santiago"))
    due = promise_due("mañana te envío", now=now)
    assert due.date().isoformat() == "2026-11-03"
    assert due.tzinfo is not None


def test_el_lunes_means_next_monday_even_when_today_is_monday():
    now = datetime(2026, 11, 2, 10, 0, tzinfo=ZoneInfo("America/Santiago"))
    due = promise_due("el lunes le confirmo", now=now)
    assert due.date().isoformat() == "2026-11-09"


def test_en_n_dias_resolves_from_business_local_day():
    now = datetime(2026, 11, 2, 23, 30, tzinfo=ZoneInfo("America/Santiago"))
    due = promise_due("en 3 días te aviso", now=now)
    assert due.date().isoformat() == "2026-11-05"


def test_la_proxima_semana_resolves_to_next_monday():
    now = datetime(2026, 11, 4, 12, 0, tzinfo=ZoneInfo("America/Santiago"))
    due = promise_due("la próxima semana lo preparo", now=now)
    assert due.date().isoformat() == "2026-11-09"


@pytest.mark.parametrize("text", ["te aviso en un rato", "te aviso a la brevedad"])
def test_vague_dates_do_not_create_a_due_date(text):
    now = datetime(2026, 11, 2, 12, 0, tzinfo=ZoneInfo("America/Santiago"))
    assert promise_due(text, now=now) is None
