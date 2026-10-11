from datetime import datetime, time, timezone

import pytest

from app.db import SessionLocal
from app.models import TechnicianAvailability, TechnicianWeeklySchedule, User, UserRole
from app.services import technician_schedule
from app.services import scheduling
from app.services.settings import set_setting


def _technician(session):
    technician = User(username="weekly-schedule-tech", password_hash="test", role=UserRole.TECNICO)
    session.add(technician)
    session.flush()
    return technician


@pytest.mark.parametrize(
    "entry",
    [
        {"weekday": 0, "opens_at": time(9), "closes_at": time(17)},
        {"weekday": 1, "opens_at": time(17), "closes_at": time(9)},
    ],
)
def test_set_schedule_rejects_invalid_entries(entry):
    with SessionLocal() as session:
        technician = _technician(session)
        with pytest.raises(technician_schedule.InvalidSchedule):
            technician_schedule.set_schedule(session, technician.id, [entry])


def test_materialize_is_idempotent_and_uses_local_weekday():
    with SessionLocal() as session:
        technician = _technician(session)
        set_setting(session, "hours.timezone", "UTC")
        session.add(TechnicianWeeklySchedule(
            technician_id=technician.id, weekday=2,
            opens_at=time(9), closes_at=time(12),
        ))
        session.flush()
        now = datetime(2030, 1, 1, 8, tzinfo=timezone.utc)  # Tuesday

        technician_schedule.materialize(session, technician.id, now, horizon_days=3)
        first_count = session.query(TechnicianAvailability).filter_by(technician_id=technician.id).count()
        technician_schedule.materialize(session, technician.id, now, horizon_days=3)

        assert first_count == 1
        assert session.query(TechnicianAvailability).filter_by(technician_id=technician.id).count() == 1


def test_weekly_schedule_produces_assignment_slots_without_manual_blocks(monkeypatch):
    with SessionLocal() as session:
        technician = _technician(session)
        set_setting(session, "hours.timezone", "UTC")
        session.add(TechnicianWeeklySchedule(
            technician_id=technician.id, weekday=2,
            opens_at=time(9), closes_at=time(12),
        ))
        session.flush()
        now = datetime(2030, 1, 1, 8, tzinfo=timezone.utc)
        monkeypatch.setattr(technician_schedule, "get_hours_timezone", lambda _session: "UTC")

        technician_schedule.ensure_horizon(session, now, horizon_days=3)
        slots = scheduling.open_slots_for_assignment(session, now=now, days=3)

        assert slots
        assert all(assigned_id == technician.id for assigned_id, _, _ in slots)
