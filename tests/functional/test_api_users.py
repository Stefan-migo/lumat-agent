from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, User
from app.services.users import verify_password


def _login(client, make_user, username, password, role):
    make_user(username, password, role=role)
    response = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 200


def _admin(client, make_user, username="users-admin"):
    user_id = make_user(username, "admin-pass", role="admin")
    response = client.post(
        "/panel/api/login", json={"username": username, "password": "admin-pass"}
    )
    assert response.status_code == 200
    return user_id


def test_every_users_endpoint_returns_json_auth_errors(client, make_user):
    requests = [
        ("get", "/panel/api/users", {}),
        ("post", "/panel/api/users", {"json": {"username": "new", "password": "long-pass", "role": "admin"}}),
        ("post", "/panel/api/users/1/toggle-active", {}),
        ("post", "/panel/api/users/1/reset-password", {"json": {"password": "long-pass"}}),
        ("get", "/panel/api/users/1", {}),
        ("patch", "/panel/api/users/1", {"json": {"name": "x"}}),
        ("post", "/panel/api/users/1/unlock", {}),
    ]
    for method, path, kwargs in requests:
        response = getattr(client, method)(path, follow_redirects=False, **kwargs)
        assert response.status_code == 401
        assert response.headers["content-type"].startswith("application/json")
        assert "location" not in response.headers

    for role in ("operador", "tecnico"):
        client.post("/panel/api/logout")
        _login(client, make_user, f"{role}-user", "role-pass", role)
        for method, path, kwargs in requests:
            response = getattr(client, method)(path, **kwargs)
            assert response.status_code == 403
            assert "user" not in response.json()


def test_admin_list_is_ordered_and_allow_listed(client, make_user):
    _admin(client, make_user)
    make_user("same", "password1", role="tecnico")
    make_user("alpha", "password1", role="operador")
    make_user("same-later", "password1", role="admin")

    response = client.get("/panel/api/users")

    assert response.status_code == 200
    users = response.json()["users"]
    assert [(row["username"], row["id"]) for row in users] == sorted(
        (row["username"], row["id"]) for row in users
    )
    assert {row["role"] for row in users} == {"admin", "operador", "tecnico"}
    expected = {"id", "username", "role", "active", "email", "name", "phone", "position", "locked_until", "failed_logins"}
    assert all(set(row) == expected for row in users)
    assert all("password_hash" not in row for row in users)


def test_technician_list_is_operator_readable_minimal_and_ordered(client, make_user):
    unauthenticated = client.get("/panel/api/technicians", follow_redirects=False)
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["content-type"].startswith("application/json")
    assert "location" not in unauthenticated.headers

    make_user("zulu-tech", "password1", role="tecnico")
    make_user("alpha-operator", "password1", role="operador")
    make_user("bravo-tech", "password1", role="tecnico")
    _login(client, make_user, "technician-picker-operator", "password1", "operador")

    response = client.get("/panel/api/technicians")

    assert response.status_code == 200
    technicians = response.json()["technicians"]
    assert [row["username"] for row in technicians] == ["bravo-tech", "zulu-tech"]
    assert all(set(row) == {"id", "username"} for row in technicians)

    client.post("/panel/api/logout")
    _login(client, make_user, "technician-picker-technician", "password1", "tecnico")
    forbidden = client.get("/panel/api/technicians", follow_redirects=False)
    assert forbidden.status_code == 403
    assert forbidden.headers["content-type"].startswith("application/json")
    assert "location" not in forbidden.headers


def test_create_accepts_each_role_and_hashes_password(client, make_user):
    _admin(client, make_user)
    for role in ("admin", "operador", "tecnico"):
        response = client.post(
            "/panel/api/users",
            json={"username": f"created-{role}", "password": "initial-pass", "role": role},
        )
        assert response.status_code == 201
        assert response.json()["user"] == {
            "id": response.json()["user"]["id"],
            "username": f"created-{role}",
            "role": role,
            "active": True,
            "email": None,
            "name": None,
            "phone": None,
            "position": None,
            "locked_until": None,
            "failed_logins": 0,
        }
        assert "initial-pass" not in response.text

    with SessionLocal() as session:
        users = session.scalars(select(User).where(User.username.like("created-%"))).all()
        assert len(users) == 3
        assert all(user.password_hash != "initial-pass" for user in users)
        assert [audit.action for audit in session.scalars(select(AuditLog).where(AuditLog.action.like("user.%")).order_by(AuditLog.id)).all()] == [
            "user.create",
            "user.create",
            "user.create",
        ]


def test_create_rejects_invalid_and_duplicate_without_rows(client, make_user):
    _admin(client, make_user)
    make_user("existing", "password1")
    before = None
    with SessionLocal() as session:
        before = session.query(User).count()

    for payload, status in (
        ({"username": "", "password": "password1", "role": "operador"}, 422),
        ({"username": "short", "password": "short", "role": "operador"}, 422),
        ({"username": "bad-role", "password": "password1", "role": "manager"}, 422),
        ({"username": "existing", "password": "password1", "role": "operador"}, 409),
    ):
        response = client.post("/panel/api/users", json=payload)
        assert response.status_code == status

    with SessionLocal() as session:
        assert session.query(User).count() == before


def test_toggle_audits_result_and_rejects_missing_or_self(client, make_user):
    admin_id = _admin(client, make_user)
    target_id = make_user("toggle-target", "password1", role="operador")

    response = client.post(f"/panel/api/users/{target_id}/toggle-active")
    assert response.status_code == 200
    assert response.json()["user"]["active"] is False
    assert client.post(f"/panel/api/users/{target_id}/toggle-active").json()["user"]["active"] is True
    assert client.post(f"/panel/api/users/{admin_id}/toggle-active").status_code == 403
    assert client.post("/panel/api/users/999999/toggle-active").status_code == 404

    with SessionLocal() as session:
        audits = session.scalars(select(AuditLog).where(AuditLog.action.like("user.%")).order_by(AuditLog.id)).all()
        assert [audit.action for audit in audits] == ["user.toggle_active", "user.toggle_active"]
        assert audits[0].actor == "users-admin"
        assert audits[0].after["active"] is False


def test_reset_password_audits_and_rejects_short_missing_or_self(client, make_user):
    admin_id = _admin(client, make_user)
    target_id = make_user("reset-target", "old-pass", role="tecnico")

    response = client.post(f"/panel/api/users/{target_id}/reset-password", json={"password": "new-pass"})
    assert response.status_code == 200
    assert "new-pass" not in response.text
    assert response.json()["user"]["username"] == "reset-target"
    assert client.post(f"/panel/api/users/{target_id}/reset-password", json={"password": "short"}).status_code == 422
    assert client.post(f"/panel/api/users/{admin_id}/reset-password", json={"password": "new-pass"}).status_code == 403
    assert client.post("/panel/api/users/999999/reset-password", json={"password": "new-pass"}).status_code == 404

    with SessionLocal() as session:
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "user.reset_password"))
        assert audit.actor == "users-admin"
        assert "new-pass" not in str(audit.after)
        assert session.get(User, target_id).password_hash != "old-pass"


def test_user_profile_ficha_mutations_and_audit(client, make_user):
    _admin(client, make_user)
    target_id = make_user("profile-target", "initial-pass", role="operador")
    assert client.get(f"/panel/api/users/{target_id}").status_code == 200
    ficha = client.get(f"/panel/api/users/{target_id}").json()["user"]
    assert {key: ficha[key] for key in ("email", "name", "phone", "position")} == {
        "email": None, "name": None, "phone": None, "position": None,
    }
    assert client.get("/panel/api/users/999999").status_code == 404
    for field, value in (("email", "UPPER@example.com"), ("name", "Profile Name"), ("phone", "+56912345678"), ("position", "Manager")):
        response = client.patch(f"/panel/api/users/{target_id}", json={field: value})
        assert response.status_code == 200, response.text
        assert response.json()["user"][field] == (value.lower() if field == "email" else value)
    assert client.patch(f"/panel/api/users/{target_id}", json={"name": None}).json()["user"]["name"] is None
    for forbidden in ("role", "active"):
        assert client.patch(f"/panel/api/users/{target_id}", json={forbidden: "admin"}).status_code == 422
    duplicate_id = make_user("profile-duplicate", "initial-pass")
    assert client.patch(f"/panel/api/users/{duplicate_id}", json={"email": "upper@EXAMPLE.com"}).status_code == 409

    with SessionLocal() as session:
        actions = session.scalars(select(AuditLog.action).where(AuditLog.action.in_(("user.profile_update",)))).all()
        assert len(actions) >= 5


def test_self_profile_patch_only_changes_name_and_phone_and_audits(client, make_user):
    user_id = make_user("self-profile", "initial-pass", role="tecnico")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        user.email = "kept@example.com"
        user.position = "Admin-only label"
        session.commit()

    unauthenticated = client.patch("/panel/api/me", json={"name": "Changed"})
    assert unauthenticated.status_code == 401
    login = client.post(
        "/panel/api/login",
        json={"username": "self-profile", "password": "initial-pass"},
    )
    assert login.status_code == 200

    response = client.patch(
        "/panel/api/me",
        json={"name": " Self Name ", "phone": "+56912345678"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["name"] == "Self Name"
    assert response.json()["user"]["phone"] == "+56912345678"
    forbidden_fields = client.patch(
        "/panel/api/me", json={"email": "attacker@example.com", "position": "Owner"}
    )
    assert forbidden_fields.status_code == 422
    me = client.get("/panel/api/me").json()
    assert me["name"] == "Self Name"
    assert me["phone"] == "+56912345678"
    assert "locked_until" not in me and "failed_logins" not in me
    with SessionLocal() as session:
        user = session.get(User, user_id)
        assert user.email == "kept@example.com"
        assert user.position == "Admin-only label"
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "user.self_profile_update"))
        assert audit is not None
        assert audit.actor == "self-profile"
        assert audit.after == {"name": "Self Name", "phone": "+56912345678"}

    for field in ("name", "phone"):
        assert client.patch("/panel/api/me", json={field: ""}).status_code == 400
    assert client.patch("/panel/api/me", json={"name": None}).status_code == 200
    assert client.get("/panel/api/me").json()["name"] is None


def test_self_password_change_and_admin_unlock(client, make_user):
    user_id = make_user("password-self", "current-pass", role="tecnico")
    client.post("/panel/api/login", json={"username": "password-self", "password": "current-pass"})
    assert client.post("/panel/api/me/password", json={"current_password": "wrong-pass", "new_password": "new-pass-123"}).status_code == 401
    assert client.post("/panel/api/me/password", json={"current_password": "current-pass", "new_password": "short"}).status_code == 422
    with SessionLocal() as session:
        user = session.get(User, user_id)
        user.failed_logins = 3
        from datetime import datetime, timezone
        user.locked_until = datetime.now(timezone.utc)
        session.commit()
    changed = client.post("/panel/api/me/password", json={"current_password": "current-pass", "new_password": "new-pass-123"})
    assert changed.status_code == 200
    with SessionLocal() as session:
        user = session.get(User, user_id)
        assert user.failed_logins == 0 and user.locked_until is None
        assert verify_password("new-pass-123", user.password_hash)
        assert session.scalar(select(AuditLog).where(AuditLog.action == "user.change_password")) is not None

    client.post("/panel/api/logout")
    admin_id = _admin(client, make_user, "unlock-admin")
    target_id = make_user("unlock-target", "initial-pass")
    with SessionLocal() as session:
        target = session.get(User, target_id)
        target.failed_logins = 4
        target.locked_until = datetime.now(timezone.utc)
        session.commit()
    unlocked = client.post(f"/panel/api/users/{target_id}/unlock")
    assert unlocked.status_code == 200
    assert unlocked.json()["user"]["failed_logins"] == 0
    assert unlocked.json()["user"]["locked_until"] is None
    assert client.post(f"/panel/api/users/{admin_id}/unlock").status_code == 200
    with SessionLocal() as session:
        assert session.scalar(select(AuditLog).where(AuditLog.action == "user.unlock")) is not None


def test_new_user_admin_routes_denied_for_each_non_admin(client, make_user):
    target_id = make_user("matrix-target", "initial-pass")
    routes = (("get", f"/panel/api/users/{target_id}", {}), ("patch", f"/panel/api/users/{target_id}", {"json": {"name": "x"}}), ("post", f"/panel/api/users/{target_id}/unlock", {}))
    for role in ("operador", "tecnico"):
        _login(client, make_user, f"matrix-{role}", "role-pass", role)
        for method, path, kwargs in routes:
            assert getattr(client, method)(path, **kwargs).status_code == 403
        client.post("/panel/api/logout")
