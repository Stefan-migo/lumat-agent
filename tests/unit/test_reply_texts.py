"""Deterministic reply texts (S8): every customer-facing canned reply is a
settings key whose default is the current wording.

Booking, cancellation, rescheduling, handoff and the capture steps answer with
texts that do not come from the model. Moving them to settings changes where the
wording lives, never what the customer reads: the defaults must reproduce the
current string byte for byte.

Slots are whitelisted per key. The owner can drop a slot from a text, but not
introduce one the call site does not know how to fill: an unfilled `{{fecha}}`
would reach the customer.
"""

from unittest.mock import MagicMock

import pytest

from app.services import prompts
from app.services.settings import (
    REPLY_TEXTS_KEY,
    REPLY_TEXT_DEFAULTS,
    REPLY_TEXT_SLOTS,
    get_reply_texts,
    validate_reply_texts,
)

EXPECTED_KEYS = {
    "booking_offer",
    "booking_no_more_today",
    "booking_unclear",
    "booking_confirmed",
    "manage_no_visits",
    "manage_confirm_cancel",
    "manage_select",
    "manage_slots_offer",
    "manage_expired",
    "manage_appointment_unclear",
    "manage_slots_unclear",
    "manage_kept",
    "manage_reschedule_unavailable",
    "manage_rescheduled",
    "manage_cancel_prompt",
    "manage_cancel_unavailable",
    "manage_cancelled",
    "handoff",
    "handoff_cobertura",
    "handoff_persona",
    "handoff_unknown_intent_thrice",
    "handoff_campo_sin_respuesta",
    "handoff_booking_unavailable",
    "capture_evidence",
    "capture_consent",
}


def test_the_key_is_reply_texts():
    assert REPLY_TEXTS_KEY == "reply.texts"


def test_the_catalog_covers_booking_manage_handoff_and_capture():
    assert set(REPLY_TEXT_DEFAULTS) == EXPECTED_KEYS
    assert set(REPLY_TEXT_SLOTS) == EXPECTED_KEYS


def test_the_defaults_keep_the_current_wording():
    assert REPLY_TEXT_DEFAULTS["booking_offer"] == (
        "Tengo estos horarios disponibles para la visita técnica:\n"
        "{{opciones}}\n"
        "Responde con el número del horario que prefieres."
    )
    assert REPLY_TEXT_DEFAULTS["booking_confirmed"] == (
        "Tu visita técnica quedó confirmada para el {{fecha}} con {{tecnico}}."
    )
    # S1 (chatbot-experiencia): the owner approved this wording verbatim; the pin
    # keeps a refactor from quietly rewording what the customer reads.
    assert REPLY_TEXT_DEFAULTS["booking_no_more_today"] == (
        "Para ese día no me quedan más horarios. Te propongo estos otros días:\n"
        "{{opciones}}\n"
        "Responde con el número del horario que prefieres."
    )
    assert REPLY_TEXT_DEFAULTS["manage_cancelled"] == (
        "Tu visita del {{visita}} quedó cancelada."
    )
    assert REPLY_TEXT_DEFAULTS["handoff"] == (
        "Un asesor revisará tu caso y te contactará a la brevedad."
    )


def test_every_default_slot_is_whitelisted_for_its_key():
    for key, text in REPLY_TEXT_DEFAULTS.items():
        assert prompts.placeholders(text) <= REPLY_TEXT_SLOTS[key], key


def test_the_slot_vocabulary_is_closed():
    assert set().union(*REPLY_TEXT_SLOTS.values()) == {
        "opciones", "fecha", "visita", "accion", "tecnico", "comuna"
    }


def test_only_the_coverage_derivation_takes_a_slot():
    """S4: one derivation text names the comuna; the other four are plain."""
    assert REPLY_TEXT_SLOTS["handoff_cobertura"] == frozenset({"comuna"})
    for key in (
        "handoff_persona",
        "handoff_unknown_intent_thrice",
        "handoff_campo_sin_respuesta",
        "handoff_booking_unavailable",
    ):
        assert REPLY_TEXT_SLOTS[key] == frozenset(), key


def test_validate_accepts_a_complete_map():
    assert validate_reply_texts(dict(REPLY_TEXT_DEFAULTS)) == REPLY_TEXT_DEFAULTS


def test_validate_accepts_a_text_that_drops_its_slot():
    value = {**REPLY_TEXT_DEFAULTS, "booking_confirmed": "Tu visita quedó agendada."}

    assert validate_reply_texts(value)["booking_confirmed"] == "Tu visita quedó agendada."


@pytest.mark.parametrize(
    "value",
    [
        pytest.param([], id="not-a-map"),
        pytest.param("handoff=hola", id="not-a-map-string"),
        pytest.param({}, id="empty"),
        pytest.param(
            {key: text for key, text in REPLY_TEXT_DEFAULTS.items() if key != "handoff"},
            id="missing-a-text",
        ),
        pytest.param({**REPLY_TEXT_DEFAULTS, "handoff": ""}, id="empty-text"),
        pytest.param({**REPLY_TEXT_DEFAULTS, "handoff": "   "}, id="blank-text"),
        pytest.param({**REPLY_TEXT_DEFAULTS, "handoff": 5}, id="non-string-text"),
        pytest.param({**REPLY_TEXT_DEFAULTS, "un_asesor": "..."}, id="unknown-key"),
        pytest.param(
            {**REPLY_TEXT_DEFAULTS, "manage_kept": "De acuerdo, {{fecha}}."},
            id="slot-not-allowed-for-the-key",
        ),
        pytest.param(
            {**REPLY_TEXT_DEFAULTS, "booking_confirmed": "Confirmado {{telefono}}."},
            id="unknown-slot",
        ),
        pytest.param(
            {**REPLY_TEXT_DEFAULTS, "handoff_persona": "Te paso con {{comuna}}."},
            id="comuna-not-allowed-for-the-key",
        ),
    ],
)
def test_validate_rejects_malformed_maps(value):
    with pytest.raises(ValueError):
        validate_reply_texts(value)


def test_get_falls_back_to_the_defaults_without_a_row():
    session = MagicMock()
    session.get.return_value = None

    assert get_reply_texts(session) == REPLY_TEXT_DEFAULTS


def test_get_merges_a_stored_text_over_the_default():
    row = MagicMock()
    row.value = {"handoff": "Ya te contactamos."}
    session = MagicMock()
    session.get.return_value = row

    texts = get_reply_texts(session)

    assert texts["handoff"] == "Ya te contactamos."
    assert texts["manage_kept"] == REPLY_TEXT_DEFAULTS["manage_kept"]
