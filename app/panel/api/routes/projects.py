"""Read-only project registry and typed SDB artifact browse."""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Memory, Project, User
from app.panel.api.deps import require_operator_json
from app.panel.api.serializers import to_project_artifact_dict, to_project_dict
from app.panel.deps import get_db

router = APIRouter(tags=["panel-api-projects"])


@router.get("/projects")
def projects_list(
    session: Session = Depends(get_db), current: User = Depends(require_operator_json)
) -> dict:
    return {"projects": [to_project_dict(project) for project in session.scalars(select(Project).order_by(Project.slug))]}


@router.get("/projects/{slug}")
def project_detail(
    slug: str, session: Session = Depends(get_db), current: User = Depends(require_operator_json)
) -> dict:
    project = session.scalar(select(Project).where(Project.slug == slug))
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    rows = session.scalars(
        select(Memory)
        .where(Memory.proyecto == project.slug, Memory.scope == "panel", Memory.topic_key.like("sdb:%"))
        .order_by(Memory.entity_id, Memory.updated_at.desc(), Memory.id.desc())
    )
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row.entity_id].append(to_project_artifact_dict(row))
    return {"project": to_project_dict(project), "artifacts": dict(grouped)}
