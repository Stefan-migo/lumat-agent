from pathlib import Path

import pytest
import httpx
import respx
from app.db import SessionLocal
from app.config import get_settings
from app.models import AssistantAttachment, AuditLog, InternalChatThread, User
from app.services.users import hash_password

from app.chat.assistant.attachments import (
    MAX_ATTACHMENTS_PER_THREAD,
    MAX_FILE_SIZE,
    allowed_attachment,
    build_multimodal_content,
    cleanup_attachments,
    prepare_attachment_context,
)


def test_allowed_attachment_accepts_supported_document_and_rejects_mismatch():
    assert allowed_attachment("manual.PDF", "application/pdf", 120) == "pdf"
    assert allowed_attachment("data.csv", "text/csv", 120) == "csv"
    with pytest.raises(ValueError, match="unsupported"):
        allowed_attachment("manual.pdf", "text/plain", 120)


def test_attachment_limits_cover_size_and_count():
    with pytest.raises(ValueError, match="size"):
        allowed_attachment("photo.png", "image/png", MAX_FILE_SIZE + 1)
    assert MAX_ATTACHMENTS_PER_THREAD == 10


def test_document_context_uses_extracted_text_and_is_bounded(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.chat.assistant.attachments.extract_text",
        lambda content, fmt: "manual: " + content.decode(),
    )
    source = tmp_path / "a.txt"
    source.write_bytes(b"hello")
    attachment = type("Attachment", (), {"kind": "txt", "stored_path": str(source), "filename": "a.txt"})()
    result = prepare_attachment_context([attachment], max_chars=12)
    assert result == [{"type": "document", "filename": "a.txt", "kind": "txt", "text": "manual: hell", "attachment_id": None}]


def test_limits_are_read_from_settings(monkeypatch):
    monkeypatch.setenv("ASSISTANT_ATTACHMENT_MAX_BYTES", "3")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="size"):
        allowed_attachment("a.txt", "text/plain", 4)
    monkeypatch.setenv("ASSISTANT_ATTACHMENT_MAX_BYTES", "5242880")
    get_settings.cache_clear()


def test_document_context_preserves_source_identity_in_prompt(tmp_path):
    source = tmp_path / "manual.txt"
    source.write_bytes(b"source text")
    attachment = type("Attachment", (), {"kind": "txt", "stored_path": str(source), "filename": "manual.txt", "id": 42})()
    result = prepare_attachment_context([attachment], max_chars=100)
    assert result[0]["filename"] == "manual.txt"
    assert result[0]["attachment_id"] == 42
    assert result[0]["kind"] == "txt"


def test_images_are_openai_parts_and_oversized_images_are_rejected(tmp_path):
    image = tmp_path / "photo.png"
    image.write_bytes(b"png")
    attachment = type("Attachment", (), {"kind": "image", "stored_path": str(image), "filename": "photo.png", "id": 7})()
    parts = build_multimodal_content([attachment], "Describe this")
    assert parts[0] == {"type": "text", "text": "Describe this"}
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_cleanup_removes_only_orphaned_assistant_files(tmp_path):
    orphan = tmp_path / "orphan"
    active = tmp_path / "active"
    orphan.write_bytes(b"x")
    active.write_bytes(b"x")
    rows = [
        type("Attachment", (), {"stored_path": str(orphan), "thread_id": 1, "deleted_at": None})(),
        type("Attachment", (), {"stored_path": str(active), "thread_id": 2, "deleted_at": None})(),
    ]
    assert cleanup_attachments(rows, active_thread_ids={2}) == 1
    assert not orphan.exists()
    assert active.exists()


def test_cleanup_removes_expired_attachment_even_on_active_thread(tmp_path):
    expired = tmp_path / "expired"
    expired.write_bytes(b"x")
    row = type("Attachment", (), {"stored_path": str(expired), "thread_id": 2, "deleted_at": None})()
    assert cleanup_attachments([row], active_thread_ids={2}, expired=True) == 1
    assert not expired.exists()


def test_admin_upload_persists_private_thread_scoped_reference(client, monkeypatch, tmp_path):
    username = "attachment-admin"
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role="admin"))
        session.commit()
    assert client.post("/panel/api/login", json={"username": username, "password": "pass"}).status_code == 200
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    response = client.post(f"/panel/api/chat/threads/{thread_id}/attachments", files={"file": ("notes.txt", b"private notes", "text/plain")})
    assert response.status_code == 201, response.text
    payload = response.json()["attachment"]
    assert payload["filename"] == "notes.txt"
    assert "stored_path" not in payload
    assert list(tmp_path.glob(f"assistant/{thread_id}/*"))


def test_upload_rejection_paths_return_errors_without_success_audit(client, monkeypatch):
    username = "attachment-rejections"
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role="admin"))
        session.commit()
    assert client.post("/panel/api/login", json={"username": username, "password": "pass"}).status_code == 200
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    with SessionLocal() as session:
        before = session.query(AuditLog).filter(AuditLog.action == "internal_chat.attachment_uploaded").count()
    bad = client.post(f"/panel/api/chat/threads/{thread_id}/attachments", files={"file": ("x.exe", b"x", "application/octet-stream")})
    assert bad.status_code == 400
    monkeypatch.setenv("ASSISTANT_ATTACHMENT_MAX_BYTES", "2")
    get_settings.cache_clear()
    oversized = client.post(f"/panel/api/chat/threads/{thread_id}/attachments", files={"file": ("x.txt", b"large", "text/plain")})
    assert oversized.status_code == 400
    with SessionLocal() as session:
        assert session.query(AuditLog).filter(AuditLog.action == "internal_chat.attachment_uploaded").count() == before
    get_settings.cache_clear()


def test_cross_thread_attachment_upload_is_denied(client):
    first, second = "attachment-owner-a", "attachment-owner-b"
    with SessionLocal() as session:
        session.add_all([User(username=first, password_hash=hash_password("pass"), role="admin"), User(username=second, password_hash=hash_password("pass"), role="admin")])
        session.commit()
    assert client.post("/panel/api/login", json={"username": first, "password": "pass"}).status_code == 200
    own = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    client.post("/panel/api/logout")
    assert client.post("/panel/api/login", json={"username": second, "password": "pass"}).status_code == 200
    denied = client.post(f"/panel/api/chat/threads/{own}/attachments", files={"file": ("x.txt", b"x", "text/plain")})
    assert denied.status_code == 404


def test_expired_cleanup_deletes_metadata_for_active_thread(tmp_path):
    from datetime import datetime, timedelta, timezone
    from app.chat.assistant.attachments import cleanup_expired
    path = tmp_path / "expired"
    path.write_bytes(b"x")
    with SessionLocal() as session:
        user = User(username="cleanup-owner", password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
        thread = InternalChatThread(user_id=user.id)
        session.add(thread)
        session.flush()
        row = AssistantAttachment(thread_id=thread.id, filename="x.txt", kind="txt", content_type="text/plain", size=1, sha256="x", stored_path=str(path), created_at=datetime.now(timezone.utc) - timedelta(days=40))
        session.add(row)
        session.flush()
        assert cleanup_expired(session, datetime.now(timezone.utc) - timedelta(days=30), {thread.id}) == 1
        session.commit()
        assert session.get(AssistantAttachment, row.id) is None
    assert not path.exists()


def test_multimodal_invocation_uses_openrouter_image_part_and_audits(tmp_path, monkeypatch):
    image = tmp_path / "photo.png"
    image.write_bytes(b"png")
    attachment = type("Attachment", (), {"kind": "image", "stored_path": str(image), "filename": "photo.png", "id": 77})()
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    get_settings.cache_clear()
    with respx.mock(base_url="https://openrouter.ai/api/v1") as router:
        route = router.post("/chat/completions").mock(
            return_value=httpx.Response(200, headers={"content-type": "text/event-stream"}, content='data: {"choices":[{"delta":{"content":"Seen"}}]}\n\ndata: [DONE]\n\n'))
        from app.chat.assistant.nodes import execute
        with SessionLocal() as session:
            result = execute({"thread_id": 9, "run_id": "run-image", "content": "Describe", "plan": {"tool": None, "arguments": {}, "requires_approval": False}, "attachments": [attachment], "on_token": lambda token: None, "session": session, "actor": "attachment-admin"})
            session.flush()
            actions = {row.action for row in session.query(AuditLog).filter(AuditLog.entity_id == "9").all()}
            session.rollback()
        assert result["status"] == "completed"
        assert "internal_chat.attachments_used" in actions
        assert route.called
        request = route.calls[0].request
        body = __import__("json").loads(request.content)
        assert body["model"] == "google/gemini-2.5-flash"
        assert body["messages"][1]["content"][1]["type"] == "image_url"
    get_settings.cache_clear()
