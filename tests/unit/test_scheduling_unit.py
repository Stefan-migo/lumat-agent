from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.services.scheduling import (
    AmbiguousLocalTime,
    InvalidRange,
    NonexistentLocalTime,
    _candidate_starts,
    local_interval,
    open_slots,
)
from app.services.automation import ALLOWED_EVENTS
from app.services.settings import SETTINGS_DEFAULTS


def test_followup_defaults_and_events_are_registered():
    assert SETTINGS_DEFAULTS["notify.followup_template_name"] == "appointment_followup"
    assert SETTINGS_DEFAULTS["notify.followup_no_show_template_name"] == "appointment_followup_no_show"
    assert {"appointment.completed", "appointment.no_show"} <= ALLOWED_EVENTS
    assert {"appointment.review_due", "customer.maintenance_due"} <= ALLOWED_EVENTS


def test_local_interval_preserves_chile_dst_and_returns_utc_range():
    starts_at, ends_at = local_interval(
        date(2026, 7, 15), time(10, 0), "America/Santiago", 90
    )

    assert starts_at.isoformat() == "2026-07-15T14:00:00+00:00"
    assert ends_at.isoformat() == "2026-07-15T15:30:00+00:00"


@pytest.mark.parametrize(
    "day,clock,error",
    [
        (date(2026, 9, 6), time(0, 30), NonexistentLocalTime),
        (date(2026, 4, 4), time(23, 30), AmbiguousLocalTime),
    ],
)
def test_local_interval_rejects_nonexistent_and_ambiguous_times(day, clock, error):
    with pytest.raises(error):
        local_interval(day, clock, "America/Santiago", 60)


def test_local_interval_rejects_unknown_timezone_and_non_positive_duration():
    with pytest.raises(ValueError, match="unknown timezone"):
        local_interval(date(2026, 7, 15), time(10), "not/a-zone", 60)
    with pytest.raises(ValueError, match="duration"):
        local_interval(date(2026, 7, 15), time(10), "UTC", 0)


def test_candidate_starts_steps_caps_at_window_and_skips_past():
    start = datetime(2026, 7, 15, 14, tzinfo=timezone.utc)
    assert list(_candidate_starts(
        start, start + timedelta(hours=3), 60, 30,
        start + timedelta(minutes=45),
    )) == [start + timedelta(minutes=60), start + timedelta(minutes=90), start + timedelta(minutes=120)]


@pytest.mark.parametrize(
    "start,end",
    [
        (datetime(2026, 7, 15, 14), datetime(2026, 7, 15, 15, tzinfo=timezone.utc)),
        (datetime(2026, 7, 15, 15, tzinfo=timezone.utc), datetime(2026, 7, 15, 14, tzinfo=timezone.utc)),
    ],
)
def test_open_slots_rejects_naive_or_reversed_window(start, end):
    with pytest.raises(InvalidRange):
        open_slots(None, technician_id=1, window_start=start, window_end=end,
                   duration_minutes=30, timezone_name="UTC")


def test_open_slots_defaults_step_to_duration_and_respects_limit(monkeypatch):
    class EmptySession:
        def scalar(self, statement):
            return None

    monkeypatch.setattr("app.services.scheduling.datetime", _FixedDateTime)
    start = datetime(2026, 4, 1, 1, tzinfo=timezone.utc)
    assert open_slots(
        EmptySession(), technician_id=1, window_start=start,
        window_end=start + timedelta(hours=2), duration_minutes=30,
        timezone_name="UTC", limit=1,
    ) == [(start.date(), start.time())]


def test_open_slots_skips_ambiguous_local_time(monkeypatch):
    class EmptySession:
        def scalar(self, statement):
            return None

    monkeypatch.setattr("app.services.scheduling.datetime", _FixedDateTime)
    assert open_slots(
        EmptySession(), technician_id=1,
        window_start=datetime(2026, 4, 5, 2, 30, tzinfo=timezone.utc),
        window_end=datetime(2026, 4, 5, 3, tzinfo=timezone.utc),
        duration_minutes=30, timezone_name="America/Santiago",
    ) == []


def test_open_slots_steps_across_dst_gap_without_emitting_missing_local_time(monkeypatch):
    class EmptySession:
        def scalar(self, statement):
            return None

    monkeypatch.setattr("app.services.scheduling.datetime", _FixedDateTime)
    slots = open_slots(
        EmptySession(), technician_id=1,
        window_start=datetime(2026, 9, 6, 3, tzinfo=timezone.utc),
        window_end=datetime(2026, 9, 6, 6, tzinfo=timezone.utc),
        duration_minutes=30, timezone_name="America/Santiago",
    )
    assert (date(2026, 9, 6), time(0)) not in slots


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
