from app.db import SessionLocal
from app.models import AuditLog, AutomationRule


def _login(client, make_user, username, password, role):
    make_user(username, password, role=role)
    response = client.post("/panel/api/login", json={"username": username, "password": password})
    assert response.status_code == 200


def test_admin_can_list_recipe_catalog(client, make_user):
    response = client.get("/panel/api/automation-recipes")
    assert response.status_code == 401
    _login(client, make_user, "recipe-admin", "admin-pass", "admin")
    payload = client.get("/panel/api/automation-recipes").json()["recipes"]
    assert [item["recipe_id"] for item in payload] == [
        "appointment_confirmation", "appointment_cancellation", "appointment_rescheduled",
        "appointment_no_show", "case_new_request",
        "appointment_review_request", "customer_maintenance",
        "admin_daily_summary", "admin_weekly_summary",
    ]
    assert all(item["description"].strip() for item in payload)
    assert set(payload[0]) == {
        "recipe_id", "name", "description", "category", "trigger_kind", "event_type",
        "channel_allowed", "recipient_target", "content", "cooldown_seconds", "parameters",
    }
    client.post("/panel/api/logout")
    _login(client, make_user, "recipe-operator", "operator-pass", "operador")
    assert client.get("/panel/api/automation-recipes").status_code == 403


def test_installation_api_lifecycle_and_validation(client, make_user):
    _login(client, make_user, "recipe-admin", "admin-pass", "admin")
    url = "/panel/api/automation-installations"
    for body, status in (({"recipe_id": "missing", "parameters": {}}, 422),
                         ({"recipe_id": "appointment_confirmation", "parameters": {}}, 422),
                         ({"recipe_id": "appointment_confirmation", "parameters": {"channel": "email"}}, 422)):
        assert client.post(url, json=body).status_code == status

    response = client.post(url, json={"recipe_id": "appointment_confirmation", "parameters": {"channel": "whatsapp"}})
    assert response.status_code == 201, response.text
    installation = response.json()["installation"]
    assert installation["enabled"] is False
    with SessionLocal() as session:
        rule = session.query(AutomationRule).filter_by(installation_id=installation["id"]).one()
        audit = session.query(AuditLog).filter_by(entity="automation_installation").one()
        assert audit.action == "automation.installation.create"
        assert rule.enabled is False

    assert client.post(url, json={"recipe_id": "appointment_confirmation", "parameters": {"channel": "whatsapp"}}).status_code == 409
    assert client.get(url).json()["installations"][0]["id"] == installation["id"]
    path = f"{url}/{installation['id']}"
    update = client.patch(path, json={"parameters": {"channel": "whatsapp"}})
    assert update.status_code == 200
    assert client.patch(f"{url}/999999", json={"parameters": {"channel": "whatsapp"}}).status_code == 404
    assert client.post(f"{path}/enable").json()["installation"]["enabled"] is True
    assert client.post(f"{path}/disable").json()["installation"]["enabled"] is False
    assert client.post(f"{url}/999999/enable").status_code == 404
    assert client.post(f"{url}/999999/disable").status_code == 404

    second = client.post(url, json={"recipe_id": "appointment_no_show", "parameters": {"channel": "whatsapp"}})
    assert second.status_code == 201
    second_path = f"{url}/{second.json()['installation']['id']}"
    changed = client.patch(f"{second_path}", json={"parameters": {"channel": "email"}})
    assert changed.status_code == 200
    with SessionLocal() as session:
        compiled = session.query(AutomationRule).filter_by(installation_id=second.json()["installation"]["id"]).one()
        assert compiled.channel == "email"


def test_request_bodies_forbid_extra_fields(client, make_user):
    _login(client, make_user, "recipe-admin", "admin-pass", "admin")
    assert client.post("/panel/api/automation-installations", json={"recipe_id": "x", "parameters": {}, "extra": 1}).status_code == 422
