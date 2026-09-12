"""Minimal registry operations for agent-owned project namespaces."""

from dataclasses import dataclass
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.services import kb

SIMILARITY_THRESHOLD = 0.85
MAX_CANDIDATES = 3


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


def list(session: Session) -> list[models.Project]:
    """Return every project, including archived entries."""
    return session.scalars(select(models.Project).order_by(models.Project.slug)).all()


def find(session: Session, query: str) -> ProjectResult:
    """Resolve an exact slug or return at most three approval-bound candidates."""
    slug = normalize_slug(query)
    exact = session.scalar(select(models.Project).where(func.lower(models.Project.slug) == slug))
    if exact is not None:
        return ProjectResult(project=exact, candidates=[])

    embeddings, _ = kb.embed_texts([query])
    vector = embeddings[0]
    similarity = (1 - models.Project.purpose_embedding.cosine_distance(vector)).label("similarity")
    rows = session.execute(
        select(models.Project, similarity)
        .where(models.Project.purpose_embedding.cosine_distance(vector) <= 1 - SIMILARITY_THRESHOLD)
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
    allow_ambiguous: bool = False,
) -> models.Project | ProjectResult:
    """Create a project unless purpose similarity makes reuse ambiguous.

    ``allow_ambiguous`` is intentionally not an approval system; WU-4 owns that
    boundary. The default therefore returns candidates without persisting.
    """
    normalized_purpose = normalize(purpose)
    duplicate = session.scalar(
        select(models.Project).where(
            func.lower(func.regexp_replace(models.Project.purpose, r"\s+", " ", "g"))
            == normalized_purpose
        )
    )
    if duplicate is not None and not allow_ambiguous:
        return ProjectResult(
            project=None,
            candidates=[ProjectCandidate(duplicate.slug, duplicate.name, 1.0)],
            requires_approval=True,
        )

    embedding, _ = kb.embed_texts([purpose])
    project = models.Project(
        slug=normalize_slug(slug),
        name=name.strip(),
        purpose=purpose.strip(),
        purpose_embedding=embedding[0],
    )
    session.add(project)
    return project
