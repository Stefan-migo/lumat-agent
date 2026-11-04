"""S1 (agenda-preferencia): the window a customer asked for, read deterministically."""

from datetime import date, datetime, time, timezone

import pytest

from app.chat.slot_window import SlotWindow, resolve_window, slot_label, when_label, window_label

# 2026-10-27 is a Tuesday: every expectation below is anchored to the day the
# production conversation and the three harness conversations actually happened.
TUESDAY = date(2026, 10, 27)


def _resolve(text: str, today: date = TUESDAY) -> SlotWindow | None:
    return resolve_window(text, today=today)


def test_weekday_and_morning_franja_from_the_harness_conversation():
    window = _resolve("jueves por la mañana")

    assert window is not None
    assert window.day == date(2026, 10, 29)
    assert window.franja == (time(9, 0), time(13, 0))


def test_weekday_without_franja_from_the_harness_conversation():
    window = _resolve("un dia sabado")

    assert window is not None
    assert window.day == date(2026, 10, 31)
    assert window.franja is None


def test_afternoon_franja_from_the_harness_conversation():
    window = _resolve("viernes en la tarde")

    assert window is not None
    assert window.day == date(2026, 10, 30)
    assert window.franja == (time(13, 0), time(18, 0))


def test_proximo_weekday_from_the_production_conversation():
    window = _resolve("el proximo miercoles en la mañana")

    assert window is not None
    assert window.day == date(2026, 10, 28)


def test_question_about_a_weekday_mid_selection():
    window = _resolve("para el proximo jueves tienes algun tecnico disponible_")

    assert window is not None
    assert window.day == date(2026, 10, 29)


def test_question_with_an_explicit_day_of_month():
    window = _resolve("tienes horarios disponibles para el viernes 30?")

    assert window is not None
    assert window.day == date(2026, 10, 30)


def test_explicit_day_of_month_named_without_a_weekday():
    window = _resolve("el 30 de octubre")

    assert window is not None
    assert window.day == date(2026, 10, 30)


def test_cualquier_dia_drops_the_day_and_keeps_the_franja():
    window = _resolve("si, me sirve cualquier dia en la mañana")

    assert window is not None
    assert window.day is None
    assert window.franja == (time(9, 0), time(13, 0))


def test_today_matches_its_own_weekday():
    window = _resolve("el martes", today=date(2026, 10, 27))

    assert window is not None
    assert window.day == date(2026, 10, 27)


def test_past_weekday_moves_to_the_next_week():
    window = _resolve("el jueves", today=date(2026, 10, 30))

    assert window is not None
    assert window.day == date(2026, 11, 5)


def test_standalone_manana_is_tomorrow_not_a_franja():
    window = _resolve("mañana", today=date(2026, 10, 27))

    assert window is not None
    assert window.day == date(2026, 10, 28)
    assert window.franja is None


def test_a_long_slot_answer_is_not_a_window():
    assert _resolve("No me sirve ninguno de los horarios que me ofreces") is None


def test_a_bare_option_number_is_not_a_window():
    assert _resolve("3") is None


def test_an_unrecognized_time_of_day_is_ignored_instead_of_guessed():
    """`complejo-no-quiere-email` asks for "despues de las 6": guessing 18:00 would
    empty the agenda, so the text stays unconstrained and S2 never has to widen."""
    assert _resolve("si, cualquier dia despues de las 6") is None


def test_despues_del_mediodia_is_the_afternoon_franja():
    """S8: production #23 turn 304 — the customer asked for the afternoon and got
    the same three morning slots back, three times, until they stopped writing."""
    window = _resolve("Podría ser después del mediodía ?")

    assert window is not None
    assert window.day is None
    assert window.franja == (time(13, 0), time(18, 0))


def test_despues_del_mediodia_keeps_the_named_day():
    """S8/S9: production #23 turn 306 — day plus franja, not day alone."""
    window = _resolve("Podría ser para el 3 de noviembre después del mediodía?")

    assert window is not None
    assert window.day == date(2026, 11, 3)
    assert window.franja == (time(13, 0), time(18, 0))


def test_despues_de_las_12_is_the_afternoon_franja():
    """S8: production #23 turn 308, verbatim."""
    window = _resolve("Después de las 12 del mediodía?")

    assert window is not None
    assert window.day is None
    assert window.franja == (time(13, 0), time(18, 0))


def test_medium_day_spelling_and_the_named_day():
    """S8: production #23 turn 310, verbatim."""
    window = _resolve("3 de noviembre después de las 12 del mediodía")

    assert window is not None
    assert window.day == date(2026, 11, 3)
    assert window.franja == (time(13, 0), time(18, 0))


def test_a_bare_mediodia_alone_is_not_a_guessed_hour():
    """The boundary with the next cliff: "al mediodía" names 12:00 exactly, and the
    business sells 09:00-18:00, so it is left unconstrained rather than guessed."""
    assert _resolve("al mediodía") is None


def test_an_empty_message_is_not_a_window():
    assert _resolve("") is None


def test_abbreviated_month_keeps_the_requested_day():
    """S9: harness #45 turn 604 — "3 de nov" lost its day, so the offer started from
    today and proposed 29/10 and 30/10, days BEFORE the one the customer asked for."""
    window = _resolve("y para el dia 3 de nov podria ser en la tarde?", today=date(2026, 10, 29))

    assert window is not None
    assert window.day == date(2026, 11, 3)
    assert window.franja == (time(13, 0), time(18, 0))


@pytest.mark.parametrize("text", [
    "después de las 17", "después de las 17 hrs", "a las 17",
    "cerca de las 17", "desde las 17", "17:00", "17 hrs",
])
def test_requested_hour_is_parsed_as_an_inclusive_floor(text):
    window = _resolve(text)

    assert window is not None
    assert window.desde == time(17, 0)


def test_mas_tarde_uses_the_afternoon_floor():
    window = _resolve("podría ser más tarde")

    assert window is not None
    assert window.desde == time(13, 0)


def test_every_shipped_month_abbreviation_resolves():
    expected = {
        "ene": date(2027, 1, 5), "feb": date(2027, 2, 5), "mar": date(2027, 3, 5),
        "abr": date(2027, 4, 5), "may": date(2027, 5, 5), "jun": date(2027, 6, 5),
        "jul": date(2027, 7, 5), "ago": date(2027, 8, 5), "sep": date(2027, 9, 5),
        "sept": date(2027, 9, 5), "set": date(2027, 9, 5), "oct": date(2027, 10, 5),
        # November and December are still ahead of 2026-10-29, so they stay in 2026.
        "nov": date(2026, 11, 5), "dic": date(2026, 12, 5),
    }

    for abbreviation, day in expected.items():
        window = _resolve(f"el 5 de {abbreviation}", today=date(2026, 10, 29))
        assert window is not None and window.day == day, abbreviation


def test_an_hour_inside_a_stated_franja_is_twelve_hour_clock():
    """S3: "a las 3 de la tarde" is 15:00, never 03:00.

    The hour parser reads the digits, so a customer who already said which half of
    the day wins: without this, the S4 notice told them "a partir de las 03:00".
    """
    afternoon = _resolve("a las 3 de la tarde")
    morning = _resolve("a las 3 de la mañana")

    assert afternoon is not None and afternoon.desde == time(15, 0)
    assert morning is not None and morning.desde == time(3, 0)


def test_the_notice_label_reads_after_para():
    """S4: `booking_window_unavailable` renders "Para {{momento}} no me quedan…"."""
    day = date(2026, 11, 6)

    with_day = window_label(SlotWindow(day=day, desde=time(17, 0)))
    without_day = window_label(SlotWindow(desde=time(17, 0)))

    assert with_day == "el viernes 06/11 a partir de las 17:00"
    assert without_day == "las 17:00 en adelante"


def test_slot_label_names_the_weekday_first():
    """S5: "Viernes 06/11 a las 13:00" -- the owner's requested shape."""
    assert slot_label(date(2026, 11, 6), time(13, 0)) == "Viernes 06/11 a las 13:00"
    assert slot_label(date(2026, 11, 9), time(9, 30)) == "Lunes 09/11 a las 09:30"


def test_when_label_renders_a_stored_appointment_the_same_way():
    moment = datetime(2026, 11, 6, 13, 0, 45, tzinfo=timezone.utc)

    assert when_label(moment) == "Viernes 06/11 a las 13:00"
