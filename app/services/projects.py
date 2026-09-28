"""Minimal registry operations for agent-owned project namespaces."""

from dataclasses import dataclass
import re
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import models
from app.services import kb

SIMILARITY_THRESHOLD = 0.85
MAX_CANDIDATES = 3


@dataclass(frozen=True)
class _ProjectAuthorization:
    """Opaque capability issued by this service for one active namespace."""

    slug: str
    owner_id: int | None = None


@dataclass(frozen=True)
class _ApprovedProjectDecision:
    """Approval decision issued only by the assistant execution boundary."""

    operation: str
    decision: dict[str, Any]


@dataclass(frozen=True)
class ProjectCandidate:
    slug: str
    name: str
    similarity: float


@dataclass(frozen=True)
class ProjectResult:
    project: models.Project | None
    candidates: list[ProjectCandidate]
    requires_approval: bool = False


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def normalize_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def list(session: Session, owner_id: int | None = None) -> list[models.Project]:
    """Return every project, including archived entries."""
    return session.scalars(select(models.Project).where(models.Project.owner_id == owner_id).order_by(models.Project.slug)).all()


def find(
    session: Session,
    query: str,
    *,
    owner_id: int | None = None,
    _approval: _ApprovedProjectDecision | None = None,
) -> ProjectResult:
    """Resolve an exact slug or return at most three approval-bound candidates."""
    slug = normalize_slug(query)
    owner_filter = models.Project.owner_id.is_(None) if owner_id is None else models.Project.owner_id == owner_id
    exact = session.scalar(select(models.Project).where(owner_filter, func.lower(models.Project.slug) == slug))
    if exact is not None:
        return ProjectResult(project=exact, candidates=[])

    embeddings, _ = kb.embed_texts([query])
    result = _semantic_candidates(session, embeddings[0], owner_id)
    if _approval is not None and _approval.operation == "find":
        selected_slug = _approval.decision.get("selected_slug")
        if selected_slug and any(candidate.slug == selected_slug for candidate in result.candidates):
            project = session.scalar(select(models.Project).where(models.Project.slug == selected_slug, owner_filter))
            if project is not None:
                return ProjectResult(project=project, candidates=result.candidates)
    return result


def _semantic_candidates(session: Session, vector: list[float], owner_id: int | None = None) -> ProjectResult:
    similarity = (1 - models.Project.purpose_embedding.cosine_distance(vector)).label("similarity")
    owner_filter = models.Project.owner_id.is_(None) if owner_id is None else models.Project.owner_id == owner_id
    rows = session.execute(
        select(models.Project, similarity)
        .where(owner_filter, models.Project.purpose_embedding.cosine_distance(vector) <= 1 - SIMILARITY_THRESHOLD)
        .order_by(similarity.desc())
        .limit(MAX_CANDIDATES)
    ).all()
    candidates = [ProjectCandidate(row[0].slug, row[0].name, float(row[1])) for row in rows]
    return ProjectResult(project=None, candidates=candidates, requires_approval=bool(candidates))


def create(
    session: Session,
    slug: str,
    name: str,
    purpose: str,
    *,
    owner_id: int | None = None,
    _approval: _ApprovedProjectDecision | None = None,
) -> models.Project | ProjectResult:
    """Create a project only when no exact or semantic purpose candidate exists."""
    normalized_purpose = normalize(purpose)
    duplicate = session.scalar(
        select(models.Project).where(
            models.Project.owner_id.is_(None) if owner_id is None else models.Project.owner_id == owner_id,
            func.lower(func.regexp_replace(models.Project.purpose, r"\s+", " ", "g"))
            == normalized_purpose
        )
    )
    if duplicate is not None:
        result = ProjectResult(
            project=None,
            candidates=[ProjectCandidate(duplicate.slug, duplicate.name, 1.0)],
            requires_approval=True,
        )
        if _approval is not None and _approval.operation == "create":
            selected_slug = _approval.decision.get("selected_slug")
            if selected_slug == duplicate.slug:
                return duplicate
            if _approval.decision.get("create_distinct") is not True:
                return result
        elif _approval is None:
            return result
        else:
            return result

    embedding, _ = kb.embed_texts([purpose])
    semantic_result = _semantic_candidates(session, embedding[0], owner_id)
    if semantic_result.requires_approval:
        if _approval is None or _approval.operation != "create":
            return semantic_result
        selected_slug = _approval.decision.get("selected_slug")
        if selected_slug:
            if not any(candidate.slug == selected_slug for candidate in semantic_result.candidates):
                return semantic_result
            project = session.scalar(select(models.Project).where(models.Project.slug == selected_slug, models.Project.owner_id == owner_id))
            return project or semantic_result
        if _approval.decision.get("create_distinct") is not True:
            return semantic_result

    project = models.Project(
        slug=normalize_slug(slug),
        name=name.strip(),
        purpose=purpose.strip(),
        purpose_embedding=embedding[0],
        owner_id=owner_id,
    )
    session.add(project)
    return project


def agent_context(session: Session, proyecto: str, owner_id: int | None = None) -> _ProjectAuthorization:
    """Issue the canonical service capability for an active project namespace."""
    slug = normalize_slug(proyecto)
    owner_filter = models.Project.owner_id.is_(None) if owner_id is None else models.Project.owner_id == owner_id
    project = session.scalar(select(models.Project).where(models.Project.slug == slug, owner_filter))
    if project is None or _status_value(project.status) != "active":
        raise ValueError(f"project {proyecto!r} is not an active project")
    return _ProjectAuthorization(slug=project.slug, owner_id=project.owner_id)


def _project_id(project: models.Project | str) -> str:
    return project.slug if isinstance(project, models.Project) else normalize_slug(project)


def _status_value(status: models.ProjectStatus | str) -> str:
    return status.value if isinstance(status, models.ProjectStatus) else str(status)


def _lock_projects(session: Session, *projects: models.Project | str, owner_id: int | None = None) -> dict[str, models.Project]:
    slugs = {_project_id(project) for project in projects}
    selected_owner = owner_id if owner_id is not None else next(
        (project.owner_id for project in projects if isinstance(project, models.Project)), None
    )
    owner_filter = models.Project.owner_id.is_(None) if selected_owner is None else models.Project.owner_id == selected_owner
    rows = session.scalars(
        select(models.Project)
        .where(models.Project.slug.in_(slugs), owner_filter)
        .order_by(models.Project.id)
        .with_for_update()
    ).all()
    locked = {row.slug: row for row in rows}
    if len(locked) != len(slugs):
        missing = sorted(slugs - locked.keys())[0]
        raise ValueError(f"project {missing!r} not found")
    return locked


def _has_active_run(session: Session, slug: str) -> bool:
    for thread in session.scalars(select(models.InternalChatThread)):
        state = thread.assistant_state or {}
        sdb = state.get("sdb") or {}
        namespace = sdb.get("proyecto") or sdb.get("project") or state.get("proyecto")
        if namespace == slug and (thread.active_run_id or state.get("recoverable")):
            return True
    return False


def _validate_namespace(session: Session, project: models.Project) -> None:
    """Validate that the namespace has no duplicate composite keys before mutation."""
    rows = session.execute(
        select(
            models.Memory.scope,
            models.Memory.entity_id,
            models.Memory.topic_key,
            func.count(models.Memory.id),
        )
        .where(models.Memory.proyecto == project.slug)
        .where(models.Memory.owner_id == project.owner_id)
        .group_by(models.Memory.scope, models.Memory.entity_id, models.Memory.topic_key)
        .having(func.count(models.Memory.id) > 1)
    ).all()
    if rows:
        raise ValueError(f"namespace migration failed for {project.slug!r}")


def _audit(session: Session, project_id: int, action: str, actor: str, before: Any, after: Any) -> None:
    session.add(models.ProjectAudit(
        project_id=project_id, actor=actor, action=action, before=before, after=after
    ))


def rename(session: Session, project: models.Project | str, name: str, *, actor: str = "agent") -> models.Project:
    locked = _lock_projects(session, project)
    row = locked[_project_id(project)]
    if _has_active_run(session, row.slug):
        raise ValueError("cannot rename project with an active SDB run")
    _validate_namespace(session, row)
    old = {"slug": row.slug, "name": row.name, "status": _status_value(row.status)}
    new_name = name.strip()
    if not new_name:
        raise ValueError("project name cannot be empty")
    alias = normalize(new_name)
    owner_filter = models.Project.owner_id.is_(None) if row.owner_id is None else models.Project.owner_id == row.owner_id
    alias_filter = models.ProjectAlias.owner_id.is_(None) if row.owner_id is None else models.ProjectAlias.owner_id == row.owner_id
    if session.scalar(select(models.Project).where(owner_filter, func.lower(models.Project.slug) == alias)) or session.scalar(select(models.ProjectAlias).where(alias_filter, models.ProjectAlias.alias == alias)):
        raise ValueError(f"project alias {alias!r} already exists")
    row.name = new_name
    session.add(models.ProjectAlias(project_id=row.id, owner_id=row.owner_id, alias=alias))
    _audit(session, row.id, "rename", actor, old, {"slug": row.slug, "name": new_name, "status": _status_value(row.status)})
    session.flush()
    return row


def archive(session: Session, project: models.Project | str, *, actor: str = "agent") -> models.Project:
    locked = _lock_projects(session, project)
    row = locked[_project_id(project)]
    if row.slug == "default":
        raise ValueError("default project cannot be archived")
    if _has_active_run(session, row.slug):
        raise ValueError("cannot archive project with an active SDB run")
    old = {"slug": row.slug, "name": row.name, "status": _status_value(row.status)}
    row.status = models.ProjectStatus.ARCHIVED
    _audit(session, row.id, "archive", actor, old, {**old, "status": "archived"})
    session.flush()
    return row


def _memory_equivalent(left: models.Memory, right: models.Memory) -> bool:
    return all(getattr(left, field) == getattr(right, field) for field in (
        "scope", "entity_id", "topic_key", "tipo", "titulo", "contenido",
        "embedding", "pin", "review_after", "status",
    ))


def merge(session: Session, source: models.Project | str, target: models.Project | str, *, owner_id: int | None = None, actor: str = "agent") -> models.Project:
    locked = _lock_projects(session, source, target, owner_id=owner_id)
    source_row, target_row = locked[_project_id(source)], locked[_project_id(target)]
    if source_row.id == target_row.id:
        raise ValueError("cannot merge a project into itself")
    if source_row.owner_id != target_row.owner_id or source_row.owner_id != owner_id:
        raise ValueError("cannot merge projects across owners")
    if source_row.slug == "default":
        raise ValueError("default project cannot be merged away")
    if _has_active_run(session, source_row.slug) or _has_active_run(session, target_row.slug):
        raise ValueError("cannot merge projects with an active SDB run")

    source_memories = session.scalars(
        select(models.Memory).where(
            models.Memory.proyecto == source_row.slug,
            models.Memory.owner_id == source_row.owner_id,
        )
    ).all()
    target_memories = session.scalars(
        select(models.Memory).where(
            models.Memory.proyecto == target_row.slug,
            models.Memory.owner_id == target_row.owner_id,
        )
    ).all()
    target_by_key = {(m.scope, m.entity_id, m.topic_key): m for m in target_memories}
    target_by_hash = {
        (m.scope, m.entity_id, m.normalized_hash): m
        for m in target_memories
        if m.normalized_hash is not None
    }
    for memory in source_memories:
        existing = target_by_key.get((memory.scope, memory.entity_id, memory.topic_key))
        if existing is not None and not _memory_equivalent(memory, existing):
            raise ValueError("merge conflict: byte-different memory composite key")

    for memory in source_memories:
        existing = target_by_key.get((memory.scope, memory.entity_id, memory.topic_key))
        hash_existing = (
            target_by_hash.get((memory.scope, memory.entity_id, memory.normalized_hash))
            if memory.normalized_hash is not None
            else None
        )
        if existing is None:
            if hash_existing is None:
                memory.proyecto = target_row.slug
                target_by_key[(memory.scope, memory.entity_id, memory.topic_key)] = memory
                if memory.normalized_hash is not None:
                    target_by_hash[(memory.scope, memory.entity_id, memory.normalized_hash)] = memory
            else:
                session.execute(update(models.MemoryObservation).where(models.MemoryObservation.memory_id == memory.id).values(memory_id=hash_existing.id))
                session.execute(update(models.MemoryRelation).where(models.MemoryRelation.id_a == memory.id).values(id_a=hash_existing.id))
                session.execute(update(models.MemoryRelation).where(models.MemoryRelation.id_b == memory.id).values(id_b=hash_existing.id))
                hash_existing.duplicate_count += memory.duplicate_count
                hash_existing.last_seen_at = func.now()
                session.delete(memory)
        else:
            session.execute(update(models.MemoryObservation).where(models.MemoryObservation.memory_id == memory.id).values(memory_id=existing.id))
            session.execute(update(models.MemoryRelation).where(models.MemoryRelation.id_a == memory.id).values(id_a=existing.id))
            session.execute(update(models.MemoryRelation).where(models.MemoryRelation.id_b == memory.id).values(id_b=existing.id))
            session.delete(memory)
    target_row_alias = models.ProjectAlias(project_id=target_row.id, owner_id=target_row.owner_id, alias=source_row.slug)
    session.add(target_row_alias)
    before = {"source": source_row.slug, "target": target_row.slug, "source_status": _status_value(source_row.status)}
    source_row.status = models.ProjectStatus.ARCHIVED
    _audit(session, target_row.id, "merge", actor, before, {"target": target_row.slug, "source": source_row.slug, "source_status": "archived"})
    session.flush()
    return target_row
