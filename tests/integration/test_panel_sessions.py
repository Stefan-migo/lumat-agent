"""DB-backed contract for per-device panel remember sessions."""

from datetime import datetime, timezone

from sqlalchemy import select

from _testdb import admin_database_url
from app.db import SessionLocal
from app.models import AuditLog, PanelSession, User
from app.services.panel_sessions import hash_token
from app.services.users import hash_password

ADMIN_DB_URL = admin_database_url()


def _user(username: str) -> int:
    with SessionLocal() as session:
        user = User(username=username, password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.commit()
        return user.id


def _login(client, username: str):
    response = client.post("/panel/api/login", json={"username": username, "password": "pass"})
    assert response.status_code == 200
    return response


def _session_rows(user_id: int) -> list[PanelSession]:
    with SessionLocal() as session:
        return list(session.scalars(select(PanelSession).where(PanelSession.user_id == user_id).order_by(PanelSession.id)))


def _clear_signed_cookie(client):
    client.cookies.delete("session", path="/")


def test_login_sets_remember_cookie_and_persists_only_hash(client, migrated_db):
    user_id = _user("remember-login")

    response = _login(client, "remember-login")

    token = response.cookies.get("lumat_remember")
    assert token
    assert response.json() == {"ok": True, "id": user_id, "role": "admin"}
    assert response.cookies.get("session")
    cookie = next(value for value in response.headers.get_list("set-cookie") if value.startswith("lumat_remember="))
    assert "Path=/" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=7776000" in cookie
    assert "Secure" not in cookie
    rows = _session_rows(user_id)
    assert len(rows) == 1
    assert rows[0].token_hash == hash_token(token)
    assert rows[0].token_hash != token
    assert rows[0].user_agent == "testclient"


def test_login_can_skip_remember_cookie_without_changing_signed_session(client, migrated_db):
    user_id = _user("remember-opt-out")

    response = client.post(
        "/panel/api/login",
        json={"username": "remember-opt-out", "password": "pass", "remember": False},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "id": user_id, "role": "admin"}
    assert response.cookies.get("session")
    assert "lumat_remember" not in response.cookies
    assert _session_rows(user_id) == []


def test_remember_cookie_restores_and_rotates_after_signed_cookie_is_cleared(client, migrated_db):
    user_id = _user("remember-restore")
    login = _login(client, "remember-restore")
    original = login.cookies.get("lumat_remember")
    _clear_signed_cookie(client)

    response = client.get("/panel/api/me")

    assert response.status_code == 200
    assert response.json()["id"] == user_id
    rotated = response.cookies.get("lumat_remember")
    assert rotated and rotated != original
    assert len(_session_rows(user_id)) == 2
    with SessionLocal() as session:
        assert session.scalar(select(AuditLog).where(AuditLog.action == "auth.session_restored"))


def test_revoked_remember_token_does_not_restore_or_reissue_cookie(client, migrated_db):
    user_id = _user("remember-revoked")
    token = _login(client, "remember-revoked").cookies.get("lumat_remember")
    with SessionLocal() as session:
        row = session.scalar(select(PanelSession).where(PanelSession.token_hash == hash_token(token)))
        row.revoked_at = datetime.now(timezone.utc)
        session.commit()
    _clear_signed_cookie(client)

    response = client.get("/panel/api/me")

    assert response.status_code == 401
    assert "lumat_remember" not in response.cookies
    assert _session_rows(user_id)[0].revoked_at is not None


def test_rotated_token_reuse_revokes_all_and_is_audited(client, migrated_db):
    user_id = _user("remember-reuse")
    old_token = _login(client, "remember-reuse").cookies.get("lumat_remember")
    _clear_signed_cookie(client)
    restored = client.get("/panel/api/me")
    assert restored.status_code == 200
    new_token = restored.cookies.get("lumat_remember")
    # Present the copied, already-rotated cookie with no signed session.
    client.cookies.set("lumat_remember", old_token, path="/")
    _clear_signed_cookie(client)

    response = client.get("/panel/api/me")

    assert response.status_code == 401
    cleared = {cookie.split("=", 1)[0].split(";")[0] for cookie in response.headers.get_list("set-cookie")}
    assert {"session", "lumat_remember"}.issubset(cleared)
    rows = _session_rows(user_id)
    assert rows and all(row.revoked_at is not None for row in rows)
    with SessionLocal() as session:
        assert session.scalar(select(AuditLog).where(AuditLog.action == "auth.session_reuse"))
    assert new_token


def test_locked_user_remember_token_cannot_restore(client, migrated_db):
    user_id = _user("remember-locked")
    _login(client, "remember-locked")
    with SessionLocal() as session:
        session.get(User, user_id).locked_until = datetime(2099, 1, 1, tzinfo=timezone.utc)
        session.commit()
    _clear_signed_cookie(client)

    response = client.get("/panel/api/me")

    assert response.status_code == 401
    assert "lumat_remember" not in response.cookies


def test_deactivated_user_remember_token_cannot_restore(client, migrated_db):
    user_id = _user("remember-inactive")
    _login(client, "remember-inactive")
    with SessionLocal() as session:
        session.get(User, user_id).active = False
        session.commit()
    _clear_signed_cookie(client)

    response = client.get("/panel/api/me")

    assert response.status_code == 401
    assert "lumat_remember" not in response.cookies


def test_logout_revokes_current_row_and_clears_both_cookies(client, migrated_db):
    user_id = _user("remember-logout")
    _login(client, "remember-logout")

    response = client.post("/panel/api/logout")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    cleared = {cookie.split("=", 1)[0].split(";")[0] for cookie in response.headers.get_list("set-cookie")}
    assert {"session", "lumat_remember"}.issubset(cleared)
    assert _session_rows(user_id)[0].revoked_at is not None


def test_sessions_lists_current_device(client, migrated_db):
    _user("remember-list")
    _login(client, "remember-list")

    response = client.get("/panel/api/sessions")

    assert response.status_code == 200
    assert len(response.json()["sessions"]) == 1
    listed = response.json()["sessions"][0]
    assert listed["current"] is True
    assert {"id", "user_agent", "created_at", "last_used_at", "current"} == set(listed)


def test_cannot_revoke_another_users_session(client, migrated_db):
    owner_id = _user("remember-owner")
    other_id = _user("remember-other")
    with SessionLocal() as session:
        own = PanelSession(user_id=owner_id, token_hash="a" * 64, expires_at=datetime.now(timezone.utc))
        foreign = PanelSession(user_id=other_id, token_hash="b" * 64, expires_at=datetime.now(timezone.utc))
        session.add_all([own, foreign])
        session.commit()
        foreign_id = foreign.id
    _login(client, "remember-owner")

    response = client.post(f"/panel/api/sessions/{foreign_id}/revoke")

    assert response.status_code == 404
    with SessionLocal() as session:
        assert session.get(PanelSession, foreign_id).revoked_at is None


def test_revoke_all_keeps_current_device(client, migrated_db):
    user_id = _user("remember-revoke-all")
    current_token = _login(client, "remember-revoke-all").cookies.get("lumat_remember")
    with SessionLocal() as session:
        session.add(PanelSession(user_id=user_id, token_hash="c" * 64, expires_at=datetime.now(timezone.utc)))
        session.commit()

    response = client.post("/panel/api/sessions/revoke-all")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    rows = _session_rows(user_id)
    current = next(row for row in rows if row.token_hash == hash_token(current_token))
    other = next(row for row in rows if row.id != current.id)
    assert current.revoked_at is None
    assert other.revoked_at is not None


class _Handshake:
    """The attributes `restore_panel_user` reads from a connection, without a transport."""

    def __init__(self, scope_type: str, cookies: dict[str, str]):
        from starlette.datastructures import State

        self.scope = {"type": scope_type}
        self.cookies = cookies
        self.session = {}
        self.state = State()


def test_a_websocket_handshake_never_consumes_the_remember_token(migrated_db):
    """S1: the live connection cannot receive the rotated cookie, so it must not spend it.

    FastAPI solves a WebSocket route's dependencies with no `Response`, so a rotation there revokes
    a token the browser keeps -- and the next HTTP request would be read as a copied cookie and sign
    the operator out of every device.
    """
    from app.panel.deps import REMEMBER_COOKIE, restore_panel_user
    from app.services import panel_sessions

    user_id = _user("remember-ws")
    with SessionLocal() as session:
        token = panel_sessions.issue(session, user_id, "live")
        session.commit()

    with SessionLocal() as session:
        handshake = _Handshake("websocket", {REMEMBER_COOKIE: token})
        user = restore_panel_user(handshake, session, None)
        session.commit()

        assert user is not None and user.id == user_id
        # The credential survives: the same token still restores a real HTTP request afterwards.
        assert panel_sessions.resolve(session, token) is not None

    with SessionLocal() as session:
        from starlette.datastructures import State

        request = _Handshake("http", {REMEMBER_COOKIE: token})
        request.scope = {"type": "http"}
        request.state = State()
        assert restore_panel_user(request, session, None) is not None
        session.commit()
        assert panel_sessions.resolve(session, token) is None
