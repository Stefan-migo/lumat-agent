"""Knowledge base pipeline (KB-1..KB-4; design "KB Pipeline").

Ingest (PDF/MD/CSV) -> RecursiveCharacterTextSplitter (500/50, CSV rows
grouped) -> local fastembed multilingual model (384d, ONNX Runtime, no API)
-> kb_chunks (version-tagged with source_meta). Retrieval = pgvector cosine
similarity, top_k=5, min_sim=0.65 (both configurable). Versioning per D8:
update = new version + re-embed; restore = active_version pointer flip
(chunks persist per version, no re-embed); disable = excluded from retrieval.

Embeddings are LOCAL (no API key, no token billing): fastembed TextEmbedding,
loaded once and cached. The `get_embedder()` seam is injectable — tests
monkeypatch it with a deterministic fake so the suite never downloads the
~130MB model.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from decimal import Decimal

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DocumentFormat, KbChunk, KbDocument
from app.services.audit import record_audit

EMBED_MODEL = get_settings().embed_model  # fastembed model id, multilingual, 384d
EMBED_DIMS = get_settings().embed_dims
EMBED_COST_PER_1M = Decimal("0")  # local embeddings: no token billing

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

DEFAULT_TOP_K = 5
DEFAULT_MIN_SIM = 0.65

PROVIDER = "local"


@dataclass
class RetrievedChunk:
    """One retrieval result (KB-2)."""

    document_id: int
    version: int
    chunk_index: int
    content: str
    source_meta: dict | None
    similarity: float


# ---------------------------------------------------------------------------
# Extraction + chunking (pure functions)
# ---------------------------------------------------------------------------


def extract_text(content: bytes, fmt: DocumentFormat) -> str:
    """Extract plain text from a PDF/MD/CSV payload (KB-1).

    CSV is row-grouped: each row becomes its own text block so the splitter
    keeps tariff rows intact (design: "CSV rows grouped per topic -> chunks").
    """
    if fmt == DocumentFormat.PDF:
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if fmt == DocumentFormat.CSV:
        return _csv_rows_to_text(content.decode("utf-8", errors="replace"))
    return content.decode("utf-8", errors="replace")


def _csv_rows_to_text(raw: str) -> str:
    """Group CSV rows: header + each data row as one 'field: value' block."""
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        return ""
    header = rows[0]
    blocks = []
    for row in rows[1:]:
        if not row or all(not cell.strip() for cell in row):
            continue
        pairs = []
        for i, cell in enumerate(row):
            name = header[i] if i < len(header) else f"col{i}"
            pairs.append(f"{name}: {cell.strip()}")
        blocks.append("\n".join(pairs))
    return "\n\n".join(blocks)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text with RecursiveCharacterTextSplitter (single H1 strategy).

    ponytail: chunk_size counts characters unless a tokenizer is injected —
    tiktoken adds a dependency; at 500 chars a Spanish chunk is well under a
    typical embedding context window. Upgrade path: pass
    `length_function=tiktoken_len` when exact token budget matters.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=overlap
    )
    return splitter.split_text(text)


# ---------------------------------------------------------------------------
# Embedding (local fastembed; injectable seam for tests)
# ---------------------------------------------------------------------------

_embedder = None


def get_embedder():
    """Return the shared fastembed TextEmbedding, loading it once (lazy).

    Injectable seam: tests monkeypatch this function with a deterministic fake
    embedder so the ~130MB model is never downloaded by the suite.
    """
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding

        _embedder = TextEmbedding(model_name=EMBED_MODEL)
    return _embedder


def embed_texts(texts: list[str]) -> tuple[list[list[float]], int]:
    """Embed a batch locally; returns (embeddings, prompt_tokens=0).

    Local inference has no token billing, so the second element is always 0
    (keeps the caller contract — `_embed_cost` and any cost bookkeeping —
    intact while recording 0 cost).
    """
    if not texts:
        return [], 0
    # fastembed yields numpy arrays; the test fake yields plain lists — accept both.
    embeddings = [v.tolist() if hasattr(v, "tolist") else list(v) for v in get_embedder().embed(texts)]
    return embeddings, 0


def _embed_cost(prompt_tokens: int) -> Decimal:
    return Decimal("0")  # local embeddings: no per-token cost


# ---------------------------------------------------------------------------
# Document lifecycle (KB-3, KB-4, D8)
# ---------------------------------------------------------------------------


def _store_chunks(
    session: Session,
    doc: KbDocument,
    version: int,
    source_meta: dict | None,
) -> None:
    """Chunk + embed + insert kb_chunks for one document version; records cost."""
    chunks = chunk_text(doc.content)
    embeddings, tokens = embed_texts(chunks)
    for index, (chunk_value, embedding) in enumerate(zip(chunks, embeddings)):
        session.add(
            KbChunk(
                document_id=doc.id,
                version=version,
                chunk_index=index,
                content=chunk_value,
                source_meta={**(source_meta or {}), "chunk_index": index},
                embedding=embedding,
            )
        )
    doc.provider = PROVIDER
    doc.model = EMBED_MODEL
    doc.cost_meta = float(_embed_cost(tokens))


def ingest_document(
    session: Session,
    title: str,
    fmt: DocumentFormat,
    content: bytes,
    source_meta: dict | None = None,
    actor: str = "system",
) -> KbDocument:
    """Create a document (version 1) and ingest its chunks (KB-1)."""
    doc = KbDocument(
        title=title,
        format=fmt,
        content=extract_text(content, fmt),
        version=1,
        active_version=1,
        active=True,
        provider=PROVIDER,
        model=EMBED_MODEL,
    )
    session.add(doc)
    session.flush()
    _store_chunks(session, doc, version=1, source_meta=source_meta)
    record_audit(
        session,
        actor=actor,
        action="kb.document_ingest",
        entity="kb_document",
        entity_id=str(doc.id),
        after={"title": title, "format": fmt.value, "version": 1},
    )
    return doc


def update_document(
    session: Session,
    doc_id: int,
    new_content: str,
    title: str | None = None,
    actor: str = "system",
) -> KbDocument:
    """Edit a document: new version + re-embed; prior version stays (KB-4)."""
    doc = session.get(KbDocument, doc_id)
    if doc is None:
        raise ValueError(f"kb document {doc_id} not found")
    new_version = doc.version + 1
    doc.content = new_content
    if title is not None:
        doc.title = title
    doc.version = new_version
    doc.active_version = new_version
    doc.active = True
    _store_chunks(session, doc, version=new_version, source_meta=None)
    record_audit(
        session,
        actor=actor,
        action="kb.document_update",
        entity="kb_document",
        entity_id=str(doc.id),
        before={"version": new_version - 1},
        after={"version": new_version, "title": doc.title},
    )
    return doc


def restore_version(
    session: Session, doc_id: int, version: int, actor: str = "system"
) -> KbDocument:
    """Restore a prior version: active_version pointer flip (D8, no re-embed)."""
    doc = session.get(KbDocument, doc_id)
    if doc is None:
        raise ValueError(f"kb document {doc_id} not found")
    if version < 1 or version > doc.version:
        raise ValueError(f"invalid version {version} for document {doc_id}")
    previous = doc.active_version
    doc.active_version = version
    doc.active = True
    record_audit(
        session,
        actor=actor,
        action="kb.document_restore",
        entity="kb_document",
        entity_id=str(doc.id),
        before={"active_version": previous},
        after={"active_version": version},
    )
    return doc


def disable_document(session: Session, doc_id: int, actor: str = "system") -> KbDocument:
    """Disable a document: excluded from retrieval, content kept (KB-3)."""
    doc = session.get(KbDocument, doc_id)
    if doc is None:
        raise ValueError(f"kb document {doc_id} not found")
    doc.active = False
    record_audit(
        session,
        actor=actor,
        action="kb.document_disable",
        entity="kb_document",
        entity_id=str(doc_id),
        after={"active": False},
    )
    return doc


# ---------------------------------------------------------------------------
# Retrieval (KB-2)
# ---------------------------------------------------------------------------


def retrieve(
    session: Session,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    min_sim: float = DEFAULT_MIN_SIM,
    scope: list[str] | None = None,
) -> list[dict]:
    """Semantic retrieval over the ACTIVE versions of enabled documents.

    Filters: kb_documents.active AND kb_chunks.version == active_version.
    Cosine similarity >= min_sim (pgvector <=> distance); ordered best-first.
    Below-threshold queries return [] -> the CM-4 "cannot answer reliably" path.

    ``scope`` (AO-7): when provided (e.g. a sub-agent's ``kb_scope``), only
    chunks whose ``source_meta.category`` (JSONB) is in the scope list are
    returned. ``scope=None`` returns the unfiltered active-version set —
    backward compatible with today's behavior.
    """
    query_embedding, _ = embed_texts([query])
    if not query_embedding:
        return []
    vec = query_embedding[0]
    distance = KbChunk.embedding.cosine_distance(vec)
    filters = [
        KbDocument.active.is_(True),
        KbChunk.version == KbDocument.active_version,
        distance <= 1 - min_sim,
    ]
    if scope is not None:
        if not scope:
            return []  # empty scope matches nothing by definition
        filters.append(KbChunk.source_meta["category"].astext.in_(scope))
    rows = session.execute(
        select(KbChunk, distance.label("distance"))
        .join(KbDocument, KbChunk.document_id == KbDocument.id)
        .where(*filters)
        .order_by(distance.asc())
        .limit(top_k)
    ).all()
    return [
        {
            "document_id": chunk.document_id,
            "version": chunk.version,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "source_meta": chunk.source_meta,
            "similarity": round(1 - float(dist), 4),
        }
        for chunk, dist in rows
    ]
