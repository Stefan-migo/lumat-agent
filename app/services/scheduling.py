"""Local appointment scheduling: timezone-safe, linked, and auditable."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.chat.slot_window import SlotWindow
from app.models import Appointment, AppointmentCalendarSync, AppointmentHistory, AppointmentStatus, Case, Customer, TechnicianAvailability, User, UserRole
from app.services.audit import record_audit
from app.services.calendar import ICSProvider, synchronize as synchronize_calendar
from app.services.events import publish_event
from app.services.notifications import notify_admins
from app.services.settings import (
    get_hours_schedule,
    get_hours_timezone,
    validate_hours_schedule,
)


_OVERLAP_CONSTRAINTS = {
    "appointments_technician_no_overlap",
    "appointments_customer_no_overlap",
}


def _is_overlap_violation(exc: IntegrityError) -> bool:
    return getattr(getattr(exc.orig, "diag", None), "constraint_name", None) in _OVERLAP_CONSTRAINTS


def _sync_existing_calendar(session: Session, appointment: Appointment, *, actor: str) -> None:
    if session.scalar(select(AppointmentCalendarSync.id).where(
        AppointmentCalendarSync.appointment_id == appointment.id
    )) is not None:
        synchronize_calendar(session, appointment, provider=ICSProvider(), actor=actor)


class NonexistentLocalTime(ValueError):
    pass


class AmbiguousLocalTime(ValueError):
    pass


class UnlinkedAppointment(ValueError):
    pass


class AppointmentConflict(ValueError):
    pass


class Unavailable(ValueError):
    pass


class InvalidTimezone(ValueError):
    pass


class InvalidRange(ValueError):
    pass


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise InvalidTimezone(f"unknown timezone: {name}") from exc


def local_interval(day: date, clock: time, timezone_name: str, duration_minutes: int) -> tuple[datetime, datetime]:
    if duration_minutes <= 0:
        raise ValueError("duration must be positive")
    zone = _zone(timezone_name)
    naive = datetime.combine(day, clock)
    candidates = [naive.replace(tzinfo=zone, fold=fold) for fold in (0, 1)]
    valid = [
        candidate
        for candidate in candidates
        if candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == naive
    ]
    if not valid:
        raise NonexistentLocalTime(f"nonexistent local time: {naive}")
    if len(valid) > 1 and valid[0].utcoffset() != valid[1].utcoffset():
        raise AmbiguousLocalTime(f"ambiguous local time: {naive}")
    starts = valid[0].astimezone(timezone.utc)
    return starts, starts + timedelta(minutes=duration_minutes)


def _history(session: Session, appointment: Appointment, *, actor: str, action: str, previous: AppointmentStatus | None, details: dict | None = None) -> None:
    session.add(AppointmentHistory(appointment_id=appointment.id, actor=actor, action=action, from_status=previous, to_status=appointment.status, details=details))


def _validate_slot(session: Session, *, customer_id: int, technician_id: int, local_date: date, local_time: time, timezone_name: str, duration_minutes: int, exclude_appointment_id: int | None = None) -> tuple[datetime, datetime]:
    starts, ends = local_interval(local_date, local_time, timezone_name, duration_minutes)
    _validate_interval(session, customer_id=customer_id, technician_id=technician_id, starts=starts, ends=ends, exclude_appointment_id=exclude_appointment_id)
    return starts, ends


def _validate_interval(session: Session, *, customer_id: int | None, technician_id: int, starts: datetime, ends: datetime, exclude_appointment_id: int | None = None) -> None:
    configured = session.scalar(select(TechnicianAvailability.id).where(TechnicianAvailability.technician_id == technician_id)) is not None
    if configured and not availability(session, technician_id, starts, ends):
        raise Unavailable("technician is not available for the requested interval")
    overlap = Appointment.technician_id == technician_id
    if customer_id is not None:
        overlap = overlap | (Appointment.customer_id == customer_id)
    statement = select(Appointment).where(
        Appointment.status == AppointmentStatus.BOOKED,
        overlap,
        Appointment.starts_at < ends, Appointment.ends_at > starts,
    )
    if exclude_appointment_id is not None:
        statement = statement.where(Appointment.id != exclude_appointment_id)
    if session.scalar(statement) is not None:
        raise AppointmentConflict("technician or customer has an overlapping booking")


# S1 (chatbot-experiencia): offered starts sit on a half-hour grid. Before this
# the first candidate was the window start itself, so a customer who wrote at
# 10:04 was offered 10:04, 11:04 and 12:04 and the appointment was stored at
# 10:04:32 — a time nobody reads as a slot, on a visit nobody could staff.
SLOT_GRID_MINUTES = 30


def _align_to_grid(moment: datetime, grid_minutes: int) -> datetime:
    """Round ``moment`` up to the next ``grid_minutes`` boundary, seconds dropped.

    Alignment happens in UTC, which is the same instant grid as Chilean local
    time: the offset is a whole number of hours, so a 30-minute grid lines up
    either way.
    """
    truncated = moment.replace(second=0, microsecond=0)
    remainder = truncated.minute % grid_minutes
    if not remainder:
        return truncated
    return truncated + timedelta(minutes=grid_minutes - remainder)


def _candidate_starts(window_start: datetime, window_end: datetime, duration_minutes: int, step_minutes: int, now: datetime):
    step = timedelta(minutes=step_minutes)
    duration = timedelta(minutes=duration_minutes)
    candidate = window_start
    while candidate + duration <= window_end:
        if candidate >= now:
            yield candidate
        candidate += step


def open_slots(
    session: Session,
    *,
    technician_id: int,
    window_start: datetime,
    window_end: datetime,
    duration_minutes: int,
    timezone_name: str,
    limit: int = 5,
    step_minutes: int | None = None,
    lead_minutes: int = 0,
    grid_minutes: int = SLOT_GRID_MINUTES,
    now: datetime | None = None,
) -> list[tuple[date, time]]:
    """Return up to ``limit`` bookable local start times in a UTC window.

    Candidates sit on a ``grid_minutes`` grid and start no earlier than
    ``lead_minutes`` from ``now`` (the real clock when the caller does not pin
    it). The lead time is not decoration: a visit offered for "right now" cannot
    be staffed — the office has to be told and the technician has to arrive.
    """
    if (window_start.tzinfo is None or window_start.utcoffset() is None
            or window_end.tzinfo is None or window_end.utcoffset() is None
            or window_start >= window_end):
        raise InvalidRange("window must be timezone-aware and ordered")
    if duration_minutes <= 0:
        raise ValueError("duration must be positive")
    if grid_minutes <= 0:
        raise ValueError("grid must be positive")
    if lead_minutes < 0:
        raise ValueError("lead must not be negative")
    step_minutes = grid_minutes if step_minutes is None else step_minutes
    if step_minutes <= 0 or limit <= 0:
        raise ValueError("step and limit must be positive")
    zone = _zone(timezone_name)
    start_utc = _align_to_grid(window_start.astimezone(timezone.utc), grid_minutes)
    end_utc = window_end.astimezone(timezone.utc)
    earliest = (now or datetime.now(timezone.utc)) + timedelta(minutes=lead_minutes)
    slots: list[tuple[date, time]] = []
    for starts in _candidate_starts(start_utc, end_utc, duration_minutes, step_minutes, earliest):
        local = starts.astimezone(zone)
        local_date, local_time = local.date(), local.timetz().replace(tzinfo=None)
        try:
            validated_start, validated_end = local_interval(local_date, local_time, timezone_name, duration_minutes)
            if validated_start != starts:
                continue
            _validate_interval(session, customer_id=None, technician_id=technician_id, starts=validated_start, ends=validated_end)
        except (NonexistentLocalTime, AmbiguousLocalTime, Unavailable, AppointmentConflict):
            continue
        slots.append((local_date, local_time))
        if len(slots) == limit:
            break
    return slots


def _daily_loads(
    session: Session,
    *,
    technician_ids: list[int],
    zone: ZoneInfo,
    now: datetime,
    window_end: datetime,
) -> dict[tuple[int, date], int]:
    """Booked visits per technician and local day, inside the offered window.

    Counted from the agenda itself, never from the offers this call is about to
    build: an offer is not a visit until the customer takes it, and counting
    offers would let one unanswered offer push the next one to somebody else.
    """
    day_start = now.astimezone(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = session.execute(
        select(Appointment.technician_id, Appointment.starts_at).where(
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.technician_id.in_(technician_ids),
            Appointment.starts_at >= day_start.astimezone(timezone.utc),
            Appointment.starts_at < window_end,
        )
    ).all()
    loads: dict[tuple[int, date], int] = {}
    for technician_id, starts_at in rows:
        key = (technician_id, starts_at.astimezone(zone).date())
        loads[key] = loads.get(key, 0) + 1
    return loads


def _least_loaded(
    candidates: set[int], loads: dict[tuple[int, date], int], day: date, rotation: int
) -> int:
    """The candidate with the fewest visits that day; a tie alternates by id.

    The rotation is what turns a tie into a round-robin instead of a rule that
    always hands the slot to the lowest id, which is how one technician ended up
    carrying every visit while the other stayed empty.
    """
    ordered = sorted(candidates)
    lowest = min(loads.get((technician_id, day), 0) for technician_id in ordered)
    tied = [
        technician_id
        for technician_id in ordered
        if loads.get((technician_id, day), 0) == lowest
    ]
    return tied[rotation % len(tied)]


def _matches_window(slot: tuple[date, time], window: SlotWindow | None) -> bool:
    """Whether a local slot satisfies the day and franja a customer asked for."""

    if window is None:
        return True
    day, clock = slot
    if window.day is not None and day != window.day:
        return False
    if window.franja is not None and not (window.franja[0] <= clock < window.franja[1]):
        return False
    return True


def _minutes_of_day(value: str) -> int:
    """A `"HH:MM"` clock as minutes since midnight, so an end can never wrap."""
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def business_window(schedule: list[dict]) -> list[tuple[frozenset[int], int, int]]:
    """Parse `hours.schedule` into (weekdays, open minute, close minute) entries.

    Empty or malformed input returns an empty list, which every caller reads as
    "no restriction": unreadable legacy data must not empty the calendar, the
    same fail-open rule `is_open_at` documents.
    """
    try:
        validate_hours_schedule(schedule)
    except (TypeError, ValueError):
        return []
    return [
        (
            frozenset(entry["days"]),
            _minutes_of_day(entry["open"]),
            _minutes_of_day(entry["close"]),
        )
        for entry in schedule
    ]


def fits_business_window(
    slot: tuple[date, time],
    duration_minutes: int,
    window_entries: list[tuple[frozenset[int], int, int]],
) -> bool:
    """Whether the WHOLE visit fits inside one configured business-window entry.

    Both bounds are required. Filtering only the start would keep offering 17:30
    for a 60-minute visit at a business that closes at 18:00 — an offer nobody
    can honour, which is the incoherence this filter exists to remove.
    """
    if not window_entries:
        return True
    day, clock = slot
    start = _minutes_of_day(f"{clock.hour:02d}:{clock.minute:02d}")
    end = start + duration_minutes
    return any(
        day.isoweekday() in days and opens <= start and end <= closes
        for days, opens, closes in window_entries
    )


def open_slots_for_assignment(
    session: Session,
    *,
    now: datetime,
    days: int = 7,
    duration_minutes: int = 60,
    limit: int = 3,
    lead_minutes: int = 0,
    window: SlotWindow | None = None,
) -> list[tuple[int, date, time]]:
    """Return deterministic slots assigned by the day's load, not by id.

    Every technician that can cover a slot is a candidate; among them the one
    with the fewest visits already booked that local day wins, and a tie
    alternates by id so two idle technicians share the offers instead of the
    lowest id absorbing all of them.

    ``window`` (S1 agenda-preferencia) narrows the candidates to the day and
    franja the customer asked for. A named day past ``days`` is still reachable:
    the request itself is what extends the search, so "para el viernes 30" is
    answered instead of silently ignored.
    """
    if now.tzinfo is None or now.utcoffset() is None or days <= 0 or limit <= 0:
        raise InvalidRange("now must be aware and days/limit must be positive")

    window_end = now.astimezone(timezone.utc) + timedelta(days=days)
    timezone_name = get_hours_timezone(session)
    window_entries = business_window(get_hours_schedule(session))
    zone = _zone(timezone_name)
    if window is not None and window.day is not None:
        requested_end = datetime.combine(window.day + timedelta(days=1), time.min, tzinfo=zone)
        window_end = max(window_end, requested_end.astimezone(timezone.utc))
    candidates: dict[tuple[date, time], set[int]] = {}
    technicians = session.scalars(
        select(User).where(User.role == UserRole.TECNICO).order_by(User.id)
    ).all()
    for technician in technicians:
        blocks = session.scalars(
            select(TechnicianAvailability)
            .where(
                TechnicianAvailability.technician_id == technician.id,
                TechnicianAvailability.available.is_(True),
                TechnicianAvailability.starts_at < window_end,
                TechnicianAvailability.ends_at > now,
            )
            .order_by(TechnicianAvailability.starts_at, TechnicianAvailability.id)
        ).all()
        for block in blocks:
            # The block scan must be wide enough to survive the window filter: the
            # filter runs *after* the scan, so capping the scan at the panel limit
            # would hide an afternoon that starts past the first `limit` starts.
            # One candidate per minute bounds every grid start the block allows.
            scan_limit = limit
            if window is not None:
                scan_limit = max(limit, int((block.ends_at - block.starts_at).total_seconds() // 60))
            slots = open_slots(
                session,
                technician_id=technician.id,
                window_start=max(now, block.starts_at),
                window_end=min(window_end, block.ends_at),
                duration_minutes=duration_minutes,
                timezone_name=timezone_name,
                limit=scan_limit,
                lead_minutes=lead_minutes,
                now=now,
            )
            for local_date, local_time in slots:
                candidates.setdefault((local_date, local_time), set()).add(technician.id)

    loads = _daily_loads(
        session,
        technician_ids=[technician.id for technician in technicians],
        zone=zone,
        now=now,
        window_end=window_end,
    )
    ordered = [
        (slot, coverers)
        for slot, coverers in sorted(candidates.items(), key=lambda item: item[0])
        if _matches_window(slot, window)
        and fits_business_window(slot, duration_minutes, window_entries)
    ]
    return [
        (_least_loaded(coverers, loads, day, rotation), day, clock)
        for rotation, ((day, clock), coverers) in enumerate(ordered[:limit])
    ]


def book(session: Session, *, service: str, customer_id: int, case_id: int, technician_id: int, local_date: date, local_time: time, timezone_name: str, duration_minutes: int, actor: str) -> Appointment:
    customer = session.get(Customer, customer_id)
    case = session.get(Case, case_id)
    if customer is None or case is None or case.customer_id != customer_id:
        raise UnlinkedAppointment("appointment requires a valid customer and matching case")
    starts, ends = _validate_slot(session, customer_id=customer_id, technician_id=technician_id, local_date=local_date, local_time=local_time, timezone_name=timezone_name, duration_minutes=duration_minutes)
    appointment = Appointment(service=service, customer_id=customer_id, case_id=case_id, technician_id=technician_id, local_start=datetime.combine(local_date, local_time), timezone=timezone_name, starts_at=starts, ends_at=ends, duration_minutes=duration_minutes)
    session.add(appointment)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        if _is_overlap_violation(exc):
            raise AppointmentConflict("technician or customer has an overlapping booking") from exc
        raise
    _history(session, appointment, actor=actor, action="booked", previous=None)
    record_audit(session, actor=actor, action="appointment.booked", entity="appointment", entity_id=str(appointment.id), after={"customer_id": customer_id, "case_id": case_id, "technician_id": technician_id})
    dedupe_key = f"appointment:{appointment.id}:booked"
    # ponytail: only the chat node books as "assistant" (it confirms in-channel); every
    # other caller is the panel. Revisit if a third booking origin appears.
    origin = "assistant" if actor == "assistant" else "panel"
    publish_event(session, event_type="appointment.booked", entity_type="appointment", entity_id=appointment.id, payload={"customer_id": customer_id, "case_id": case_id, "recipient": customer.phone_e164, "service": service, "origin": origin}, dedupe_key=dedupe_key)
    notify_admins(session, title="Nueva visita agendada", content=f"Se agendó una visita de {service}.", source="appointment", source_id=appointment.id, dedupe_key=dedupe_key)
    return appointment


def cancel(session: Session, appointment: Appointment, *, actor: str, reason: str | None = None) -> Appointment:
    if appointment.status is not AppointmentStatus.BOOKED:
        raise ValueError("only booked appointments can be cancelled")
    previous = appointment.status
    appointment.status = AppointmentStatus.CANCELLED
    session.flush()
    _history(session, appointment, actor=actor, action="cancelled", previous=previous, details={"reason": reason} if reason else None)
    record_audit(session, actor=actor, action="appointment.cancelled", entity="appointment", entity_id=str(appointment.id), after={"reason": reason})
    _sync_existing_calendar(session, appointment, actor=actor)
    customer = session.get(Customer, appointment.customer_id)
    dedupe_key = f"appointment:{appointment.id}:cancelled"
    publish_event(session, event_type="appointment.cancelled", entity_type="appointment", entity_id=appointment.id, payload={"customer_id": appointment.customer_id, "case_id": appointment.case_id, "recipient": customer.phone_e164 if customer else None, "reason": reason}, dedupe_key=dedupe_key)
    notify_admins(session, title="Visita cancelada", content=f"Se canceló la visita de {appointment.service}.", source="appointment", source_id=appointment.id, dedupe_key=dedupe_key)
    return appointment


def close(session: Session, appointment: Appointment, *, outcome: AppointmentStatus, actor: str, reason: str | None = None) -> Appointment:
    if appointment.status is not AppointmentStatus.BOOKED:
        raise ValueError("only booked appointments can be closed")
    if outcome not in (AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW):
        raise ValueError("invalid outcome")
    previous = appointment.status
    appointment.status = outcome
    session.flush()
    _history(session, appointment, actor=actor, action=outcome.value, previous=previous, details={"reason": reason} if reason else None)
    record_audit(session, actor=actor, action=f"appointment.{outcome.value}", entity="appointment", entity_id=str(appointment.id), after={"outcome": outcome.value, "reason": reason})
    customer = session.get(Customer, appointment.customer_id)
    dedupe_key = f"appointment:{appointment.id}:{outcome.value}"
    publish_event(
        session,
        event_type=f"appointment.{outcome.value}",
        entity_type="appointment",
        entity_id=appointment.id,
        payload={"customer_id": appointment.customer_id, "case_id": appointment.case_id,
                 "recipient": customer.phone_e164 if customer else None, "outcome": outcome.value},
        dedupe_key=dedupe_key,
    )
    if outcome is AppointmentStatus.NO_SHOW:
        notify_admins(session, title="Visita no realizada", content=f"La visita de {appointment.service} quedó marcada como no asistida.", source="appointment", source_id=appointment.id, dedupe_key=dedupe_key)
    return appointment


def reschedule(session: Session, appointment: Appointment, *, local_date: date, local_time: time, timezone_name: str, duration_minutes: int, technician_id: int, actor: str) -> Appointment:
    if appointment.status is not AppointmentStatus.BOOKED:
        raise ValueError("only booked appointments can be rescheduled")
    starts, ends = _validate_slot(session, customer_id=appointment.customer_id, technician_id=technician_id, local_date=local_date, local_time=local_time, timezone_name=timezone_name, duration_minutes=duration_minutes, exclude_appointment_id=appointment.id)
    previous = appointment.status
    from_start = appointment.local_start.isoformat()
    from_technician_id = appointment.technician_id
    appointment.local_start = datetime.combine(local_date, local_time)
    appointment.timezone = timezone_name
    appointment.starts_at = starts
    appointment.ends_at = ends
    appointment.duration_minutes = duration_minutes
    appointment.technician_id = technician_id
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        if _is_overlap_violation(exc):
            raise AppointmentConflict("technician or customer has an overlapping booking") from exc
        raise
    details = {"from_start": from_start, "to_start": appointment.local_start.isoformat(), "from_technician_id": from_technician_id, "to_technician_id": technician_id}
    _history(session, appointment, actor=actor, action="rescheduled", previous=previous, details=details)
    record_audit(session, actor=actor, action="appointment.rescheduled", entity="appointment", entity_id=str(appointment.id), after=details)
    _sync_existing_calendar(session, appointment, actor=actor)
    customer = session.get(Customer, appointment.customer_id)
    dedupe_key = f"appointment:{appointment.id}:rescheduled"
    publish_event(
        session,
        event_type="appointment.rescheduled",
        entity_type="appointment",
        entity_id=appointment.id,
        payload={
            "customer_id": appointment.customer_id,
            "case_id": appointment.case_id,
            "recipient": customer.phone_e164 if customer else None,
            **details,
        },
        dedupe_key=dedupe_key,
    )
    notify_admins(session, title="Visita reagendada", content=f"Se actualizó la fecha de la visita de {appointment.service}.", source="appointment", source_id=appointment.id, dedupe_key=dedupe_key)
    return appointment


def availability(session: Session, technician_id: int, starts_at: datetime, ends_at: datetime) -> bool:
    if ends_at <= starts_at:
        raise ValueError("availability interval must be positive")
    return session.scalar(select(TechnicianAvailability.id).where(TechnicianAvailability.technician_id == technician_id, TechnicianAvailability.available.is_(True), TechnicianAvailability.starts_at <= starts_at, TechnicianAvailability.ends_at >= ends_at)) is not None


def add_availability(session: Session, *, technician_id: int, starts_at: datetime, ends_at: datetime, available: bool = True) -> TechnicianAvailability:
    if ends_at <= starts_at:
        raise ValueError("availability interval must be positive")
    block = TechnicianAvailability(
        technician_id=technician_id,
        starts_at=starts_at,
        ends_at=ends_at,
        available=available,
    )
    session.add(block)
    session.flush()
    return block


def list_overdue(session: Session, *, now: datetime | None = None) -> list[tuple[Appointment, str | None, str | None, str | None, str | None, str | None, AppointmentCalendarSync | None]]:
    """Return booked appointments and their agenda projection, oldest first."""
    cutoff = now or datetime.now(timezone.utc)
    statement = (
        select(Appointment, Customer.name, Customer.address, Customer.comuna, Case.service, User.username, AppointmentCalendarSync)
        .join(Customer, Customer.id == Appointment.customer_id)
        .join(Case, Case.id == Appointment.case_id)
        .join(User, User.id == Appointment.technician_id)
        .outerjoin(AppointmentCalendarSync, AppointmentCalendarSync.appointment_id == Appointment.id)
        .where(
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.starts_at < cutoff,
        )
        .order_by(Appointment.starts_at, Appointment.id)
    )
    return list(session.execute(statement).all())


def list_for_customer(session: Session, customer_id: int) -> list[Appointment]:
    return list(session.scalars(select(Appointment).where(Appointment.customer_id == customer_id).order_by(Appointment.starts_at, Appointment.id)))


def list_for_technician(session: Session, technician_id: int) -> list[tuple[Appointment, Customer, Case]]:
    statement = (
        select(Appointment, Customer, Case)
        .join(Customer, Customer.id == Appointment.customer_id)
        .join(Case, Case.id == Appointment.case_id)
        .where(Appointment.technician_id == technician_id)
        .order_by(Appointment.starts_at, Appointment.id)
    )
    return list(session.execute(statement).all())


def list_for_range(session: Session, from_date: date, to_date: date, timezone_name: str) -> list[tuple[Appointment, str | None, str | None, str | None, str | None, str | None, AppointmentCalendarSync | None]]:
    """Return the read-only agenda projection for an inclusive local date range."""
    zone = _zone(timezone_name)
    if from_date > to_date or (to_date - from_date).days >= 31:
        raise InvalidRange("range must be ordered and no longer than 31 days")
    starts_at = datetime.combine(from_date, time.min, tzinfo=zone).astimezone(timezone.utc)
    ends_at = datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=zone).astimezone(timezone.utc)
    statement = (
        select(Appointment, Customer.name, Customer.address, Customer.comuna, Case.service, User.username, AppointmentCalendarSync)
        .join(Customer, Customer.id == Appointment.customer_id)
        .join(Case, Case.id == Appointment.case_id)
        .join(User, User.id == Appointment.technician_id)
        .outerjoin(AppointmentCalendarSync, AppointmentCalendarSync.appointment_id == Appointment.id)
        .where(Appointment.starts_at >= starts_at, Appointment.starts_at < ends_at)
        .order_by(Appointment.starts_at, Appointment.id)
    )
    return list(session.execute(statement).all())
