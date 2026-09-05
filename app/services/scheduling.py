"""Local appointment scheduling: timezone-safe, linked, and auditable."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Appointment, AppointmentCalendarSync, AppointmentHistory, AppointmentStatus, Case, Customer, TechnicianAvailability, User
from app.services.audit import record_audit
from app.services.events import publish_event


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


def book(session: Session, *, service: str, customer_id: int, case_id: int, technician_id: int, local_date: date, local_time: time, timezone_name: str, duration_minutes: int, actor: str) -> Appointment:
    customer = session.get(Customer, customer_id)
    case = session.get(Case, case_id)
    if customer is None or case is None or case.customer_id != customer_id:
        raise UnlinkedAppointment("appointment requires a valid customer and matching case")
    starts, ends = local_interval(local_date, local_time, timezone_name, duration_minutes)
    configured = session.scalar(select(TechnicianAvailability.id).where(TechnicianAvailability.technician_id == technician_id)) is not None
    if configured and not availability(session, technician_id, starts, ends):
        raise Unavailable("technician is not available for the requested interval")
    overlap = session.scalar(select(Appointment).where(
        Appointment.status == AppointmentStatus.BOOKED,
        ((Appointment.technician_id == technician_id) | (Appointment.customer_id == customer_id)),
        Appointment.starts_at < ends, Appointment.ends_at > starts,
    ))
    if overlap is not None:
        raise AppointmentConflict("technician or customer has an overlapping booking")
    appointment = Appointment(service=service, customer_id=customer_id, case_id=case_id, technician_id=technician_id, local_start=datetime.combine(local_date, local_time), timezone=timezone_name, starts_at=starts, ends_at=ends, duration_minutes=duration_minutes)
    session.add(appointment)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise AppointmentConflict("technician or customer has an overlapping booking") from exc
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
    customer = session.get(Customer, appointment.customer_id)
    publish_event(session, event_type="appointment.cancelled", entity_type="appointment", entity_id=appointment.id, payload={"customer_id": appointment.customer_id, "case_id": appointment.case_id, "recipient": customer.phone_e164 if customer else None, "reason": reason}, dedupe_key=f"appointment:{appointment.id}:cancelled")
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
