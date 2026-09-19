"""Panel JSON API KB admin (B4/T4.1; PDW-API-1, PDW-API-3, PDW-API-4, D1, D4).

Admin-only JSON wrappers over `app/services/kb.py` (thin, no new business
logic; the mutation audits are the existing service calls, SH-5):

- GET  /kb              -> {"docs": [{provider, model, cost_meta}]} (newest 1st)
- GET  /kb/{id}         -> document detail including content
- GET  /kb/search       -> retrieval probe with ranked chunks and titles
- POST /kb              -> multipart title + file (pdf/md/txt/csv); ingest + audit
- POST /kb/{id}/edit    -> {"title","content"}: new version + re-embed (KB-4)
- POST /kb/{id}/disable -> KB-3 disable (excluded from retrieval)
- POST /kb/{id}/restore -> {"version":n}: active_version pointer flip (D8)

Role enforcement server-side (PDW-API-4): `require_admin_json` -> operador 403
{"detail":"admin role required"}; unauthenticated 401 {"detail":"unauthorized"}
no redirect (D4, PDW-AUTH-1). No CORS (D1). Errors JSON {"detail": ...}
(PDW-API-3). Upload format mapping is the same as the Jinja route
(app/panel/routes/kb.py) so the JSON and HTML panels accept identical files.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentFormat, KbDocument, User
from app.panel.api.deps import require_admin_json
from app.panel.api.serializers import to_doc_dict
from app.panel.deps import get_db
from app.services import kb as kb_service

router = APIRouter(tags=["panel-api-kb"])

# Upload extension -> document format (same table as the Jinja route, KB-1).
FORMAT_BY_EXTENSION = {
    ".pdf": DocumentFormat.PDF,
    ".md": DocumentFormat.MD,
    ".txt": DocumentFormat.MD,
    ".csv": DocumentFormat.CSV,
}


class DocEditBody(BaseModel):
    title: str | None = None
    content: str


class DocRestoreBody(BaseModel):
    version: int


def _doc_or_404(session: Session, doc_id: int) -> KbDocument:
    doc = session.get(KbDocument, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="kb document not found")
    return doc


@router.get("/kb")
def kb_list(
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """Document list for the KB manager (provider/model/cost exposed, AP-6)."""
    docs = session.scalars(select(KbDocument).order_by(KbDocument.id.desc())).all()
    return {"docs": [to_doc_dict(doc) for doc in docs]}


@router.get("/kb/search")
def kb_search(
    q: str = Query(...),
    top_k: int = kb_service.DEFAULT_TOP_K,
    min_sim: float = kb_service.DEFAULT_MIN_SIM,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """Run the existing KB retrieval pipeline for panel evaluation."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="query must not be blank")

    results = kb_service.retrieve(session, q, top_k=top_k, min_sim=min_sim)
    document_ids = {result["document_id"] for result in results}
    titles = {}
    if document_ids:
        docs = session.scalars(
            select(KbDocument).where(KbDocument.id.in_(document_ids))
        ).all()
        titles = {doc.id: doc.title for doc in docs}

    return {
        "results": [
            {**result, "title": titles[result["document_id"]]}
            for result in results
        ]
    }


@router.get("/kb/{doc_id}")
def kb_detail(
    doc_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """Return one KB document, including its stored content."""
    doc = _doc_or_404(session, doc_id)
    return to_doc_dict(doc, include_content=True)


@router.post("/kb")
def kb_upload(
    title: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """Ingest a doc upload (PDW-API-1); 400 unsupported type/empty payload."""
    fmt = FORMAT_BY_EXTENSION.get(Path(file.filename or "").suffix.lower())
    if fmt is None:
        raise HTTPException(status_code=400, detail="unsupported file type (pdf/md/csv)")
    content = file.file.read()
    if not content.strip():
        raise HTTPException(status_code=400, detail="empty document")
    doc = kb_service.ingest_document(
        session, title, fmt, content, actor=current.username
    )
    session.commit()
    return {"ok": True, "doc": to_doc_dict(doc)}


@router.post("/kb/{doc_id}/edit")
def kb_edit(
    doc_id: int,
    body: DocEditBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """New version + re-embed (KB-4); prior version stays retrievable."""
    _doc_or_404(session, doc_id)
    doc = kb_service.update_document(
        session, doc_id, body.content, title=body.title, actor=current.username
    )
    session.commit()
    return {"ok": True, "doc": to_doc_dict(doc)}


@router.post("/kb/{doc_id}/disable")
def kb_disable(
    doc_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """Disable a doc (KB-3): excluded from retrieval, content kept."""
    _doc_or_404(session, doc_id)
    doc = kb_service.disable_document(session, doc_id, actor=current.username)
    session.commit()
    return {"ok": True, "doc": to_doc_dict(doc)}


@router.post("/kb/{doc_id}/restore")
def kb_restore(
    doc_id: int,
    body: DocRestoreBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """Restore a prior version: active_version pointer flip (D8, no re-embed)."""
    _doc_or_404(session, doc_id)
    try:
        doc = kb_service.restore_version(
            session, doc_id, body.version, actor=current.username
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    session.commit()
    return {"ok": True, "doc": to_doc_dict(doc)}
