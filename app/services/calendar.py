"""Narrow, non-authoritative calendar synchronization boundary."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Appointment, AppointmentCalendarSync
from app.services.audit import record_audit


class ProviderResult:
    def __init__(self, *, external_id: str, payload: str):
        self.external_id = external_id
        self.payload = payload


class CalendarProvider(Protocol):
    def sync(self, appointment: Appointment, *, uid: str, idempotency_key: str) -> ProviderResult: ...


def calendar_uid(appointment_id: int) -> str:
    return f"appointment-{appointment_id}@lumat.local"


def idempotency_key(appointment_id: int) -> str:
    return f"calendar:appointment:{appointment_id}"


def build_ics(*, uid: str, service: str, starts_at: datetime, ends_at: datetime, timezone_name: str, cancelled: bool = False) -> str:
    zone = ZoneInfo(timezone_name)
    local_start = starts_at.astimezone(zone).strftime("%Y%m%dT%H%M%S")
    local_end = ends_at.astimezone(zone).strftime("%Y%m%dT%H%M%S")
    status = "CANCELLED" if cancelled else "CONFIRMED"
    return "\r\n".join((
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Lumat//Scheduling//EN",
        "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{starts_at.astimezone().strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;TZID={timezone_name}:{local_start}", f"DTEND;TZID={timezone_name}:{local_end}",
        f"SUMMARY:{service}", f"STATUS:{status}", "END:VEVENT", "END:VCALENDAR", "",
    ))


class ICSProvider:
    def sync(self, appointment: Appointment, *, uid: str, idempotency_key: str) -> ProviderResult:
        return ProviderResult(
            external_id=uid,
            payload=build_ics(uid=uid, service=appointment.service, starts_at=appointment.starts_at,
                              ends_at=appointment.ends_at, timezone_name=appointment.timezone,
                              cancelled=appointment.status.value == "cancelled"),
        )


def synchronize(session: Session, appointment: Appointment, *, provider: CalendarProvider, actor: str) -> AppointmentCalendarSync:
    sync = session.scalar(select(AppointmentCalendarSync).where(AppointmentCalendarSync.appointment_id == appointment.id))
    if sync is None:
        sync = AppointmentCalendarSync(appointment_id=appointment.id, timezone=appointment.timezone,
                                       uid=calendar_uid(appointment.id), idempotency_key=idempotency_key(appointment.id))
        session.add(sync)
        session.flush()
    sync.cancelled = appointment.status.value == "cancelled"
    sync.attempts += 1
    sync.last_attempt_at = datetime.now().astimezone()
    try:
        result = provider.sync(appointment, uid=sync.uid, idempotency_key=sync.idempotency_key)
    except Exception as exc:
        sync.status = "failed"
        sync.error = str(exc)
        record_audit(session, actor=actor, action="calendar.sync_failed", entity="appointment", entity_id=str(appointment.id), after={"error": str(exc), "retryable": True})
        return sync
    sync.status = "synced"
    sync.error = None
    sync.external_id = result.external_id
    sync.payload = result.payload
    sync.synced_at = datetime.now().astimezone()
    record_audit(session, actor=actor, action="calendar.synced", entity="appointment", entity_id=str(appointment.id), after={"uid": sync.uid, "cancelled": sync.cancelled})
    return sync
