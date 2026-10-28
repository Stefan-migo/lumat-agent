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
  would empty the agenda of a business open 09:00-18:00. S2 widens instead.
* **"cualquier día" removes the day, never the franja.** "cualquier día en la
  mañana" keeps the morning and drops the day.
* **"mañana" is ambiguous in Spanish.** After the franja has been consumed
  ("por la mañana", "en la mañana"), a bare "mañana" means *tomorrow*.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, time, timedelta

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
_AFTERNOON = re.compile(r"\b(?:a|de|en|por|durante)\s+la\s+tarde\b|\bla\s+tarde\b")
_TOMORROW = re.compile(r"\bmanana(?:\s+mismo)?\b")

_DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b")
_DAY_OF_MONTH = re.compile(r"\b(\d{1,2})\s+de\s+([a-z]+)\b")
_WEEKDAY_AND_DAY = re.compile(r"\b([a-z]+)\s+(\d{1,2})\b")

# A day of the month with no month name is only trusted next to a weekday
# ("viernes 30"), never alone: a bare number is a slot answer.


@dataclass(frozen=True)
class SlotWindow:
    """A requested local ``day`` and/or ``franja``; ``None`` means unconstrained."""

    day: date | None = None
    franja: tuple[time, time] | None = None


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


def window_label(window: SlotWindow) -> str:
    """Name the window in the customer's own words for the S2 notice."""

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
        return SlotWindow(day=None, franja=franja) if franja else None

    if day is None and franja is None:
        return None
    return SlotWindow(day=day, franja=franja)
