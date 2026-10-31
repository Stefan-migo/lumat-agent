"""Assistant-produced downloadable artifacts, scoped to a chat thread.

An artifact is identified by its `root_id` and grows an append-only revision chain: `store_artifact`
creates version 1, `append_revision` inserts the next version with the full blob, and nothing is ever
updated in place or deleted. The current version is the row with the highest `version` for a root.
"""

import hashlib
import mimetypes
from pathlib import Path
from uuid import uuid4

from sqlalchemy import and_, func, select, text
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


def _validated_bytes(content: str) -> bytes:
    """The content bounds every artifact write shares: non-empty and under the configured limit."""
    data = content.encode("utf-8")
    if not data:
        raise ValueError("artifact content is empty")
    if len(data) > get_settings().assistant_artifact_max_bytes:
        raise ValueError("artifact size exceeds the configured limit")
    return data


def _write_blob(destination: Path, data: bytes) -> None:
    """Write the stored bytes, removing a partial file so a failed write leaves no orphan blob."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.write_bytes(data)
    except OSError:
        destination.unlink(missing_ok=True)
        raise


def store_artifact(session: Session, thread: InternalChatThread, filename: str, content: str, actor: str) -> AssistantArtifact:
    name = safe_artifact_filename(filename)
    data = _validated_bytes(content)
    destination = artifact_path(thread.id)
    # The row is its own root, and `root_id` is NOT NULL, so the identity is taken from the same
    # sequence before the insert instead of patching `root_id` afterwards.
    root_id = session.execute(text("SELECT nextval('assistant_artifacts_id_seq')")).scalar_one()
    row = AssistantArtifact(
        id=root_id,
        root_id=root_id,
        version=1,
        thread_id=thread.id,
        filename=name,
        content_type=mimetypes.guess_type(name)[0] or "text/plain",
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        stored_path=str(destination),
    )
    # The row lands before the bytes: a failed write then rolls the row back instead of leaving a
    # blob on disk that nothing references.
    session.add(row)
    session.flush()
    _write_blob(destination, data)
    record_audit(session, actor=actor, action="assistant_artifact.created", entity="assistant_artifact",
                 entity_id=str(row.id), after={"thread_id": thread.id, "filename": name, "size": len(data),
                                               "root_id": row.root_id, "version": row.version})
    return row


def latest_for_root(session: Session, thread_id: int, root_id: int) -> AssistantArtifact | None:
    return session.scalar(
        select(AssistantArtifact)
        .where(AssistantArtifact.thread_id == thread_id, AssistantArtifact.root_id == root_id)
        .order_by(AssistantArtifact.version.desc())
        .limit(1)
    )


def append_revision(
    session: Session, thread: InternalChatThread, artifact: AssistantArtifact, content: str, actor: str
) -> tuple[AssistantArtifact, bool]:
    """Append the next version of `artifact`. Returns (row, changed).

    Identical bytes are not a new version (S7): the current row comes back unchanged with
    `changed=False`. The root row is locked before the next version is computed, so concurrent edits
    of the same artifact serialize instead of racing for one version number (S11).
    """
    data = _validated_bytes(content)
    digest = hashlib.sha256(data).hexdigest()
    session.scalar(
        select(AssistantArtifact.id).where(AssistantArtifact.id == artifact.root_id).with_for_update()
    )
    latest = latest_for_root(session, thread.id, artifact.root_id)
    if latest is None:
        raise ValueError("artifact not found")
    if latest.sha256 == digest:
        return latest, False
    destination = artifact_path(thread.id)
    row = AssistantArtifact(
        thread_id=thread.id,
        root_id=latest.root_id,
        version=latest.version + 1,
        filename=latest.filename,
        content_type=latest.content_type,
        size=len(data),
        sha256=digest,
        stored_path=str(destination),
    )
    session.add(row)
    session.flush()
    _write_blob(destination, data)
    record_audit(session, actor=actor, action="assistant_artifact.updated", entity="assistant_artifact",
                 entity_id=str(row.id), after={"thread_id": thread.id, "filename": row.filename,
                                               "size": len(data), "root_id": row.root_id,
                                               "version": row.version,
                                               "previous_version": latest.version})
    return row, True


def list_artifacts(session: Session, thread_id: int) -> list[AssistantArtifact]:
    """One row per artifact: the current version of each root (S2)."""
    current = (
        select(AssistantArtifact.root_id, func.max(AssistantArtifact.version).label("version"))
        .where(AssistantArtifact.thread_id == thread_id)
        .group_by(AssistantArtifact.root_id)
        .subquery()
    )
    return list(session.scalars(
        select(AssistantArtifact)
        .join(current, and_(
            AssistantArtifact.root_id == current.c.root_id,
            AssistantArtifact.version == current.c.version,
        ))
        .where(AssistantArtifact.thread_id == thread_id)
        .order_by(AssistantArtifact.root_id)
    ))


def revision_chain(session: Session, thread_id: int) -> dict[int, list[AssistantArtifact]]:
    """Every revision of every artifact in the thread, grouped by root, oldest version first."""
    rows = session.scalars(
        select(AssistantArtifact)
        .where(AssistantArtifact.thread_id == thread_id)
        .order_by(AssistantArtifact.root_id, AssistantArtifact.version)
    )
    chain: dict[int, list[AssistantArtifact]] = {}
    for row in rows:
        chain.setdefault(row.root_id, []).append(row)
    return chain


def get_artifact(session: Session, thread_id: int, artifact_id: int) -> AssistantArtifact | None:
    return session.scalar(select(AssistantArtifact).where(AssistantArtifact.thread_id == thread_id, AssistantArtifact.id == artifact_id))


def get_current(session: Session, thread_id: int, artifact_id: int) -> AssistantArtifact | None:
    """Resolve any revision id of a thread to the current version of its artifact."""
    row = get_artifact(session, thread_id, artifact_id)
    if row is None:
        return None
    return latest_for_root(session, thread_id, row.root_id)


def get_revision(session: Session, thread_id: int, artifact_id: int, version: int) -> AssistantArtifact | None:
    """Resolve any revision id of a thread plus a version to that exact revision."""
    row = get_artifact(session, thread_id, artifact_id)
    if row is None:
        return None
    return session.scalar(
        select(AssistantArtifact).where(
            AssistantArtifact.thread_id == thread_id,
            AssistantArtifact.root_id == row.root_id,
            AssistantArtifact.version == version,
        )
    )
