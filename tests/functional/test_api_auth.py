"""Panel JSON API authentication (B1/T1.2; PDW-AUTH-1/2/4, PDW-API-3, D1, D4).

The JSON layer (`/panel/api/*`) coexists with the Jinja2 routes but answers
errors as JSON instead of redirecting (D4): the SPA must never follow a 302
to the HTML login page (PDW-AUTH-1). This suite covers the auth trio —
login / me / logout — reusing the same service calls, lockout sequence and
audit actions as the Jinja route (SH-5), with unchanged cookie flags and no
CORS (D1, PDW-AUTH-4).

Error shape contract (PDW-API-3): every failure is JSON `{"detail": "..."}`
with the appropriate status — never an HTML page.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, User  # noqa: E402


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
# PDW-AUTH-1 — /me without a session: 401 JSON, no redirect
# ---------------------------------------------------------------------------


def test_me_without_session_returns_401_json_no_redirect(client):
    """No session cookie -> 401 JSON {"detail":"unauthorized"}, never a 302."""
    resp = client.get("/panel/api/me", follow_redirects=False)

    assert resp.status_code == 401, "must be 401, not a redirect"
    assert "location" not in resp.headers, "must not redirect to the login page"
    assert resp.headers["content-type"].startswith("application/json"), (
        "error must be JSON (PDW-API-3)"
    )
    assert resp.json() == {"detail": "unauthorized"}


def test_me_without_session_has_no_cors_headers(client):
    """D1: same-origin only — no CORS headers on API responses."""
    resp = client.get("/panel/api/me", follow_redirects=False)

    assert "access-control-allow-origin" not in resp.headers


# ---------------------------------------------------------------------------
# PDW-AUTH-2 — /me with a session: 200 {username, role}
# ---------------------------------------------------------------------------


def test_me_with_session_returns_username_role(client, make_user):
    """Valid session -> 200 JSON with username and role (operador)."""
    make_user("oper", "oper-pass", role="operador")
    client.post(
        "/panel/api/login",
        json={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )

    resp = client.get("/panel/api/me", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json() == {"username": "oper", "role": "operador"}


def test_me_with_admin_session_returns_admin_role(client, make_user):
    """Valid admin session -> 200 JSON with the admin role (triangulation)."""
    make_user("adm", "adm-pass", role="admin")
    client.post(
        "/panel/api/login",
        json={"username": "adm", "password": "adm-pass"},
        follow_redirects=False,
    )

    resp = client.get("/panel/api/me", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json() == {"username": "adm", "role": "admin"}


def test_me_with_tecnico_session_returns_tecnico_role(client, make_user):
    make_user("tech", "tech-pass", role="tecnico")
    login = client.post(
        "/panel/api/login",
        json={"username": "tech", "password": "tech-pass"},
        follow_redirects=False,
    )
    assert login.status_code == 200
    assert login.json() == {"ok": True, "role": "tecnico"}

    resp = client.get("/panel/api/me", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json() == {"username": "tech", "role": "tecnico"}


def test_me_deactivated_user_returns_401(client, make_user):
    """active=False loses access immediately (same as the Jinja dep)."""
    user_id = make_user("oper", "oper-pass", role="operador")
    client.post(
        "/panel/api/login",
        json={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )
    with SessionLocal() as session:
        user = session.get(User, user_id)
        user.active = False
        session.commit()

    resp = client.get("/panel/api/me", follow_redirects=False)

    assert resp.status_code == 401
    assert resp.json() == {"detail": "unauthorized"}


# ---------------------------------------------------------------------------
# PDW-AUTH-4 — JSON login sets the same session cookie; logout clears it
# ---------------------------------------------------------------------------


def test_json_login_sets_cookie_and_audits(client, make_user):
    """Valid JSON credentials -> 200 {ok, role}, session cookie, audit."""
    make_user("admin", "s3cret-admin", role="admin")

    resp = client.post(
        "/panel/api/login",
        json={"username": "admin", "password": "s3cret-admin"},
        follow_redirects=False,
    )

    assert resp.status_code == 200, "JSON login must not redirect"
    assert resp.json() == {"ok": True, "role": "admin"}
    assert "session" in resp.cookies, "the existing session cookie must be set (PDW-AUTH-4)"
    assert ("auth.login", "admin") in _audit_actions(), "login must be audited (SH-5)"


def test_json_login_returns_operador_role(client, make_user):
    """operador credentials -> same cookie, role=operador (triangulation)."""
    make_user("oper", "oper-pass", role="operador")

    resp = client.post(
        "/panel/api/login",
        json={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "role": "operador"}
    assert "session" in resp.cookies


def test_tecnico_is_denied_admin_and_operational_json_surfaces(client, make_user):
    make_user("tech", "tech-pass", role="tecnico")
    client.post(
        "/panel/api/login",
        json={"username": "tech", "password": "tech-pass"},
        follow_redirects=False,
    )

    for method, path in (
        ("get", "/panel/api/settings"),
        ("get", "/panel/api/conversations"),
        ("get", "/panel/api/clients"),
        ("get", "/panel/api/cases"),
        ("post", "/panel/api/chat/threads"),
    ):
        if method == "post":
            response = client.post(path, json={}, follow_redirects=False)
        else:
            response = client.get(path, follow_redirects=False)
        assert response.status_code == 403, path
        assert response.headers["content-type"].startswith("application/json")


def test_json_login_invalid_credentials(client, make_user):
    """Wrong password -> 401 JSON {"detail":"invalid credentials"}, audited."""
    make_user("admin", "s3cret-admin", role="admin")

    resp = client.post(
        "/panel/api/login",
        json={"username": "admin", "password": "wrong-pass"},
        follow_redirects=False,
    )

    assert resp.status_code == 401
    assert resp.json() == {"detail": "invalid credentials"}
    assert resp.headers["content-type"].startswith("application/json")
    assert "session" not in resp.cookies
    assert _user_row("admin").failed_logins == 1
    assert ("auth.login_failed", "admin") in _audit_actions()


def test_json_login_unknown_username_generic_error(client):
    """No such user -> same generic 401, nothing leaks (no user oracle)."""
    resp = client.post(
        "/panel/api/login",
        json={"username": "ghost", "password": "whatever"},
        follow_redirects=False,
    )

    assert resp.status_code == 401
    assert resp.json() == {"detail": "invalid credentials"}
    assert "session" not in resp.cookies
    assert ("auth.login_failed", "ghost") in _audit_actions()


def test_json_login_locked_account(client, make_user):
    """5 failures -> lock; even a correct password returns 401 "account locked"."""
    make_user("admin", "s3cret-admin", role="admin")
    for _ in range(5):
        client.post(
            "/panel/api/login",
            json={"username": "admin", "password": "wrong"},
            follow_redirects=False,
        )

    locked = _user_row("admin")
    assert locked.locked_until is not None, "5th failure must set locked_until"

    resp = client.post(
        "/panel/api/login",
        json={"username": "admin", "password": "s3cret-admin"},
        follow_redirects=False,
    )

    assert resp.status_code == 401
    assert resp.json() == {"detail": "account locked"}
    assert "session" not in resp.cookies
    assert ("auth.login_locked", "admin") in _audit_actions()


def test_json_logout_clears_session_and_audits(client, make_user):
    """Logout -> 200 {ok}, audit row, session gone (next /me is 401 again)."""
    make_user("oper", "oper-pass", role="operador")
    client.post(
        "/panel/api/login",
        json={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )

    resp = client.post("/panel/api/logout", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert ("auth.logout", "oper") in _audit_actions(), "logout must be audited (SH-5)"
    me = client.get("/panel/api/me", follow_redirects=False)
    assert me.status_code == 401, "session must be cleared by logout"


def test_json_logout_without_session_returns_401(client):
    """Unauthenticated logout -> 401 JSON, same error shape (PDW-API-3)."""
    resp = client.post("/panel/api/logout", follow_redirects=False)

    assert resp.status_code == 401
    assert resp.json() == {"detail": "unauthorized"}
