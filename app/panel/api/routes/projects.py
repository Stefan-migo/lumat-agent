"""Owner-scoped project registry and creation."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import InternalChatThread, Project, User
from app.panel.api.deps import require_agent_surface_json
from app.panel.api.serializers import to_project_dict
from app.panel.deps import get_db
from app.services import projects as project_service
from app.services.project_config import ProjectConfigUpdate, set_project_config

router = APIRouter(tags=["panel-api-projects"])


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=500)


@router.get("/projects")
def projects_list(
    session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)
) -> dict:
    return {"projects": [to_project_dict(project) for project in session.scalars(select(Project).where(Project.owner_id == current.id).order_by(Project.slug))]}


@router.get("/projects/{slug}")
def project_detail(
    slug: str, session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)
) -> dict:
    project = session.scalar(select(Project).where(Project.slug == slug, Project.owner_id == current.id))
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"project": to_project_dict(project, include_config=True)}


@router.get("/projects/{slug}/agents")
def project_agents(
    slug: str, session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)
) -> dict:
    project = session.scalar(select(Project).where(Project.slug == slug, Project.owner_id == current.id))
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    thread = session.scalar(
        select(InternalChatThread)
        .where(InternalChatThread.proyecto == slug, InternalChatThread.user_id == current.id)
        .order_by(InternalChatThread.updated_at.desc(), InternalChatThread.id.desc())
        .limit(1)
    )
    live = (thread.assistant_state or {}).get("live") if thread else None
    latest_run = None
    if isinstance(live, dict) and live.get("status"):
        latest_run = {
            "status": live["status"],
            "tool": live.get("tool"),
            "at": thread.updated_at.isoformat() if thread.updated_at else None,
        }

    return {
        "agents": [
            {"key": "orchestrator", "name": "Orquestador", "role": "Asistente del proyecto",
             "description": "Responde consultas del proyecto y ejecuta las herramientas disponibles según la solicitud.", "read_only": False},
            {"key": "verifier", "name": "Verificador", "role": "Verificación independiente",
             "description": "Contrasta un criterio con evidencia y, cuando corresponde, consulta herramientas de solo lectura.", "read_only": True},
            {"key": "explorer", "name": "Explorador", "role": "Investigación de solo lectura",
             "description": "Investiga mediante las herramientas de solo lectura habilitadas para la delegación.", "read_only": True},
        ],
        "latest_run": latest_run,
    }


@router.patch("/projects/{slug}/config")
def project_config_update(
    slug: str,
    payload: ProjectConfigUpdate,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    project = session.scalar(select(Project).where(Project.slug == slug, Project.owner_id == current.id))
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        set_project_config(session, project, payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    session.commit()
    return {"project": to_project_dict(project, include_config=True)}


@router.post("/projects", status_code=201)
def projects_create(
    payload: ProjectCreateRequest,
    session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json),
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
