"""Owner-scoped project file upload, listing, and download API."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Project, User
from app.panel.api.deps import require_agent_surface_json
from app.panel.api.serializers import to_project_file_dict
from app.panel.deps import get_db
from app.services.project_files import get_project_file, list_project_files, store_project_file

router = APIRouter(tags=["panel-api-project-files"])


def _owned_project(session: Session, slug: str, owner_id: int) -> Project:
    project = session.scalar(select(Project).where(Project.slug == slug, Project.owner_id == owner_id))
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.post("/projects/{slug}/files", status_code=201)
def upload_project_file(
    slug: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    project = _owned_project(session, slug, current.id)
    filename = file.filename or "attachment"
    content = file.file.read(get_settings().project_file_max_bytes + 1)
    try:
        row = store_project_file(session, project, current, filename, file.content_type, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    return {"file": to_project_file_dict(row)}


@router.get("/projects/{slug}/files")
def get_project_files(
    slug: str,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    project = _owned_project(session, slug, current.id)
    return {"files": [to_project_file_dict(row) for row in list_project_files(session, project.id)]}


@router.get("/projects/{slug}/files/{file_id}/download")
def download_project_file(
    slug: str,
    file_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> FileResponse:
    project = _owned_project(session, slug, current.id)
    row = get_project_file(session, project.id, file_id)
    if row is None:
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(row.stored_path, filename=row.filename, media_type=row.content_type)
