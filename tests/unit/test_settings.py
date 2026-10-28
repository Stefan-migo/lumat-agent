import pytest

from app.services.settings import (
    ASSISTANT_WRITABLE_SETTINGS,
    MESSAGE_DEFAULTS,
    SETTINGS_DEFAULTS,
    get_hours_closure_enabled,
    get_message_templates,
    get_service_duration,
    validate_assistant_setting,
    validate_message_templates,
)


class FakeSession:
    def __init__(self, value=None):
        self.value = value

    def get(self, model, key):
        if self.value is not None:
            return type("Setting", (), {"value": self.value})()
        return None


def test_get_service_duration_returns_mapped_value():
    assert get_service_duration(FakeSession({"Caldera": 90}), "Caldera") == 90


def test_get_service_duration_defaults_for_unknown_and_empty_service():
    session = FakeSession({"Caldera": 90})
    assert get_service_duration(session, "Calefont") == 60
    assert get_service_duration(session, None) == 60
    assert get_service_duration(session, "") == 60


def test_get_service_duration_normalizes_case_and_accents():
    assert get_service_duration(FakeSession({"Calefón": 45}), "  CALEFON ") == 45


def test_get_service_duration_rejects_malformed_values():
    for value in ("45", 0, -1, True):
        assert get_service_duration(FakeSession({"Caldera": value}), "Caldera") == 60


def test_get_service_duration_empty_map_defaults():
    assert get_service_duration(FakeSession({}), "Caldera") == 60


def test_clarification_default_does_not_invent_a_menu():
    clarification = MESSAGE_DEFAULTS["clarification"].lower()

    assert "menú" not in clarification
    assert "elige una opción" not in clarification


def test_get_message_templates_returns_empty_for_unset_or_non_list():
    assert get_message_templates(FakeSession()) == []
    assert get_message_templates(FakeSession({"invalid": "stored value"})) == []


@pytest.mark.parametrize(
    "templates",
    [
        [],
        [{"id": "visit-confirmation", "text": "Hola {{nombre}}, visita {{visita}}"}],
    ],
)
def test_validate_message_templates_accepts_valid_lists(templates):
    assert validate_message_templates(templates) is templates


@pytest.mark.parametrize(
    "templates",
    [
        None,
        ["not a template"],
        [{"text": "Hola"}],
        [{"id": "  ", "text": "Hola"}],
        [{"id": "greeting"}],
        [{"id": "greeting", "text": "  "}],
        [
            {"id": "greeting", "text": "Hola"},
            {"id": "greeting", "text": "Hola de nuevo"},
        ],
        [{"id": "greeting", "text": "Hola {{unknown_slot}}"}],
    ],
)
def test_validate_message_templates_rejects_invalid_lists(templates):
    with pytest.raises(ValueError):
        validate_message_templates(templates)


def test_smalltalk_default_matches_the_approved_copy_byte_for_byte():
    assert MESSAGE_DEFAULTS["smalltalk"] == "Con gusto. ¿En qué más te puedo ayudar?"


def test_greeting_defaults_match_the_approved_variants_byte_for_byte():
    assert MESSAGE_DEFAULTS["greeting"] == "Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar."
    assert MESSAGE_DEFAULTS["greeting_name"] == "Hola, {{nombre}}. Soy Max, el asistente virtual de Lumat. ¿En qué te puedo ayudar?"
    assert MESSAGE_DEFAULTS["greeting_short"] == "Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso."
    assert MESSAGE_DEFAULTS["greeting_short_name"] == "Hola, {{nombre}}. Soy Max, de Lumat. Ya te ayudo con eso."


def test_assistant_writable_settings_is_the_curated_allowlist():
    assert ASSISTANT_WRITABLE_SETTINGS == frozenset({
        "tone.style",
        "messages.greeting",
        "messages.greeting_short",
        "messages.greeting_name",
        "messages.greeting_short_name",
        "messages.smalltalk",
        "messages.farewell",
        "messages.clarification",
        "messages.cannot_answer",
        "messages.out_of_hours",
        "hours.timezone",
        "hours.schedule",
    })


@pytest.mark.parametrize(
    "key,value",
    [
        ("tone.style", "formal"),
        ("tone.style", "cercano"),
        ("messages.greeting", "Hola, soy Lumat."),
        ("messages.greeting_short", "Hola!"),
        ("messages.greeting_name", "Hola, {{nombre}}."),
        ("messages.greeting_short_name", "Hola, {{nombre}}."),
        ("messages.smalltalk", "Con gusto."),
        ("messages.out_of_hours", "Estamos cerrados."),
        ("hours.timezone", "America/Santiago"),
        ("hours.timezone", "UTC"),
        ("hours.schedule", []),
        ("hours.schedule", [{"days": [1, 2, 3, 4, 5], "open": "09:00", "close": "18:00"}]),
    ],
)
def test_validate_assistant_setting_accepts_valid_values(key, value):
    validate_assistant_setting(key, value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("tone.style", "sarcastico"),
        ("tone.style", 3),
        ("messages.greeting", ""),
        ("messages.greeting", "   "),
        ("messages.greeting", 123),
        ("messages.greeting_name", "Hola, {{otro}}."),
        ("messages.cannot_answer", "Hola, {{nombre}}."),
        ("hours.timezone", "Marte/Crater"),
        ("hours.timezone", ""),
        ("hours.schedule", "not-a-list"),
        ("hours.schedule", [{"days": [1], "open": "18:00", "close": "09:00"}]),
        ("hours.schedule", [{"days": [9], "open": "09:00", "close": "18:00"}]),
        ("hours.schedule", [{"days": [1], "open": "9:00", "close": "18:00"}]),
        ("hours.schedule", [{"days": [1, 1], "open": "09:00", "close": "18:00"}]),
        (
            "hours.schedule",
            [
                {"days": [1], "open": "09:00", "close": "18:00"},
                {"days": [1], "open": "09:00", "close": "13:00"},
            ],
        ),
    ],
)
def test_validate_assistant_setting_rejects_invalid_values(key, value):
    with pytest.raises(ValueError):
        validate_assistant_setting(key, value)


def test_hours_closure_enabled_defaults_to_false_and_reads_stored_boolean():
    assert SETTINGS_DEFAULTS["hours.closure_enabled"] is False
    assert get_hours_closure_enabled(FakeSession()) is False
    assert get_hours_closure_enabled(FakeSession(True)) is True


def test_validate_assistant_setting_rejects_keys_outside_the_allowlist():
    with pytest.raises(ValueError):
        validate_assistant_setting("cost.daily_limit", 0)
    with pytest.raises(ValueError):
        validate_assistant_setting("emergency.keywords", ["gas"])


@pytest.mark.parametrize(
    "key",
    [
        "cost.conversation_limit",
        "meta_pricing",
        "notify.owner_email",
        "messages.templates",
        "kpi.window_days",
        "tone.style ",
        "TONE.STYLE",
    ],
)
def test_validate_assistant_setting_rejects_near_miss_and_privileged_keys(key):
    with pytest.raises(ValueError):
        validate_assistant_setting(key, 0)


def test_validate_assistant_setting_rejects_an_overlong_message():
    with pytest.raises(ValueError):
        validate_assistant_setting("messages.greeting", "x" * 2001)
