"""Unique JSON authentication contracts not covered by ``test_api_auth``."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.services.users import verify_password  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def _user_row(username: str) -> User:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == username))
        assert user is not None
        return user


@pytest.mark.spec("AP-1")
def test_authorized_json_login_resets_failed_counter(client, make_user):
    user_id = make_user("admin", "s3cret-admin", role="admin")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        user.failed_logins = 3
        session.commit()

    resp = client.post(
        "/panel/api/login",
        json={"username": "admin", "password": "s3cret-admin"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "id": user_id, "role": "admin"}
    refreshed = _user_row("admin")
    assert refreshed.failed_logins == 0
    assert refreshed.locked_until is None


@pytest.mark.spec("AP-1")
def test_lock_expiry_allows_json_login_again(client, make_user):
    user_id = make_user("admin", "s3cret-admin", role="admin")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()

    resp = client.post(
        "/panel/api/login",
        json={"username": "admin", "password": "s3cret-admin"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "id": user_id, "role": "admin"}


@pytest.mark.spec("AP-1")
def test_inactive_user_cannot_json_login(client, make_user):
    user_id = make_user("admin", "s3cret-admin", role="admin")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        user.active = False
        session.commit()

    resp = client.post(
        "/panel/api/login",
        json={"username": "admin", "password": "s3cret-admin"},
        follow_redirects=False,
    )

    assert resp.status_code == 401
    assert resp.json() == {"detail": "invalid credentials"}


@pytest.mark.spec("AP-2")
def test_json_session_role_and_tampered_cookie_are_enforced(client, make_user):
    user_id = make_user("oper", "oper-pass", role="operador")
    resp = client.post(
        "/panel/api/login",
        json={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    assert client.get("/panel/api/me").json() == {
        "id": user_id, "username": "oper", "role": "operador",
        "email": None, "name": None, "phone": None, "position": None,
    }

    # A forged session cookie is not a credential. The remembered device is one, so it is removed
    # first: otherwise the request would be restored on purpose and the assertion would prove nothing.
    client.cookies.delete("lumat_remember", path="/")
    client.cookies.set("session", "tampered")
    resp = client.get("/panel/api/me", follow_redirects=False)
    assert resp.status_code == 401
    assert resp.json() == {"detail": "unauthorized"}


def test_a_remembered_device_outlives_a_forged_session_cookie(client, make_user):
    """AP-2 with the remember feature: the forged cookie is discarded, the device is not."""
    user_id = make_user("oper-remember", "oper-pass", role="operador")
    token = client.post(
        "/panel/api/login",
        json={"username": "oper-remember", "password": "oper-pass"},
        follow_redirects=False,
    ).cookies["lumat_remember"]

    client.cookies.set("session", "tampered")
    resp = client.get("/panel/api/me", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json()["id"] == user_id
    # Restoring rotates: the credential the client now holds is not the one it presented.
    assert resp.cookies["lumat_remember"] not in (None, "", token)


def _run_seed_admin(env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            str(REPO_ROOT / ".venv" / "bin" / "python"),
            str(REPO_ROOT / "app" / "panel" / "seed_admin.py"),
        ],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
    )


@pytest.mark.spec("AP-1")
def test_seed_admin_creates_idempotent_bcrypt_admin(client):
    result = _run_seed_admin(
        {"PANEL_ADMIN_USERNAME": "root-admin", "PANEL_ADMIN_PASSWORD": "seed-pass"}
    )
    assert result.returncode == 0, f"seed failed: {result.stdout} {result.stderr}"
    user = _user_row("root-admin")
    assert user.role.value == "admin"
    assert verify_password("seed-pass", user.password_hash)

    _run_seed_admin({"PANEL_ADMIN_USERNAME": "root-admin", "PANEL_ADMIN_PASSWORD": "other"})
    with SessionLocal() as session:
        count = session.scalar(
            select(func.count()).select_from(User).where(User.username == "root-admin")
        )
    assert count == 1
    assert verify_password("seed-pass", _user_row("root-admin").password_hash)


@pytest.mark.spec("AP-1")
def test_seed_admin_requires_password(client):
    result = _run_seed_admin({"PANEL_ADMIN_USERNAME": "root-admin"})
    assert result.returncode != 0
    assert "PANEL_ADMIN_PASSWORD" in result.stderr
    with SessionLocal() as session:
        count = session.scalar(
            select(func.count()).select_from(User).where(User.username == "root-admin")
        )
    assert count == 0
