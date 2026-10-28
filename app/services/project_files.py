"""Durable project-scoped file storage."""

import hashlib
import mimetypes
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import KbDocument, Project, ProjectFile, ProjectFolder, User
from app.services.audit import record_audit
from app.services.document_extract import extract_document_text

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


def store_project_file(session: Session, project: Project, owner: User, filename: str, content_type: str | None, content: bytes, folder_id: int | None = None) -> ProjectFile:
    kind = allowed_project_file(filename, content_type, len(content))
    destination = project_file_path(project.id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    row = ProjectFile(
        project_id=project.id, owner_id=owner.id, filename=filename,
        content_type=content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        size=len(content), sha256=hashlib.sha256(content).hexdigest(), stored_path=str(destination), status="ready",
        folder_id=folder_id,
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


def list_project_folders(session: Session, project_id: int) -> list[ProjectFolder]:
    return list(session.scalars(select(ProjectFolder).where(ProjectFolder.project_id == project_id).order_by(ProjectFolder.name)))


def get_project_folder(session: Session, project_id: int, folder_id: int) -> ProjectFolder | None:
    return session.scalar(select(ProjectFolder).where(ProjectFolder.project_id == project_id, ProjectFolder.id == folder_id))


def create_project_folder(session: Session, project: Project, owner: User, name: str, parent_id: int | None = None) -> ProjectFolder:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("folder name is required")
    if parent_id is not None and get_project_folder(session, project.id, parent_id) is None:
        raise ValueError("parent folder not found")
    duplicate = session.scalar(
        select(ProjectFolder).where(
            ProjectFolder.project_id == project.id,
            ProjectFolder.parent_id == parent_id,
            ProjectFolder.name == cleaned,
        )
    )
    if duplicate is not None:
        raise ValueError("a folder with that name already exists here")
    row = ProjectFolder(project_id=project.id, parent_id=parent_id, name=cleaned)
    session.add(row)
    session.flush()
    record_audit(session, actor=owner.username, action="project_folder.created", entity="project_folder",
                 entity_id=str(row.id), after={"project_id": project.id, "name": cleaned, "parent_id": parent_id})
    session.flush()
    return row


def rename_project_folder(session: Session, project: Project, owner: User, folder_id: int, name: str) -> ProjectFolder | None:
    row = get_project_folder(session, project.id, folder_id)
    if row is None:
        return None
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("folder name is required")
    row.name = cleaned
    record_audit(session, actor=owner.username, action="project_folder.renamed", entity="project_folder",
                 entity_id=str(row.id), after={"name": cleaned})
    session.flush()
    return row


def move_project_file(session: Session, project: Project, owner: User, file_id: int, folder_id: int | None) -> ProjectFile | None:
    """Reparent a project file; a null folder moves it back to the project root."""
    row = get_project_file(session, project.id, file_id)
    if row is None:
        return None
    if folder_id is not None and get_project_folder(session, project.id, folder_id) is None:
        raise ValueError("folder not found")
    previous = row.folder_id
    row.folder_id = folder_id
    record_audit(session, actor=owner.username, action="project_file.moved", entity="project_file",
                 entity_id=str(file_id), after={"project_id": project.id, "folder_id": previous, "to_folder_id": folder_id})
    session.flush()
    return row


def delete_project_file(session: Session, project: Project, owner: User, file_id: int) -> bool:
    """Remove a project file, its stored bytes and the KB document it produced."""
    row = get_project_file(session, project.id, file_id)
    if row is None:
        return False
    filename = row.filename
    stored = Path(row.stored_path)
    kb_document_id = row.kb_document_id
    session.delete(row)
    if kb_document_id is not None:
        doc = session.get(KbDocument, kb_document_id)
        if doc is not None:
            session.delete(doc)
    try:
        stored.unlink(missing_ok=True)
    except OSError:
        # A missing or unreadable blob must not block removing the record.
        pass
    record_audit(session, actor=owner.username, action="project_file.deleted", entity="project_file",
                 entity_id=str(file_id), after={"project_id": project.id, "filename": filename, "kb_document_id": kb_document_id})
    session.flush()
    return True


def delete_project_folder(session: Session, project: Project, owner: User, folder_id: int) -> int | None:
    """Delete a folder, its subfolders and every file they hold.

    Returns the number of deleted files, or None when the folder is unknown.
    """
    row = get_project_folder(session, project.id, folder_id)
    if row is None:
        return None
    folder_ids = [folder_id]
    frontier = [folder_id]
    while frontier:
        children = list(session.scalars(select(ProjectFolder.id).where(
            ProjectFolder.project_id == project.id, ProjectFolder.parent_id.in_(frontier))))
        frontier = [child for child in children if child not in folder_ids]
        folder_ids.extend(frontier)
    file_ids = list(session.scalars(select(ProjectFile.id).where(
        ProjectFile.project_id == project.id, ProjectFile.folder_id.in_(folder_ids))))
    for file_id in file_ids:
        delete_project_file(session, project, owner, file_id)
    name = row.name
    session.delete(row)
    record_audit(session, actor=owner.username, action="project_folder.deleted", entity="project_folder",
                 entity_id=str(folder_id), after={"project_id": project.id, "name": name, "files": len(file_ids)})
    session.flush()
    return len(file_ids)


MAX_FILE_TEXT_CHARS = 20_000


def owned_project(session: Session, owner_id: int | None, *, project_id: int | None = None, slug: str | None = None) -> Project | None:
    """Resolve a project the owner may access, or None. Fails closed."""
    if owner_id is None:
        return None
    stmt = select(Project).where(Project.owner_id == owner_id)
    if project_id is not None:
        stmt = stmt.where(Project.id == project_id)
    elif slug:
        stmt = stmt.where(Project.slug == slug)
    else:
        return None
    return session.scalar(stmt)


def read_file_text(row: ProjectFile, *, offset: int = 0, limit: int = MAX_FILE_TEXT_CHARS) -> dict:
    """Return a bounded slice of a stored file's exact extracted text.

    Reads the original stored blob (the source of truth) and re-extracts text,
    so it works even when KB ingestion failed or was skipped. `offset`/`limit`
    let the agent page a large file across tool-loop turns: `next_offset` is the
    cursor for the following read, or None when the slice reached the end.
    """
    kind = allowed_project_file(row.filename, row.content_type, row.size)
    if kind == "image":
        return {"kind": "image", "text": "", "truncated": False, "chars": 0, "offset": 0, "limit": 0, "next_offset": None}
    content = Path(row.stored_path).read_bytes()
    text = extract_document_text(content, kind)
    total = len(text)
    chunk = text[offset:offset + limit]
    end = offset + len(chunk)
    truncated = end < total
    return {
        "kind": kind,
        "text": chunk,
        "truncated": truncated,
        "chars": total,
        "offset": offset,
        "limit": limit,
        "next_offset": end if truncated else None,
    }
