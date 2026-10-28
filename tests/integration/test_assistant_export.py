from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, User
from app.services.users import hash_password


def _login(client, username: str) -> None:
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role="admin"))
        session.commit()
    response = client.post("/panel/api/login", json={"username": username, "password": "pass"})
    assert response.status_code == 200


def test_export_thread_includes_all_messages_and_attachment_headers(client):
    _login(client, "assistant-export-owner")
    thread_response = client.post("/panel/api/chat/threads", json={"proyecto": "default"})
    assert thread_response.status_code == 201
    thread_id = thread_response.json()["thread"]["id"]
    start = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        thread.title = "Plan / resumen"
        session.add_all([
            InternalChatMessage(
                thread_id=thread_id,
                author="admin" if index % 2 == 0 else "agent",
                content=f"Mensaje completo {index + 1}",
                status="processed",
                created_at=start + timedelta(minutes=index),
            )
            for index in range(12)
        ])
        session.commit()

    response = client.get(f"/panel/api/chat/threads/{thread_id}/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"] == f'attachment; filename="Plan-resumen.md"'
    body = response.text
    for index in range(12):
        assert f"Mensaje completo {index + 1}" in body
    assert "admin" in body
    assert "agent" in body
    assert "2026-11-01T12:00:00" in body
    assert "2026-11-01T12:11:00" in body


def test_export_thread_is_owner_scoped(client):
    _login(client, "assistant-export-other-owner")
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]

    _login(client, "assistant-export-outsider")

    response = client.get(f"/panel/api/chat/threads/{thread_id}/export")

    assert response.status_code == 404


def test_export_unknown_thread_is_not_found(client):
    _login(client, "assistant-export-unknown")

    assert client.get("/panel/api/chat/threads/999999/export").status_code == 404
