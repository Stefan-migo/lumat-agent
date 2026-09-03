from datetime import date, time

import pytest

from app.services.scheduling import (
    AmbiguousLocalTime,
    NonexistentLocalTime,
    local_interval,
)


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
