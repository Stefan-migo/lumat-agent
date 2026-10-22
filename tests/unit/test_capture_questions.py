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


@pytest.mark.parametrize(
    "text",
    [
        "Hola {{nombre}}, cuéntame la falla.",
        "Hola {{ nombre }}, cuéntame la falla.",
        "Hola {{nombre del cliente}}, cuéntame la falla.",
        "Hola {{}}, cuéntame la falla.",
        "Hola {{ nombre, cuéntame la falla.",
    ],
)
def test_validate_rejects_any_slot_because_the_text_is_sent_verbatim(text):
    """F6: nothing renders `capture.questions`, so a slot would reach the client
    as literal braces. T7 allowed them assuming the F3 LLM-redaction path; that
    path shipped without a reader, so the contract narrows to plain text."""
    value = {**COMPLETE, "failure": text}

    with pytest.raises(ValueError):
        validate_capture_questions(value, FIELDS)


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
    ],
)
def test_validate_rejects_malformed_questions(value):
    with pytest.raises(ValueError):
        validate_capture_questions(value, FIELDS)


def test_get_returns_an_empty_map_without_a_row():
    session = MagicMock()
    session.get.return_value = None

    assert get_capture_questions(session) == {}


def test_get_drops_a_stored_text_with_slots():
    """A row saved before F6 narrowed the contract must not reach the client."""
    session = MagicMock()
    session.get.return_value = MagicMock(
        value={"failure": "{{nombre}}, cuéntame la falla.", "comuna": "¿En qué comuna estás?"}
    )

    assert get_capture_questions(session) == {"comuna": "¿En qué comuna estás?"}
