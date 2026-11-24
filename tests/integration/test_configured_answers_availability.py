from datetime import datetime, time, timedelta, timezone

import psycopg
import pytest

from app.chat.nodes import configured_answers
from app.chat.nodes.booking import DEFAULT_DURATION_MINUTES
from app.chat.state import ConversationState
from app.db import SessionLocal
from app.models import User, UserRole
from app.services import scheduling
from app.services.settings import get_booking_lead_minutes, get_hours_timezone, set_setting
from _testdb import admin_database_url


@pytest.fixture(autouse=True)
def clean_availability_db(migrated_db):
    with psycopg.connect(admin_database_url(), autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customers, users RESTART IDENTITY CASCADE"
        )


def _state(text: str) -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=2,
        intent="consulta",
        window=[{"id": 1, "text": text}],
        captured={},
    )


def _fixed_clock(monkeypatch, now):
    class FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            assert tz is timezone.utc
            return now

    monkeypatch.setattr(configured_answers, "datetime", FixedDateTime)


def test_reply_names_only_slots_returned_inside_a_technicians_availability(monkeypatch):
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    _fixed_clock(monkeypatch, now)
    start = (now + timedelta(days=2)).replace(hour=9, minute=0)
    end = start + timedelta(hours=3)
    with SessionLocal() as session:
        technician = User(
            username="availability-preview-technician",
            password_hash="test",
            role=UserRole.TECNICO,
        )
        session.add(technician)
        session.flush()
        scheduling.add_availability(
            session,
            technician_id=technician.id,
            starts_at=start,
            ends_at=end,
        )
        set_setting(
            session,
            "hours.schedule",
            [{"days": [1, 2, 3, 4, 5, 6, 7], "open": "00:00", "close": "23:59"}],
        )
        session.commit()

        slots = scheduling.open_slots_for_assignment(
            session,
            now=now,
            days=7,
            duration_minutes=DEFAULT_DURATION_MINUTES,
            limit=3,
            lead_minutes=get_booking_lead_minutes(session),
        )
        # The availability block was seeded in UTC but the slots come back local:
        # comparing one against the other is what makes a correct slot look outside
        # its own window. Both sides are read in the configured zone.
        from zoneinfo import ZoneInfo

        zone = ZoneInfo(get_hours_timezone(session))
        start_local, end_local = start.astimezone(zone), end.astimezone(zone)
        assert slots
        assert all(start_local.date() <= slot_day <= end_local.date() for _, slot_day, _ in slots)
        assert all(
            datetime.combine(slot_day, slot_time, tzinfo=zone) >= start_local
            and datetime.combine(slot_day, slot_time, tzinfo=zone)
            + timedelta(minutes=DEFAULT_DURATION_MINUTES)
            <= end_local
            for _, slot_day, slot_time in slots
        )

        rendered = configured_answers.configuration_reply(
            session, _state("¿Tienen horarios disponibles para reservar?")
        )

    # One slot per distinct day: the preview answers "which days", not "which hours".
    names = [
        f"{configured_answers._WEEKDAY_NAMES[slot_day.isoweekday() - 1]} "
        f"{slot_day.day} a las {slot_time:%H:%M}"
        for _, slot_day, slot_time in configured_answers._one_slot_per_day(slots)
    ]
    expected = (
        "Tengo estas horas libres: "
        f"{configured_answers._join_es(names)}. "
        "Si te sirve alguna, te tomo los datos y la reservo."
    )
    assert rendered == expected


def test_no_technicians_falls_back_to_the_hours_policy_sentence():
    with SessionLocal() as session:
        set_setting(
            session,
            "hours.schedule",
            [{"days": [1, 2, 3, 4, 5, 6, 7], "open": "00:00", "close": "23:59"}],
        )
        session.commit()

        assert configured_answers.configuration_reply(
            session, _state("¿Tienen hora disponible esta semana?")
        ) == "Las visitas se agendan según la disponibilidad de los técnicos."


def _seed_blocks(session, blocks, *, zone):
    technician = User(
        username=f"availability-preview-{len(blocks)}",
        password_hash="test",
        role=UserRole.TECNICO,
    )
    session.add(technician)
    session.flush()
    for start, end in blocks:
        scheduling.add_availability(
            session, technician_id=technician.id, starts_at=start, ends_at=end
        )
    set_setting(
        session,
        "hours.schedule",
        [{"days": [1, 2, 3, 4, 5, 6, 7], "open": "00:00", "close": "23:59"}],
    )
    session.commit()
    return technician


def test_the_preview_names_different_days_instead_of_three_hours_of_one_day(monkeypatch):
    """Measured on the corpus: three consecutive half-hours of the same day are the
    booking menu, not an answer to "¿qué días tienen?". The judged run scored it 0."""
    import re
    from zoneinfo import ZoneInfo

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    _fixed_clock(monkeypatch, now)
    zone = ZoneInfo("America/Santiago")
    today = now.astimezone(zone).date()
    blocks = [
        (
            datetime.combine(today + timedelta(days=offset), time(10, 0), tzinfo=zone),
            datetime.combine(today + timedelta(days=offset), time(14, 0), tzinfo=zone),
        )
        for offset in (2, 3, 4)
    ]
    with SessionLocal() as session:
        _seed_blocks(session, blocks, zone=zone)

        reply = configured_answers.configuration_reply(
            session, _state("¿Qué días tienen disponibilidad esta semana?")
        )

    assert reply is not None
    named = re.findall(r"(lunes|martes|miércoles|jueves|viernes|sábado|domingo) (\d+)", reply)
    assert len(named) == 3, reply
    assert len({day for _, day in named}) == 3, f"tres días distintos, no tres horas: {reply}"


def test_a_named_day_is_answered_with_that_days_slots(monkeypatch):
    """Corpus `real-solo-sabados`: the customer asks for one day and got the earliest one.

    The requested day is the *last* seeded one on purpose: without parsing the
    request, the preview names the earliest day and this test says so.
    """
    import re
    from zoneinfo import ZoneInfo

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    _fixed_clock(monkeypatch, now)
    zone = ZoneInfo("America/Santiago")
    today = now.astimezone(zone).date()
    offsets = (1, 2, 3)
    requested = today + timedelta(days=offsets[-1])
    weekday = configured_answers._WEEKDAY_NAMES[requested.isoweekday() - 1]
    blocks = [
        (
            datetime.combine(today + timedelta(days=offset), time(10, 0), tzinfo=zone),
            datetime.combine(today + timedelta(days=offset), time(14, 0), tzinfo=zone),
        )
        for offset in offsets
    ]
    with SessionLocal() as session:
        _seed_blocks(session, blocks, zone=zone)

        reply = configured_answers.configuration_reply(
            session, _state(f"¿Este {weekday} {requested.day} tiene disponibilidad?")
        )

    assert reply is not None
    named = re.findall(r"(lunes|martes|miércoles|jueves|viernes|sábado|domingo) (\d+)", reply)
    assert named, reply
    assert {day for _, day in named} == {str(requested.day)}, reply
