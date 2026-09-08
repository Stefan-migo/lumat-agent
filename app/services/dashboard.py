"""Bounded, timezone-aware operational dashboard aggregates."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import func, select

from app.models import (
    Appointment,
    AutomationExecution,
    Case,
    Message,
    MessageDirection,
    NotificationOperation,
)
from app.panel.api.serializers import to_appointment_dict, to_case_dict, to_message_dict

MAX_PERIOD = timedelta(days=31)


def compute_kpis(session, window_days: int) -> dict:
    """Return the legacy panel KPI counts for the API dashboard."""
    start = datetime.now(timezone.utc) - timedelta(days=window_days)
    contacts = session.scalar(
        select(func.count(func.distinct(Message.conversation_id))).where(
            Message.direction == MessageDirection.INBOUND,
            Message.created_at >= start,
        )
    )
    motivos = session.execute(
        select(Case.service, func.count().label("n"))
        .where(Case.created_at >= start)
        .group_by(Case.service)
        .order_by(func.count().desc(), Case.service)
    ).all()
    derived = session.scalar(
        select(func.count()).select_from(Case).where(Case.escalated_at >= start)
    )
    visits = session.scalar(
        select(func.count()).select_from(Case).where(
            Case.service == "visita", Case.created_at >= start
        )
    )
    return {
        "contacts": contacts or 0,
        "motivos": [(service, count) for service, count in motivos],
        "derived": derived or 0,
        "visit_requests": visits or 0,
        "window_days": window_days,
        "window_start": start.date().isoformat(),
    }


def parse_period(start: datetime, end: datetime, timezone_name: str) -> tuple[datetime, datetime, ZoneInfo]:
    if start.tzinfo is None or end.tzinfo is None or end <= start or end - start > MAX_PERIOD:
        raise HTTPException(status_code=422, detail="period must be a valid range of at most 31 days")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=422, detail="invalid timezone") from exc
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc), zone


def _count(session, model, field, start: datetime, end: datetime) -> int:
    return int(session.scalar(select(func.count()).select_from(model).where(field >= start, field < end)) or 0)


def _period_dict(start: datetime, end: datetime, timezone_name: str) -> dict:
    def iso(value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")
    return {"start": iso(start), "end": iso(end), "timezone": timezone_name}


def operational_summary(session, start: datetime, end: datetime, timezone_name: str) -> dict:
    utc_start, utc_end, _ = parse_period(start, end, timezone_name)
    contacts = session.scalar(
        select(func.count(func.distinct(Message.conversation_id))).where(
            Message.direction == MessageDirection.INBOUND,
            Message.created_at >= utc_start,
            Message.created_at < utc_end,
        )
    ) or 0
    notification_rows = session.execute(
        select(NotificationOperation.status, func.count()).where(
            NotificationOperation.created_at >= utc_start,
            NotificationOperation.created_at < utc_end,
        ).group_by(NotificationOperation.status)
    ).all()
    outcomes = session.execute(
        select(AutomationExecution.outcome, func.count()).where(
            AutomationExecution.created_at >= utc_start,
            AutomationExecution.created_at < utc_end,
        ).group_by(AutomationExecution.outcome)
    ).all()
    return {
        "period": _period_dict(start, end, timezone_name),
        "metrics": {
            "contacts": int(contacts),
            "cases": _count(session, Case, Case.created_at, utc_start, utc_end),
            "appointments": _count(session, Appointment, Appointment.starts_at, utc_start, utc_end),
            "notification_health": {status: int(count) for status, count in notification_rows},
            "automation_outcomes": {outcome: int(count) for outcome, count in outcomes},
        },
    }


def _bucket(value: datetime, zone: ZoneInfo) -> date:
    return value.astimezone(zone).date()


def trend(session, start: datetime, end: datetime, timezone_name: str, metric: str) -> dict:
    utc_start, utc_end, zone = parse_period(start, end, timezone_name)
    fields = {"contacts": Message.created_at, "cases": Case.created_at, "appointments": Appointment.starts_at}
    if metric not in fields:
        raise HTTPException(status_code=422, detail="unsupported dashboard metric")
    model = {"contacts": Message, "cases": Case, "appointments": Appointment}[metric]
    query = select(fields[metric]).where(fields[metric] >= utc_start, fields[metric] < utc_end)
    if metric == "contacts":
        query = query.where(Message.direction == MessageDirection.INBOUND)
    if metric == "contacts":
        values = session.execute(select(Message.created_at, Message.conversation_id).where(Message.direction == MessageDirection.INBOUND, Message.created_at >= utc_start, Message.created_at < utc_end)).all()
    else:
        values = [(value, None) for value in session.scalars(query).all()]
    first = start.astimezone(zone).date()
    last = end.astimezone(zone).date()
    buckets = []
    current = first
    counts: dict[date, int] = {}
    seen_contacts: set[tuple[date, int]] = set()
    for value, conversation_id in values:
        day = _bucket(value, zone)
        if metric == "contacts":
            key = (day, conversation_id)
            if key in seen_contacts:
                continue
            seen_contacts.add(key)
        counts[day] = counts.get(day, 0) + 1
    while current < last:
        buckets.append({"start": current.isoformat(), "count": counts.get(current, 0)})
        current += timedelta(days=1)
    return {"period": _period_dict(start, end, timezone_name), "metric": metric, "buckets": buckets}


def drilldown(session, start: datetime, end: datetime, timezone_name: str, metric: str, bucket_start: date) -> dict:
    utc_start, utc_end, zone = parse_period(start, end, timezone_name)
    local_start = datetime.combine(bucket_start, datetime.min.time(), tzinfo=zone)
    local_end = local_start + timedelta(days=1)
    lower, upper = max(utc_start, local_start.astimezone(timezone.utc)), min(utc_end, local_end.astimezone(timezone.utc))
    if lower >= upper:
        return {"period": _period_dict(start, end, timezone_name), "metric": metric, "rows": []}
    if metric == "cases":
        rows = session.scalars(select(Case).where(Case.created_at >= lower, Case.created_at < upper).order_by(Case.id)).all()
        payload = [to_case_dict(row) for row in rows]
    elif metric == "appointments":
        rows = session.scalars(select(Appointment).where(Appointment.starts_at >= lower, Appointment.starts_at < upper).order_by(Appointment.id)).all()
        payload = [to_appointment_dict(row) for row in rows]
    elif metric == "contacts":
        rows = session.scalars(select(Message).where(Message.direction == MessageDirection.INBOUND, Message.created_at >= lower, Message.created_at < upper).order_by(Message.id)).all()
        payload = [to_message_dict(row) for row in rows]
    else:
        raise HTTPException(status_code=422, detail="unsupported dashboard metric")
    return {"period": _period_dict(start, end, timezone_name), "metric": metric, "rows": payload}
