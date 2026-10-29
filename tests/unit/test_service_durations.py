"""Service durations (S4): positive minutes, unambiguous keys, bounded length.

`booking.service_durations` maps a service name to the minutes a visit reserves.
The panel never wrote this key, so a malformed row could only come from a
migration or a script; it is validated now before it reaches scheduling.
"""

import pytest

from app.services.settings import (
    MAX_SERVICE_DURATION_MINUTES,
    validate_service_durations,
)


def test_validate_accepts_positive_integer_minutes():
    value = {"Calefont": 60, "Caldera": 90}

    assert validate_service_durations(value) == value


def test_validate_accepts_an_empty_map():
    assert validate_service_durations({}) == {}


def test_the_cap_is_one_day():
    assert MAX_SERVICE_DURATION_MINUTES == 1440


def test_validate_rejects_a_duration_above_the_cap():
    with pytest.raises(ValueError):
        validate_service_durations({"Caldera": MAX_SERVICE_DURATION_MINUTES + 1})


@pytest.mark.parametrize(
    "value",
    [
        pytest.param([], id="not-a-map"),
        pytest.param("Caldera=90", id="not-a-map-string"),
        pytest.param({"": 60}, id="empty-key"),
        pytest.param({"   ": 60}, id="blank-key"),
        pytest.param({1: 60}, id="non-string-key"),
        pytest.param({"Caldera": 0}, id="zero"),
        pytest.param({"Caldera": -30}, id="negative"),
        pytest.param({"Caldera": 90.5}, id="float"),
        pytest.param({"Caldera": "90"}, id="string-minutes"),
        pytest.param({"Caldera": True}, id="bool"),
        pytest.param({"Calefón": 45, "calefon": 60}, id="duplicate-after-normalization"),
    ],
)
def test_validate_rejects_malformed_durations(value):
    with pytest.raises(ValueError):
        validate_service_durations(value)


def test_keys_are_stored_without_stray_whitespace():
    """Collapsing on write keeps one key per service, not one per typo."""
    assert validate_service_durations({"Mantención de  calefont": 60}) == {
        "Mantención de calefont": 60
    }
    assert validate_service_durations({" Visión  de red ": 45}) == {"Visión de red": 45}


def test_duplicate_after_whitespace_normalization_is_rejected():
    with pytest.raises(ValueError):
        validate_service_durations({"Calefont": 60, " Calefont ": 90})
