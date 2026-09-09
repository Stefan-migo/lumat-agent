from pathlib import Path

import pytest
from app.db import SessionLocal
from app.config import get_settings
from app.models import User
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
    assert result == [{"type": "document", "filename": "a.txt", "text": "manual: hell", "attachment_id": None}]


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


def test_admin_upload_persists_private_thread_scoped_reference(client, monkeypatch, tmp_path):
    username = "attachment-admin"
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role="admin"))
        session.commit()
    assert client.post("/panel/api/login", json={"username": username, "password": "pass"}).status_code == 200
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    response = client.post(f"/panel/api/chat/threads/{thread_id}/attachments", files={"file": ("notes.txt", b"private notes", "text/plain")})
    assert response.status_code == 201, response.text
    payload = response.json()["attachment"]
    assert payload["filename"] == "notes.txt"
    assert "stored_path" not in payload
    assert list(tmp_path.glob(f"assistant/{thread_id}/*"))
