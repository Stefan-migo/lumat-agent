"""Independent verifier pins for the WU-E email API (S2, S5).

Committed from the verifier's probe set so the contract it exercised stays
guarded (WU-E/T6).
"""

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import AuditLog, PanelSecret
from app.services import smtp

_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
_VALID = {
    "host": "mail.example.test",
    "port": 587,
    "from_address": "sys@example.test",
    "user": "sys@example.test",
    "tls": "starttls",
}


def _key(monkeypatch):
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", _KEY)
    get_settings.cache_clear()


def _login(client, u="adm", p="adm-pass"):
    assert client.post(
        "/panel/api/login", json={"username": u, "password": p}, follow_redirects=False
    ).status_code == 200


def test_password_plaintext_never_leaks(client, make_user, monkeypatch, caplog):
    _key(monkeypatch)
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    secret = "PA55W0RD-UNIQUE-Zx9q"
    with caplog.at_level("DEBUG"):
        responses = [
            client.post("/panel/api/settings/email/password", json={"password": secret}),
            client.get("/panel/api/settings"),
            client.post("/panel/api/settings/email", json=_VALID),
            client.delete("/panel/api/settings/email/password"),
        ]
    for response in responses:
        assert secret not in response.text
    with SessionLocal() as session:
        blob = "\n".join(
            f"{row.action}|{row.entity_id}|{row.before}|{row.after}"
            for row in session.scalars(select(AuditLog))
        )
        assert secret not in blob
        assert (
            session.scalar(
                select(PanelSecret).where(PanelSecret.key == smtp.SMTP_PASSWORD_KEY)
            )
            is None
        )
    assert secret not in caplog.text


def test_config_save_never_clears_password(client, make_user, monkeypatch):
    _key(monkeypatch)
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    assert client.post(
        "/panel/api/settings/email/password", json={"password": "keep-me-1234"}
    ).status_code == 200
    response = client.post("/panel/api/settings/email", json=_VALID)
    assert response.json()["email"]["password"] == {"configured": True, "masked": "…1234"}


def test_denials_on_every_email_route(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    paths = [
        ("post", "/panel/api/settings/email", _VALID),
        ("post", "/panel/api/settings/email/password", {"password": "x"}),
        ("delete", "/panel/api/settings/email/password", None),
        ("post", "/panel/api/settings/email2", {}),
        ("post", "/panel/api/settings/not-a-section", {}),
    ]
    for method, path, body in paths:
        response = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
        assert response.status_code == 401
    _login(client, "oper", "oper-pass")
    for method, path, body in paths:
        response = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
        assert response.status_code == 403
    assert client.get("/panel/api/settings").status_code == 403
    assert client.delete("/panel/api/settings/email/password").status_code == 403


def test_boundaries(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    assert client.post("/panel/api/settings/email", json={**_VALID, "port": 1}).status_code == 200
    assert client.post("/panel/api/settings/email", json={**_VALID, "port": 65535}).status_code == 200
    for bad in (0, 65536, -1, 70000):
        assert client.post("/panel/api/settings/email", json={**_VALID, "port": bad}).status_code == 400
    for tls in ("ssl2", "STARTTLS", "", "tls"):
        assert client.post("/panel/api/settings/email", json={**_VALID, "tls": tls}).status_code == 400
    assert client.post("/panel/api/settings/email", json={**_VALID, "host": "  "}).status_code == 400
    assert client.post("/panel/api/settings/email", json={**_VALID, "from_address": "  "}).status_code == 400
    assert client.post("/panel/api/settings/not-a-section", json={}).status_code == 400
