import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, KbChunk, KbDocument, KbVisibility, Project, ProjectFile, User
from app.services.project_files import (
    allowed_project_file,
    get_project_file,
    ingest_project_file,
    list_project_files,
    store_project_file,
)
from app.services.users import hash_password


def _seed_project(session, slug):
    owner = User(username=f"owner-{slug}", password_hash=hash_password("pass"), role="operador")
    session.add(owner)
    session.flush()
    project = Project(slug=slug, name=slug, purpose=f"Purpose {slug}", purpose_embedding=[0.0] * 384, owner_id=owner.id)
    session.add(project)
    session.flush()
    return owner, project


def test_allowed_project_file_rejects_oversize(monkeypatch):
    monkeypatch.setenv("PROJECT_FILE_MAX_BYTES", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="file size exceeds the configured limit"):
        allowed_project_file("notes.txt", "text/plain", 3)
    get_settings.cache_clear()


def test_allowed_project_file_rejects_unsupported_type():
    with pytest.raises(ValueError, match="unsupported file type"):
        allowed_project_file("program.exe", "application/octet-stream", 1)


def test_store_project_file_persists_bytes_metadata_and_audit(monkeypatch, tmp_path):
    from app.config import get_settings
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    content = b"project notes"
    with SessionLocal() as session:
        owner, project = _seed_project(session, "files-store")
        row = store_project_file(session, project, owner, "notes.txt", "text/plain", content)
        session.flush()
        assert row.size == len(content)
        assert row.sha256 == hashlib.sha256(content).hexdigest()
        assert row.status == "ready"
        assert row.project_id == project.id
        assert open(row.stored_path, "rb").read() == content
        audit = session.query(AuditLog).filter_by(action="project_file.uploaded", entity_id=str(row.id)).one()
        assert audit.actor == owner.username
        assert audit.after == {"project_id": project.id, "filename": "notes.txt", "size": len(content)}
        session.rollback()
    get_settings.cache_clear()


def test_list_orders_newest_first_and_get_scopes_project(monkeypatch, tmp_path):
    from app.config import get_settings
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    with SessionLocal() as session:
        owner, project = _seed_project(session, "files-list")
        other_owner, other_project = _seed_project(session, "files-other")
        first = store_project_file(session, project, owner, "first.txt", "text/plain", b"1")
        second = store_project_file(session, project, owner, "second.txt", "text/plain", b"2")
        second.created_at = datetime.now(timezone.utc) + timedelta(seconds=1)
        other = store_project_file(session, other_project, other_owner, "other.txt", "text/plain", b"3")
        session.flush()
        rows = list_project_files(session, project.id)
        assert [row.id for row in rows] == [second.id, first.id]
        assert get_project_file(session, project.id, first.id).id == first.id
        assert get_project_file(session, project.id, other.id) is None
        session.rollback()
    get_settings.cache_clear()


def test_ingest_project_text_file_creates_project_scoped_internal_kb_document(fake_embedder, tmp_path):
    from app.config import get_settings
    get_settings.cache_clear()
    with SessionLocal() as session:
        owner, project = _seed_project(session, "files-ingest-text")
        content = ("Project-specific operational notes and safety instructions. " * 20).encode()
        row = store_project_file(session, project, owner, "notes.txt", "text/plain", content)
        doc = ingest_project_file(session, project, row, content, owner.username)
        session.commit()

        assert doc is not None
        assert doc.project_id == project.id
        assert doc.visibility == KbVisibility.INTERNAL
        assert doc.content == content.decode()
        assert row.kb_document_id == doc.id
        chunks = list(session.scalars(select(KbChunk).where(KbChunk.document_id == doc.id)))
        assert chunks
        assert all(chunk.content for chunk in chunks)
    get_settings.cache_clear()


def test_ingest_project_image_skips_kb_and_keeps_ready_status(tmp_path):
    from app.config import get_settings
    get_settings.cache_clear()
    with SessionLocal() as session:
        owner, project = _seed_project(session, "files-ingest-image")
        content = b"image bytes"
        row = store_project_file(session, project, owner, "photo.png", "image/png", content)
        assert ingest_project_file(session, project, row, content, owner.username) is None
        assert row.status == "ready"
        assert row.kb_document_id is None
        assert session.scalar(select(KbDocument).where(KbDocument.project_id == project.id)) is None
        session.rollback()
    get_settings.cache_clear()


def test_ingest_corrupt_docx_marks_failed_and_keeps_stored_file(tmp_path):
    from app.config import get_settings
    get_settings.cache_clear()
    with SessionLocal() as session:
        owner, project = _seed_project(session, "files-ingest-corrupt-docx")
        content = b"not a valid docx"
        row = store_project_file(
            session, project, owner,
            "broken.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content,
        )
        assert ingest_project_file(session, project, row, content, owner.username) is None
        assert row.status == "failed"
        assert row.kb_document_id is None
        assert Path(row.stored_path).read_bytes() == content
        assert session.get(ProjectFile, row.id) is row
        session.rollback()
    get_settings.cache_clear()
