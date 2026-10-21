"""Capture questions (S7): every field in the order has non-empty fallback text.

`capture.questions` stores the deterministic fallback used when the LLM does not
redact the question (model down, cost blocked, fixed-text mode). The code still
decides which field is missing; only the wording is configurable, and the order
stays in code (`chat.conduct.orden` in T10).

Validation is order-aware: a field with no text would leave the fallback path
with nothing to ask, so a partial map is rejected instead of silently defaulting
one key and using the configured text for the rest.
"""

from unittest.mock import MagicMock

import pytest

from app.services.settings import (
    CAPTURE_QUESTIONS_KEY,
    get_capture_questions,
    validate_capture_questions,
)

FIELDS = ["failure", "equipment", "comuna"]
COMPLETE = {
    "failure": "Cuéntame la falla con tus palabras.",
    "equipment": "¿Qué equipo es?",
    "comuna": "¿En qué comuna estás?",
}


def test_the_key_is_capture_questions():
    assert CAPTURE_QUESTIONS_KEY == "capture.questions"


def test_validate_accepts_a_complete_map_in_field_order():
    assert validate_capture_questions(COMPLETE, FIELDS) == COMPLETE


def test_validate_accepts_the_known_slots():
    value = {**COMPLETE, "failure": "Hola {{nombre}}, cuéntame la falla."}

    assert validate_capture_questions(value, FIELDS)["failure"] == "Hola {{nombre}}, cuéntame la falla."


@pytest.mark.parametrize(
    "value",
    [
        pytest.param([], id="not-a-map"),
        pytest.param("failure=hola", id="not-a-map-string"),
        pytest.param({}, id="empty"),
        pytest.param({key: text for key, text in COMPLETE.items() if key != "comuna"}, id="missing-a-field"),
        pytest.param({**COMPLETE, "comuna": ""}, id="empty-text"),
        pytest.param({**COMPLETE, "comuna": "   "}, id="blank-text"),
        pytest.param({**COMPLETE, "comuna": 5}, id="non-string-text"),
        pytest.param({**COMPLETE, "telefono": "¿Cuál es tu teléfono?"}, id="unknown-field"),
        pytest.param({**COMPLETE, "comuna": "¿En qué comuna estás, {{telefono}}?"}, id="unknown-slot"),
    ],
)
def test_validate_rejects_malformed_questions(value):
    with pytest.raises(ValueError):
        validate_capture_questions(value, FIELDS)


def test_get_returns_an_empty_map_without_a_row():
    session = MagicMock()
    session.get.return_value = None

    assert get_capture_questions(session) == {}
