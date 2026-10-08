"""Assistant-produced downloadable artifacts, scoped to a chat thread."""

import hashlib
import mimetypes
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AssistantArtifact, InternalChatThread
from app.services.audit import record_audit

MAX_ARTIFACT_CONTENT_CHARS = 200_000


def artifact_path(thread_id: int, opaque_id: str | None = None) -> Path:
    return Path(get_settings().media_dir) / "assistant_artifacts" / str(thread_id) / (opaque_id or uuid4().hex)


def safe_artifact_filename(filename: str) -> str:
    """A bare, bounded filename with no path components or control characters."""
    name = Path(filename).name.strip()
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:255] or "artifact.txt"


def owned_thread(session: Session, thread_id: int | None, owner_id: int | None) -> InternalChatThread | None:
    """Resolve a chat thread the owner may access, or None. Fails closed."""
    if owner_id is None or not isinstance(thread_id, int) or thread_id <= 0:
        return None
    return session.scalar(
        select(InternalChatThread).where(
            InternalChatThread.id == thread_id, InternalChatThread.user_id == owner_id
        )
    )


def store_artifact(session: Session, thread: InternalChatThread, filename: str, content: str, actor: str) -> AssistantArtifact:
    name = safe_artifact_filename(filename)
    data = content.encode("utf-8")
    if not data:
        raise ValueError("artifact content is empty")
    if len(data) > get_settings().assistant_artifact_max_bytes:
        raise ValueError("artifact size exceeds the configured limit")
    destination = artifact_path(thread.id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    row = AssistantArtifact(
        thread_id=thread.id,
        filename=name,
        content_type=mimetypes.guess_type(name)[0] or "text/plain",
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        stored_path=str(destination),
    )
    session.add(row)
    session.flush()
    record_audit(session, actor=actor, action="assistant_artifact.created", entity="assistant_artifact",
                 entity_id=str(row.id), after={"thread_id": thread.id, "filename": name, "size": len(data)})
    return row


def list_artifacts(session: Session, thread_id: int) -> list[AssistantArtifact]:
    return list(session.scalars(select(AssistantArtifact).where(AssistantArtifact.thread_id == thread_id).order_by(AssistantArtifact.id)))


def get_artifact(session: Session, thread_id: int, artifact_id: int) -> AssistantArtifact | None:
    return session.scalar(select(AssistantArtifact).where(AssistantArtifact.thread_id == thread_id, AssistantArtifact.id == artifact_id))
