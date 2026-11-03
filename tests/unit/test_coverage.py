"""Coverage communes (S3): the seven communes and forgiving matching.

The list is data; the lookup folds case, accents, punctuation and spacing, and
tolerates one typo when exactly one covered commune is that close.
"Huechuraba." used to normalize to "huechuraba." and "Huchuraba" to a stranger,
and either one derived a covered lead to a human while telling the customer we
do not serve there.
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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Huechuraba.", "huechuraba"),
        ("¿Ñuñoa?", "nunoa"),
        ("Lo Barnechea,", "lo barnechea"),
        ("Las  Condes!!", "las condes"),
        ("Lo-Barnechea", "lo barnechea"),
        ("Peñalolén;", "penalolen"),
        ("...", ""),
    ],
)
def test_normalize_comuna_ignores_punctuation(raw, expected):
    """A trailing dot used to normalize to "huechuraba." and fall out of coverage."""
    assert normalize_comuna(raw) == expected


@pytest.mark.parametrize(
    "nombre", ["Huechuraba.", "huechuraba,", "¡Huechuraba!", "(Huechuraba)"]
)
def test_a_covered_commune_matches_despite_punctuation(nombre):
    assert comuna_cubierta(DEFAULT_COVERAGE_COMMUNES, nombre) is True


@pytest.mark.parametrize(
    "nombre",
    [
        "Huchuraba",  # deleted "e" -- the spelling the owner actually typed
        "Huechurava",  # substituted "b" -> "v"
        "Huechurabaa",  # inserted "a"
        "Huechurab",  # truncated tail
        "Las Conde",
        "Nunua",
    ],
)
def test_a_one_typo_spelling_of_a_covered_commune_still_matches(nombre):
    assert comuna_cubierta(DEFAULT_COVERAGE_COMMUNES, nombre) is True


@pytest.mark.parametrize(
    "nombre", ["Maipu", "Probidencia", "Santiagoo", "Vitacura", "Puente Altp"]
)
def test_a_typo_of_an_uncovered_commune_matches_nothing(nombre):
    """Tolerance must not invent coverage for a commune the owner does not serve."""
    assert comuna_cubierta(DEFAULT_COVERAGE_COMMUNES, nombre) is False


def test_a_typo_equidistant_from_two_covered_communes_is_not_covered():
    """Ambiguity never resolves to a guess: it takes the derivation, not a wrong list."""
    communes = ["La Reina", "La Reine"]
    assert comuna_cubierta(communes, "La Rein") is False
    assert comuna_cubierta(communes, "La Reina") is True
    assert comuna_cubierta(communes, "La Reine") is True


@pytest.mark.parametrize(
    ("communes", "nombre"), [(["Coli"], "Cola"), (["Colina"], "Coli")]
)
def test_names_shorter_than_five_characters_do_not_take_a_typo_match(communes, nombre):
    """One edit is most of a short name, so it is not evidence of the same place."""
    assert comuna_cubierta(communes, nombre) is False


def test_a_five_character_spelling_still_takes_a_typo_match():
    assert comuna_cubierta(["Colina"], "Colin") is True


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
