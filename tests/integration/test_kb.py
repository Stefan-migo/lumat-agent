"""T3.3 integration tests — KB ingestion + retrieval + versioning (KB-1..KB-4).

Scenarios mapped 1:1 from openspec/specs/knowledge-base/spec.md:

- KB-1 "Document ingested": PDF/MD/CSV chunked + embedded + stored with
  source metadata; provider/model/cost recorded and named
- KB-2 "Relevant retrieval": semantic search returns top chunks; "No relevant
  content": below the relevance threshold -> empty (drives CM-4 unresolved)
- KB-3 "Admin edits a document": update takes effect without redeploy
- KB-4 "Re-ingestion on update": new version + re-embed, prior version kept;
  "Restore previous version": active_version flip, no re-embed (D8)

Embeddings are LOCAL (fastembed, 384d): the test injects a deterministic fake
via the `fake_embedder` seam (kb.get_embedder monkeypatched), so the suite
never downloads the ~130MB model. The fake derives a deterministic 384-d
one-hot embedding per input text, so identical text -> cosine 1.0, unrelated
text -> 0.0: retrieval threshold behavior is fully exercised.
"""

import hashlib
import inspect
from pathlib import Path
from runpy import run_path
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import func, select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, DocumentFormat, KbChunk, KbDocument, KbVisibility, Project  # noqa: E402
from app.services import kb  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

fake_embedding = run_path(Path(__file__).with_name("conftest.py"))["fake_embedding"]

ADMIN_DB_URL = admin_database_url()


def _embed(text: str) -> list[float]:
    """Deterministic fake embedding: one-hot index from the text hash."""
    digest = hashlib.sha256(text.encode()).digest()
    index = int.from_bytes(digest[:4], "big") % kb.EMBED_DIMS
    vec = [0.0] * kb.EMBED_DIMS
    vec[index] = 1.0
    return vec


@pytest.fixture
def fake_embedder(monkeypatch):
    """Inject a deterministic 384-d embedder; counts `.embed` calls."""
    calls = {"count": 0}

    class _FakeEmbedder:
        def embed(self, texts):
            calls["count"] += 1
            return (_embed(t) for t in texts)

    monkeypatch.setattr(kb, "get_embedder", lambda: _FakeEmbedder())
    return calls


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


def test_delete_document_removes_document_and_chunks(fake_embedder):
    with SessionLocal() as session:
        doc = kb.ingest_document(
            session, "Delete me", DocumentFormat.MD,
            ("# Delete me\n" + "content " * 400).encode(),
        )
        session.commit()
        doc_id = doc.id
        assert _chunk_rows(doc_id)
        kb.delete_document(session, doc_id, actor="admin")
        session.commit()

    with SessionLocal() as session:
        assert session.get(KbDocument, doc_id) is None
        assert _chunk_rows(doc_id) == []


# ---------------------------------------------------------------------------
# KB-1 — ingestion: MD / PDF / CSV + provider/model/cost recorded
# ---------------------------------------------------------------------------


def test_kb1_ingest_markdown_chunks_stored(fake_embedder):
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
    assert all(len(c.embedding) == kb.EMBED_DIMS == 384 for c in chunks)
    # KB-1 "Provider and model named": recorded on the document
    assert stored.provider == "local"
    assert stored.model == kb.EMBED_MODEL
    assert stored.cost_meta is not None and stored.cost_meta == 0  # local: free


def test_kb5_ingest_defaults_to_internal(fake_embedder):
    with SessionLocal() as session:
        doc = kb.ingest_document(
            session, title="Internal manual", fmt=DocumentFormat.MD, content=b"internal"
        )
        session.commit()

    assert doc.visibility == KbVisibility.INTERNAL


def test_kb5_retrieve_defaults_to_customer_and_hides_internal(fake_embedder):
    query = "shared audience phrase"
    with SessionLocal() as session:
        internal_id = _ingest_with_visibility(
            session, "Internal", query, KbVisibility.INTERNAL
        )
        customer_id = _ingest_with_visibility(
            session, "Customer", query, KbVisibility.CUSTOMER
        )
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, query)

    assert [result["document_id"] for result in results] == [customer_id]
    assert internal_id not in {result["document_id"] for result in results}


def test_kb5_retrieve_audience_none_reads_whole_corpus(fake_embedder):
    query = "shared audience phrase"
    with SessionLocal() as session:
        internal_id = _ingest_with_visibility(
            session, "Internal", query, KbVisibility.INTERNAL
        )
        customer_id = _ingest_with_visibility(
            session, "Customer", query, KbVisibility.CUSTOMER
        )
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, query, audience=None)

    assert {result["document_id"] for result in results} == {internal_id, customer_id}


def _ingest_with_visibility(session, title, text, visibility):
    doc = kb.ingest_document(
        session,
        title=title,
        fmt=DocumentFormat.MD,
        content=text.encode(),
        visibility=visibility,
    )
    session.flush()
    return doc.id


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


def test_kb1_ingest_pdf_extracts_text(fake_embedder):
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


def test_kb1_ingest_csv_row_grouped(fake_embedder):
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


def test_kb1_chunk_count_for_long_document(fake_embedder):
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


def _project(session, slug: str) -> int:
    slug = f"{slug}-{uuid4().hex}"
    project = Project(
        slug=slug,
        name=slug,
        purpose="KB test project",
        purpose_embedding=[0.0] * kb.EMBED_DIMS,
    )
    session.add(project)
    session.flush()
    return project.id


def test_kb_retrieve_global_only_returns_global_documents(fake_embedder):
    query = "project scope retrieval"
    with SessionLocal() as session:
        project_id = _project(session, "kb-global-only")
        global_id = _ingest(session, "Global", query)
        project_doc = kb.ingest_document(
            session, title="Project", fmt=DocumentFormat.MD, content=query.encode(), project_id=project_id
        )
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, query, audience=None, global_only=True, project_id=project_id)

    assert {result["document_id"] for result in results} == {global_id}
    assert project_doc.id not in {result["document_id"] for result in results}


def test_kb_retrieve_project_includes_global_and_own_but_excludes_other_projects(fake_embedder):
    query = "project isolation retrieval"
    with SessionLocal() as session:
        project_a = _project(session, "kb-project-a")
        project_b = _project(session, "kb-project-b")
        global_id = _ingest(session, "Global", query)
        project_a_id = kb.ingest_document(
            session, title="Project A", fmt=DocumentFormat.MD, content=query.encode(), project_id=project_a
        ).id
        project_b_id = kb.ingest_document(
            session, title="Project B", fmt=DocumentFormat.MD, content=query.encode(), project_id=project_b
        ).id
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, query, audience=None, project_id=project_a)

    assert {result["document_id"] for result in results} == {global_id, project_a_id}
    assert project_b_id not in {result["document_id"] for result in results}


def test_kb_retrieve_default_project_filter_returns_all_documents(fake_embedder):
    query = "unfiltered project retrieval"
    with SessionLocal() as session:
        project_a = _project(session, "kb-default-a")
        project_b = _project(session, "kb-default-b")
        ids = {
            _ingest(session, "Global", query),
            kb.ingest_document(session, title="A", fmt=DocumentFormat.MD, content=query.encode(), project_id=project_a).id,
            kb.ingest_document(session, title="B", fmt=DocumentFormat.MD, content=query.encode(), project_id=project_b).id,
        }
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, query, audience=None)

    assert {result["document_id"] for result in results} == ids


def test_kb_retrieve_audience_filter_is_orthogonal_to_project_filter(fake_embedder):
    query = "audience and project"
    with SessionLocal() as session:
        project_id = _project(session, "kb-audience-project")
        matching_id = kb.ingest_document(
            session, title="Customer project", fmt=DocumentFormat.MD, content=query.encode(),
            visibility=KbVisibility.CUSTOMER, project_id=project_id,
        ).id
        internal_id = kb.ingest_document(
            session, title="Internal project", fmt=DocumentFormat.MD, content=query.encode(),
            visibility=KbVisibility.INTERNAL, project_id=project_id,
        ).id
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, query, project_id=project_id)

    assert {result["document_id"] for result in results} == {matching_id}
    assert internal_id not in {result["document_id"] for result in results}


def test_kb_ingest_project_binding_and_global_default(fake_embedder):
    with SessionLocal() as session:
        project_id = _project(session, "kb-ingest-project")
        bound = kb.ingest_document(
            session, title="Bound", fmt=DocumentFormat.MD, content=b"bound", project_id=project_id
        )
        global_doc = kb.ingest_document(
            session, title="Global", fmt=DocumentFormat.MD, content=b"global"
        )
        session.commit()

    assert bound.project_id == project_id
    assert global_doc.project_id is None


def test_kb_set_project_reclassifies_and_returns_document_to_global(fake_embedder):
    with SessionLocal() as session:
        project_id = _project(session, "kb-reclassify-project")
        doc_id = _ingest(session, "Global", "reclassify document")
        session.commit()

    with SessionLocal() as session:
        changed = kb.set_project(session, doc_id, project_id)
        session.commit()
    assert changed.project_id == project_id

    with SessionLocal() as session:
        changed = kb.set_project(session, doc_id, None)
        session.commit()
    assert changed.project_id is None


def test_kb2_retrieval_relevant_hit(fake_embedder):
    with SessionLocal() as session:
        _ingest(session, "Manual", "como enciendo mi calefont correctamente")
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(
            session, "como enciendo mi calefont correctamente", audience=None
        )

    assert len(results) == 1
    assert "como enciendo mi calefont correctamente" in results[0]["content"]
    assert results[0]["document_id"] is not None
    assert results[0]["similarity"] >= 0.99  # identical text -> cosine ~1


def test_kb2_retrieval_threshold_miss(fake_embedder):
    with SessionLocal() as session:
        _ingest(session, "Manual", "como enciendo mi calefont correctamente")
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, "que precio tiene un grifo de cocina", audience=None)

    assert results == []  # unrelated -> below min_sim 0.50 (CM-4 unresolved path)


def test_kb2_default_threshold_returns_intermediate_similarity_hit(monkeypatch):
    class _TrigramEmbedder:
        def embed(self, texts):
            return (fake_embedding(text) for text in texts)

    monkeypatch.setattr(kb, "get_embedder", lambda: _TrigramEmbedder())
    document_text = "manual calefont revision anual seguridad mantenimiento precio visita tecnica"
    query_text = "calefont seguridad"
    document_embedding = fake_embedding(document_text)
    query_embedding = fake_embedding(query_text)
    similarity = sum(
        left * right for left, right in zip(document_embedding, query_embedding)
    ) / (
        sum(value * value for value in document_embedding)
        * sum(value * value for value in query_embedding)
    ) ** 0.5
    assert 0.50 <= similarity < 0.65
    # The shorter query shares enough trigrams to score 0.5121, inside the old/new band.

    with SessionLocal() as session:
        document_id = _ingest(session, "Manual", document_text)
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(session, query_text, audience=None)

    assert [result["document_id"] for result in results] == [document_id]


def test_kb2_retrieval_top_k_limits_results(fake_embedder):
    with SessionLocal() as session:
        for i in range(8):
            _ingest(session, f"Doc{i}", f"marca de calefont modelo {i}")
        session.commit()

    with SessionLocal() as session:
        results = kb.retrieve(
            session, "marca de calefont modelo 3", top_k=5, audience=None
        )

    assert len(results) <= 5  # top_k respected even with 8 near-matches


def test_kb2_min_sim_configurable(fake_embedder):
    with SessionLocal() as session:
        _ingest(session, "Manual", "texto totalmente distinto sobre gasfiteria")
        session.commit()

    # strict default: unrelated query -> no hit
    with SessionLocal() as session:
        strict = kb.retrieve(session, "como enciendo mi calefont", audience=None)
    assert strict == []

    # relaxed threshold: everything matches
    with SessionLocal() as session:
        relaxed = kb.retrieve(
            session, "como enciendo mi calefont", min_sim=0.0, audience=None
        )
    assert len(relaxed) == 1


# ---------------------------------------------------------------------------
# KB-4 — versioning: update re-ingests, restore flips active_version (D8)
# ---------------------------------------------------------------------------


def test_kb4_update_creates_new_version_and_reembeds(fake_embedder):
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
        results = kb.retrieve(
            session, "revision anual 20000, nuevo valor", audience=None
        )
    assert len(results) == 1
    assert results[0]["version"] == 2


def test_kb4_restore_previous_version_flip_no_reembed(fake_embedder):
    with SessionLocal() as session:
        doc_id = _ingest(session, "Valores", "revision anual 15000")
        session.commit()
    with SessionLocal() as session:
        kb.update_document(session, doc_id, "revision anual 20000, nuevo valor")
        session.commit()

    # restore v1: pointer flip, no re-embed (D8 — embedder untouched)
    assert fake_embedder["count"] > 0
    calls_before = fake_embedder["count"]
    with SessionLocal() as session:
        kb.restore_version(session, doc_id, version=1)
        session.commit()
    assert fake_embedder["count"] == calls_before  # D8: no re-embed

    with SessionLocal() as session:
        stored = session.get(KbDocument, doc_id)
        assert stored.active_version == 1
        assert stored.version == 2  # document version history untouched
        results = kb.retrieve(session, "revision anual 15000", audience=None)
    assert len(results) == 1
    assert results[0]["version"] == 1


# ---------------------------------------------------------------------------
# Topic-scope retirement guard
# ---------------------------------------------------------------------------


def test_kb_retrieve_has_no_scope_parameter():
    assert "scope" not in inspect.signature(kb.retrieve).parameters


# ---------------------------------------------------------------------------
# KB-3 — disable: excluded from retrieval
# ---------------------------------------------------------------------------


def test_kb3_disable_document_excludes_from_retrieval(fake_embedder):
    with SessionLocal() as session:
        doc_id = _ingest(session, "Manual", "como enciendo mi calefont")
        session.commit()
    with SessionLocal() as session:
        kb.disable_document(session, doc_id)
        session.commit()

    with SessionLocal() as session:
        stored = session.get(KbDocument, doc_id)
        assert stored.active is False
        results = kb.retrieve(session, "como enciendo mi calefont", audience=None)
    assert results == []  # disabled documents never answer (KB-3)


def test_kb5_restore_never_widens(fake_embedder):
    with SessionLocal() as session:
        doc_id = _ingest_with_visibility(
            session, "Customer manual", "version one", KbVisibility.CUSTOMER
        )
        session.commit()
    with SessionLocal() as session:
        kb.update_document(session, doc_id, "version two")
        session.commit()

    chunks_before = len(_chunk_rows(doc_id))
    with SessionLocal() as session:
        kb.restore_version(session, doc_id, version=1)
        session.commit()

    with SessionLocal() as session:
        restored = session.get(KbDocument, doc_id)
    assert restored.visibility == KbVisibility.INTERNAL
    assert restored.active_version == 1
    assert len(_chunk_rows(doc_id)) == chunks_before


def test_kb5_set_visibility_does_not_create_version(fake_embedder):
    with SessionLocal() as session:
        doc_id = _ingest_with_visibility(
            session, "Internal manual", "internal content", KbVisibility.INTERNAL
        )
        session.commit()
    chunk_count = len(_chunk_rows(doc_id))

    with SessionLocal() as session:
        changed = kb.set_visibility(session, doc_id, KbVisibility.CUSTOMER)
        session.commit()

    with SessionLocal() as session:
        stored = session.get(KbDocument, doc_id)
        audit = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "kb.document_visibility")
            .order_by(AuditLog.id.desc())
        )
    assert changed.visibility == KbVisibility.CUSTOMER
    assert stored.version == 1
    assert len(_chunk_rows(doc_id)) == chunk_count
    assert audit is not None
    assert audit.action == "kb.document_visibility"


def test_kb5_invalid_visibility_rejected(fake_embedder):
    with SessionLocal() as session:
        with pytest.raises(ValueError):
            kb.ingest_document(
                session,
                title="Invalid",
                fmt=DocumentFormat.MD,
                content=b"invalid",
                visibility="public",
            )

        doc_id = _ingest_with_visibility(
            session, "Internal", "content", KbVisibility.INTERNAL
        )
        with pytest.raises(ValueError):
            kb.set_visibility(session, doc_id, "public")
