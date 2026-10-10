"""Weekly technician schedule persistence and availability materialization."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import TechnicianAvailability, TechnicianWeeklySchedule
from app.services import scheduling
from app.services.settings import get_hours_timezone


class InvalidSchedule(ValueError):
    """A weekly schedule entry is invalid or duplicated."""


def _entries(session: Session, technician_id: int) -> list[TechnicianWeeklySchedule]:
    return session.scalars(
        select(TechnicianWeeklySchedule)
        .where(TechnicianWeeklySchedule.technician_id == technician_id)
        .order_by(TechnicianWeeklySchedule.weekday)
    ).all()


def get_schedule(session: Session, technician_id: int) -> list[dict]:
    return [
        {"weekday": row.weekday, "opens_at": row.opens_at, "closes_at": row.closes_at}
        for row in _entries(session, technician_id)
    ]


def _validate(entries: list[dict]) -> None:
    weekdays: set[int] = set()
    for entry in entries:
        weekday = entry["weekday"]
        opens_at = entry["opens_at"]
        closes_at = entry["closes_at"]
        if not 1 <= weekday <= 7:
            raise InvalidSchedule("weekday must be between 1 and 7")
        if weekday in weekdays:
            raise InvalidSchedule("weekday must not be duplicated")
        if opens_at >= closes_at:
            raise InvalidSchedule("opens_at must be before closes_at")
        weekdays.add(weekday)


def set_schedule(session: Session, technician_id: int, entries: list[dict]) -> list[dict]:
    _validate(entries)
    old = get_schedule(session, technician_id)
    now = datetime.now(timezone.utc)
    zone = get_hours_timezone(session)
    # Remove prior generated blocks by their exact schedule-derived start times;
    # manually authored availability outside those starts remains untouched.
    starts_to_remove = set()
    for entry in old:
        for offset in range(14):
            day = now.astimezone(ZoneInfo(zone)).date() + timedelta(days=offset)
            if day.isoweekday() == entry["weekday"]:
                duration = int((datetime.combine(day, entry["closes_at"]) - datetime.combine(day, entry["opens_at"])).total_seconds() // 60)
                try:
                    starts_to_remove.add(scheduling.local_interval(day, entry["opens_at"], zone, duration)[0])
                except (scheduling.NonexistentLocalTime, scheduling.AmbiguousLocalTime):
                    continue
    if starts_to_remove:
        session.execute(delete(TechnicianAvailability).where(
            TechnicianAvailability.technician_id == technician_id,
            TechnicianAvailability.starts_at.in_(starts_to_remove),
            TechnicianAvailability.starts_at >= now,
        ))
    session.execute(delete(TechnicianWeeklySchedule).where(
        TechnicianWeeklySchedule.technician_id == technician_id
    ))
    session.add_all(
        TechnicianWeeklySchedule(technician_id=technician_id, **entry)
        for entry in entries
    )
    session.flush()
    materialize(session, technician_id, now)
    return get_schedule(session, technician_id)


def materialize(
    session: Session,
    technician_id: int,
    now: datetime,
    horizon_days: int = 14,
) -> None:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    zone = get_hours_timezone(session)
    today = now.astimezone(ZoneInfo(zone)).date()
    entries = _entries(session, technician_id)
    for offset in range(horizon_days):
        day = today + timedelta(days=offset)
        for entry in entries:
            if day.isoweekday() != entry.weekday:
                continue
            duration = int((datetime.combine(day, entry.closes_at) - datetime.combine(day, entry.opens_at)).total_seconds() // 60)
            try:
                starts_at, ends_at = scheduling.local_interval(day, entry.opens_at, zone, duration)
            except (scheduling.NonexistentLocalTime, scheduling.AmbiguousLocalTime):
                continue
            exists = session.scalar(select(TechnicianAvailability.id).where(
                TechnicianAvailability.technician_id == technician_id,
                TechnicianAvailability.starts_at == starts_at,
            ))
            if exists is None:
                session.add(TechnicianAvailability(
                    technician_id=technician_id, starts_at=starts_at,
                    ends_at=ends_at, available=True,
                ))
    session.flush()


def ensure_horizon(session: Session, now: datetime, horizon_days: int = 14) -> None:
    technician_ids = session.scalars(
        select(TechnicianWeeklySchedule.technician_id).distinct()
    ).all()
    for technician_id in technician_ids:
        materialize(session, technician_id, now, horizon_days)
