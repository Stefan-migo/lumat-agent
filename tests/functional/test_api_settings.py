"""Settings GET contracts for fixed message defaults and option catalogs."""

from app.services import settings as settings_service


def _login(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    response = client.post(
        "/panel/api/login",
        json={"username": "adm", "password": "adm-pass"},
        follow_redirects=False,
    )
    assert response.status_code == 200, response.text


def test_settings_get_exposes_every_fixed_message_default_and_option_catalog(client, make_user):
    _login(client, make_user)

    response = client.get("/panel/api/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["messages"] == settings_service.MESSAGE_DEFAULTS
    assert "smalltalk" in payload["messages"]
    assert payload["options"]["tones"] == list(settings_service.TONE_STYLES)
    assert payload["options"]["tarifa_labels"] == settings_service.TARIFA_LABELS
