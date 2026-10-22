"""S12/S13 unit contracts — persona and emergency protocol are settings-backed.

The editable persona is an *override* stored in the settings KV; the bundled
`agent/personas/*.md` files stay the default, so the byte-coupled contract
(`tests/unit/test_prompts.py:162`) keeps proving the shipped prompt.

DB-free: reads go through a fake session, so this file runs with an unreachable
`DATABASE_URL` like the rest of `tests/unit`.
"""

from types import SimpleNamespace
from unittest import mock

import pytest

from app.services import prompts, settings


def _fake_session(value):
    """A session whose single stored row returns `value` (or no row at all)."""
    session = mock.Mock()
    session.get.return_value = None if value is None else SimpleNamespace(value=value)
    return session


_ORCHESTRATOR = "personas/orchestrator.md"
_BRIEF = "personas/orchestrator_brief.md"


def _valid_persona() -> dict[str, str]:
    return {_ORCHESTRATOR: "Eres Max, asistente virtual de Lumat.", _BRIEF: "Sé breve."}


# --- S12: persona validation ------------------------------------------------


def test_persona_texts_accept_both_prompt_keys():
    assert settings.validate_persona_texts(_valid_persona()) == _valid_persona()


@pytest.mark.parametrize("field", [_ORCHESTRATOR, _BRIEF])
def test_persona_texts_reject_blank_text(field):
    value = {**_valid_persona(), field: "   \n "}
    with pytest.raises(ValueError):
        settings.validate_persona_texts(value)


@pytest.mark.parametrize("field", [_ORCHESTRATOR, _BRIEF])
def test_persona_texts_require_both_keys(field):
    value = _valid_persona()
    value.pop(field)
    with pytest.raises(ValueError):
        settings.validate_persona_texts(value)


def test_persona_texts_reject_a_placeholder():
    """Personas are loaded verbatim, never rendered: a slot would leak literally."""
    value = {**_valid_persona(), _ORCHESTRATOR: "Eres Max. Saluda a {{nombre}}."}
    with pytest.raises(ValueError):
        settings.validate_persona_texts(value)


def test_persona_texts_reject_an_unknown_key():
    value = {**_valid_persona(), "personas/summary.md": "Resume la conversación."}
    with pytest.raises(ValueError):
        settings.validate_persona_texts(value)


def test_persona_texts_reject_oversized_text():
    value = {**_valid_persona(), _ORCHESTRATOR: "x" * (settings.PERSONA_TEXT_MAX_CHARS + 1)}
    with pytest.raises(ValueError):
        settings.validate_persona_texts(value)


# --- S12: the loader prefers the configured text ----------------------------


def test_load_prefers_the_configured_override():
    assert prompts.load(_ORCHESTRATOR, override="Eres Max editado.") == "Eres Max editado."


def test_load_without_override_still_reads_the_bundled_file():
    assert prompts.load(_ORCHESTRATOR) == prompts.FALLBACKS[_ORCHESTRATOR]


def test_load_ignores_an_empty_override():
    assert prompts.load(_ORCHESTRATOR, override="") == prompts.FALLBACKS[_ORCHESTRATOR]


# --- S12/S13: unset or malformed stored values fall back to the defaults ----


def test_persona_texts_are_empty_when_unset():
    assert settings.get_persona_texts(_fake_session(None)) == {}


def test_persona_texts_ignore_a_stored_value_that_is_not_a_map():
    assert settings.get_persona_texts(_fake_session("basura")) == {}


def test_persona_texts_ignore_a_partial_stored_map():
    partial = {_ORCHESTRATOR: "Eres Max."}
    assert settings.get_persona_texts(_fake_session(partial)) == {}


# --- S13: emergency protocol validation -------------------------------------


def _valid_protocol() -> dict:
    return {
        "safety_instructions": ["Corta el gas.", "Ventila el lugar."],
        "contacts": ["Bomberos 132."],
        "notify_message": "Un técnico fue notificado.",
    }


def test_emergency_protocol_accepts_the_three_fields():
    assert settings.validate_emergency_protocol(_valid_protocol()) == _valid_protocol()


@pytest.mark.parametrize("field", ["safety_instructions", "contacts"])
def test_emergency_protocol_rejects_an_empty_list(field):
    value = {**_valid_protocol(), field: []}
    with pytest.raises(ValueError):
        settings.validate_emergency_protocol(value)


@pytest.mark.parametrize("field", ["safety_instructions", "contacts"])
def test_emergency_protocol_rejects_blank_items(field):
    value = {**_valid_protocol(), field: ["ok", "  "]}
    with pytest.raises(ValueError):
        settings.validate_emergency_protocol(value)


def test_emergency_protocol_rejects_a_blank_notify_message():
    value = {**_valid_protocol(), "notify_message": " "}
    with pytest.raises(ValueError):
        settings.validate_emergency_protocol(value)


def test_emergency_protocol_rejects_an_unknown_field():
    value = {**_valid_protocol(), "silence_everything": True}
    with pytest.raises(ValueError):
        settings.validate_emergency_protocol(value)


def test_emergency_protocol_defaults_when_unset():
    assert settings.get_emergency_protocol(_fake_session(None)) == {
        "safety_instructions": settings.DEFAULT_SAFETY_INSTRUCTIONS,
        "contacts": settings.DEFAULT_EMERGENCY_CONTACTS,
        "notify_message": settings.DEFAULT_EMERGENCY_NOTIFY_MESSAGE,
    }


def test_emergency_protocol_defaults_when_the_stored_value_is_not_a_map():
    assert settings.get_emergency_protocol(_fake_session(["basura"])) == {
        "safety_instructions": settings.DEFAULT_SAFETY_INSTRUCTIONS,
        "contacts": settings.DEFAULT_EMERGENCY_CONTACTS,
        "notify_message": settings.DEFAULT_EMERGENCY_NOTIFY_MESSAGE,
    }
