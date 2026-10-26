from app.services import settings as settings_service


def test_fixed_message_defaults_have_one_complete_settings_source():
    message_defaults = {
        f"messages.{key}": value
        for key, value in settings_service.MESSAGE_DEFAULTS.items()
    }

    assert "messages.smalltalk" in message_defaults
    assert {
        key: value
        for key, value in settings_service.SETTINGS_DEFAULTS.items()
        if key.startswith("messages.") and key != settings_service.MESSAGE_TEMPLATES_KEY
    } == message_defaults


def test_every_fixed_message_resolves_from_the_default_source():
    class EmptySession:
        def get(self, model, key):
            return None

    session = EmptySession()
    assert {
        key: settings_service.get_message(session, key)
        for key in settings_service.MESSAGE_DEFAULTS
    } == settings_service.MESSAGE_DEFAULTS
