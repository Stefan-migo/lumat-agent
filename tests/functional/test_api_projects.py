"""Read-only operator project browse contract (PNL-APP-27)."""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Memory, MemoryType, Project


def _login(client, make_user, *, role="operador"):
    make_user("projects-operator", "projects-pass", role=role)
    response = client.post("/panel/api/login", json={"username": "projects-operator", "password": "projects-pass"})
    assert response.status_code == 200


def _seed_project():
    with SessionLocal() as session:
        project = session.scalar(select(Project).where(Project.slug == "browse-contract"))
        if project is None:
            project = Project(slug="browse-contract", name="Browse Contract", purpose="Read-only browse", purpose_embedding=[0.0] * 384)
            session.add(project)
            session.flush()
        session.add_all([
            Memory(proyecto=project.slug, scope="panel", entity_id="thread:11", topic_key="sdb:run-1:spec", tipo=MemoryType.PATTERN, titulo="SDB specification", contenido='{"step":1}', embedding=[0.0] * 384),
            Memory(proyecto=project.slug, scope="panel", entity_id="thread:11", topic_key="assistant-recap:11:1", tipo=MemoryType.SUMMARY, titulo="WhatsApp recap", contenido="must not appear", embedding=[0.0] * 384),
            Memory(proyecto=project.slug, scope="panel", entity_id="project:browse-contract", topic_key="sdb:project:decision", tipo=MemoryType.DECISION, titulo="Decision", contenido='{"ok":true}', embedding=[0.0] * 384),
        ])
        session.commit()
        return project.slug


def test_projects_list_and_detail_are_operator_only_and_sdb_only(client, make_user):
    slug = _seed_project()
    assert client.get("/panel/api/projects").status_code == 401
    _login(client, make_user)

    listing = client.get("/panel/api/projects")
    assert listing.status_code == 200
    assert any(item["slug"] == slug and item["name"] == "Browse Contract" for item in listing.json()["projects"])

    detail = client.get(f"/panel/api/projects/{slug}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["project"]["slug"] == slug
    assert set(body["artifacts"]) == {"thread:11", "project:browse-contract"}
    assert all(item["topic_key"].startswith("sdb:") for rows in body["artifacts"].values() for item in rows)
    assert "must not appear" not in str(body)


def test_projects_detail_missing_and_crud_routes_absent(client, make_user):
    _login(client, make_user)
    assert client.get("/panel/api/projects/does-not-exist").status_code == 404
    for method, kwargs in ((client.post, {"json": {}}), (client.patch, {"json": {}}), (client.delete, {})):
        response = method("/panel/api/projects/browse-contract", **kwargs)
        assert response.status_code == 405


def test_projects_browse_allows_operator_but_not_tecnico(client, make_user):
    make_user("projects-tech", "projects-pass", role="tecnico")
    response = client.post("/panel/api/login", json={"username": "projects-tech", "password": "projects-pass"})
    assert response.status_code == 200
    assert client.get("/panel/api/projects").status_code == 403
