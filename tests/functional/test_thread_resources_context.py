"""Pinned project files and skills surface as compact turn-context references."""

from app.chat.assistant import nodes
from app.db import SessionLocal
from app.models import InternalChatThread, Project
from app.services.thread_resources import ThreadResources, set_thread_resources


def _login(client, username, password="res-pass"):
    response = client.post("/panel/api/login", json={"username": username, "password": password})
    assert response.status_code == 200


def _seed(owner_id, *, slug):
    with SessionLocal() as session:
        project = Project(
            slug=slug, name=slug, purpose="Context test", purpose_embedding=[0.0] * 384,
            owner_id=owner_id,
            config={"skills": [{"name": "local-skill", "description": "Local", "body": "BODY-MARKER"}]},
        )
        session.add(project)
        session.flush()
        thread = InternalChatThread(user_id=owner_id, proyecto=slug)
        session.add(thread)
        session.add(InternalChatThread(
            user_id=owner_id, proyecto=slug,
        ))
        session.commit()
        return thread.id


def _upload(client, slug, filename, content=b"HELLO-CONTENT"):
    response = client.post(f"/panel/api/projects/{slug}/files", files={"file": (filename, content, "text/plain")})
    assert response.status_code == 201, response.text
    return response.json()["file"]


def _pinned_thread(client, make_user, monkeypatch, tmp_path, username, slug):
    from app.config import get_settings

    owner_id = make_user(username, "res-pass", role="admin")
    thread_id = _seed(owner_id, slug=slug)
    _login(client, username)
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    file = _upload(client, slug, "notes.txt")
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        set_thread_resources(
            session,
            thread,
            ThreadResources(project_files=[file["id"]], skills=["local-skill"]),
        )
        session.commit()
    get_settings.cache_clear()
    return thread_id


def test_assemble_context_surfaces_a_compact_pinned_reference(client, make_user, monkeypatch, tmp_path):
    thread_id = _pinned_thread(client, make_user, monkeypatch, tmp_path, "ctx-owner", "ctx-project")

    with SessionLocal() as session:
        assembled = nodes.assemble_context_node({
            "session": session, "thread_id": thread_id, "actor_role": "admin", "content": "hola",
        })

    pinned = [item for item in assembled["context"]["items"] if item.get("source") == "pinned_resources"]
    assert len(pinned) == 1
    reference = pinned[0]["content"]
    assert reference.startswith("<pinned_resources>")
    assert "notes.txt" in reference
    assert "plan-1" not in reference
    assert "local-skill" in reference
    assert "HELLO-CONTENT" not in reference
    assert "BODY-MARKER" not in reference
    assert assembled["effective"]["pinned_skills"] == ["local-skill"]


def test_no_pinned_reference_when_nothing_is_pinned(client, make_user, monkeypatch, tmp_path):
    from app.config import get_settings

    owner_id = make_user("ctx-none", "res-pass", role="admin")
    thread_id = _seed(owner_id, slug="ctx-none")
    get_settings.cache_clear()

    with SessionLocal() as session:
        assembled = nodes.assemble_context_node({
            "session": session, "thread_id": thread_id, "actor_role": "admin", "content": "hola",
        })

    assert not [item for item in assembled["context"]["items"] if item.get("source") == "pinned_resources"]
    assert assembled["effective"]["pinned_skills"] == []


def test_pinned_skills_are_declared_for_the_responder():
    effective = {
        "project_id": None,
        "instructions": "",
        "tools_whitelist": [],
        "skills_index": [
            {"name": "local-skill", "description": "Local", "scope": "project", "path": None, "body": "BODY-MARKER"},
        ],
        "pinned_skills": ["local-skill"],
    }
    state = {"effective": effective, "plan": {"kind": "respond"}, "content": "hola"}

    guarded = nodes.guardrails(state)

    assert "local-skill" in guarded["guardrails"]["skills"]
    skill_context = nodes._skill_context({**state, **guarded})
    assert "local-skill" in skill_context
    assert "BODY-MARKER" in skill_context
