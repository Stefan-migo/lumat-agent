"""Verifier API regression probes for the automation-uninstall work unit."""
from app.db import SessionLocal
from app.models import AuditLog, AutomationInstallation, AutomationRule

URL = "/panel/api/automation-installations"
A, B = "appointment_confirmation", "appointment_no_show"


def _login(client, make_user, username, password, role):
    make_user(username, password, role=role)
    assert client.post("/panel/api/login", json={"username": username, "password": password}).status_code == 200


def _create(client, recipe_id):
    resp = client.post(URL, json={"recipe_id": recipe_id, "parameters": {"channel": "whatsapp"}})
    assert resp.status_code == 201, resp.text
    return resp.json()["installation"]


def test_404_leaves_data_intact(client, make_user):
    _login(client, make_user, "probe-admin", "pw", "admin")
    a, b = _create(client, A), _create(client, B)
    with SessionLocal() as session:
        assert session.query(AutomationInstallation).count() == 2
        assert session.query(AutomationRule).count() == 2
        assert session.query(AuditLog).filter_by(action="automation.installation.delete").count() == 0
    resp = client.delete(f"{URL}/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "automation installation not found"
    with SessionLocal() as session:
        assert session.query(AutomationInstallation).count() == 2
        assert session.query(AutomationRule).count() == 2
        assert session.query(AuditLog).filter_by(action="automation.installation.delete").count() == 0
    assert {i["id"] for i in client.get(URL).json()["installations"]} == {a["id"], b["id"]}


def test_admin_ok_and_single_audit_snapshot(client, make_user):
    _login(client, make_user, "probe-admin2", "pw", "admin")
    created = _create(client, A)
    resp = client.delete(f"{URL}/{created['id']}")
    assert resp.status_code == 200 and resp.json() == {"ok": True}
    with SessionLocal() as session:
        rows = session.query(AuditLog).filter_by(action="automation.installation.delete").all()
        assert len(rows) == 1
        row = rows[0]
        assert row.entity == "automation_installation" and row.entity_id == str(created["id"]) and row.actor == "probe-admin2"
        assert row.before == {"id": created["id"], "recipe_id": A, "parameters": {"channel": "whatsapp"}, "enabled": False,
                              "created_by": "probe-admin2", "created_at": row.before["created_at"], "updated_at": row.before["updated_at"]}
        assert row.after is None
    assert client.delete(f"{URL}/{created['id']}").status_code == 404


def test_operator_403_no_mutation(client, make_user):
    _login(client, make_user, "probe-admin3", "pw", "admin")
    created = _create(client, A)
    client.post("/panel/api/logout")
    _login(client, make_user, "probe-oper", "pw", "operador")
    assert client.delete(f"{URL}/{created['id']}").status_code == 403
    with SessionLocal() as session:
        assert session.query(AutomationInstallation).count() == 1
        assert session.query(AutomationRule).count() == 1


def test_enable_disable_unchanged(client, make_user):
    _login(client, make_user, "probe-admin4", "pw", "admin")
    created = _create(client, A)
    path = f"{URL}/{created['id']}"
    assert client.post(f"{path}/enable").json()["installation"]["enabled"] is True
    assert client.post(f"{path}/disable").json()["installation"]["enabled"] is False
    assert client.post(f"{URL}/999999/enable").status_code == 404
    assert client.post(f"{URL}/999999/disable").status_code == 404
