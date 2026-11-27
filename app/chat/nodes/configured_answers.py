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
from datetime import date, datetime, time, timezone
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from sqlalchemy import select

from app.chat.nodes.booking import DEFAULT_DURATION_MINUTES
from app.chat.nodes.replies import render_reply
from app.chat.slot_window import when_label
from app.chat.state import ConversationState
from app.chat.visit_questions import asks_about_booked_visit
from app.models import Appointment, AppointmentStatus, KbChunk, KbDocument, KbVisibility
from app.services.users import technician_display_name
from app.services.prompts import render_text
from app.services.scheduling import open_slots_for_assignment
from app.services.settings import (
    get_booking_lead_minutes,
    get_coverage_communes,
    get_reply_texts,
    get_hours_schedule,
    get_hours_timezone,
    get_service_durations,
)
from app.chat.slot_window import resolve_window, window_label

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
_ASKED_PLACE_RE = re.compile(
    r"\b(?:atienden|atiende|trabajan|trabaja|llegan|llega|van|visitan|visita)\s+(?:en|a)\s+(?P<direct>[^?!,.;\n]+)|"
    r"\b(?:vivo|vives|viven|estoy|estas|estamos)\s+en\s+(?P<residence>[^?!,.;\n]+)",
    re.IGNORECASE,
)
_RM_COMMUNE_FILE = Path(__file__).resolve().parents[2] / "data" / "rm_communes.txt"
_SCHEDULE_TAIL = re.compile(
    r"(?:(?:el|este|los|cada|en|durante)\s+)?"
    r"(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo|festivos?|feriados?)s?"
    r"(?:\s+(?:por la|en la)\s+(?:manana|tarde|noche))?"
)

# The owner's decision: every upcoming visit is named, not only the nearest one.
# Three is the same ceiling the reschedule menu uses, so a customer never reads a
# list longer than the one cancellation and rescheduling already show.
MAX_STATUS_VISITS = 3

# The preview asks the agenda for a wide slice and keeps one slot per day: the
# service returns the earliest slots, which for a free agenda are consecutive
# hours of the same afternoon.
_PREVIEW_UNIVERSE = 30

# The day and franja words `resolve_window` can turn into a window. Matched
# against the folded words: `_fold` drops diacritics, so "mañana" arrives as
# "manana". A turn that carries none of these cannot name a window, and reading
# the business clock for it would make the answer depend on settings nobody asked
# about.
_WINDOW_TERMS = frozenset(
    {
        "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "sabados",
        "domingo", "domingos", "hoy", "manana", "tarde", "noche", "mediodia",
        "cualquier", "finde", "semana", "proximo", "proxima",
        "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
        "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    }
)

# Business-hours vocabulary: the verbs and nouns of *when the business works*,
# not of a slot. A turn carrying one of these asks when the business opens,
# closes or works ("¿hasta qué hora abren el sábado?", "¿trabajan en domingo?")
# and the configured week is its answer. Deliberately excludes `hora`/`horas`:
# in Chilean usage "¿tienen hora el sábado?" asks for an appointment slot, so the
# agenda owns that turn. Kept apart from `_HOURS_TERMS`, which also holds the
# weekday words themselves.
_HOURS_VOCABULARY = frozenset(
    {
        "horario", "horarios", "abren", "abrimos", "cierran", "cerramos",
        "abierto", "abiertos", "cerrado", "cerrados",
        "trabajan", "trabaja", "trabajamos",
    }
)

_AVAILABILITY_TERMS = frozenset(
    {
        "disponible",
        "disponibles",
        "disponibilidad",
        "cupo",
        "cupos",
        "agenda",
        "agendar",
        "reservar",
        "reserva",
    }
)

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


@lru_cache(maxsize=1)
def _load_rm_communes() -> tuple[str, ...]:
    """Load the curated Región Metropolitana commune names from package data."""
    return tuple(
        line.strip()
        for line in _RM_COMMUNE_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _asked_place(text: str, known_places: list[str]) -> str | None:
    """Return the customer's spelling of a known commune in the place complement."""
    match = _ASKED_PLACE_RE.search(text)
    if match is None:
        return None
    place = re.sub(
        r"[,.;!?¿¡]+", " ", match.group("direct") or match.group("residence")
    )
    original_words = place.split()
    for commune in sorted(known_places, key=lambda name: len(_fold(name)), reverse=True):
        commune_word_count = len(_fold(commune).split())
        place_name = " ".join(original_words[:commune_word_count])
        if _fold(place_name) != _fold(commune):
            continue
        tail = " ".join(original_words[commune_word_count:])
        if not tail or _SCHEDULE_TAIL.fullmatch(_fold(tail)):
            return place_name
    return None


def _customer_kb_mentions_place(session, place: str) -> bool:
    """Check active, global customer KB chunks without paying for embeddings."""
    escaped_place = place.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    coverage_language = (
        KbChunk.content.ilike("%cobertura%")
        | KbChunk.content.ilike("%cubr%")
        | KbChunk.content.ilike("%atend%")
    )
    statement = (
        select(KbChunk.id)
        .join(KbDocument, KbChunk.document_id == KbDocument.id)
        .where(
            KbDocument.active.is_(True),
            KbDocument.visibility == KbVisibility.CUSTOMER,
            KbDocument.project_id.is_(None),
            KbChunk.version == KbDocument.active_version,
            KbChunk.content.ilike(f"%{escaped_place}%", escape="\\"),
            coverage_language,
        )
        .limit(1)
    )
    return session.scalar(statement) is not None


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
    """Answer a named place from `coverage.communes`, or the configured policy (S4).

    Direct place questions are answered only when the complement matches a
    configured commune or a curated Región Metropolitana commune. Configured
    places receive the normal confirmation; other known RM communes receive the
    advisor-coordination policy. Unknown places remain with normal KB retrieval.
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
    known_places = communes + list(_load_rm_communes())
    place = _asked_place(text, known_places)
    if place and words & _PLACE_TERMS:
        place_folded = _fold(place)
        if any(_mentions(place_folded, commune) for commune in communes):
            return f"Atendemos normalmente en {_join_es(communes)}."
        if _customer_kb_mentions_place(session, place):
            return None
        reply_text = get_reply_texts(session)["coverage_out_of_area"]
        return (
            render_text(reply_text, comuna=place)
            if "{{comuna}}" in reply_text
            else reply_text
        )
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


def _schedule_closes_day(session, window) -> bool:
    """True when the configured week does not cover the day the customer named.

    A day the business works and is full and a day the week closes are different
    facts, and the same sentence cannot carry both: "no me quedan horarios"
    implies there were hours to run out of. A window that restricts nothing (the
    24/7 placeholder the offer filter needs) is not a closing statement, so it
    never takes this branch.
    """
    if window is None or window.day is None:
        return False
    schedule = get_hours_schedule(session)
    if not schedule or any(_covers_every_hour(entry) for entry in schedule):
        return False
    weekday = window.day.isoweekday()
    return not any(
        weekday in (entry.get("days") or [])
        for entry in schedule
        if isinstance(entry, dict)
    )


def appointment_status_reply(session, state: ConversationState) -> str | None:
    """Answer a question about the visit the customer already holds.

    Measured production case (2026-11-27, conversation 50): «Tengo una visita para
    el lunes, puedes confirmarme que técnico va?» was answered with free hours by
    `availability_reply`, and «Tengo una hora agendada para el lunes» was stored as
    a day preference by `capture`. The appointment was `booked` throughout.

    The answer reads the same rows `manage` reads — `booked`, `starts_at > now` —
    and renders date and hour in the customer's local time, the service and the
    technician. Owner decisions pinned here: the technician is always named, every
    upcoming visit is named, and a visit nobody is named on says "por asignar"
    rather than deriving to a person. Deterministic: no model call.

    Returns None for every other turn, including an explicit change request, which
    belongs to `manage` (`asks_about_booked_visit` excludes it).
    """
    if not getattr(state, "customer_id", None):
        return None
    text = _current_text(state)
    if not text or not asks_about_booked_visit(text):
        return None
    now = datetime.now(timezone.utc)
    appointments = session.scalars(
        select(Appointment)
        .where(
            Appointment.customer_id == state.customer_id,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.starts_at > now,
        )
        .order_by(Appointment.starts_at)
        .limit(MAX_STATUS_VISITS)
    ).all()
    texts = get_reply_texts(session)
    if not appointments:
        # Nothing to name is a fact to state, not a reason to offer free hours for
        # a visit the customer says she already has.
        return render_reply(texts, "appointment_status_none")
    unassigned = render_reply(texts, "appointment_technician_unassigned")
    lines = [
        render_reply(
            texts,
            "appointment_line",
            fecha=when_label(appointment.local_start),
            servicio=appointment.service,
            tecnico=technician_display_name(session, appointment.technician_id)
            or unassigned,
        )
        for appointment in appointments
    ]
    if len(lines) == 1:
        return render_reply(texts, "appointment_status_one", visita=lines[0])
    return render_reply(
        texts,
        "appointment_status_many",
        opciones="\n".join(f"{index}. {line}" for index, line in enumerate(lines, 1)),
    )


def availability_reply(session, state: ConversationState) -> str | None:
    """Preview real technician slots without creating a booking offer.

    The preview horizon is seven days from now, not the calendar week, so its
    wording deliberately does not claim "esta semana".

    Two rules, both measured on the corpus before they were code: a general question
    is answered with **different days**, because three consecutive half-hours of one
    day is the booking menu and scored 0 when the customer asked which days exist;
    and a question that names a day is answered with that day, because naming the
    requested day is what the customer asked for.

    `odd/tasks/saturday-day-continuity.md` added two boundaries to that. A day the
    customer names in question form reaches the agenda even without an availability
    term ("¿Pueden el sábado?"), while a question about the configured week keeps
    the week ("¿hasta qué hora abren el sábado?", "¿trabajan en domingo?") — the
    `_HOURS_VOCABULARY` sentence, still owned by `hours_reply`. And a day with no
    eligible slots answers from configuration instead of falling through to the
    policy sentence that made the reported defect invisible.
    """
    text = _current_text(state)
    if not text or _asks_price(text):
        return None
    words = _words(text)
    has_term = bool(words & _AVAILABILITY_TERMS)
    # Only a day/franja word can become a window, so the business clock and the
    # settings table are read for exactly those turns. A question about the
    # configured hours ("¿cuál es el horario?") is answered by `hours_reply`
    # without this module ever asking for the timezone or the reply texts.
    names_a_window = bool(words & _WINDOW_TERMS)
    if not has_term and (words & _HOURS_VOCABULARY):
        # "¿Hasta qué hora abren el sábado?" names a day and asks about the week:
        # answering it with slot times turns a closing-time question into a menu.
        return None
    asks = (
        "?" in text
        or "¿" in text
        or bool(words & {"pueden", "puede", "atienden", "tienen", "hay", "dan", "dar"})
    )
    if not has_term and not (names_a_window and asks):
        return None

    now = datetime.now(timezone.utc)
    window = (
        resolve_window(text, today=_local_today(session, now)) if names_a_window else None
    )
    if window is None and not has_term:
        return None
    slots = open_slots_for_assignment(
        session,
        now=now,
        days=7,
        duration_minutes=DEFAULT_DURATION_MINUTES,
        limit=3 if window is not None else _PREVIEW_UNIVERSE,
        lead_minutes=get_booking_lead_minutes(session),
        window=window,
    )
    if not slots:
        if window is None:
            # Nothing to render: `hours_reply` keeps this turn, and the reply
            # texts stay unread so the answer never depends on them.
            return None
        if _schedule_closes_day(session, window) and (words & _HOURS_VOCABULARY):
            # The customer asked whether the business works that day, and it does
            # not: "no me quedan horarios" would claim it does and is merely full.
            # The configured week is the honest answer, and `hours_reply` renders
            # it. A question about a visit ("¿Pueden el sábado?") keeps the slot
            # answer below even when the day is closed.
            return None
        return render_reply(
            get_reply_texts(session),
            "availability_preview_day_none",
            dia=window_label(window),
        )
    texts = get_reply_texts(session)
    chosen = slots[:3] if window is not None else _one_slot_per_day(slots)
    if window is None:
        # Which days have room is the question; naming hours here reads as a promise
        # the conversation has not earned yet.
        days = _join_es(
            [
                f"{_WEEKDAY_NAMES[slot_day.isoweekday() - 1]} {slot_day.day}"
                for _, slot_day, _ in chosen
            ]
        )
        return render_reply(texts, "availability_preview", dias=days)
    # A named day was asked for, so its hours are the answer.
    first: date = chosen[0][1]
    hours = _join_es([f"{slot_time:%H:%M}" for _, _, slot_time in chosen])
    return render_reply(
        texts,
        "availability_preview_day",
        dia=f"{_WEEKDAY_NAMES[first.isoweekday() - 1]} {first.day}",
        horas=f"a las {hours}",
    )


def _local_today(session, now: datetime) -> date:
    """Today where the business lives, which is where `resolve_window` reads days."""
    from zoneinfo import ZoneInfo

    return now.astimezone(ZoneInfo(get_hours_timezone(session))).date()


def _one_slot_per_day(slots: Sequence[tuple[int, date, time]]) -> list[tuple[int, date, time]]:
    """The first slot of each distinct day, up to three days.

    `open_slots_for_assignment` returns the earliest slots, which for a free agenda
    are consecutive hours of the same afternoon. Which days have room is the
    question this answer serves.
    """
    chosen: list[tuple[int, date, time]] = []
    seen: set[date] = set()
    for slot in slots:
        if slot[1] in seen:
            continue
        seen.add(slot[1])
        chosen.append(slot)
        if len(chosen) == 3:
            break
    return chosen


def configuration_reply(session, state: ConversationState) -> str | None:
    """The configuration answer for this turn, if it asks one of these questions.

    Precedence is explicit and pinned by test: the first answer that recognises
    the turn owns it, so the same text can never be claimed by two of them.
    Duration is most specific, followed by coverage, then schedule. The place
    branch is restricted to known communes, so weekdays reach the hours answer.
    """
    for answer in (
        duration_reply,
        coverage_reply,
        # An appointment the customer holds is a fact the configuration answers
        # cannot state, and it outranks the free-agenda preview: without this row
        # the measured question about a booked visit read three free hours back.
        appointment_status_reply,
        availability_reply,
        hours_reply,
    ):
        reply = answer(session, state)
        if reply is not None:
            return reply
    return None
