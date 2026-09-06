import pytest
from sqlalchemy import delete

from app.db import SessionLocal
from app.models import AuditLog, AutomationRule


RULE = {
    "name": "Case created notice",
    "event_type": "case.created",
    "conditions": {"priority": "high", "attempts": 2, "urgent": True, "note": None},
    "channel": "whatsapp",
    "template_event": "case.created",
    "cooldown_seconds": 60,
}


@pytest.fixture(autouse=True)
def clean_automation_rules():
    with SessionLocal() as session:
        session.execute(delete(AutomationRule))
        session.commit()
    yield


def _login(client, make_user, username, password, role):
    make_user(username, password, role=role)
    response = client.post(
        "/panel/api/login", json={"username": username, "password": password}, follow_redirects=False
    )
    assert response.status_code == 200


def _create_rule(client, make_user, username="automation-admin", password="admin-pass"):
    _login(client, make_user, username, password, "admin")
    response = client.post("/panel/api/automation-rules", json=RULE)
    assert response.status_code == 201, response.text
    return response.json()["rule"]


def test_automation_api_requires_json_auth_and_operators_can_read(client, make_user):
    anonymous = client.get("/panel/api/automation-rules", follow_redirects=False)
    assert anonymous.status_code == 401
    assert anonymous.headers["content-type"].startswith("application/json")
    assert "location" not in anonymous.headers

    rule = _create_rule(client, make_user)
    client.post("/panel/api/logout")
    _login(client, make_user, "automation-operator", "operator-pass", "operador")
    listing = client.get("/panel/api/automation-rules")
    detail = client.get(f"/panel/api/automation-rules/{rule['id']}")
    assert listing.status_code == detail.status_code == 200
    assert listing.json()["rules"][0]["id"] == rule["id"]
    assert detail.json()["rule"]["created_by"] == "automation-admin"

    forbidden = client.patch(f"/panel/api/automation-rules/{rule['id']}", json={"name": "changed"})
    assert forbidden.status_code == 403
    assert client.post(f"/panel/api/automation-rules/{rule['id']}/disable").status_code == 403


def test_automation_api_envelopes_404_and_no_hard_delete(client, make_user):
    rule = _create_rule(client, make_user)
    assert client.get("/panel/api/automation-rules/999999").json() == {"detail": "automation rule not found"}
    assert client.delete(f"/panel/api/automation-rules/{rule['id']}").status_code == 405
    assert client.get("/panel/api/automation-rules").json()["rules"][0]["id"] == rule["id"]


def test_admin_crud_preserves_creator_and_audits_snapshots(client, make_user):
    rule = _create_rule(client, make_user)
    update = client.patch(
        f"/panel/api/automation-rules/{rule['id']}",
        json={**RULE, "name": "Updated notice", "cooldown_seconds": 2592000},
    )
    assert update.status_code == 200
    assert update.json()["rule"]["created_by"] == "automation-admin"
    assert update.json()["rule"]["name"] == "Updated notice"
    assert client.post(f"/panel/api/automation-rules/{rule['id']}/disable").json()["rule"]["enabled"] is False
    assert client.post(f"/panel/api/automation-rules/{rule['id']}/disable").json()["rule"]["enabled"] is False
    assert client.post(f"/panel/api/automation-rules/{rule['id']}/enable").json()["rule"]["enabled"] is True

    with SessionLocal() as session:
        audits = session.query(AuditLog).filter(AuditLog.entity == "automation_rule").order_by(AuditLog.id).all()
        assert [entry.action for entry in audits] == [
            "automation.rule.create", "automation.rule.update", "automation.rule.disable",
            "automation.rule.disable", "automation.rule.enable",
        ]
        assert audits[0].before is None
        assert audits[0].after["created_by"] == "automation-admin"
        assert audits[1].before["name"] == RULE["name"]
        assert audits[1].after["name"] == "Updated notice"
        assert audits[2].before["enabled"] is True
        assert audits[2].after["enabled"] is False


def test_automation_validation_is_bounded_and_atomic(client, make_user):
    _login(client, make_user, "validation-admin", "validation-pass", "admin")
    for field, value in (
        ("event_type", "unknown.event"),
        ("template_event", "unknown.event"),
        ("channel", "sms"),
        ("cooldown_seconds", -1),
        ("cooldown_seconds", 2592001),
        ("conditions", {"nested": {"operator": "equals"}}),
        ("conditions", {"items": ["unsupported"]}),
    ):
        payload = {**RULE, field: value}
        response = client.post("/panel/api/automation-rules", json=payload)
        assert response.status_code == 422
        assert response.json()["detail"]

    with SessionLocal() as session:
        assert session.query(AutomationRule).count() == 0


def test_automation_detail_and_status_return_not_found(client, make_user):
    _login(client, make_user, "missing-admin", "missing-pass", "admin")
    for method, path in (
        ("get", "/panel/api/automation-rules/999999"),
        ("patch", "/panel/api/automation-rules/999999"),
        ("post", "/panel/api/automation-rules/999999/enable"),
        ("post", "/panel/api/automation-rules/999999/disable"),
    ):
        response = getattr(client, method)(path, **({"json": RULE} if method == "patch" else {}))
        assert response.status_code == 404
        assert response.json() == {"detail": "automation rule not found"}
