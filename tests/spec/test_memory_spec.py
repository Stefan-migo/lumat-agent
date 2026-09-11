"""OpenSpec scenario tests — MEM-1 (Schema and Migration), MEM-2 (Service CRUD),
MEM-3 (Hybrid Search). Marks: spec (see pyproject [tool.pytest.ini_options]).

The spec tests drive the memory layer directly through the service API
(`app.services.memory`) against the migrated pgvector test DB with the fake
embedder. Companion integration coverage lives in the S2..S4 suites (context
injection, close memo, panel).
"""

import psycopg
import pytest
from sqlalchemy import inspect

from app.db import SessionLocal
from app.models import Memory, MemoryType
from app.services import memory, tukulpan  # noqa: F401  (services under test)

pytestmark = pytest.mark.spec("MEM-1 MEM-2 MEM-3")


# ---------------------------------------------------------------------------
# MEM-1 — Schema and Migration
# ---------------------------------------------------------------------------


def _table_names(admin_conn) -> set[str]:
    rows = admin_conn.execute(
        """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        """
    ).fetchall()
    return {r[0] for r in rows}


def test_mem1_migration_creates_memory_tables(migrated_db, admin_conn):
    """Migration 009 MUST create memories, memory_relations, memory_observations.

    Scenario: Migration applies (MEM-1).
    """
    tables = _table_names(admin_conn)
    assert {"memories", "memory_relations", "memory_observations"} <= tables


def test_mem1_hnsw_embedding_index(migrated_db, admin_conn):
    """memories.embedding indexed with HNSW vector_cosine_ops (MEM-1)."""
    row = admin_conn.execute(
        """
        SELECT indexdef FROM pg_indexes
        WHERE tablename = 'memories' AND indexname = 'idx_memories_embedding_hnsw'
        """
    ).fetchone()
    assert row is not None, "HNSW index missing on memories.embedding"
    indexdef = row[0]
    assert "USING hnsw" in indexdef
    assert "vector_cosine_ops" in indexdef


def test_mem1_memories_unique_key(migrated_db, admin_conn):
    """memories MUST enforce UNIQUE(proyecto, scope, entity_id, topic_key).

    Two upserts with identical (proyecto, scope, entity_id) but distinct
    topic_key MUST both persist (scenario: Topic-key uniqueness).
    """
    admin_conn.execute(
        "INSERT INTO memories (scope, entity_id, topic_key, titulo, contenido, embedding) "
        "VALUES ('customer', '42', 'a', 't1', 'c1', %s::vector)",
        ("[" + ",".join(["0.1"] * 384) + "]",),
    )
    admin_conn.execute(
        "INSERT INTO memories (scope, entity_id, topic_key, titulo, contenido, embedding) "
        "VALUES ('customer', '42', 'b', 't2', 'c2', %s::vector)",
        ("[" + ",".join(["0.1"] * 384) + "]",),
    )
    rows = admin_conn.execute(
        "SELECT topic_key FROM memories WHERE scope='customer' AND entity_id='42' "
        "ORDER BY topic_key"
    ).fetchall()
    assert rows == [("a",), ("b",)], "distinct topic_key must not collide"

    # Duplicate (project, scope, entity, topic_key) MUST be rejected.
    with pytest.raises(psycopg.errors.UniqueViolation):
        admin_conn.execute(
            "INSERT INTO memories (scope, entity_id, topic_key, titulo, contenido, embedding) "
            "VALUES ('customer', '42', 'a', 't1', 'c1', %s::vector)",
            ("[" + ",".join(["0.1"] * 384) + "]",),
        )


def test_mem1_orm_models_reflect_schema(migrated_db):
    """ORM models map the migrated memory tables (labels match exactly)."""
    with SessionLocal() as session:
        inspector = inspect(session.bind)
        tables = set(inspector.get_table_names())
    assert {"memories", "memory_relations", "memory_observations"} <= tables
    assert Memory.__tablename__ == "memories"


# ---------------------------------------------------------------------------
# MEM-2 — Memory Service CRUD
# ---------------------------------------------------------------------------


def test_mem2_canonical_and_legacy_services_are_identical():
    """The legacy module forwards the canonical Tukulpan service objects."""
    assert memory.upsert is tukulpan.upsert
    assert memory.get_by_key is tukulpan.get_by_key
    assert memory.list_for_entity is tukulpan.list_for_entity
    assert memory.delete is tukulpan.delete
    assert memory.set_mark is tukulpan.set_mark


def test_mem2_canonical_upsert_and_project_guard(fake_embedder, migrated_db):
    """Canonical CRUD writes default rows and rejects other projects."""
    with SessionLocal() as session:
        row = tukulpan.upsert(
            session,
            scope="panel",
            entity_id="thread:7",
            topic_key="milestone",
            tipo=MemoryType.SUMMARY,
            titulo="Milestone",
            contenido="The panel turn reached a milestone.",
        )
        session.commit()

        assert row.proyecto == "default"
        assert tukulpan.get_by_key(
            session,
            scope="panel",
            entity_id="thread:7",
            topic_key="milestone",
        ).id == row.id

        with pytest.raises(ValueError, match="default"):
            tukulpan.upsert(
                session,
                proyecto="other",
                scope="panel",
                entity_id="thread:7",
                topic_key="blocked",
                tipo=MemoryType.DECISION,
                titulo="Blocked",
                contenido="Must not persist.",
            )
        session.rollback()
        assert session.query(Memory).filter_by(topic_key="blocked").count() == 0


def test_mem2_upsert_writes_memory(fake_embedder, migrated_db):
    """Upsert stores content with a 384-dim embedding and no duplicates.

    Scenario: Upsert writes memory (MEM-2).
    """
    with SessionLocal() as session:
        m = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="prefs",
            tipo=MemoryType.PREFERENCE,
            titulo="Prefiere horario tarde",
            contenido="Cliente prefiere atencion en la tarde.",
        )
        session.commit()
        memory_id = m.id

        # re-upsert same key with new content -> single row, content updated
        m2 = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="prefs",
            tipo=MemoryType.PREFERENCE,
            titulo="Prefiere horario tarde",
            contenido="Cliente prefiere atencion por la tarde, despues de 15hs.",
        )
        session.commit()
        assert m2.id == memory_id, "upsert must reuse the same row (unique key)"
        assert len(m2.embedding) == 384
        fetched = memory.get_by_key(
            session, scope="customer", entity_id="42", topic_key="prefs"
        )
        assert fetched.contenido == (
            "Cliente prefiere atencion por la tarde, despues de 15hs."
        )


def test_mem2_get_list_delete_mark(fake_embedder, migrated_db):
    """get_by_key, list_for_entity, delete, set_mark behave per MEM-2."""
    with SessionLocal() as session:
        a = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="k1",
            tipo=MemoryType.DISCOVERY,
            titulo="Titulo 1",
            contenido="Contenido uno.",
        )
        b = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="k2",
            tipo=MemoryType.PATTERN,
            titulo="Titulo 2",
            contenido="Contenido dos.",
        )
        session.commit()

        ids = {r.id for r in memory.list_for_entity(
            session, scope="customer", entity_id="42"
        )}
        assert ids == {a.id, b.id}

        # list scoped to entity_id -> other entity's memories invisible
        other = memory.upsert(
            session,
            scope="customer",
            entity_id="99",
            topic_key="k_x",
            tipo=MemoryType.PATTERN,
            titulo="Otro",
            contenido="Otra entidad.",
        )
        session.commit()
        ids42 = {r.id for r in memory.list_for_entity(
            session, scope="customer", entity_id="42"
        )}
        assert ids42 == {a.id, b.id} and other.id not in ids42

        # set_mark: pin + status
        memory.set_mark(session, a.id, pin=True)
        session.commit()
        assert memory.get_by_key(
            session, scope="customer", entity_id="42", topic_key="k1"
        ).pin is True

        # delete removes only the target row
        memory.delete(session, b.id)
        session.commit()
        remaining = {r.id for r in memory.list_for_entity(
            session, scope="customer", entity_id="42"
        )}
        assert remaining == {a.id}


def test_mem2_non_default_project_rejected(fake_embedder, migrated_db):
    """Writes targeting proyecto != 'default' MUST be rejected (MEM-2).

    Scenario: Non-default project rejected.
    """
    from sqlalchemy import func, select

    with SessionLocal() as session:
        with pytest.raises(ValueError):
            memory.upsert(
                session,
                proyecto="cross-project",
                scope="customer",
                entity_id="42",
                topic_key="k",
                tipo=MemoryType.DECISION,
                titulo="t",
                contenido="c",
            )
        session.rollback()
        # nothing persisted, of any proyecto
        n = session.execute(select(func.count()).select_from(Memory)).scalar_one()
        assert n == 0


def test_mem7_milestone_and_decision_use_meaningful_types(fake_embedder, migrated_db):
    with SessionLocal() as session:
        milestone = tukulpan.record_milestone(
            session, thread_id=7, topic_key="milestone:1", title="Milestone", content="Reached review"
        )
        decision = tukulpan.record_decision(
            session, thread_id=7, topic_key="decision:1", title="Decision", content="Keep DB authoritative"
        )
        session.commit()

        assert milestone.tipo is MemoryType.SUMMARY
        assert decision.tipo is MemoryType.DECISION
        assert {milestone.entity_id, decision.entity_id} == {"thread:7"}


def test_mem7_recap_has_bounded_schema_and_idempotent_key(fake_embedder, migrated_db):
    with SessionLocal() as session:
        first = tukulpan.write_recap(
            session, thread_id=7, source_message_ids=[4, 5], recap="A bounded recap",
            source_tokens=1_999, truncated=True,
        )
        session.commit()
        second = tukulpan.write_recap(
            session, thread_id=7, source_message_ids=[4, 5], recap="A bounded recap",
            source_tokens=1_999, truncated=True,
        )
        session.commit()

        row = tukulpan.get_by_key(
            session, scope="panel", entity_id="thread:7", topic_key="assistant-recap:7:5"
        )
        payload = __import__("json").loads(row.contenido)
        assert set(payload) == {"schema_version", "thread_id", "source_message_ids", "source_tokens", "truncated", "recap"}
        assert payload["source_message_ids"] == [4, 5]
        assert first["written"] is True and second["id"] == first["id"]
        assert session.query(Memory).filter_by(topic_key="assistant-recap:7:5").count() == 1


def test_mem7_recap_failure_returns_degraded_evidence_and_keeps_session_usable(monkeypatch, migrated_db):
    monkeypatch.setattr(tukulpan, "_embed", lambda texts: (_ for _ in ()).throw(RuntimeError("embed offline")))
    with SessionLocal() as session:
        result = tukulpan.write_recap(
            session, thread_id=7, source_message_ids=[5], recap="Retry me",
            source_tokens=2, truncated=False,
        )
        assert result["written"] is False
        assert "embed offline" in result["degraded_reason"]
        session.execute(__import__("sqlalchemy").text("SELECT 1"))


# ---------------------------------------------------------------------------
# MEM-3 — Hybrid Search
# ---------------------------------------------------------------------------


def test_mem3_threshold_recall_and_order(fake_embedder, migrated_db):
    """Only memories above the fused threshold return, ranked desc.

    Scenario: Threshold recall (MEM-3). Triangulates ranking: the closest
    memory scores above the weaker-but-still-close one, and the unrelated one
    (below threshold) is excluded.
    """
    with SessionLocal() as session:
        # two close memories + one clearly unrelated
        for key, contenido in (
            ("close1", "Cliente reporta ruido en la caldera al encender"),
            ("close2", "Problema de ruido con la caldera cuando enciende"),
            ("unrelated", "Instalacion de gases y certificacion en la comuna"),
        ):
            memory.upsert(
                session,
                scope="customer",
                entity_id="42",
                topic_key=key,
                tipo=MemoryType.DISCOVERY,
                titulo=key,
                contenido=contenido,
            )
        session.commit()

        results = memory.hybrid_search(
            session,
            "ruido en la caldera al encender",
            scope="customer",
            entity_id="42",
        )
        topics = [r["topic_key"] for r in results]
        # unrelated below threshold must never appear
        assert "unrelated" not in topics
        # both close memories present and ranked by fused score (close1 first)
        assert topics[0] == "close1", f"expected close1 first, got {topics}"


def test_mem3_role_isolation(fake_embedder, migrated_db):
    """Search returns only the given scope/entity's memories (MEM-3).

    Scenario: Role isolation.
    """
    with SessionLocal() as session:
        memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="k42",
            tipo=MemoryType.PATTERN,
            titulo="A",
            contenido="El cliente corrobora el mismo detalle tecnico aqui",
        )
        memory.upsert(
            session,
            scope="customer",
            entity_id="99",
            topic_key="k99",
            tipo=MemoryType.PATTERN,
            titulo="B",
            contenido="El cliente corrobora el mismo detalle tecnico aqui",
        )
        session.commit()

        results = memory.hybrid_search(
            session,
            "corrobora el mismo detalle tecnico aqui",
            scope="customer",
            entity_id="42",
        )
        # never the other entity's memory
        assert all(r["entity_id"] == "42" for r in results)
        assert any(r["topic_key"] == "k42" for r in results)


def test_mem3_panel_and_whatsapp_entities_are_isolated(fake_embedder, migrated_db):
    """Panel thread and WhatsApp customer scopes never cross-read (MEM-3)."""
    with SessionLocal() as session:
        memory.upsert(
            session, scope="panel", entity_id="thread:42", topic_key="panel-note",
            tipo=MemoryType.PATTERN, titulo="Panel", contenido="shared technical detail",
        )
        memory.upsert(
            session, scope="customer", entity_id="customer:42", topic_key="wa-note",
            tipo=MemoryType.PATTERN, titulo="WhatsApp", contenido="shared technical detail",
        )
        session.commit()

        panel = memory.hybrid_search(
            session, "shared technical detail", scope="panel", entity_id="thread:42"
        )
        whatsapp = memory.hybrid_search(
            session, "shared technical detail", scope="customer", entity_id="customer:42"
        )

        assert [row["topic_key"] for row in panel] == ["panel-note"]
        assert [row["topic_key"] for row in whatsapp] == ["wa-note"]


def test_mem3_empty_result_no_fallback(fake_embedder, migrated_db):
    """No memory above threshold -> empty set, no out-of-scope fallback.

    Scenario: Empty result (MEM-3).
    """
    with SessionLocal() as session:
        memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="only",
            tipo=MemoryType.PATTERN,
            titulo="Solo",
            contenido="Un contenido completamente distinto y ajeno",
        )
        session.commit()

        results = memory.hybrid_search(
            session,
            "un texto que no comparte trigramas con nada guardado aqui",
            scope="customer",
            entity_id="42",
        )
        assert results == []


def test_mem3_top_k_caps_results(fake_embedder, migrated_db):
    """hybrid_search caps results at top_k (default 5)."""
    with SessionLocal() as session:
        for i in range(8):
            memory.upsert(
                session,
                scope="customer",
                entity_id="42",
                topic_key=f"t{i}",
                tipo=MemoryType.PATTERN,
                titulo=f"T{i}",
                contenido=f"misma base de contenido tecnico numero {i}",
            )
        session.commit()

        results = memory.hybrid_search(
            session,
            "misma base de contenido tecnico",
            scope="customer",
            entity_id="42",
        )
        assert len(results) <= 5
