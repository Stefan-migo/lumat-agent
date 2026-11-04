"""S1 (agenda-preferencia): the local day and franja a customer asked for.

The booking node is deterministic and never asks the model, so the only place a
requested day can come from is the customer's own words. This module turns those
words into a narrow, testable ``SlotWindow``; it deliberately understands less
than a human would, because a wrong guess here silently offers a day the customer
did not ask for.

Rules that matter, and why:

* **Narrow by default.** Only an explicit day of the month, a month name or a
  weekday name produces a ``day``. Anything else leaves it ``None`` so the offer
  stays unrestricted exactly as it is today.
* **No guessed times.** "después de las 6" is not parsed: mapping it to 18:00
  would empty the agenda of a business open 09:00-18:00. S2 widens instead. The
  line is *does the phrase land on a franja boundary the business already sells*:
  "después del mediodía" and "después de las 12" start the afternoon, so they are
  read; "al mediodía" names 12:00 exactly and is not.
* **"cualquier día" removes the day, never the franja.** "cualquier día en la
  mañana" keeps the morning and drops the day.
* **"mañana" is ambiguous in Spanish.** After the franja has been consumed
  ("por la mañana", "en la mañana"), a bare "mañana" means *tomorrow*.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

# The franjas the business actually sells. Weekdays open 09:00-18:00, so a
# franja is a filter over that window, not a second schedule.
MORNING = (time(9, 0), time(13, 0))
AFTERNOON = (time(13, 0), time(18, 0))

_WEEKDAYS = {
    "lunes": 1,
    "martes": 2,
    "miercoles": 3,
    "jueves": 4,
    "viernes": 5,
    "sabado": 6,
    "sabados": 6,
    "domingo": 7,
    "domingos": 7,
}

_WEEKDAY_LABELS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    # S9 (chatbot-realismo-conversacional): people write "3 de nov". Before these,
    # the day silently disappeared and the offer started from today, proposing days
    # EARLIER than the one the customer named (harness #45 turn 604).
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "sept": 9,
    "set": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

# Phrases that say "you pick" without naming a day. They drop the day constraint
# and leave any franja in place.
_ANY_DAY = (
    "cualquier dia",
    "cualquier fecha",
    "cualquier horario",
    "cualquiera",
    "cuando puedan",
    "cuando pueda",
    "cuando le acomode",
    "cuando te acomode",
    "cuando sea",
    "el que sea",
    "la que sea",
)

_MORNING = re.compile(r"\b(?:a|de|en|por|durante)\s+la\s+manana\b|\bla\s+manana\b|\bmanana\s+(?:temprano|am)\b")
_AFTERNOON = re.compile(
    r"\b(?:a|de|en|por|durante)\s+la\s+tarde\b"
    r"|\bla\s+tarde\b"
    # S8 (chatbot-realismo-conversacional): production #23 asked "después del
    # mediodía" / "después de las 12" four times and was offered the same three
    # morning slots every time, because only "la tarde" was read. Both phrasings
    # start the afternoon the business sells, so they are not a guess.
    r"|\bdespues\s+del\s+(?:medio\s*dia|mediodia)\b"
    r"|\bdespues\s+de\s+las\s+12(?:\s+del\s+(?:medio\s*dia|mediodia))?\b"
)
_TOMORROW = re.compile(r"\bmanana(?:\s+mismo)?\b")
_HOUR = re.compile(
    r"\b(?:(?:despues\s+de\s+las?|cerca\s+de\s+las?|desde\s+las?|a\s+las?)\s*"
    r"(\d{1,2})(?::(\d{2}))?|"
    r"(\d{1,2}):(\d{2})|"
    r"(\d{1,2})\s*(?:hrs?|horas?))\b"
)
_LATER = re.compile(r"\bmas\s+tarde\b")

_DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b")
_DAY_OF_MONTH = re.compile(r"\b(\d{1,2})\s+de\s+([a-z]+)\b")
_WEEKDAY_AND_DAY = re.compile(r"\b([a-z]+)\s+(\d{1,2})\b")

# A day of the month with no month name is only trusted next to a weekday
# ("viernes 30"), never alone: a bare number is a slot answer.


@dataclass(frozen=True)
class SlotWindow:
    """Requested local day, franja and/or inclusive hour floor."""

    day: date | None = None
    franja: tuple[time, time] | None = None
    desde: time | None = None


def _fold(value: str) -> str:
    """Lowercase and strip accents so "miércoles" and "miercoles" read the same."""

    return "".join(
        char for char in unicodedata.normalize("NFD", value.casefold())
        if not unicodedata.combining(char)
    ).strip()


def _next_weekday(today: date, weekday: int) -> date:
    """The next date on or after ``today`` that falls on ``weekday`` (1 = Monday)."""

    return today + timedelta(days=(weekday - today.isoweekday()) % 7)


def _next_month_day(today: date, month: int, day: int) -> date | None:
    """The next occurrence on or after ``today`` of ``day``/``month``, if valid."""

    for year in (today.year, today.year + 1, today.year + 2):
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        if candidate >= today:
            return candidate
    return None


def _weekday_and_day(today: date, weekday: int, day: int) -> date | None:
    """Resolve "viernes 30" to the next date matching both, within a year."""

    candidate = _next_weekday(today, weekday)
    for _ in range(53):
        if candidate.day == day:
            return candidate
        candidate += timedelta(days=7)
    return None


def franja_label(franja: tuple[time, time]) -> str:
    return "la mañana" if franja == MORNING else "la tarde"


def slot_label(day: date, clock: time) -> str:
    """The one rendering of a slot the customer reads: "Viernes 06/11 a las 13:00".

    S5 (agenda-horarios): the owner asked for the weekday by name; a bare
    "06/11/2026" makes the customer count days in their head. One formatter, so
    the offer, the reschedule list, the confirmation and the panel prompt cannot
    drift apart.
    """
    weekday = _WEEKDAY_LABELS[day.isoweekday() - 1]
    return f"{weekday.capitalize()} {day:%d/%m} a las {clock:%H:%M}"


def when_label(moment: datetime) -> str:
    """`slot_label` for a stored appointment: a visit the customer already holds."""
    return slot_label(moment.date(), moment.time().replace(second=0, microsecond=0))


def window_label(window: SlotWindow) -> str:
    """Name the window in the customer's own words for the S2 notice."""

    if window.desde is not None:
        # The notice renders "Para {{momento}} no me quedan horarios", so the label
        # has to read after "Para": "el viernes 06/11 a partir de las 17:00" and
        # "las 17:00 en adelante".
        if window.day is None:
            return f"las {window.desde:%H:%M} en adelante"
        label = f"{_WEEKDAY_LABELS[window.day.isoweekday() - 1]} {window.day:%d/%m}"
        return f"el {label} a partir de las {window.desde:%H:%M}"
    if window.day is None:
        return franja_label(window.franja or AFTERNOON)
    label = f"{_WEEKDAY_LABELS[window.day.isoweekday() - 1]} {window.day:%d/%m}"
    if window.franja is None:
        return f"el {label}"
    return f"{franja_label(window.franja)} del {label}"


def resolve_window(text: str, *, today: date) -> SlotWindow | None:
    """Return the window ``text`` asks for, or ``None`` when it names none."""

    normalized = _fold(text or "")
    if not normalized:
        return None

    franja: tuple[time, time] | None = None
    if _AFTERNOON.search(normalized):
        franja = AFTERNOON
        normalized = _AFTERNOON.sub(" ", normalized)
    elif _MORNING.search(normalized):
        franja = MORNING
        normalized = _MORNING.sub(" ", normalized)

    hour_match = _HOUR.search(normalized)
    desde: time | None = None
    if hour_match:
        groups = hour_match.groups()
        if groups[0] is not None:
            hour, minute = int(groups[0]), int(groups[1] or 0)
        elif groups[2] is not None:
            hour, minute = int(groups[2]), int(groups[3])
        else:
            hour, minute = int(groups[4]), 0
        ambiguous_evening_six = (
            hour == 6
            and normalized[hour_match.start():].startswith("despues de las 6")
            and not re.match(r"despues de las 6\s*(?:hrs?|horas?)\b", normalized[hour_match.start():])
        )
        if franja == AFTERNOON and 0 < hour < 12:
            # "a las 3 de la tarde" is 15:00: when the customer already said which
            # half of the day, the digits are a twelve-hour clock. Without this the
            # notice told them "a partir de las 03:00".
            hour += 12
        if 0 <= hour <= 23 and 0 <= minute <= 59 and not ambiguous_evening_six:
            desde = time(hour, minute)
            normalized = normalized[:hour_match.start()] + " " + normalized[hour_match.end():]
    elif _LATER.search(normalized):
        desde = AFTERNOON[0]
        normalized = _LATER.sub(" ", normalized)

    day: date | None = None

    match = _DAY_MONTH_YEAR.search(normalized)
    if match:
        day_of_month, month = int(match.group(1)), int(match.group(2))
        year = match.group(3)
        if year:
            year = int(year) + (2000 if len(str(year)) == 2 else 0)
            try:
                day = date(year, month, day_of_month)
            except ValueError:
                day = None
            if day is not None and day < today:
                day = None
        else:
            day = _next_month_day(today, month, day_of_month)

    if day is None:
        match = _DAY_OF_MONTH.search(normalized)
        if match:
            day_of_month = int(match.group(1))
            month = _MONTHS.get(match.group(2))
            if month is not None:
                day = _next_month_day(today, month, day_of_month)

    if day is None:
        match = _WEEKDAY_AND_DAY.search(normalized)
        if match and match.group(1) in _WEEKDAYS:
            day = _weekday_and_day(today, _WEEKDAYS[match.group(1)], int(match.group(2)))

    if day is None:
        for name, weekday in _WEEKDAYS.items():
            if re.search(rf"\b{name}\b", normalized):
                day = _next_weekday(today, weekday)
                break

    if day is None and _TOMORROW.search(normalized):
        day = today + timedelta(days=1)

    if day is None and any(phrase in normalized for phrase in _ANY_DAY):
        return SlotWindow(day=None, franja=franja, desde=desde) if franja or desde else None

    if day is None and franja is None and desde is None:
        return None
    return SlotWindow(day=day, franja=franja, desde=desde)
