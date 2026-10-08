"""Durable project-scoped file storage."""

import hashlib
import mimetypes
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Project, ProjectFile, User
from app.services.audit import record_audit

_DOCUMENTS = {
    ".pdf": ("pdf", "application/pdf"),
    ".csv": ("csv", "text/csv"),
    ".txt": ("txt", "text/plain"),
    ".md": ("md", {"text/markdown", "text/plain"}),
    ".docx": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ".xlsx": ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
}
_IMAGES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}


def allowed_project_file(filename: str, content_type: str | None, size: int) -> str:
    settings = get_settings()
    if size > settings.project_file_max_bytes:
        raise ValueError("file size exceeds the configured limit")
    suffix = Path(filename).suffix.lower()
    mime = (content_type or mimetypes.guess_type(filename)[0] or "").split(";", 1)[0].lower()
    if suffix in _DOCUMENTS:
        kind, expected = _DOCUMENTS[suffix]
        if mime in (expected if isinstance(expected, set) else {expected}) and kind in settings.project_file_allowed_types:
            return kind
    if suffix in _IMAGES and mime == _IMAGES[suffix] and "image" in settings.project_file_allowed_types:
        return "image"
    raise ValueError("unsupported file type")


def project_file_path(project_id: int, opaque_id: str | None = None) -> Path:
    return Path(get_settings().media_dir) / "projects" / str(project_id) / (opaque_id or uuid4().hex)


def store_project_file(session: Session, project: Project, owner: User, filename: str, content_type: str | None, content: bytes) -> ProjectFile:
    kind = allowed_project_file(filename, content_type, len(content))
    destination = project_file_path(project.id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    row = ProjectFile(
        project_id=project.id, owner_id=owner.id, filename=filename,
        content_type=content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        size=len(content), sha256=hashlib.sha256(content).hexdigest(), stored_path=str(destination), status="ready",
    )
    session.add(row)
    session.flush()
    record_audit(session, actor=owner.username, action="project_file.uploaded", entity="project_file",
                 entity_id=str(row.id), after={"project_id": project.id, "filename": filename, "size": len(content)})
    session.flush()
    return row


def list_project_files(session: Session, project_id: int) -> list[ProjectFile]:
    return list(session.scalars(select(ProjectFile).where(ProjectFile.project_id == project_id).order_by(ProjectFile.created_at.desc())))


def get_project_file(session: Session, project_id: int, file_id: int) -> ProjectFile | None:
    return session.scalar(select(ProjectFile).where(ProjectFile.project_id == project_id, ProjectFile.id == file_id))
