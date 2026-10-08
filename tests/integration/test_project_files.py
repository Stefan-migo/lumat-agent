import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from app.db import SessionLocal
from app.models import AuditLog, Project, User
from app.services.project_files import (
    allowed_project_file,
    get_project_file,
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
