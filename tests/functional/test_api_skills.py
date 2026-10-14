from app.services.prompts import load_assistant_config
from app.services.skills import SkillError, global_skill_index, load_skill_body


def test_global_skills_catalog_is_authenticated_and_read_only(client, make_user):
    response = client.get("/panel/api/skills")
    assert response.status_code == 401

    make_user("skills-owner", "skills-pass", role="operador")
    client.post("/panel/api/login", json={"username": "skills-owner", "password": "skills-pass"})
    response = client.get("/panel/api/skills")

    assert response.status_code == 200
    skills = response.json()["skills"]
    expected = global_skill_index(load_assistant_config())
    assert skills == [
        {"name": skill.name, "description": skill.description, "scope": "global", "body": load_skill_body(skill)}
        for skill in expected
    ]
    assert skills
    # The declared markdown body is exposed so the panel can preview it read-only.
    assert isinstance(skills[0]["body"], str) and skills[0]["body"].strip()
    assert client.post("/panel/api/skills", json={}).status_code == 405


def test_global_skills_catalog_returns_empty_list_when_index_is_empty(client, make_user, monkeypatch):
    from app.panel.api.routes import skills

    monkeypatch.setattr(skills, "load_assistant_config", lambda: type("Config", (), {"skills": ()})())
    make_user("skills-empty", "skills-pass", role="operador")
    client.post("/panel/api/login", json={"username": "skills-empty", "password": "skills-pass"})

    assert client.get("/panel/api/skills").json() == {"skills": []}


def test_global_skills_catalog_degrades_when_a_body_is_unavailable(client, make_user, monkeypatch):
    from app.panel.api.routes import skills as skills_route

    def explode(_skill):
        raise SkillError("unreadable")

    monkeypatch.setattr(skills_route, "load_skill_body", explode)
    make_user("skills-degraded", "skills-pass", role="operador")
    client.post("/panel/api/login", json={"username": "skills-degraded", "password": "skills-pass"})

    skills = client.get("/panel/api/skills").json()["skills"]
    assert skills
    assert all(skill["body"] is None for skill in skills)
