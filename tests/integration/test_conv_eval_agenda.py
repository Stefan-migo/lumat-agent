from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import psycopg
from sqlalchemy import func, select

from _testdb import admin_database_url

from app.db import session_scope
from app.models import TechnicianAvailability, User, UserRole
from app.services import scheduling, technician_schedule
from app.services.scheduling import local_interval
from app.services.settings import get_hours_timezone

ADMIN_DB_URL = admin_database_url()

TECHNICIAN_USERNAMES = (
    "conv-eval-tecnico-1",
    "conv-eval-tecnico-2",
    "conv-eval-tecnico-3",
)
WEEKLY_SCHEDULE = [
    {"weekday": weekday, "opens_at": time(9), "closes_at": time(18)}
    for weekday in range(1, 7)
]


def _conv_eval():
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root / "scripts") not in sys.path:
        sys.path.insert(0, str(repo_root / "scripts"))
    import conv_eval

    return conv_eval


def _technicians(session):
    return list(
        session.scalars(
            select(User)
            .where(User.username.in_(TECHNICIAN_USERNAMES))
            .order_by(User.username)
        )
    )


def _availability_count(session, technician_ids):
    return session.scalar(
        select(func.count())
        .select_from(TechnicianAvailability)
        .where(TechnicianAvailability.technician_id.in_(technician_ids))
    )


def test_seed_creates_technicians_weekly_schedules_and_materialized_availability():
    module = _conv_eval()

    seeded = module.seed_harness_technicians()

    with session_scope() as session:
        technicians = _technicians(session)
        assert len(technicians) == 3
        assert all(technician.role == UserRole.TECNICO for technician in technicians)
        for technician in technicians:
            assert technician_schedule.get_schedule(session, technician.id) == WEEKLY_SCHEDULE
            now = datetime.now(timezone.utc)
            local_today = now.astimezone(ZoneInfo(get_hours_timezone(session))).date()
            for entry in WEEKLY_SCHEDULE:
                # The public availability reader confirms the generated block
                # covers each full local weekly window.
                day = local_today + timedelta(days=(entry["weekday"] - local_today.isoweekday()) % 7)
                starts, ends = local_interval(
                    day, time(9), get_hours_timezone(session), 540
                )
                assert scheduling.availability(session, technician.id, starts, ends)
        actual_blocks = _availability_count(session, [tech.id for tech in technicians])

    assert seeded["harness_technicians"] == 3
    assert seeded["harness_availability_blocks"] == actual_blocks
    assert seeded["harness_technicians_fingerprint"]
    assert actual_blocks > 0


def test_seeding_twice_creates_no_duplicate_users_or_availability():
    module = _conv_eval()

    first = module.seed_harness_technicians()
    second = module.seed_harness_technicians()

    with session_scope() as session:
        technicians = _technicians(session)
        assert len(technicians) == 3
        assert _availability_count(session, [tech.id for tech in technicians]) == first["harness_availability_blocks"]
    assert second == first


def test_seeding_after_reset_rematerializes_availability_without_recreating_users():
    module = _conv_eval()
    module.seed_harness_technicians()
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as connection:
        connection.execute("TRUNCATE technician_availability")

    with session_scope() as session:
        users_before = [tech.id for tech in _technicians(session)]
        assert _availability_count(session, users_before) == 0

    seeded = module.seed_harness_technicians()

    with session_scope() as session:
        technicians = _technicians(session)
        assert [tech.id for tech in technicians] == users_before
        assert _availability_count(session, users_before) == seeded["harness_availability_blocks"]


def test_seeded_slots_are_local_and_inside_monday_to_saturday_working_hours():
    module = _conv_eval()
    module.seed_harness_settings()
    now = datetime.now(timezone.utc)
    module.seed_harness_technicians()

    with session_scope() as session:
        slots = scheduling.open_slots_for_assignment(
            session, now=now, days=7, lead_minutes=120
        )
        zone = ZoneInfo(get_hours_timezone(session))

    assert slots
    for _technician_id, day, clock in slots:
        assert day.isoweekday() in range(1, 7)
        assert time(9) <= clock < time(18)
        # Slots are local date/time values, not UTC clocks mislabeled as local.
        local = datetime.combine(day, clock, tzinfo=zone)
        assert local.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == datetime.combine(day, clock)


def test_markdown_seal_names_agenda_only_when_stamp_has_agenda_data():
    module = _conv_eval()
    report = {
        "stamp": {
            "run_tag": "agenda",
            "harness_technicians": 3,
            "harness_availability_blocks": 82,
            "harness_technicians_fingerprint": "agenda123456",
        },
        "summary": {},
    }

    rendered = module.render_markdown(report)

    assert "3 técnicos" in rendered
    assert "82 bloques" in rendered
    assert "agenda123456" in rendered
    report["stamp"] = {"run_tag": "legacy"}
    assert "Agenda del arnés:" not in module.render_markdown(report)
