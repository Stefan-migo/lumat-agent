"""Owner-scoped project file and folder API."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Project, User
from app.panel.api.deps import require_agent_surface_json
from app.panel.api.serializers import to_project_file_dict, to_project_folder_dict
from app.panel.deps import get_db
from app.services.project_files import (
    create_project_folder,
    delete_project_file,
    delete_project_folder,
    get_project_file,
    get_project_folder,
    ingest_project_file,
    list_project_files,
    list_project_folders,
    rename_project_folder,
    store_project_file,
)

router = APIRouter(tags=["panel-api-project-files"])


class FolderCreateBody(BaseModel):
    name: str
    parent_id: int | None = None


class FolderRenameBody(BaseModel):
    name: str


def _owned_project(session: Session, slug: str, owner_id: int) -> Project:
    project = session.scalar(select(Project).where(Project.slug == slug, Project.owner_id == owner_id))
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.post("/projects/{slug}/files", status_code=201)
def upload_project_file(
    slug: str,
    file: UploadFile = File(...),
    folder_id: int | None = Form(None),
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    project = _owned_project(session, slug, current.id)
    if folder_id is not None and get_project_folder(session, project.id, folder_id) is None:
        raise HTTPException(status_code=400, detail="folder not found")
    filename = file.filename or "attachment"
    content = file.file.read(get_settings().project_file_max_bytes + 1)
    try:
        row = store_project_file(session, project, current, filename, file.content_type, content, folder_id)
        ingest_project_file(session, project, row, content, current.username)
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


@router.delete("/projects/{slug}/files/{file_id}", status_code=204)
def remove_project_file(
    slug: str,
    file_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> None:
    project = _owned_project(session, slug, current.id)
    if not delete_project_file(session, project, current, file_id):
        raise HTTPException(status_code=404, detail="file not found")
    session.commit()


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


@router.get("/projects/{slug}/folders")
def get_project_folders(
    slug: str,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    project = _owned_project(session, slug, current.id)
    return {"folders": [to_project_folder_dict(row) for row in list_project_folders(session, project.id)]}


@router.post("/projects/{slug}/folders", status_code=201)
def add_project_folder(
    slug: str,
    body: FolderCreateBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    project = _owned_project(session, slug, current.id)
    try:
        row = create_project_folder(session, project, current, body.name, body.parent_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    return {"folder": to_project_folder_dict(row)}


@router.patch("/projects/{slug}/folders/{folder_id}")
def update_project_folder(
    slug: str,
    folder_id: int,
    body: FolderRenameBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> dict:
    project = _owned_project(session, slug, current.id)
    try:
        row = rename_project_folder(session, project, current, folder_id, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="folder not found")
    session.commit()
    return {"folder": to_project_folder_dict(row)}


@router.delete("/projects/{slug}/folders/{folder_id}", status_code=204)
def remove_project_folder(
    slug: str,
    folder_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_agent_surface_json),
) -> None:
    project = _owned_project(session, slug, current.id)
    if delete_project_folder(session, project, current, folder_id) is None:
        raise HTTPException(status_code=404, detail="folder not found")
    session.commit()
