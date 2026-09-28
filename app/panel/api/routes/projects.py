"""Owner-scoped project registry, creation, and typed SDB artifact browse."""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Memory, Project, User
from app.panel.api.deps import require_operator_json
from app.panel.api.serializers import to_project_artifact_dict, to_project_dict
from app.panel.deps import get_db
from app.services import projects as project_service

router = APIRouter(tags=["panel-api-projects"])


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=500)


@router.get("/projects")
def projects_list(
    session: Session = Depends(get_db), current: User = Depends(require_operator_json)
) -> dict:
    return {"projects": [to_project_dict(project) for project in session.scalars(select(Project).where(Project.owner_id == current.id).order_by(Project.slug))]}


@router.get("/projects/{slug}")
def project_detail(
    slug: str, session: Session = Depends(get_db), current: User = Depends(require_operator_json)
) -> dict:
    project = session.scalar(select(Project).where(Project.slug == slug, Project.owner_id == current.id))
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    rows = session.scalars(
        select(Memory)
        .where(Memory.proyecto == project.slug, Memory.owner_id == current.id, Memory.scope == "panel", Memory.topic_key.like("sdb:%"))
        .order_by(Memory.entity_id, Memory.updated_at.desc(), Memory.id.desc())
    )
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row.entity_id].append(to_project_artifact_dict(row))
    return {"project": to_project_dict(project), "artifacts": dict(grouped)}


@router.post("/projects", status_code=201)
def projects_create(
    payload: ProjectCreateRequest,
    session: Session = Depends(get_db), current: User = Depends(require_operator_json),
) -> dict:
    try:
        project = project_service.create(session, payload.slug, payload.name, payload.purpose, owner_id=current.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(project, project_service.ProjectResult):
        return JSONResponse(status_code=409, content={
            "detail": "project purpose conflicts with existing projects",
            "candidates": [{"slug": item.slug, "name": item.name, "similarity": item.similarity} for item in project.candidates],
        })
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="project slug already exists") from exc
    return {"project": to_project_dict(project)}
