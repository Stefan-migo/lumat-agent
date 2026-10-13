from app.services.settings import MESSAGE_DEFAULTS, get_service_duration


class FakeSession:
    def __init__(self, value=None):
        self.value = value

    def get(self, model, key):
        if key == "booking.service_durations" and self.value is not None:
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
