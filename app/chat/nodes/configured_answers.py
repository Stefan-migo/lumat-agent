"""Answers that come from configuration, never from customer KB prose (S4-S6).

The covered communes, the weekly window and the service durations all live in
`settings`, and the scheduling engine obeys them. The customer KB described the
same values in prose, so the two could disagree without anything failing: the
measured case is a document saying Saturday visits go to an advisor while the
engine offered Saturday slots (`odd/kb-drift`).

These answers read the configuration directly, which is what lets the KB keep
only the policy (S7). They are deterministic: no model call, and no figure that
the configuration does not hold.
"""

from __future__ import annotations

import re
import unicodedata

from app.chat.state import ConversationState
from app.services.settings import (
    get_coverage_communes,
    get_hours_schedule,
    get_service_durations,
)

# Terms that ask WHERE the visits happen, as opposed to a question that merely
# names a commune. Deliberately narrow: `cubre`/`cubren` are verbs other questions
# use ("la garantia cubre algo?" is postventa), so they only count next to a
# configured commune, through `_PLACE_TERMS` below.
_COVERAGE_TERMS = frozenset({"comuna", "comunas", "cobertura"})
_PLACE_TERMS = frozenset(
    {"atienden", "trabajan", "llegan", "van", "visitan", "cubren", "cubre"}
)

# A price question that happens to name a commune ("cuanto sale la visita en
# Nunoa") belongs to the tariff answer, not here.
_PRICE_TERMS = frozenset({"precio", "precios", "vale", "cuesta", "sale", "tarifa", "valor"})

# Terms that ask WHEN: the reply names the configured days and range. `atienden`
# is deliberately absent, because the place reading of it ("atienden en
# Providencia?") belongs to the out-of-coverage policy that stays in the KB.
_HOURS_TERMS = frozenset(
    {
        "horario",
        "horarios",
        "hora",
        "horas",
        "dia",
        "dias",
        "abren",
        "cierran",
        "abierto",
        "cerrado",
        "sabado",
        "domingo",
        "festivo",
        "semana",
    }
)

# S9: a window that exists only because the offer filter reads it, covering every
# weekday and the whole day, is not a business-hours statement.
_NO_RESTRICTION_REPLY = "Las visitas se agendan según la disponibilidad de los técnicos."

# Stored accented: they are rendered to the customer, and matched folded.
_WEEKDAY_NAMES = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)


def _fold(text: str) -> str:
    """Casefold, drop diacritics and collapse spacing, so matching is by words.

    Spacing is collapsed because a configured name can arrive with a stray space
    ("Mantención de  calefont", measured in production) and it is matched as a
    phrase against this text.
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_accents.split())


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _fold(text)))


def _mentions(folded_text: str, name: str) -> bool:
    """True when the whole `name` appears as a word in `folded_text`."""
    folded_name = _fold(name).strip()
    if not folded_name:
        return False
    return re.search(rf"(?<!\w){re.escape(folded_name)}(?!\w)", folded_text) is not None


def _join_es(items: list[str]) -> str:
    """Join names the way Spanish lists do: "A, B y C"."""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} y {items[-1]}"


def _current_text(state: ConversationState) -> str:
    return (state.window[-1].get("text") or "") if state.window else ""


def _asks_price(text: str) -> bool:
    return bool(_words(text) & _PRICE_TERMS)


def _day_label(days: list[int]) -> str:
    """The configured days as Spanish text: "de lunes a sábado", "lunes y jueves".

    A run of three or more consecutive days reads as a range; anything shorter is
    listed, because "de lunes a miércoles" for two days sounds like a closed
    interval the configuration does not have.
    """
    ordered = sorted({day for day in days if isinstance(day, int) and 1 <= day <= 7})
    runs: list[list[int]] = []
    for day in ordered:
        if runs and day == runs[-1][-1] + 1:
            runs[-1].append(day)
        else:
            runs.append([day])
    parts = [
        f"de {_WEEKDAY_NAMES[run[0] - 1]} a {_WEEKDAY_NAMES[run[-1] - 1]}"
        if len(run) >= 3
        else " y ".join(_WEEKDAY_NAMES[day - 1] for day in run)
        for run in runs
    ]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return f"{', '.join(parts[:-1])} y {parts[-1]}"


def _window_label(entry) -> str:
    """One configured window as text, or empty when the entry is unusable."""
    if not isinstance(entry, dict):
        return ""
    days = _day_label(entry.get("days") or [])
    opening = entry.get("open")
    closing = entry.get("close")
    if not days or not isinstance(opening, str) or not isinstance(closing, str):
        return ""
    return f"{days}, de {opening} a {closing}"


def coverage_reply(session, state: ConversationState) -> str | None:
    """The covered communes, from `coverage.communes` (S4).

    Returns ``None`` when the turn does not ask about coverage, when it names a
    commune the configuration does not cover (the existing derivation path keeps
    the policy), or when no commune is configured: no list is ever invented.
    """
    text = _current_text(state)
    if not text or _asks_price(text):
        return None
    communes = [
        commune.strip() for commune in get_coverage_communes(session) if commune.strip()
    ]
    if not communes:
        return None
    folded = _fold(text)
    words = _words(text)
    names_covered = any(_mentions(folded, commune) for commune in communes)
    if not (words & _COVERAGE_TERMS) and not (names_covered and words & _PLACE_TERMS):
        return None
    return f"Atendemos normalmente en {_join_es(communes)}."


# Terms that ask HOW LONG. The service name itself comes from the
# `booking.service_durations` keys, so this answer needs no phrase table of its
# own: a service the operator wrote is a service the customer can ask about.
_DURATION_TERMS = frozenset(
    {"dura", "duran", "duracion", "demora", "demoran", "tarda", "tardan", "tiempo"}
)


def _minutes_label(minutes: int) -> str:
    """Minutes as Spanish text: "45 minutos", "1 hora", "1 hora y 30 minutos"."""
    hours, rest = divmod(minutes, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hora" if hours == 1 else f"{hours} horas")
    if rest:
        parts.append(f"{rest} minutos")
    return " y ".join(parts) or "0 minutos"


def duration_reply(session, state: ConversationState) -> str | None:
    """How long a configured service takes, from `booking.service_durations` (S6).

    Returns ``None`` when the turn does not ask how long something takes or names
    no configured service: the KB keeps answering, and no duration is invented.
    """
    text = _current_text(state)
    if not text or _asks_price(text) or not (_words(text) & _DURATION_TERMS):
        return None
    folded = _fold(text)
    durations = get_service_durations(session)
    for service, minutes in durations.items():
        if not _mentions(folded, service):
            continue
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            continue
        return f"{service.strip()} dura {_minutes_label(minutes)}."
    return None


def _covers_every_hour(entry) -> bool:
    """True when this window restricts nothing: every weekday, 00:00 to 23:59.

    A configuration that has to exist (the offer filter reads it) but is not a
    business-hours statement. Rendering it literally would tell a customer the
    business takes visits at any hour, while the technicians' agenda is what
    actually bounds the calendar.
    """
    if not isinstance(entry, dict):
        return False
    days = entry.get("days") or []
    return (
        set(days) == {1, 2, 3, 4, 5, 6, 7}
        and entry.get("open") == "00:00"
        and entry.get("close") == "23:59"
    )


def hours_reply(session, state: ConversationState) -> str | None:
    """The configured weekly window, from `hours.schedule` (S5, S9).

    Returns ``None`` when the turn does not ask about hours, or when no window is
    configured: the KB keeps the policy and no opening time is ever invented.
    """
    text = _current_text(state)
    if not text or _asks_price(text) or not (_words(text) & _HOURS_TERMS):
        return None
    schedule = get_hours_schedule(session)
    if any(_covers_every_hour(entry) for entry in schedule):
        return _NO_RESTRICTION_REPLY
    labels = [label for label in map(_window_label, schedule) if label]
    if not labels:
        return None
    return f"Las visitas se agendan {' y '.join(labels)}."


def configuration_reply(session, state: ConversationState) -> str | None:
    """The configuration answer for this turn, if it asks one of these questions.

    Precedence is explicit and pinned by test: the first answer that recognises
    the turn owns it, so the same text can never be claimed by two of them.
    Duration comes first because naming a service is the specific case; coverage
    and hours are the general ones.
    """
    for answer in (duration_reply, coverage_reply, hours_reply):
        reply = answer(session, state)
        if reply is not None:
            return reply
    return None
