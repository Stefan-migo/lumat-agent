"""Private attachment validation, context preparation, and cleanup."""

from __future__ import annotations

import base64
import hashlib
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.models import DocumentFormat
from app.services.kb import extract_text

MAX_FILE_SIZE = 5 * 1024 * 1024  # backwards-compatible defaults for callers/tests
MAX_ATTACHMENTS_PER_THREAD = 10
MAX_CONTEXT_CHARS = 20_000
MAX_IMAGE_BYTES = 5 * 1024 * 1024

_DOCUMENTS = {".pdf": ("pdf", "application/pdf"), ".csv": ("csv", "text/csv"), ".txt": ("txt", "text/plain")}
_IMAGES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}


def allowed_attachment(filename: str, content_type: str | None, size: int) -> str:
    settings = get_settings()
    if size > settings.assistant_attachment_max_bytes:
        raise ValueError("file size exceeds the configured limit")
    suffix = Path(filename).suffix.lower()
    mime = (content_type or mimetypes.guess_type(filename)[0] or "").split(";", 1)[0].lower()
    if suffix in _DOCUMENTS and mime == _DOCUMENTS[suffix][1] and _DOCUMENTS[suffix][0] in settings.assistant_attachment_allowed_types:
        return _DOCUMENTS[suffix][0]
    if suffix in _IMAGES and mime == _IMAGES[suffix] and "image" in settings.assistant_attachment_allowed_types:
        return "image"
    raise ValueError("unsupported attachment type")


def attachment_path(thread_id: int, opaque_id: str | None = None) -> Path:
    value = opaque_id or uuid4().hex
    return Path(get_settings().media_dir) / "assistant" / str(thread_id) / value


def store_attachment(thread_id: int, filename: str, content_type: str | None, content: bytes):
    kind = allowed_attachment(filename, content_type, len(content))
    destination = attachment_path(thread_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return kind, destination, hashlib.sha256(content).hexdigest()


def prepare_attachment_context(attachments, max_chars: int | None = None) -> list[dict]:
    context: list[dict] = []
    max_chars = get_settings().assistant_attachment_max_context_chars if max_chars is None else max_chars
    remaining = max_chars
    for attachment in attachments:
        if attachment.kind == "image":
            if Path(attachment.stored_path).stat().st_size > get_settings().assistant_attachment_max_image_bytes:
                raise ValueError("image exceeds the vision size limit")
            continue
        content = Path(attachment.stored_path).read_bytes()
        fmt = DocumentFormat.CSV if attachment.kind == "csv" else DocumentFormat.PDF if attachment.kind == "pdf" else DocumentFormat.MD
        text = extract_text(content, fmt)[:remaining]
        remaining -= len(text)
        context.append({"type": "document", "filename": attachment.filename, "kind": attachment.kind, "text": text, "attachment_id": getattr(attachment, "id", None)})
        if remaining <= 0:
            break
    return context


def build_multimodal_content(attachments, prompt: str) -> list[dict]:
    parts: list[dict] = [{"type": "text", "text": prompt}]
    for attachment in attachments:
        if attachment.kind != "image":
            continue
        content = Path(attachment.stored_path).read_bytes()
        if len(content) > get_settings().assistant_attachment_max_image_bytes:
            raise ValueError("image exceeds the vision size limit")
        mime = mimetypes.guess_type(attachment.filename)[0] or "application/octet-stream"
        encoded = base64.b64encode(content).decode("ascii")
        parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}})
    return parts


def cleanup_attachments(rows, active_thread_ids: set[int], now: datetime | None = None, expired: bool = False) -> int:
    removed = 0
    for row in rows:
        if row.thread_id in active_thread_ids and row.deleted_at is None and not expired:
            continue
        path = Path(row.stored_path)
        path.unlink(missing_ok=True)
        row.deleted_at = now or datetime.now(timezone.utc)
        removed += 1
    return removed


def cleanup_expired(session, older_than: datetime, active_thread_ids: set[int] | None = None) -> int:
    """Remove expired/orphaned assistant metadata and private files only."""
    from sqlalchemy import select
    from app.models import AssistantAttachment

    rows = list(session.scalars(select(AssistantAttachment).where(AssistantAttachment.created_at < older_than, AssistantAttachment.deleted_at.is_(None))))
    removed = cleanup_attachments(rows, active_thread_ids or set(), expired=True)
    for row in rows:
        session.delete(row)
    session.flush()
    return removed
