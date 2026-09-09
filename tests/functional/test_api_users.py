from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, User


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
    assert all(set(row) == {"id", "username", "role", "active"} for row in users)
    assert all("password_hash" not in row and "failed_logins" not in row and "locked_until" not in row for row in users)


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
