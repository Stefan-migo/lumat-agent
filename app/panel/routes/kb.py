"""Knowledge base manager panel views (T5.4; AP-6, KB-3, KB-4, SH-5).

Admin-only (require_admin — AP-2 server-side gate):

GET  /panel/kb                    -> document list (provider/model/cost shown)
POST /panel/kb                    -> add document (title + file upload)
POST /panel/kb/{id}/edit          -> edit (title + content; new version, KB-4)
POST /panel/kb/{id}/disable       -> disable (excluded from retrieval, KB-3)
POST /panel/kb/{id}/restore       -> restore version (pointer flip, D8)

All mutations delegate to app/services/kb.py and are audited with the acting
admin's username (SH-5).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.models import DocumentFormat, KbDocument
from app.panel.deps import flash, get_db, require_admin, templates
from app.services import kb as kb_service

router = APIRouter(tags=["panel-kb"])

# Upload extension -> document format (KB-1 pipeline).
FORMAT_BY_EXTENSION = {
    ".pdf": DocumentFormat.PDF,
    ".md": DocumentFormat.MD,
    ".txt": DocumentFormat.MD,
    ".csv": DocumentFormat.CSV,
}


def _doc_or_404(session, doc_id: int) -> KbDocument:
    doc = session.get(KbDocument, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="kb document not found")
    return doc


@router.get("/kb")
def kb_list(
    request: Request,
    session=Depends(get_db),
    current=Depends(require_admin),
):
    docs = list(session.scalars(select(KbDocument).order_by(KbDocument.id.desc())))
    return templates.TemplateResponse(
        request,
        "kb/list.html",
        {"current_user": current, "docs": docs, "flash": _pop_flash(request)},
    )


def _pop_flash(request: Request) -> str | None:
    return request.session.pop("flash", None)


@router.post("/kb")
def kb_add(
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    session=Depends(get_db),
    current=Depends(require_admin),
):
    fmt = FORMAT_BY_EXTENSION.get(Path(file.filename or "").suffix.lower())
    if fmt is None:
        raise HTTPException(status_code=400, detail="unsupported file type (pdf/md/csv)")
    content = file.file.read()
    if not content.strip():
        raise HTTPException(status_code=400, detail="empty document")
    try:
        kb_service.ingest_document(
            session, title, fmt, content, actor=current.username
        )
    except Exception as exc:
        flash(request, f"ingest failed: {exc}")
    else:
        flash(request, f"Document {title!r} added")
    return RedirectResponse("/panel/kb", status_code=303)


@router.post("/kb/{doc_id}/edit")
def kb_edit(
    request: Request,
    doc_id: int,
    title: str = Form(...),
    content: str = Form(...),
    session=Depends(get_db),
    current=Depends(require_admin),
):
    _doc_or_404(session, doc_id)
    try:
        kb_service.update_document(
            session, doc_id, content, title=title, actor=current.username
        )
    except ValueError as exc:
        flash(request, str(exc))
    else:
        flash(request, f"Document #{doc_id} updated (new version)")
    return RedirectResponse("/panel/kb", status_code=303)


@router.post("/kb/{doc_id}/disable")
def kb_disable(
    request: Request,
    doc_id: int,
    session=Depends(get_db),
    current=Depends(require_admin),
):
    try:
        kb_service.disable_document(session, doc_id, actor=current.username)
    except ValueError as exc:
        flash(request, str(exc))
    else:
        flash(request, f"Document #{doc_id} disabled")
    return RedirectResponse("/panel/kb", status_code=303)


@router.post("/kb/{doc_id}/restore")
def kb_restore(
    request: Request,
    doc_id: int,
    version: int = Form(...),
    session=Depends(get_db),
    current=Depends(require_admin),
):
    try:
        kb_service.restore_version(session, doc_id, version, actor=current.username)
    except ValueError as exc:
        flash(request, str(exc))
    else:
        flash(request, f"Document #{doc_id} restored to version {version}")
    return RedirectResponse("/panel/kb", status_code=303)
