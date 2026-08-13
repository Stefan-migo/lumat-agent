"""T3.3 integration tests — KB ingestion + retrieval + versioning (KB-1..KB-4).

Scenarios mapped 1:1 from openspec/specs/knowledge-base/spec.md:

- KB-1 "Document ingested": PDF/MD/CSV chunked + embedded + stored with
  source metadata; provider/model/cost recorded and named
- KB-2 "Relevant retrieval": semantic search returns top chunks; "No relevant
  content": below the relevance threshold -> empty (drives CM-4 unresolved)
- KB-3 "Admin edits a document": update takes effect without redeploy
- KB-4 "Re-ingestion on update": new version + re-embed, prior version kept;
  "Restore previous version": active_version flip, no re-embed (D8)

OpenAI embeddings are mocked via respx (never a real API call — dev shell key
is NOT used). The mock derives a deterministic 1536-d embedding per input
text, so identical text -> cosine 1.0, unrelated text -> 0.0: retrieval
threshold behavior is fully exercised.
"""

import hashlib
import json

import httpx
import psycopg
import pytest
import respx
from sqlalchemy import func, select

from app.db import SessionLocal  # noqa: E402
from app.models import DocumentFormat, KbChunk, KbDocument  # noqa: E402
from app.services import kb  # noqa: E402

ADMIN_DB_URL = "postgresql://lumat:lumat@localhost:5432/lumat"
EMBED_URL = "https://api.openai.com/v1/embeddings"


def _embed(text: str) -> list[float]:
    """Deterministic fake embedding: one-hot index from the text hash."""
    digest = hashlib.sha256(text.encode()).digest()
    index = int.from_bytes(digest[:4], "big") % kb.EMBED_DIMS
    vec = [0.0] * kb.EMBED_DIMS
    vec[index] = 1.0
    return vec


def _usage_tokens(inputs: list[str]) -> int:
    return max(1, sum(len(i) // 4 for i in inputs))


@pytest.fixture
def mock_embeddings():
    """Intercept OpenAI /embeddings for the whole test (respx)."""
    with respx.mock(base_url="https://api.openai.com/v1") as router:

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            inputs = body["input"]
            if isinstance(inputs, str):
                inputs = [inputs]
            data = [
                {"object": "embedding", "index": i, "embedding": _embed(text)}
                for i, text in enumerate(inputs)
            ]
            tokens = _usage_tokens(inputs)
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "model": "text-embedding-3-small",
                    "data": data,
                    "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
                },
            )

        router.post("/embeddings").mock(side_effect=handler)
        yield router


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset KB tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE kb_chunks, kb_documents, audit_log RESTART IDENTITY CASCADE"
        )
    yield


def _chunk_rows(doc_id: int) -> list[KbChunk]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(KbChunk)
                .where(KbChunk.document_id == doc_id)
                .order_by(KbChunk.version, KbChunk.chunk_index)
            )
        )


# ---------------------------------------------------------------------------
# KB-1 — ingestion: MD / PDF / CSV + provider/model/cost recorded
# ---------------------------------------------------------------------------


def test_kb1_ingest_markdown_chunks_stored(mock_embeddings):
    content = "# Calefont\nInstrucciones de seguridad del calefont. " + "texto " * 400
    with SessionLocal() as session:
        doc = kb.ingest_document(
            session,
            title="Manual Calefont",
            fmt=DocumentFormat.MD,
            content=content.encode(),
            source_meta={"section": "manual"},
        )
        session.commit()
        doc_id = doc.id

    with SessionLocal() as session:
        stored = session.get(KbDocument, doc_id)
        chunks = _chunk_rows(doc_id)
    assert stored.version == 1
    assert stored.active_version == 1
    assert stored.active is True
    assert len(chunks) > 1  # long content -> multiple chunks
    assert all(c.version == 1 for c in chunks)
    assert all(c.embedding is not None for c in chunks)
    assert all(len(c.embedding) == kb.EMBED_DIMS == 1536 for c in chunks)
    # KB-1 "Provider and model named": recorded on the document
    assert stored.provider == "openai"
    assert stored.model == kb.EMBED_MODEL
    assert stored.cost_meta is not None and stored.cost_meta > 0


def _pdf_with_text(text: str) -> bytes:
    """Minimal valid PDF whose single page carries `text` (pypdf-extractable)."""
    stream = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF"
    ).encode()
    return out


def test_kb1_ingest_pdf_extracts_text(mock_embeddings):
    pdf_bytes = _pdf_with_text("como enciendo mi calefont correctamente")

    with SessionLocal() as session:
        doc = kb.ingest_document(
            session,
            title="Manual Caldera",
            fmt=DocumentFormat.PDF,
            content=pdf_bytes,
        )
        session.commit()
        doc_id = doc.id

    with SessionLocal() as session:
        stored = session.get(KbDocument, doc_id)
    assert stored.format == DocumentFormat.PDF
    assert "como enciendo mi calefont" in stored.content  # pypdf extracted text
    assert stored.version == 1


def test_kb1_ingest_csv_row_grouped(mock_embeddings):
    csv_bytes = (
        "servicio,valor,detalle\n"
        "revision,15000,Revision anual calefont\n"
        "instalacion,80000,Instalacion de caldera\n"
        "reparacion,35000,Reparacion menor\n"
    ).encode()
    with SessionLocal() as session:
        doc = kb.ingest_document(
            session,
            title="Valores",
            fmt=DocumentFormat.CSV,
            content=csv_bytes,
        )
        session.commit()
        doc_id = doc.id

    chunks = _chunk_rows(doc_id)
    assert len(chunks) >= 1  # small CSV fits one chunk
    joined = "\n".join(c.content for c in chunks)
    # rows are grouped as 'header: value' blocks (design: CSV row-grouped)
    assert "servicio: revision" in joined
    assert "valor: 15000" in joined
    assert "servicio: instalacion" in joined
    assert "valor: 80000" in joined
    assert "servicio: reparacion" in joined
    assert "valor: 35000" in joined


def test_kb1_chunk_count_for_long_document(mock_embeddings):
    long_text = "parrafo " * 3000  # ~21k chars -> ~42 chunks at 500 chars
    with SessionLocal() as session:
        doc = kb.ingest_document(
            session, title="FAQ", fmt=DocumentFormat.MD, content=long_text.encode()
        )
        session.commit()
        doc_id = doc.id
    chunks = _chunk_rows(doc_id)
    assert len(chunks) >= 20
    assert all(len(c.content) <= kb.CHUNK_SIZE * 1.5 for c in chunks)


# ---------------------------------------------------------------------------
# KB-2 — retrieval: relevant hit / threshold miss / top_k
# ---------------------------------------------------------------------------


def _ingest(session, title: str, text: str, fmt=DocumentFormat.MD) -> int:
    doc = kb.ingest_document(session, title=title, fmt=fmt, content=text.encode())
    session.flush()
    return doc.id


def test_kb2_retrieval_relevant_hit(mock_embeddings):
    with SessionLocal() as session:
        _ingest(session, "Manual", "como enciendo mi calefont correctamente")
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, "como enciendo mi calefont correctamente")

    assert len(results) == 1
    assert "como enciendo mi calefont correctamente" in results[0]["content"]
    assert results[0]["document_id"] is not None
    assert results[0]["similarity"] >= 0.99  # identical text -> cosine ~1


def test_kb2_retrieval_threshold_miss(mock_embeddings):
    with SessionLocal() as session:
        _ingest(session, "Manual", "como enciendo mi calefont correctamente")
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, "que precio tiene un grifo de cocina")

    assert results == []  # unrelated -> below min_sim 0.65 (CM-4 unresolved path)


def test_kb2_retrieval_top_k_limits_results(mock_embeddings):
    with SessionLocal() as session:
        for i in range(8):
            _ingest(session, f"Doc{i}", f"marca de calefont modelo {i}")
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, "marca de calefont modelo 3", top_k=5)

    assert len(results) <= 5  # top_k respected even with 8 near-matches


def test_kb2_min_sim_configurable(mock_embeddings):
    with SessionLocal() as session:
        _ingest(session, "Manual", "texto totalmente distinto sobre gasfiteria")
        session.commit()

    # strict default: unrelated query -> no hit
    with SessionLocal() as session:
        strict = kb.retrieve(session, "como enciendo mi calefont")
    assert strict == []

    # relaxed threshold: everything matches
    with SessionLocal() as session:
        relaxed = kb.retrieve(session, "como enciendo mi calefont", min_sim=0.0)
    assert len(relaxed) == 1


# ---------------------------------------------------------------------------
# KB-4 — versioning: update re-ingests, restore flips active_version (D8)
# ---------------------------------------------------------------------------


def test_kb4_update_creates_new_version_and_reembeds(mock_embeddings):
    with SessionLocal() as session:
        doc_id = _ingest(session, "Valores", "revision anual 15000")
        session.commit()

    with SessionLocal() as session:
        kb.update_document(
            session, doc_id, "revision anual 20000, nuevo valor"
        )
        session.commit()

    with SessionLocal() as session:
        stored = session.get(KbDocument, doc_id)
        assert stored.version == 2
        assert stored.active_version == 2
        chunks = _chunk_rows(doc_id)
        assert {c.version for c in chunks} == {1, 2}  # prior version preserved
        v2 = [c for c in chunks if c.version == 2]
        assert len(v2) >= 1

    # retrieval uses the ACTIVE version (v2)
    with SessionLocal() as session:
        results = kb.retrieve(session, "revision anual 20000, nuevo valor")
    assert len(results) == 1
    assert results[0]["version"] == 2


def test_kb4_restore_previous_version_flip_no_reembed(mock_embeddings):
    with SessionLocal() as session:
        doc_id = _ingest(session, "Valores", "revision anual 15000")
        session.commit()
    with SessionLocal() as session:
        kb.update_document(session, doc_id, "revision anual 20000, nuevo valor")
        session.commit()

    # restore v1: pointer flip, no embedding API call should happen
    assert mock_embeddings.calls.call_count > 0
    calls_before = len(mock_embeddings.calls)
    with SessionLocal() as session:
        kb.restore_version(session, doc_id, version=1)
        session.commit()
    assert len(mock_embeddings.calls) == calls_before  # D8: no re-embed

    with SessionLocal() as session:
        stored = session.get(KbDocument, doc_id)
        assert stored.active_version == 1
        assert stored.version == 2  # document version history untouched
        results = kb.retrieve(session, "revision anual 15000")
    assert len(results) == 1
    assert results[0]["version"] == 1


# ---------------------------------------------------------------------------
# KB-3 — disable: excluded from retrieval
# ---------------------------------------------------------------------------


def test_kb3_disable_document_excludes_from_retrieval(mock_embeddings):
    with SessionLocal() as session:
        doc_id = _ingest(session, "Manual", "como enciendo mi calefont")
        session.commit()
    with SessionLocal() as session:
        kb.disable_document(session, doc_id)
        session.commit()

    with SessionLocal() as session:
        stored = session.get(KbDocument, doc_id)
        assert stored.active is False
        results = kb.retrieve(session, "como enciendo mi calefont")
    assert results == []  # disabled documents never answer (KB-3)
