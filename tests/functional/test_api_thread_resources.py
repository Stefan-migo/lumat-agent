"""Per-thread pinned project resources API."""

from app.db import SessionLocal
from app.models import InternalChatThread, Project


def _login(client, username, password="res-pass"):
    response = client.post("/panel/api/login", json={"username": username, "password": password})
    assert response.status_code == 200


def _seed(owner_id, *, slug, skill=True):
    with SessionLocal() as session:
        project = Project(
            slug=slug, name=slug, purpose="Resources test", purpose_embedding=[0.0] * 384, owner_id=owner_id,
            config={"skills": [{"name": "local-skill", "description": "Local", "body": "Body"}]} if skill else {},
        )
        session.add(project)
        session.flush()
        thread = InternalChatThread(user_id=owner_id, proyecto=slug)
        session.add(thread)
        session.add(InternalChatThread(
            user_id=owner_id, proyecto=slug,
            assistant_state={"cortex_session": {"slug": "plan-1", "topic": "Tema", "status": "closed"}},
        ))
        session.commit()
        return thread.id


def _upload(client, slug, filename, content=b"hello"):
    response = client.post(f"/panel/api/projects/{slug}/files", files={"file": (filename, content, "text/plain")})
    assert response.status_code == 201, response.text
    return response.json()["file"]


def test_resources_lists_available_and_starts_inherited(client, make_user, monkeypatch, tmp_path):
    from app.config import get_settings
    owner_id = make_user("res-owner", "res-pass")
    thread_id = _seed(owner_id, slug="res-project")
    _login(client, "res-owner")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    file = _upload(client, "res-project", "notes.txt")

    response = client.get(f"/panel/api/chat/threads/{thread_id}/resources")

    assert response.status_code == 200
    body = response.json()
    assert body["inherited"] is True
    assert body["resources"] == {"project_files": [], "skills": []}
    assert [row["id"] for row in body["available"]["project_files"]] == [file["id"]]
    assert [row["name"] for row in body["available"]["skills"]] == ["local-skill"]
    with SessionLocal() as session:
        legacy_thread = session.query(InternalChatThread).filter_by(user_id=owner_id).order_by(InternalChatThread.id.desc()).first()
        assert legacy_thread.assistant_state["cortex_session"]["slug"] == "plan-1"
    get_settings.cache_clear()


def test_put_pins_resources_and_delete_resets(client, make_user, monkeypatch, tmp_path):
    from app.config import get_settings
    owner_id = make_user("res-put-owner", "res-pass")
    thread_id = _seed(owner_id, slug="res-put")
    _login(client, "res-put-owner")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    file = _upload(client, "res-put", "notes.txt")

    response = client.put(
        f"/panel/api/chat/threads/{thread_id}/resources",
        json={"project_files": [file["id"]], "skills": ["local-skill"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["inherited"] is False
    assert body["resources"] == {"project_files": [file["id"]], "skills": ["local-skill"]}
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["resources"]["project_files"] == [file["id"]]

    reset = client.delete(f"/panel/api/chat/threads/{thread_id}/resources")
    assert reset.status_code == 200
    assert reset.json()["inherited"] is True
    with SessionLocal() as session:
        assert "resources" not in session.get(InternalChatThread, thread_id).assistant_state
    get_settings.cache_clear()


def test_put_rejects_unknown_and_foreign_resources(client, make_user, monkeypatch, tmp_path):
    from app.config import get_settings
    owner_id = make_user("res-reject-owner", "res-pass")
    thread_id = _seed(owner_id, slug="res-reject")
    _seed(owner_id, slug="res-other", skill=False)
    _login(client, "res-reject-owner")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    foreign = _upload(client, "res-other", "foreign.txt")

    unknown = client.put(f"/panel/api/chat/threads/{thread_id}/resources", json={"project_files": [999999]})
    assert unknown.status_code == 400
    cross_project = client.put(f"/panel/api/chat/threads/{thread_id}/resources", json={"project_files": [foreign["id"]]})
    assert cross_project.status_code == 400
    unknown_skill = client.put(f"/panel/api/chat/threads/{thread_id}/resources", json={"skills": ["missing"]})
    assert unknown_skill.status_code == 400
    get_settings.cache_clear()


def test_resources_are_hidden_from_other_owners(client, make_user):
    owner_id = make_user("res-private-owner", "res-pass")
    make_user("res-other-owner", "res-pass")
    thread_id = _seed(owner_id, slug="res-private")
    _login(client, "res-other-owner")

    url = f"/panel/api/chat/threads/{thread_id}/resources"
    assert client.get(url).status_code == 404
    assert client.put(url, json={"project_files": []}).status_code == 404
    assert client.delete(url).status_code == 404


def test_resources_writes_conflict_while_run_is_active(client, make_user):
    owner_id = make_user("res-running-owner", "res-pass")
    with SessionLocal() as session:
        project = Project(slug="res-running", name="res-running", purpose="p", purpose_embedding=[0.0] * 384, owner_id=owner_id)
        session.add(project)
        session.flush()
        thread = InternalChatThread(user_id=owner_id, proyecto="res-running", assistant_state={"live": {"status": "running"}})
        session.add(thread)
        session.commit()
        thread_id = thread.id
    _login(client, "res-running-owner")

    assert client.get(f"/panel/api/chat/threads/{thread_id}/resources").status_code == 200
    assert client.put(f"/panel/api/chat/threads/{thread_id}/resources", json={"project_files": []}).status_code == 409
    assert client.delete(f"/panel/api/chat/threads/{thread_id}/resources").status_code == 409
