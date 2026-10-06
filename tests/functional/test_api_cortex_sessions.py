"""Authenticated Cortex planning-session API contracts (CS-5, IAC-3)."""

from app.db import SessionLocal
from app.models import InternalChatThread, Memory


def _login(client, make_user, *, username="cortex-admin", role="admin"):
    make_user(username, "cortex-pass", role=role)
    response = client.post("/panel/api/login", json={"username": username, "password": "cortex-pass"})
    assert response.status_code == 200


def test_planning_session_lifecycle_and_auth_matrix(client, make_user):
    assert client.get("/panel/api/planning/sessions").status_code == 401
    make_user("cortex-operator", "cortex-pass", role="operador")
    client.post("/panel/api/login", json={"username": "cortex-operator", "password": "cortex-pass"})
    assert client.get("/panel/api/planning/sessions").status_code == 200

    client.post("/panel/api/logout")
    _login(client, make_user)
    assert client.post("/panel/api/planning/sessions", json={"topic": ""}).status_code == 400
    assert client.post("/panel/api/planning/sessions", json={"topic": "Budget review", "thread_id": 404}).status_code == 404

    opened = client.post("/panel/api/planning/sessions", json={"topic": "Budget review"})
    assert opened.status_code == 201, opened.text
    body = opened.json()
    assert body["session"]["status"] == "active"
    slug = body["session"]["slug"]
    thread_id = body["thread_id"]

    listed = client.get("/panel/api/planning/sessions")
    assert listed.status_code == 200
    assert listed.json()["sessions"][0]["slug"] == slug
    detail = client.get(f"/panel/api/planning/sessions/{slug}")
    assert detail.status_code == 200
    assert detail.json()["thread"]["id"] == thread_id
    assert client.get("/panel/api/planning/sessions/missing").status_code == 404

    closed = client.post(f"/panel/api/planning/sessions/{slug}/close")
    assert closed.status_code == 200, closed.text
    assert closed.json()["session"]["status"] == "closed"
    assert client.post(f"/panel/api/planning/sessions/{slug}/close").status_code == 409
    reopened = client.post(f"/panel/api/planning/sessions/{slug}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["session"]["status"] == "active"
    assert client.post(f"/panel/api/planning/sessions/{slug}/reopen").status_code == 409


def test_planning_unknown_thread_and_forbidden_detail(client, make_user):
    _login(client, make_user)
    assert client.post("/panel/api/planning/sessions", json={"topic": "Review", "thread_id": 9999}).status_code == 404
    assert client.get("/panel/api/planning/sessions/unknown").status_code == 404


def test_tecnico_planning_requires_own_project_namespace(client, make_user):
    _login(client, make_user, username="cortex-tecnico", role="tecnico")
    rejected = client.post("/panel/api/planning/sessions", json={"topic": "Private planning"})
    assert rejected.status_code == 400
    created = client.post("/panel/api/projects", json={
        "slug": "tech-planning", "name": "Technician Planning", "purpose": "Private technician planning namespace",
    })
    assert created.status_code == 201
    opened = client.post("/panel/api/planning/sessions", json={
        "topic": "Private planning", "proyecto": "tech-planning",
    })
    assert opened.status_code == 201, opened.text
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, opened.json()["thread_id"])
        assert thread.proyecto == "tech-planning"


def test_planning_close_writes_one_agent_report_without_handoff_or_approval(client, make_user):
    _login(client, make_user, username="cortex-report")
    opened = client.post("/panel/api/planning/sessions", json={"topic": "Final report"}).json()
    slug, thread_id = opened["session"]["slug"], opened["thread_id"]
    closed = client.post(f"/panel/api/planning/sessions/{slug}/close").json()
    assert set(closed) == {"session", "report"}
    assert closed["session"]["status"] == "closed"
    assert closed["report"]["scope"] == "agent"
    assert closed["report"]["entity_id"] == "agent:default"
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        reports = session.query(Memory).filter_by(topic_key=closed["report"]["topic_key"]).all()
        assert len(reports) == 1
        assert "approval" not in thread.assistant_state
        assert thread.current_plan is None
