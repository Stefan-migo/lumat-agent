"""Coverage communes (S3): the seven communes and accent-insensitive matching.

The list is data; the lookup normalizes case, accents and spacing so a customer
writing "nunoa" or "ÑUÑOA" matches the configured "Ñuñoa".
"""

import pytest

from app.services.settings import (
    COVERAGE_COMMUNES_KEY,
    DEFAULT_COVERAGE_COMMUNES,
    comuna_cubierta,
    get_coverage_communes,
    normalize_comuna,
    validate_coverage_communes,
)


class FakeSession:
    def __init__(self, value=None):
        self.value = value

    def get(self, model, key):
        if self.value is not None:
            return type("Setting", (), {"value": self.value})()
        return None


def test_default_coverage_is_exactly_the_seven_agreed_communes():
    assert DEFAULT_COVERAGE_COMMUNES == [
        "Las Condes",
        "Ñuñoa",
        "Lo Barnechea",
        "La Reina",
        "Peñalolén",
        "Colina",
        "Huechuraba",
    ]


def test_key_is_stable():
    assert COVERAGE_COMMUNES_KEY == "coverage.communes"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Ñuñoa", "nunoa"),
        ("  ÑUÑOA ", "nunoa"),
        ("Peñalolén", "penalolen"),
        ("  Las   Condes ", "las condes"),
        ("Lo Barnechea", "lo barnechea"),
        ("", ""),
    ],
)
def test_normalize_comuna_ignores_case_accents_and_spacing(raw, expected):
    assert normalize_comuna(raw) == expected


@pytest.mark.parametrize(
    "nombre",
    ["Ñuñoa", "nunoa", "NUNOA", "  ñuñoa  ", "Peñalolén", "penalolen", "Las Condes", "las condes"],
)
def test_a_covered_commune_matches_any_spelling(nombre):
    assert comuna_cubierta(DEFAULT_COVERAGE_COMMUNES, nombre) is True


@pytest.mark.parametrize("nombre", ["Santiago", "Providencia", "", "   ", None])
def test_an_uncovered_or_missing_commune_does_not_match(nombre):
    assert comuna_cubierta(DEFAULT_COVERAGE_COMMUNES, nombre) is False


def test_get_coverage_communes_returns_default_when_unset_or_malformed():
    assert get_coverage_communes(FakeSession()) == DEFAULT_COVERAGE_COMMUNES
    assert get_coverage_communes(FakeSession("Las Condes")) == DEFAULT_COVERAGE_COMMUNES
    assert get_coverage_communes(FakeSession([1, 2])) == DEFAULT_COVERAGE_COMMUNES


def test_get_coverage_communes_returns_the_stored_value():
    stored = ["Las Condes", "Colina"]
    assert get_coverage_communes(FakeSession(stored)) == stored


def test_validate_accepts_the_default():
    assert validate_coverage_communes(DEFAULT_COVERAGE_COMMUNES) == DEFAULT_COVERAGE_COMMUNES


def test_validate_accepts_an_empty_list():
    assert validate_coverage_communes([]) == []


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("Las Condes", id="not-a-list"),
        pytest.param([""], id="empty-name"),
        pytest.param(["   "], id="blank-name"),
        pytest.param([1], id="not-a-string"),
        pytest.param(["Las Condes", "las condes"], id="duplicate-after-normalization"),
        pytest.param(["Ñuñoa", "Nunoa"], id="duplicate-accent-insensitive"),
    ],
)
def test_validate_rejects_malformed_coverage(value):
    with pytest.raises(ValueError):
        validate_coverage_communes(value)
