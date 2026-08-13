"""Panel authentication + roles (T5.1; AP-1, AP-2, SH-5).

Functional suite over the FastAPI TestClient: login form -> bcrypt verify ->
Starlette signed-cookie session (12 h), failed_login counter with a 5-fail /
15-minute lock, server-side role enforcement on every route, and audit rows
for login/logout/failure (SH-5 — login audit was deferred to T5.1 in B1).

The full admin-gate matrix (operador -> /panel/settings and /panel/kb 403,
admin -> 200) lands with the admin-only routes in T5.4 (test_kb_settings.py);
here the matrix covers the shared routes plus the session-role contract.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, User  # noqa: E402
from app.services.users import hash_password, verify_password  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def _user_row(username: str) -> User:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == username))
        assert user is not None, f"user {username!r} not found"
        return user


def _audit_actions() -> list[tuple[str, str]]:
    with SessionLocal() as session:
        rows = session.execute(
            select(AuditLog.action, AuditLog.actor).order_by(AuditLog.id)
        ).all()
        return [(a, actor) for a, actor in rows]


# ---------------------------------------------------------------------------
# AP-1 — authentication
# ---------------------------------------------------------------------------


@pytest.mark.spec("AP-1")
def test_unauthenticated_panel_redirects_to_login(client):
    """No session cookie -> every panel page redirects to /panel/login."""
    resp = client.get("/panel/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/panel/login"


@pytest.mark.spec("AP-1")
def test_authorized_login_sets_session_and_audits(client, make_user):
    """Valid credentials -> signed session cookie + redirect + audit row."""
    make_user("admin", "s3cret-admin", role="admin")

    resp = client.post(
        "/panel/login",
        data={"username": "admin", "password": "s3cret-admin"},
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert resp.headers["location"] == "/panel/"
    assert "session" in resp.cookies, "signed session cookie must be set"
    assert ("auth.login", "admin") in _audit_actions(), "login must be audited (SH-5)"


@pytest.mark.spec("AP-1")
def test_authorized_login_resets_failed_counter(client, make_user):
    """A successful login clears failed_logins/locked_until (AP-1)."""
    user_id = make_user("admin", "s3cret-admin", role="admin")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        user.failed_logins = 3
        session.commit()

    client.post(
        "/panel/login",
        data={"username": "admin", "password": "s3cret-admin"},
        follow_redirects=False,
    )

    refreshed = _user_row("admin")
    assert refreshed.failed_logins == 0
    assert refreshed.locked_until is None


@pytest.mark.spec("AP-1")
def test_failed_login_audited_and_counted(client, make_user):
    """Wrong password -> audit row + failed_logins increment, no session."""
    make_user("admin", "s3cret-admin", role="admin")

    resp = client.post(
        "/panel/login",
        data={"username": "admin", "password": "wrong-pass"},
        follow_redirects=False,
    )

    assert resp.status_code == 200  # login page re-rendered with error
    assert "invalid credentials" in resp.text
    assert "session" not in resp.cookies
    assert _user_row("admin").failed_logins == 1
    assert ("auth.login_failed", "admin") in _audit_actions()


@pytest.mark.spec("AP-1")
def test_unknown_username_failed_login_audited(client):
    """No such user -> generic error + audit row, nothing else leaks."""
    resp = client.post(
        "/panel/login",
        data={"username": "ghost", "password": "whatever"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert "invalid credentials" in resp.text
    assert ("auth.login_failed", "ghost") in _audit_actions()


@pytest.mark.spec("AP-1")
def test_lockout_after_five_failures(client, make_user):
    """5 failed attempts -> locked_until set; correct password then rejected."""
    make_user("admin", "s3cret-admin", role="admin")

    for _ in range(5):
        client.post(
            "/panel/login",
            data={"username": "admin", "password": "wrong"},
            follow_redirects=False,
        )

    locked = _user_row("admin")
    assert locked.locked_until is not None, "5th failure must set locked_until"
    assert locked.failed_logins == 0, "counter resets so the lock is a clean 15-min ban"

    # Even with the CORRECT password the account stays locked.
    resp = client.post(
        "/panel/login",
        data={"username": "admin", "password": "s3cret-admin"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    assert "locked" in resp.text
    assert "session" not in resp.cookies


@pytest.mark.spec("AP-1")
def test_lock_expiry_allows_login_again(client, make_user):
    """After locked_until passes, a correct login succeeds (15-min ban ends)."""
    user_id = make_user("admin", "s3cret-admin", role="admin")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()

    resp = client.post(
        "/panel/login",
        data={"username": "admin", "password": "s3cret-admin"},
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert resp.headers["location"] == "/panel/"


@pytest.mark.spec("AP-1")
def test_inactive_user_cannot_login(client, make_user):
    """active=False accounts are rejected at the door (no session, audited)."""
    user_id = make_user("admin", "s3cret-admin", role="admin")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        user.active = False
        session.commit()

    resp = client.post(
        "/panel/login",
        data={"username": "admin", "password": "s3cret-admin"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert "invalid credentials" in resp.text
    assert "session" not in resp.cookies
    assert ("auth.login_failed", "admin") in _audit_actions()


# ---------------------------------------------------------------------------
# AP-2 — roles (shared-route matrix here; admin-only gates land in T5.4)
# ---------------------------------------------------------------------------


@pytest.mark.spec("AP-2")
def test_operador_can_access_panel_home(client, make_user):
    """operador logs in and reaches the panel home (shared route)."""
    make_user("oper", "oper-pass", role="operador")
    client.post(
        "/panel/login",
        data={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )

    resp = client.get("/panel/")
    assert resp.status_code == 200


@pytest.mark.spec("AP-2")
def test_admin_can_access_panel_home(client, make_user):
    """admin logs in and reaches the panel home (shared route)."""
    make_user("adm", "adm-pass", role="admin")
    client.post(
        "/panel/login",
        data={"username": "adm", "password": "adm-pass"},
        follow_redirects=False,
    )

    resp = client.get("/panel/")
    assert resp.status_code == 200


@pytest.mark.spec("AP-2")
def test_session_carries_role(client, make_user):
    """The signed session stores user_id/username/role (server-side only)."""
    import base64
    import json

    make_user("oper", "oper-pass", role="operador")
    client.post(
        "/panel/login",
        data={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )

    # Starlette signs a base64-encoded JSON payload: decode and check the
    # session claims (the signature part after the second dot is not ours).
    raw = client.cookies.get("session")
    assert raw is not None
    payload_b64 = raw.split(".")[0]
    claims = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
    assert claims["username"] == "oper"
    assert claims["role"] == "operador"

    # A corrupted cookie must NOT authenticate (server-side trust only).
    client.cookies.set("session", "tampered")
    resp = client.get("/panel/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/panel/login"


# ---------------------------------------------------------------------------
# SH-5 — logout audited
# ---------------------------------------------------------------------------


@pytest.mark.spec("SH-5")
def test_logout_clears_session_and_audits(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    client.post(
        "/panel/login",
        data={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )

    resp = client.post("/panel/logout", follow_redirects=False)

    assert resp.status_code == 302
    assert resp.headers["location"] == "/panel/login"
    assert ("auth.logout", "oper") in _audit_actions()
    # Session is gone: the next panel request redirects to login again.
    resp = client.get("/panel/", follow_redirects=False)
    assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Seed script — initial admin (bcrypt)
# ---------------------------------------------------------------------------


def _run_seed_admin(env: dict) -> subprocess.CompletedProcess:
    env = {**os.environ, **env}
    return subprocess.run(
        [str(REPO_ROOT / ".venv" / "bin" / "python"), str(REPO_ROOT / "app" / "panel" / "seed_admin.py")],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.spec("AP-1")
def test_seed_admin_creates_bcrypt_admin(client):
    """seed_admin.py creates the initial admin with a bcrypt hash (idempotent)."""
    result = _run_seed_admin(
        {"PANEL_ADMIN_USERNAME": "root-admin", "PANEL_ADMIN_PASSWORD": "seed-pass"}
    )
    assert result.returncode == 0, f"seed failed: {result.stdout} {result.stderr}"

    user = _user_row("root-admin")
    assert user.role.value == "admin"
    assert verify_password("seed-pass", user.password_hash), "hash must be bcrypt-verifiable"

    # Idempotent: a second run does not duplicate the account.
    _run_seed_admin({"PANEL_ADMIN_USERNAME": "root-admin", "PANEL_ADMIN_PASSWORD": "other"})
    with SessionLocal() as session:
        count = session.scalar(
            select(func.count()).select_from(User).where(User.username == "root-admin")
        )
    assert count == 1
    # The password from the second run did NOT overwrite (first wins).
    assert verify_password("seed-pass", _user_row("root-admin").password_hash)


@pytest.mark.spec("AP-1")
def test_seed_admin_requires_password(client):
    """Missing PANEL_ADMIN_PASSWORD -> clear error, no user created."""
    result = _run_seed_admin({"PANEL_ADMIN_USERNAME": "root-admin"})
    assert result.returncode != 0
    assert "PANEL_ADMIN_PASSWORD" in result.stderr
    with SessionLocal() as session:
        count = session.scalar(
            select(func.count()).select_from(User).where(User.username == "root-admin")
        )
    assert count == 0
