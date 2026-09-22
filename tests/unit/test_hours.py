"""Unit tests for the configurable business-hours predicate."""

from datetime import datetime, timezone

import pytest

from app.services.settings import is_open_at


def _is_open_at(*, schedule, timezone_name, now):
    return is_open_at(schedule=schedule, timezone_name=timezone_name, now=now)


WEEKDAY_SCHEDULE = [{"days": [1], "open": "09:00", "close": "17:00"}]


def test_open_at_exact_opening_minute():
    assert _is_open_at(
        schedule=WEEKDAY_SCHEDULE,
        timezone_name="America/Santiago",
        now=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
    ) is True


def test_closed_at_exact_closing_minute():
    assert _is_open_at(
        schedule=WEEKDAY_SCHEDULE,
        timezone_name="America/Santiago",
        now=datetime(2026, 9, 21, 20, 0, tzinfo=timezone.utc),
    ) is False


def test_closed_one_minute_before_opening():
    assert _is_open_at(
        schedule=WEEKDAY_SCHEDULE,
        timezone_name="America/Santiago",
        now=datetime(2026, 9, 21, 11, 59, tzinfo=timezone.utc),
    ) is False


def test_weekday_without_an_entry_is_closed():
    assert _is_open_at(
        schedule=WEEKDAY_SCHEDULE,
        timezone_name="America/Santiago",
        now=datetime(2026, 9, 22, 15, 0, tzinfo=timezone.utc),
    ) is False


def test_empty_schedule_is_open_without_warning(caplog):
    with caplog.at_level("WARNING", logger="app.services.settings"):
        result = _is_open_at(
            schedule=[],
            timezone_name="America/Santiago",
            now=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        )

    assert result is True
    assert not caplog.records


def test_malformed_entry_fails_open_and_warns(caplog):
    with caplog.at_level("WARNING", logger="app.services.settings"):
        result = _is_open_at(
            schedule=[{"days": [1], "open": "nine", "close": "17:00"}],
            timezone_name="America/Santiago",
            now=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        )

    assert result is True
    assert any("schedule" in record.getMessage().lower() for record in caplog.records)


def test_unknown_timezone_fails_open_and_warns(caplog):
    with caplog.at_level("WARNING", logger="app.services.settings"):
        result = _is_open_at(
            schedule=WEEKDAY_SCHEDULE,
            timezone_name="Not/A_Timezone",
            now=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        )

    assert result is True
    assert any("timezone" in record.getMessage().lower() for record in caplog.records)


def test_overnight_window_is_invalid_and_fails_open(caplog):
    """Overnight windows are out of scope; write-time validation requires open < close."""
    with caplog.at_level("WARNING", logger="app.services.settings"):
        result = _is_open_at(
            schedule=[{"days": [1], "open": "22:00", "close": "02:00"}],
            timezone_name="America/Santiago",
            now=datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc),
        )

    assert result is True
    assert caplog.records


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc), True),
        (datetime(2026, 9, 22, 13, 0, tzinfo=timezone.utc), True),
    ],
)
def test_different_days_use_their_own_hours(now, expected):
    schedule = [
        {"days": [1], "open": "09:00", "close": "10:00"},
        {"days": [2], "open": "10:00", "close": "11:00"},
    ]

    assert _is_open_at(
        schedule=schedule,
        timezone_name="America/Santiago",
        now=now,
    ) is expected


def test_utc_now_is_converted_before_local_day_and_time_are_checked():
    schedule = [{"days": [1], "open": "20:00", "close": "22:00"}]

    assert _is_open_at(
        schedule=schedule,
        timezone_name="America/Santiago",
        now=datetime(2026, 9, 22, 0, 30, tzinfo=timezone.utc),
    ) is True
