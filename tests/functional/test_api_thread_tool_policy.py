"""Owner-scoped per-thread assistant tool policy API."""

from app.db import SessionLocal
from app.models import InternalChatThread, Project


def _login(client, username, password="policy-pass"):
    response = client.post("/panel/api/login", json={"username": username, "password": password})
    assert response.status_code == 200


def _seed_thread(owner_id, *, slug="policy-project", policy=None, state=None):
    with SessionLocal() as session:
        project = Project(
            slug=slug, name="Policy Project", purpose="Thread tool policy test",
            purpose_embedding=[0.0] * 384, owner_id=owner_id,
            config={"tool_policy": {"opt_in_enabled": policy or []}},
        )
        session.add(project)
        session.flush()
        thread = InternalChatThread(user_id=owner_id, proyecto=slug, assistant_state=state or {})
        session.add(thread)
        session.commit()
        return thread.id


def test_get_inherits_project_policy_and_lists_available_opt_in_tools(client, make_user):
    owner = make_user("policy-get-owner", "policy-pass")
    thread_id = _seed_thread(owner, policy=["web.fetch"])
    _login(client, "policy-get-owner")

    response = client.get(f"/panel/api/chat/threads/{thread_id}/tool-policy")

    assert response.status_code == 200
    body = response.json()
    assert body["inherited"] is True
    assert body["opt_in_enabled"] == ["web.fetch"]
    assert {"web.search", "web.fetch", "project.create"} <= set(body["available"])
    assert "automation.create_rule" not in body["available"]


def test_put_sets_policy_and_preserves_sibling_state(client, make_user):
    owner = make_user("policy-put-owner", "policy-pass")
    thread_id = _seed_thread(owner, state={"live": {"status": "completed"}, "approval": {"status": "none"}})
    _login(client, "policy-put-owner")

    response = client.put(
        f"/panel/api/chat/threads/{thread_id}/tool-policy",
        json={"opt_in_enabled": ["web.fetch"]},
    )

    assert response.status_code == 200
    assert response.json()["inherited"] is False
    assert response.json()["opt_in_enabled"] == ["web.fetch"]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["tool_policy"] == {"opt_in_enabled": ["web.fetch"]}
        assert thread.assistant_state["live"] == {"status": "completed"}
        assert thread.assistant_state["approval"] == {"status": "none"}


def test_put_rejects_unknown_tool(client, make_user):
    owner = make_user("policy-unknown-owner", "policy-pass")
    thread_id = _seed_thread(owner)
    _login(client, "policy-unknown-owner")

    response = client.put(f"/panel/api/chat/threads/{thread_id}/tool-policy", json={"opt_in_enabled": ["missing.tool"]})

    assert response.status_code == 400


def test_put_rejects_tool_outside_owner_role_allowlist(client, make_user):
    owner = make_user("policy-role-owner", "policy-pass", role="operador")
    thread_id = _seed_thread(owner)
    _login(client, "policy-role-owner")

    response = client.put(
        f"/panel/api/chat/threads/{thread_id}/tool-policy",
        json={"opt_in_enabled": ["automation.create_rule"]},
    )

    assert response.status_code == 400


def test_policy_writes_conflict_while_run_is_active(client, make_user):
    owner = make_user("policy-running-owner", "policy-pass")
    thread_id = _seed_thread(owner, state={"live": {"status": "running"}})
    _login(client, "policy-running-owner")

    # Reads stay available so the UI can render the current selection; only writes are locked.
    assert client.get(f"/panel/api/chat/threads/{thread_id}/tool-policy").status_code == 200
    assert client.put(
        f"/panel/api/chat/threads/{thread_id}/tool-policy", json={"opt_in_enabled": ["web.fetch"]}
    ).status_code == 409
    assert client.delete(f"/panel/api/chat/threads/{thread_id}/tool-policy").status_code == 409


def test_delete_resets_override_to_project_policy(client, make_user):
    owner = make_user("policy-delete-owner", "policy-pass")
    thread_id = _seed_thread(owner, policy=["web.fetch"], state={"tool_policy": {"opt_in_enabled": ["web.search"]}})
    _login(client, "policy-delete-owner")

    response = client.delete(f"/panel/api/chat/threads/{thread_id}/tool-policy")

    assert response.status_code == 200
    assert response.json()["inherited"] is True
    assert response.json()["opt_in_enabled"] == ["web.fetch"]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert "tool_policy" not in thread.assistant_state


def test_tool_policy_is_hidden_from_other_owners(client, make_user):
    owner = make_user("policy-private-owner", "policy-pass")
    make_user("policy-other-owner", "policy-pass")
    thread_id = _seed_thread(owner)
    _login(client, "policy-other-owner")

    url = f"/panel/api/chat/threads/{thread_id}/tool-policy"
    assert client.get(url).status_code == 404
    assert client.put(url, json={"opt_in_enabled": []}).status_code == 404
    assert client.delete(url).status_code == 404


def test_put_policy_is_effective_for_next_turn(client, make_user):
    owner = make_user("policy-effective-owner", "policy-pass")
    thread_id = _seed_thread(owner)
    _login(client, "policy-effective-owner")

    response = client.put(
        f"/panel/api/chat/threads/{thread_id}/tool-policy", json={"opt_in_enabled": ["web.fetch"]}
    )

    assert response.status_code == 200
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        from app.models import UserRole
        from app.services.project_config import resolve_effective_config

        effective = resolve_effective_config(session, thread, UserRole.OPERADOR)
    assert "web.fetch" in effective.tools_whitelist
    assert "web.search" not in effective.tools_whitelist
