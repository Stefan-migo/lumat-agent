"""Owner-scoped project browse and creation contract (PNL-APP-27)."""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Memory, MemoryType, Project


def _login(client, make_user, *, role="operador", username="projects-operator", create=True):
    if create:
        make_user(username, "projects-pass", role=role)
    response = client.post("/panel/api/login", json={"username": username, "password": "projects-pass"})
    assert response.status_code == 200


def _seed_project(owner_id=None, slug="browse-contract"):
    with SessionLocal() as session:
        project = Project(slug=slug, name="Browse Contract", purpose=f"Read-only browse {owner_id} {slug}", purpose_embedding=[0.0] * 384, owner_id=owner_id)
        session.add(project)
        session.flush()
        session.add_all([
            Memory(proyecto=project.slug, owner_id=owner_id, scope="panel", entity_id="thread:11", topic_key="sdb:run-1:spec", tipo=MemoryType.PATTERN, titulo="SDB specification", contenido='{"step":1}', embedding=[0.0] * 384),
            Memory(proyecto=project.slug, owner_id=owner_id, scope="panel", entity_id="thread:11", topic_key=f"assistant-recap:11:1:{owner_id}", tipo=MemoryType.SUMMARY, titulo="WhatsApp recap", contenido="must not appear", embedding=[0.0] * 384),
            Memory(proyecto=project.slug, owner_id=owner_id, scope="panel", entity_id="project:browse-contract", topic_key="sdb:project:decision", tipo=MemoryType.DECISION, titulo="Decision", contenido='{"ok":true}', embedding=[0.0] * 384),
        ])
        session.commit()
        return project.slug


def test_projects_list_and_detail_are_operator_only_and_sdb_only(client, make_user):
    user_id = make_user("projects-operator", "projects-pass")
    slug = _seed_project(user_id)
    assert client.get("/panel/api/projects").status_code == 401
    client.post("/panel/api/login", json={"username": "projects-operator", "password": "projects-pass"})

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


def test_projects_detail_missing_and_mutation_routes(client, make_user):
    _login(client, make_user)
    assert client.get("/panel/api/projects/does-not-exist").status_code == 404
    response = client.post("/panel/api/projects", json={})
    assert response.status_code == 422
    for method, kwargs in ((client.patch, {"json": {}}), (client.delete, {})):
        response = method("/panel/api/projects/browse-contract", **kwargs)
        assert response.status_code == 405


def test_projects_browse_allows_operator_but_not_tecnico(client, make_user):
    make_user("projects-tech", "projects-pass", role="tecnico")
    response = client.post("/panel/api/login", json={"username": "projects-tech", "password": "projects-pass"})
    assert response.status_code == 200
    assert client.get("/panel/api/projects").status_code == 403


def test_project_reads_are_scoped_and_admin_has_no_override(client, make_user):
    owner_a = make_user("owner-a", "projects-pass")
    owner_b = make_user("owner-b", "projects-pass")
    _seed_project(owner_a, "shared")
    _seed_project(owner_b, "shared")
    _login(client, make_user, username="owner-a", create=False)
    assert [p["slug"] for p in client.get("/panel/api/projects").json()["projects"]] == ["shared"]
    detail = client.get("/panel/api/projects/shared")
    assert detail.status_code == 200
    assert all("must not appear" not in str(row) for rows in detail.json()["artifacts"].values() for row in rows)
    client.post("/panel/api/logout")
    _login(client, make_user, role="admin", username="owner-admin")
    assert client.get("/panel/api/projects").json()["projects"] == []
    assert client.get("/panel/api/projects/shared").status_code == 404


def test_project_creation_is_owned_and_ambiguous_purpose_conflicts(client, make_user):
    owner = make_user("creator", "projects-pass")
    _login(client, make_user, username="creator", create=False)
    first = client.post("/panel/api/projects", json={"slug": "created", "name": "Created", "purpose": "A unique project purpose"})
    assert first.status_code == 201
    with SessionLocal() as session:
        row = session.scalar(select(Project).where(Project.slug == "created"))
        assert row.owner_id == owner
    assert [p["slug"] for p in client.get("/panel/api/projects").json()["projects"]] == ["created"]
    duplicate = client.post("/panel/api/projects", json={"slug": "other", "name": "Other", "purpose": "A unique project purpose"})
    assert duplicate.status_code == 409
    assert duplicate.json()["candidates"][0]["slug"] == "created"
    with SessionLocal() as session:
        assert session.scalar(select(Project).where(Project.slug == "other")) is None
    assert client.post("/panel/api/projects", json={"slug": "x" * 101, "name": "X", "purpose": "valid"}).status_code == 422


def test_project_creation_rejects_a_duplicate_slug(client, make_user):
    make_user("slug-owner", "projects-pass")
    _login(client, make_user, username="slug-owner", create=False)
    first = client.post(
        "/panel/api/projects",
        json={"slug": "invoice-hub", "name": "Invoice Hub", "purpose": "Invoice reconciliation workflow"},
    )
    assert first.status_code == 201
    again = client.post(
        "/panel/api/projects",
        json={"slug": "Invoice Hub", "name": "Invoice Hub Copy", "purpose": "Espresso machine maintenance log"},
    )
    assert again.status_code == 409
    with SessionLocal() as session:
        rows = session.scalars(select(Project).where(Project.slug == "invoice-hub")).all()
        assert [row.name for row in rows] == ["Invoice Hub"]
