from app.services.prompts import load_assistant_config


def test_global_skills_catalog_is_authenticated_and_read_only(client, make_user):
    response = client.get("/panel/api/skills")
    assert response.status_code == 401

    make_user("skills-owner", "skills-pass", role="operador")
    client.post("/panel/api/login", json={"username": "skills-owner", "password": "skills-pass"})
    response = client.get("/panel/api/skills")

    assert response.status_code == 200
    skills = response.json()["skills"]
    expected = load_assistant_config().skills
    assert skills == [
        {"name": skill.name, "description": skill.description, "scope": "global"}
        for skill in expected
    ]
    assert skills
    assert client.post("/panel/api/skills", json={}).status_code == 405


def test_global_skills_catalog_returns_empty_list_when_index_is_empty(client, make_user, monkeypatch):
    from app.panel.api.routes import skills

    monkeypatch.setattr(skills, "load_assistant_config", lambda: type("Config", (), {"skills": ()})())
    make_user("skills-empty", "skills-pass", role="operador")
    client.post("/panel/api/login", json={"username": "skills-empty", "password": "skills-pass"})

    assert client.get("/panel/api/skills").json() == {"skills": []}
