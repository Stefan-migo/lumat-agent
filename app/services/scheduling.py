"""Local appointment scheduling: timezone-safe, linked, and auditable."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Appointment, AppointmentCalendarSync, AppointmentHistory, AppointmentStatus, Case, Customer, TechnicianAvailability, User, UserRole
from app.services.audit import record_audit
from app.services.calendar import ICSProvider, synchronize as synchronize_calendar
from app.services.events import publish_event
from app.services.settings import get_hours_timezone


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
) -> list[tuple[date, time]]:
    """Return up to ``limit`` currently bookable local start times in a UTC window."""
    if (window_start.tzinfo is None or window_start.utcoffset() is None
            or window_end.tzinfo is None or window_end.utcoffset() is None
            or window_start >= window_end):
        raise InvalidRange("window must be timezone-aware and ordered")
    if duration_minutes <= 0:
        raise ValueError("duration must be positive")
    step_minutes = duration_minutes if step_minutes is None else step_minutes
    if step_minutes <= 0 or limit <= 0:
        raise ValueError("step and limit must be positive")
    zone = _zone(timezone_name)
    start_utc = window_start.astimezone(timezone.utc)
    end_utc = window_end.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    slots: list[tuple[date, time]] = []
    for starts in _candidate_starts(start_utc, end_utc, duration_minutes, step_minutes, now):
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


def open_slots_for_assignment(
    session: Session,
    *,
    now: datetime,
    days: int = 7,
    duration_minutes: int = 60,
    limit: int = 3,
) -> list[tuple[int, date, time]]:
    """Return deterministic slots assigned to the lowest-id available technician."""
    if now.tzinfo is None or now.utcoffset() is None or days <= 0 or limit <= 0:
        raise InvalidRange("now must be aware and days/limit must be positive")

    window_end = now.astimezone(timezone.utc) + timedelta(days=days)
    timezone_name = get_hours_timezone(session)
    assigned: dict[tuple[date, time], int] = {}
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
            slots = open_slots(
                session,
                technician_id=technician.id,
                window_start=max(now, block.starts_at),
                window_end=min(window_end, block.ends_at),
                duration_minutes=duration_minutes,
                timezone_name=timezone_name,
                limit=limit,
            )
            for local_date, local_time in slots:
                key = (local_date, local_time)
                assigned[key] = min(technician.id, assigned.get(key, technician.id))

    ordered = sorted(assigned.items(), key=lambda item: item[0])
    return [(technician_id, day, clock) for (day, clock), technician_id in ordered[:limit]]


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
    publish_event(session, event_type="appointment.booked", entity_type="appointment", entity_id=appointment.id, payload={"customer_id": customer_id, "case_id": case_id, "recipient": customer.phone_e164, "service": service}, dedupe_key=f"appointment:{appointment.id}:booked")
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
    publish_event(session, event_type="appointment.cancelled", entity_type="appointment", entity_id=appointment.id, payload={"customer_id": appointment.customer_id, "case_id": appointment.case_id, "recipient": customer.phone_e164 if customer else None, "reason": reason}, dedupe_key=f"appointment:{appointment.id}:cancelled")
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
        dedupe_key=f"appointment:{appointment.id}:rescheduled",
    )
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


def list_for_range(session: Session, from_date: date, to_date: date, timezone_name: str) -> list[tuple[Appointment, str | None, str | None, str | None, AppointmentCalendarSync | None]]:
    """Return the read-only agenda projection for an inclusive local date range."""
    zone = _zone(timezone_name)
    if from_date > to_date or (to_date - from_date).days >= 31:
        raise InvalidRange("range must be ordered and no longer than 31 days")
    starts_at = datetime.combine(from_date, time.min, tzinfo=zone).astimezone(timezone.utc)
    ends_at = datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=zone).astimezone(timezone.utc)
    statement = (
        select(Appointment, Customer.name, Case.service, User.username, AppointmentCalendarSync)
        .join(Customer, Customer.id == Appointment.customer_id)
        .join(Case, Case.id == Appointment.case_id)
        .join(User, User.id == Appointment.technician_id)
        .outerjoin(AppointmentCalendarSync, AppointmentCalendarSync.appointment_id == Appointment.id)
        .where(Appointment.starts_at >= starts_at, Appointment.starts_at < ends_at)
        .order_by(Appointment.starts_at, Appointment.id)
    )
    return list(session.execute(statement).all())
