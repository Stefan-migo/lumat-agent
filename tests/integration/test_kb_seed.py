"""S3 (kb-drift): the seed keeps and repairs the routing metadata of `docs/kb`.

Why this file exists
--------------------
`kb.update_document` used to write the new version with `source_meta=None`. A
document seeded from `docs/kb` therefore lost `source_meta.source_id` the moment
it was re-versioned, and topic routing — which filters on exactly that key —
stopped seeing it. The measured symptom was the bot answering "No tengo ese
dato" to "puede ser este sabado?" with the document sitting right there.

These tests pin the seed side: re-versioning passes the metadata explicitly, the
report names a document that lost it, and `--force` repairs it in place instead
of paying a new embedding for identical text.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, DocumentFormat, KbChunk, KbDocument, KbVisibility  # noqa: E402
from app.services import kb  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import seed_kb_docs  # noqa: E402

ADMIN_DB_URL = admin_database_url()

TITLE = "Cobertura y horarios de Lumat"
SOURCE_ID = "lumat-cobertura-horarios"


@pytest.fixture
def fake_embedder(monkeypatch):
    """A counting fake embedder, so a repair can prove it re-embedded nothing.

    Shadows the autouse conftest fixture (which yields None) exactly as
    `tests/integration/test_kb.py` does; the autouse mount still guarantees the
    real model is never downloaded.
    """
    calls = {"count": 0}

    class _FakeEmbedder:
        def embed(self, texts):
            calls["count"] += 1
            return (_embed(text) for text in texts)

    monkeypatch.setattr(kb, "get_embedder", lambda: _FakeEmbedder())
    return calls


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset the KB tables before every test (shared test database)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE kb_chunks, kb_documents, audit_log RESTART IDENTITY CASCADE"
        )
    yield


def _local_document(text: str) -> seed_kb_docs.LocalDocument:
    return seed_kb_docs.LocalDocument(source_id=SOURCE_ID, title=TITLE, content=text)


def _embed(text: str) -> list[float]:
    """Deterministic one-hot embedding, same shape as `test_kb.py` uses."""
    digest = hashlib.sha256(text.encode()).digest()
    index = int.from_bytes(digest[:4], "big") % kb.EMBED_DIMS
    vector = [0.0] * kb.EMBED_DIMS
    vector[index] = 1.0
    return vector


def _chunks(doc_id: int, version: int | None = None) -> list[KbChunk]:
    with SessionLocal() as session:
        query = select(KbChunk).where(KbChunk.document_id == doc_id)
        if version is not None:
            query = query.where(KbChunk.version == version)
        return list(session.scalars(query.order_by(KbChunk.version, KbChunk.chunk_index)))


def _seed_document(text: str) -> int:
    """The document as `seed()` creates it: v1 with the routing metadata."""
    with SessionLocal() as session:
        doc = kb.ingest_document(
            session,
            title=TITLE,
            fmt=DocumentFormat.MD,
            content=text.encode(),
            source_meta={"source": "docs/kb", "source_id": SOURCE_ID},
            visibility=KbVisibility.CUSTOMER,
        )
        session.commit()
        return doc.id


def test_force_reversion_keeps_the_routing_metadata(fake_embedder):
    """Re-versioning drifted content must keep `source_id`, not just the text."""
    doc_id = _seed_document("Atendemos de lunes a viernes de 09:00 a 18:00.")
    document = _local_document("Atendemos de lunes a sabado de 09:00 a 18:00.")

    with SessionLocal() as session:
        seed_kb_docs.seed(session, [document], force=True)

    v2 = _chunks(doc_id, version=2)
    assert v2, "the drifted content must become a new version"
    for chunk in v2:
        assert (chunk.source_meta or {}).get("source_id") == SOURCE_ID


def test_report_names_a_document_that_lost_its_routing(fake_embedder):
    """The report must not call a document consistent while it has no routing."""
    doc_id = _seed_document("Atendemos de lunes a sabado de 09:00 a 18:00.")
    with SessionLocal() as session:
        kb.repair_source_meta(session, doc_id, source_meta={}, actor="test")
        session.commit()

    with SessionLocal() as session:
        report = seed_kb_docs.inspect_kb(
            session, [_local_document("Atendemos de lunes a sabado de 09:00 a 18:00.")]
        )

    assert report["consistent"] is True  # the content still matches
    assert report["unrouted"] == [SOURCE_ID]


def test_force_repairs_routing_in_place_without_reembedding(fake_embedder):
    """Identical content + missing routing is a metadata repair, not a new version."""
    doc_id = _seed_document("Atendemos de lunes a sabado de 09:00 a 18:00.")
    with SessionLocal() as session:
        kb.repair_source_meta(session, doc_id, source_meta={}, actor="test")
        session.commit()

    chunks_before = len(_chunks(doc_id))
    embeds_before = fake_embedder["count"]
    document = _local_document("Atendemos de lunes a sabado de 09:00 a 18:00.")

    with SessionLocal() as session:
        result = seed_kb_docs.seed(session, [document], force=True)

    assert result["repaired"] == [SOURCE_ID]
    assert fake_embedder["count"] == embeds_before  # no re-embed for identical text
    assert len(_chunks(doc_id)) == chunks_before  # no new chunks either
    with SessionLocal() as session:
        stored = session.get(KbDocument, doc_id)
        assert stored.version == 1
        assert stored.active_version == 1
        audit = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "kb.document_metadata")
            .order_by(AuditLog.id.desc())
        )
    assert audit is not None and audit.actor == "conv-eval"
    for chunk in _chunks(doc_id):
        assert (chunk.source_meta or {}).get("source_id") == SOURCE_ID


def test_without_force_nothing_is_repaired(fake_embedder):
    """`--force` is the explicit authorization for a metadata rewrite."""
    doc_id = _seed_document("Atendemos de lunes a sabado de 09:00 a 18:00.")
    with SessionLocal() as session:
        kb.repair_source_meta(session, doc_id, source_meta={}, actor="test")
        session.commit()

    document = _local_document("Atendemos de lunes a sabado de 09:00 a 18:00.")
    with SessionLocal() as session:
        result = seed_kb_docs.seed(session, [document], force=False)

    assert result["repaired"] == []
    for chunk in _chunks(doc_id):
        assert not (chunk.source_meta or {}).get("source_id")
