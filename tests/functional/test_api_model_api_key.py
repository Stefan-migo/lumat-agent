"""Functional coverage for the write-only DeepSeek API-key settings routes."""

from __future__ import annotations

import httpx
import respx
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import AuditLog, PanelSecret
from app.services.deepseek_key import DEEPSEEK_MODELS_URL


_ADMIN_USERNAME = "adm"
# Not a real credential: the panel test admin seeded by `make_user`.
_ADMIN_CREDENTIAL = "adm-pass"


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


def test_set_key_validates_stores_and_never_exposes_key(client, make_user, monkeypatch):
    _encryption_key(monkeypatch)
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    key = "sk-test-model-key-1234"
    with respx.mock(assert_all_called=True) as router:
        route = router.get(DEEPSEEK_MODELS_URL).mock(return_value=httpx.Response(200))
        response = client.post("/panel/api/settings/model_api_key", json={"api_key": key})

    assert route.calls[0].request.headers["Authorization"] == f"Bearer {key}"
    assert response.status_code == 200, response.text
    assert response.json() == {
        "ok": True,
        "model_api_key": {"configured": True, "source": "panel", "masked": "…1234"},
    }
    assert key not in response.text
    status = client.get("/panel/api/settings").json()["model_api_key"]
    assert status == {"configured": True, "source": "panel", "masked": "…1234"}
    assert key not in client.get("/panel/api/settings").text
    with SessionLocal() as session:
        audits = session.scalars(
            select(AuditLog).where(AuditLog.action == "model_api_key.set")
        ).all()
        secret = session.scalar(select(PanelSecret))
        assert len(audits) == 1
        assert key not in str(audits[0].before) + str(audits[0].after)
        assert secret is not None and key.encode() not in secret.ciphertext


def test_set_key_accepts_no_balance_response(client, make_user, monkeypatch):
    _encryption_key(monkeypatch)
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    with respx.mock(assert_all_called=True) as router:
        router.get(DEEPSEEK_MODELS_URL).mock(return_value=httpx.Response(402))
        response = client.post(
            "/panel/api/settings/model_api_key", json={"api_key": "sk-test-no-balance"}
        )
    assert response.status_code == 200, response.text
    assert response.json()["model_api_key"]["source"] == "panel"


def test_invalid_key_is_rejected_without_persisting(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    with respx.mock(assert_all_called=True) as router:
        router.get(DEEPSEEK_MODELS_URL).mock(return_value=httpx.Response(401))
        response = client.post(
            "/panel/api/settings/model_api_key", json={"api_key": "sk-test-invalid"}
        )
    assert response.status_code == 400
    assert response.json() == {"detail": "invalid api key"}
    with SessionLocal() as session:
        assert session.scalar(select(PanelSecret)) is None


def test_validation_network_failure_returns_502(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    with respx.mock(assert_all_called=True) as router:
        router.get(DEEPSEEK_MODELS_URL).mock(side_effect=httpx.ConnectTimeout("timeout"))
        response = client.post(
            "/panel/api/settings/model_api_key", json={"api_key": "sk-test-network"}
        )
    assert response.status_code == 502
    assert response.json() == {"detail": "could not validate the api key"}


def test_unexpected_validation_status_returns_502(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    with respx.mock(assert_all_called=True) as router:
        router.get(DEEPSEEK_MODELS_URL).mock(return_value=httpx.Response(503))
        response = client.post(
            "/panel/api/settings/model_api_key", json={"api_key": "sk-test-unavailable"}
        )
    assert response.status_code == 502


def test_empty_key_is_rejected(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    response = client.post("/panel/api/settings/model_api_key", json={"api_key": "  \n"})
    assert response.status_code == 400
    assert response.json() == {"detail": "api key must not be empty"}


def test_delete_clears_panel_key_and_audits_without_secret(client, make_user, monkeypatch):
    _encryption_key(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-env-fallback")
    get_settings.cache_clear()
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    with respx.mock(assert_all_called=True) as router:
        router.get(DEEPSEEK_MODELS_URL).mock(return_value=httpx.Response(200))
        client.post(
            "/panel/api/settings/model_api_key", json={"api_key": "sk-test-to-delete"}
        )
    response = client.delete("/panel/api/settings/model_api_key")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "ok": True,
        "model_api_key": {"configured": True, "source": "env", "masked": "…back"},
    }
    with SessionLocal() as session:
        assert session.scalar(select(PanelSecret)) is None
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "model_api_key.clear")
        )
        assert audit is not None and "sk-test-to-delete" not in str(audit.before) + str(audit.after)


def test_settings_get_masks_environment_key(client, make_user, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-env-secret-9876")
    get_settings.cache_clear()
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    response = client.get("/panel/api/settings")
    assert response.status_code == 200
    assert response.json()["model_api_key"] == {
        "configured": True,
        "source": "env",
        "masked": "…9876",
    }
    assert "sk-test-env-secret-9876" not in response.text


def test_settings_get_reports_no_key(client, make_user, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_settings.cache_clear()
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    response = client.get("/panel/api/settings")
    assert response.status_code == 200
    assert response.json()["model_api_key"] == {
        "configured": False,
        "source": "none",
        "masked": "",
    }


def test_model_api_key_mutations_are_admin_only(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")
    assert client.post(
        "/panel/api/settings/model_api_key", json={"api_key": "sk-test-denied"}
    ).status_code == 403
    assert client.delete("/panel/api/settings/model_api_key").status_code == 403
