"""Functional coverage for the SMTP email settings routes (WU-E/S5)."""

from __future__ import annotations

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import AuditLog, PanelSecret
from app.services import smtp

_ADMIN_USERNAME = "adm"
# Not a real credential: the panel test admin seeded by `make_user`.
_ADMIN_CREDENTIAL = "adm-pass"

EMAIL_DEFAULTS = {
    "host": "localhost",
    "port": 25,
    "from_address": "notificaciones@lumat.cl",
    "user": "",
    "tls": "none",
    "password": {"configured": False, "masked": ""},
}


def _login(client, username: str = _ADMIN_USERNAME, password: str = _ADMIN_CREDENTIAL) -> None:
    response = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 200, response.text


def _encryption_key(monkeypatch) -> None:
    monkeypatch.setenv(
        "SETTINGS_ENCRYPTION_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    )
    get_settings.cache_clear()


def test_get_settings_reports_email_defaults(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    response = client.get("/panel/api/settings")
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL_DEFAULTS


def test_save_email_config_persists_and_audits(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    body = {
        "host": "mail.lumat.cl",
        "port": 587,
        "from_address": "sistema@lumat.cl",
        "user": "sistema@lumat.cl",
        "tls": "starttls",
    }
    response = client.post("/panel/api/settings/email", json=body)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "ok": True,
        "email": {**body, "password": {"configured": False, "masked": ""}},
    }

    assert client.get("/panel/api/settings").json()["email"] == {
        **body,
        "password": {"configured": False, "masked": ""},
    }
    with SessionLocal() as session:
        changed = {
            row.entity_id
            for row in session.scalars(
                select(AuditLog).where(AuditLog.action == "settings.change")
            )
        }
    assert {
        "notify.smtp_host",
        "notify.smtp_port",
        "notify.smtp_from",
        "notify.smtp_user",
        "notify.smtp_tls",
    } <= changed


def test_save_email_config_rejects_invalid_port_and_tls(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    valid = {
        "host": "mail.lumat.cl",
        "port": 587,
        "from_address": "sistema@lumat.cl",
        "user": "",
        "tls": "none",
    }
    assert client.post("/panel/api/settings/email", json={**valid, "port": 0}).status_code == 400
    assert client.post("/panel/api/settings/email", json={**valid, "port": 70000}).status_code == 400
    assert client.post("/panel/api/settings/email", json={**valid, "tls": "ssl2"}).status_code == 400
    assert client.post("/panel/api/settings/email", json={**valid, "host": "  "}).status_code == 400
    assert client.post(
        "/panel/api/settings/email", json={**valid, "from_address": ""}
    ).status_code == 400


def test_password_round_trip_is_masked_and_audited(client, make_user, monkeypatch):
    _encryption_key(monkeypatch)
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    secret = "smtp-pass-2468"

    response = client.post("/panel/api/settings/email/password", json={"password": secret})
    assert response.status_code == 200, response.text
    assert response.json() == {
        "ok": True,
        "email": {"password": {"configured": True, "masked": "…2468"}},
    }
    assert secret not in response.text

    settings_body = client.get("/panel/api/settings")
    assert settings_body.json()["email"]["password"] == {"configured": True, "masked": "…2468"}
    assert secret not in settings_body.text

    with SessionLocal() as session:
        row = session.scalar(select(PanelSecret).where(PanelSecret.key == smtp.SMTP_PASSWORD_KEY))
        assert row is not None and secret.encode() not in row.ciphertext
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "smtp_password.set"))
        assert audit is not None
        assert secret not in str(audit.before) + str(audit.after)

    cleared = client.delete("/panel/api/settings/email/password")
    assert cleared.status_code == 200, cleared.text
    assert cleared.json() == {
        "ok": True,
        "email": {"password": {"configured": False, "masked": ""}},
    }
    with SessionLocal() as session:
        assert session.scalar(select(PanelSecret).where(PanelSecret.key == smtp.SMTP_PASSWORD_KEY)) is None


def test_empty_password_is_rejected(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    assert client.post(
        "/panel/api/settings/email/password", json={"password": ""}
    ).status_code == 400


def test_config_route_rejects_a_stray_password_field(client, make_user, monkeypatch):
    """The password has its own route; sending it here must fail, not be dropped."""
    _encryption_key(monkeypatch)
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    secret = "smtp-pass-2468"
    assert client.post(
        "/panel/api/settings/email/password", json={"password": secret}
    ).status_code == 200
    body = {
        "host": "mail.lumat.cl",
        "port": 587,
        "from_address": "sistema@lumat.cl",
        "user": "",
        "tls": "none",
        "password": "should-not-be-accepted",
    }
    assert client.post("/panel/api/settings/email", json=body).status_code == 422
    # The stored credential is untouched by the rejected save.
    assert client.get("/panel/api/settings").json()["email"]["password"] == {
        "configured": True,
        "masked": "…2468",
    }


def test_email_routes_are_admin_only(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")
    body = {
        "host": "mail.lumat.cl",
        "port": 587,
        "from_address": "sistema@lumat.cl",
        "user": "",
        "tls": "none",
    }
    assert client.post("/panel/api/settings/email", json=body).status_code == 403
    assert client.post(
        "/panel/api/settings/email/password", json={"password": "x"}
    ).status_code == 403
    assert client.delete("/panel/api/settings/email/password").status_code == 403


def test_unknown_section_still_rejected(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    assert client.post("/panel/api/settings/not-a-section", json={}).status_code == 400
