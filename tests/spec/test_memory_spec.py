"""OpenSpec scenario tests — MEM-1 (Schema and Migration), MEM-2 (Service CRUD),
MEM-3 (Hybrid Search). Marks: spec (see pyproject [tool.pytest.ini_options]).

The spec tests drive the memory layer directly through the service API
(`app.services.memory`) against the migrated pgvector test DB with the fake
embedder. Companion integration coverage lives in the S2..S4 suites (context
injection, close memo, panel).
"""

from pathlib import Path

import psycopg
import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from sqlalchemy import inspect

from app.db import SessionLocal
from app.models import (
    Memory,
    MemoryObservation,
    MemoryProducer,
    MemoryType,
    MemoryVisibility,
    ObservationType,
    User,
)
from app.services import memory, tukulpan  # noqa: F401  (services under test)

pytestmark = pytest.mark.spec("MEM-1 MEM-2 MEM-3 MEM-9 MEM-10 MEM-12 MEM-13")


# ---------------------------------------------------------------------------
# MEM-10 — Lifecycle Decay
# ---------------------------------------------------------------------------


def test_mem10_write_policy_stamps_only_decaying_types(fake_embedder, migrated_db):
    with SessionLocal() as session:
        rows = {}
        for tipo in MemoryType:
            rows[tipo] = tukulpan.upsert(
                session,
                scope="customer",
                entity_id="decay-policy",
                topic_key=f"{tipo.value}-policy",
                tipo=tipo,
                titulo=tipo.value,
                contenido=f"Content for {tipo.value}",
            )
        session.commit()

        for tipo, row in rows.items():
            if tipo in {MemoryType.SUMMARY, MemoryType.SESSION, MemoryType.DISCOVERY}:
                assert row.review_after is not None
                assert timedelta(days=29, hours=23) < row.review_after - datetime.now(timezone.utc) < timedelta(days=30, minutes=1)
            else:
                assert row.review_after is None

        summary = rows[MemoryType.SUMMARY]
        summary.review_after = datetime.now(timezone.utc) - timedelta(days=1)
        session.flush()
        rewritten = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="decay-policy",
            topic_key="summary-policy",
            tipo=MemoryType.SUMMARY,
            titulo="summary",
            contenido="Refreshed summary",
        )
        session.commit()
        assert rewritten.review_after > datetime.now(timezone.utc)

        fold_source = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="decay-policy-fold",
            topic_key="source",
            tipo=MemoryType.SUMMARY,
            titulo="source",
            contenido="folded content",
        )
        fold_source.review_after = datetime.now(timezone.utc) - timedelta(days=1)
        session.commit()
        folded = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="decay-policy-fold",
            topic_key="duplicate",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="duplicate",
            contenido=" FOLDED   CONTENT ",
        )
        session.commit()
        assert folded.tipo is MemoryType.SUMMARY
        assert folded.review_after > datetime.now(timezone.utc)

        permanent = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="decay-policy-permanent",
            topic_key="source",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="source",
            contenido="permanent content",
        )
        folded_permanent = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="decay-policy-permanent",
            topic_key="duplicate",
            tipo=MemoryType.SUMMARY,
            titulo="duplicate",
            contenido="PERMANENT CONTENT",
        )
        session.commit()
        assert folded_permanent.id == permanent.id
        assert folded_permanent.review_after is None


def test_mem10_hybrid_search_reports_staleness_without_reordering(fake_embedder, migrated_db):
    with SessionLocal() as session:
        stale = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="decay-read",
            topic_key="stale",
            tipo=MemoryType.SUMMARY,
            titulo="stale",
            contenido="memory stale entry",
        )
        fresh = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="decay-read",
            topic_key="fresh",
            tipo=MemoryType.SUMMARY,
            titulo="fresh",
            contenido="memory fresh entry",
        )
        never = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="decay-read",
            topic_key="never",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="never",
            contenido="memory permanent entry",
        )
        session.commit()
        stale.review_after = datetime.now(timezone.utc) - timedelta(days=1)
        fresh.review_after = datetime.now(timezone.utc) + timedelta(days=1)
        session.commit()

        before = tukulpan.hybrid_search(
            session, "memory entry", scope="customer", entity_id="decay-read", min_sim=0
        )
        after = tukulpan.hybrid_search(
            session, "memory entry", scope="customer", entity_id="decay-read", min_sim=0
        )

        assert [row["topic_key"] for row in after] == [row["topic_key"] for row in before]
        assert {row["topic_key"]: row["stale"] for row in after} == {
            "stale": True,
            "fresh": False,
            "never": False,
        }



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


def test_mem2_identical_normalized_content_deduplicates_by_hash(fake_embedder, migrated_db):
    with SessionLocal() as session:
        first = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="first",
            tipo=MemoryType.DECISION,
            titulo="Fact",
            contenido="The customer prefers afternoon visits.",
        )
        second = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="second",
            tipo=MemoryType.DECISION,
            titulo="Repeated fact",
            contenido="  THE customer   prefers afternoon visits. ",
        )
        session.commit()

        assert second.id == first.id
        assert second.duplicate_count == 2
        assert session.query(Memory).filter_by(entity_id="42").count() == 1


def test_mem2_distinct_content_and_identity_stays_distinct(fake_embedder, migrated_db):
    with SessionLocal() as session:
        for scope, entity_id, proyecto, topic_key, content in (
            ("customer", "42", "default", "same-content", "Shared fact"),
            ("customer", "42", "default", "different-content", "Different fact"),
            ("other", "42", "default", "other-scope", "Shared fact"),
            ("customer", "99", "default", "other-entity", "Shared fact"),
        ):
            memory.upsert(
                session,
                scope=scope,
                entity_id=entity_id,
                proyecto=proyecto,
                topic_key=topic_key,
                tipo=MemoryType.DECISION,
                titulo=topic_key,
                contenido=content,
            )
        session.commit()

        assert session.query(Memory).count() == 4


def test_mem2_same_key_rewrite_is_not_a_duplicate(fake_embedder, migrated_db):
    with SessionLocal() as session:
        row = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="fact",
            tipo=MemoryType.DECISION,
            titulo="Fact",
            contenido="Original fact",
        )
        session.commit()

        rewritten = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="fact",
            tipo=MemoryType.DECISION,
            titulo="Rewritten fact",
            contenido="Updated fact",
        )
        session.commit()

        assert rewritten.id == row.id
        assert rewritten.contenido == "Updated fact"
        assert rewritten.duplicate_count == 1


def test_memory_owner_namespace_isolated_for_writes_and_reads(fake_embedder, migrated_db):
    from app.services.projects import _ProjectAuthorization

    with SessionLocal() as session:
        owners = [User(username=f"memory-owner-{uuid4().hex}", password_hash="test") for _ in range(2)]
        session.add_all(owners)
        session.flush()
        rows = [tukulpan.upsert(
            session, authorization=_ProjectAuthorization(slug="casa", owner_id=owner.id), proyecto="casa", scope="agent",
            entity_id="agent:casa", topic_key="fact", tipo=MemoryType.DECISION,
            titulo="Fact", contenido="Private fact", visibility=MemoryVisibility.GLOBAL,
        ) for owner in owners]
        shared = tukulpan.upsert(
            session, authorization=_ProjectAuthorization(slug="casa"), proyecto="casa", scope="agent", entity_id="agent:casa",
            topic_key="business", tipo=MemoryType.DECISION, titulo="Business",
            contenido="Business shared fact", visibility=MemoryVisibility.GLOBAL,
        )
        session.commit()

        assert rows[0].id != rows[1].id
        assert tukulpan.get_by_key(
            session, owner_id=owners[0].id, proyecto="casa", scope="agent",
            entity_id="agent:casa", topic_key="fact",
        ).id == rows[0].id
        assert tukulpan.get_by_key(
            session, owner_id=owners[1].id, proyecto="casa", scope="agent",
            entity_id="agent:casa", topic_key="fact",
        ).id == rows[1].id
        assert tukulpan.get_by_key(
            session, proyecto="casa", scope="agent", entity_id="agent:casa",
            topic_key="business",
        ).id == shared.id
        assert tukulpan.get_by_key(
            session, proyecto="casa", scope="agent", entity_id="agent:casa",
            topic_key="fact",
        ) is None
        assert {row.id for row in tukulpan.list_for_entity(
            session, owner_id=owners[0].id, proyecto="casa", scope="agent", entity_id="agent:casa"
        )} == {rows[0].id}
        results = tukulpan.hybrid_search(
            session, "Private fact", owner_id=owners[0].id, proyecto="casa",
            scope="agent", entity_id="agent:casa", min_sim=0,
        )
        assert rows[0].id in {result["id"] for result in results}
        assert rows[1].id not in {result["id"] for result in results}


def test_memory_upsert_derives_and_enforces_authorized_owner(fake_embedder, migrated_db):
    from app.services.projects import _ProjectAuthorization

    with SessionLocal() as session:
        owners = [User(username=f"derived-owner-{uuid4().hex}", password_hash="test") for _ in range(2)]
        session.add_all(owners)
        session.flush()
        authorization = _ProjectAuthorization(slug="derived-project", owner_id=owners[0].id)

        owned = tukulpan.upsert(
            session, authorization=authorization, owner_id=None, proyecto="derived-project",
            scope="agent", entity_id="agent:derived-project", topic_key="owned",
            tipo=MemoryType.DECISION, titulo="Owned", contenido="Owner-derived memory",
            visibility=MemoryVisibility.GLOBAL,
        )
        shared = tukulpan.upsert(
            session, authorization=None, owner_id=None, scope="customer", entity_id="shared",
            topic_key="business", tipo=MemoryType.DECISION, titulo="Shared", contenido="Business memory",
        )
        assert owned.owner_id == owners[0].id
        assert shared.owner_id is None
        with pytest.raises(ValueError, match="owner"):
            tukulpan.upsert(
                session, authorization=authorization, owner_id=owners[1].id, proyecto="derived-project",
                scope="agent", entity_id="agent:derived-project", topic_key="contradiction",
                tipo=MemoryType.DECISION, titulo="Rejected", contenido="Must fail closed",
            )


def test_mem2_rewrite_collision_keeps_written_key_and_folds_duplicate(fake_embedder, migrated_db):
    """A keyed rewrite whose new content is already held elsewhere must not crash.

    Rewriting the ``target`` key with content ``holder`` already carries puts both
    rows on one normalized hash, which the partial unique index cannot represent.
    The written key wins: ``holder`` is folded into ``target`` (observations
    re-pointed) so ``target`` survives and stays reachable by its key.
    """
    with SessionLocal() as session:
        holder = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="holder",
            tipo=MemoryType.DECISION,
            titulo="Holder",
            contenido="Shared fact",
        )
        target = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="target",
            tipo=MemoryType.DECISION,
            titulo="Target",
            contenido="Other fact",
        )
        session.add(
            MemoryObservation(
                memory_id=holder.id,
                scope="customer",
                entity_id="42",
                tipo=ObservationType.OPORTUNIDAD,
                detalle={"source": "holder"},
            )
        )
        session.commit()

        rewritten = memory.upsert(
            session,
            scope="customer",
            entity_id="42",
            topic_key="target",
            tipo=MemoryType.DECISION,
            titulo="Target",
            contenido="  SHARED   fact ",
        )
        session.commit()

        assert rewritten.id == target.id
        assert rewritten.contenido == "  SHARED   fact "
        assert memory.get_by_key(
            session, scope="customer", entity_id="42", topic_key="target"
        ).id == target.id
        assert session.query(Memory).filter_by(entity_id="42").count() == 1
        assert session.query(Memory).filter_by(id=holder.id).count() == 0
        assert session.query(MemoryObservation).one().memory_id == target.id


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


@pytest.mark.parametrize(
    ("source_message_ids", "source_tokens", "expected_ids", "expected_tokens"),
    [([], 0, [], 0), ([4], 2_000, [4], 2_000), ([5], 2_001, [5], 2_000)],
)
def test_mem7_recap_handles_empty_sources_and_bounds_source_tokens(
    fake_embedder, migrated_db, source_message_ids, source_tokens, expected_ids, expected_tokens
):
    with SessionLocal() as session:
        result = tukulpan.write_recap(
            session,
            thread_id=7,
            source_message_ids=source_message_ids,
            recap="A bounded recap",
            source_tokens=source_tokens,
            truncated=False,
        )
        session.commit()

        row = tukulpan.get_by_key(
            session,
            scope="panel",
            entity_id="thread:7",
            topic_key=f"assistant-recap:7:{source_message_ids[-1] if source_message_ids else 'empty'}",
        )
        payload = __import__("json").loads(row.contenido)

        assert result["written"] is True
        assert payload["source_message_ids"] == expected_ids
        assert payload["source_tokens"] == expected_tokens


def test_mem7_recap_failure_returns_degraded_evidence_and_keeps_session_usable(monkeypatch, migrated_db):
    monkeypatch.setattr(tukulpan, "_embed", lambda texts: (_ for _ in ()).throw(RuntimeError("embed offline")))
    with SessionLocal() as session:
        result = tukulpan.write_recap(
            session, thread_id=7, source_message_ids=[5], recap="Retry me",
            source_tokens=2, truncated=False,
        )
        assert result["written"] is False
        assert result["degraded_reason"] == "Memory recap unavailable"
        assert "embed offline" not in result["degraded_reason"]
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


def test_mem3_literal_phrase_recall_with_flat_dense_channel(flat_embedder, migrated_db):
    """A literal keyword buried in a long memory is recalled (MEM-3).

    Scenario: Literal phrase recall. The dense channel is deliberately
    uninformative here: the real embedder dilutes a short query against a long
    content (measured ~0.18 cosine for exactly this pair). Recall must come
    from the lexical channel, so whole-string trigram similarity -- diluted by
    content length -- cannot carry it.
    """
    with SessionLocal() as session:
        memory.upsert(
            session,
            scope="agent",
            entity_id="agent:default",
            topic_key="agent:keyword",
            tipo=MemoryType.DISCOVERY,
            titulo="Palabra clave",
            contenido=(
                "El administrador pidió guardar una memoria con la palabra clave "
                "«perro» en este hilo del panel, para recuperarla más adelante."
            ),
            visibility=MemoryVisibility.GLOBAL,
        )
        session.commit()

        results = memory.hybrid_search(
            session, "perro", scope="agent", entity_id="agent:default"
        )

    assert [r["topic_key"] for r in results] == ["agent:keyword"]


def test_mem3_literal_phrase_recall_matches_accent_variants(flat_embedder, migrated_db):
    """The lexical channel folds accents, so an unaccented query still recalls.

    Scenario: Literal phrase recall. `calefón` is core domain vocabulary and is
    routinely written without its accent.
    """
    with SessionLocal() as session:
        memory.upsert(
            session,
            scope="agent",
            entity_id="agent:default",
            topic_key="agent:calefon",
            tipo=MemoryType.DISCOVERY,
            titulo="Falla de encendido",
            contenido="La clienta reportó que el calefón no enciende por las mañanas.",
            visibility=MemoryVisibility.GLOBAL,
        )
        session.commit()

        results = memory.hybrid_search(
            session, "calefon", scope="agent", entity_id="agent:default"
        )

    assert [r["topic_key"] for r in results] == ["agent:calefon"]


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


def test_mem3_own_read_orders_each_axis_by_pin_handoff_then_recency(fake_embedder, migrated_db):
    """Own read orders each axis pin -> handoff -> recency before interleaving (MEM-3).

    Scenario: Own read order and bounded digest. Both axes carry a pinned row, a
    handoff row, and a more recently updated row, so the ordering must hold per
    axis and survive the interleave, with every `contenido` bounded.
    """
    from app.chat.assistant.tools import registry

    with SessionLocal() as session:
        for scope, entity_id, prefix in (
            ("panel", "thread:42", ""),
            ("agent", "agent:default", "agent:"),
        ):
            for topic_key, pin, handoff in (
                ("pin", True, False),
                ("handoff", False, True),
                ("recent", False, False),
            ):
                memory.upsert(
                    session, scope=scope, entity_id=entity_id,
                    topic_key=f"{prefix}{topic_key}", tipo=MemoryType.DECISION,
                    titulo=f"{prefix}{topic_key}", contenido=f"{prefix}{topic_key}",
                    pin=pin, handoff=handoff,
                    visibility=MemoryVisibility.THREAD if scope == "panel" else MemoryVisibility.GLOBAL,
                )
        session.flush()

        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        offsets = {"pin": 0, "handoff": 1, "recent": 2}
        for row in session.query(Memory).all():
            row.updated_at = base + timedelta(days=offsets[row.topic_key.removeprefix("agent:")])
        session.commit()

        digest = registry._read_memory(
            session, registry.MemoryArgs.model_validate({"limit": 10}),
            trusted_thread_id=42, proyecto="default",
        )

    assert [item["topic_key"] for item in digest] == [
        "pin", "agent:pin", "handoff", "agent:handoff", "recent", "agent:recent",
    ]
    assert all(
        item["handoff"] is (item["topic_key"] in {"handoff", "agent:handoff"}) for item in digest
    )
    assert all(
        len(item["contenido"]) <= registry.MEMORY_READ_DIGEST_CONTENT_LIMIT for item in digest
    )


def test_mem9_global_visibility_records_provenance_and_cross_thread_read(
    fake_embedder, migrated_db
):
    """Global visibility is isolated to the thread's project namespace."""
    from app.chat.assistant.tools import registry
    from app.models import InternalChatThread, Project

    with SessionLocal() as session:
        project_a = f"mem9-{uuid4().hex[:8]}-a"
        project_b = f"mem9-{uuid4().hex[:8]}-b"
        session.add_all([
            Project(slug=project_a, name="Project A", purpose="A", purpose_embedding=[0.0] * 384),
            Project(slug=project_b, name="Project B", purpose="B", purpose_embedding=[0.0] * 384),
        ])
        session.flush()
        user = User(username="memory-spec", password_hash="test")
        session.add(user)
        session.flush()
        thread_a = InternalChatThread(user_id=user.id, proyecto=project_a)
        thread_a_other = InternalChatThread(user_id=user.id, proyecto=project_a)
        thread_b = InternalChatThread(user_id=user.id, proyecto=project_b)
        session.add_all([thread_a, thread_a_other, thread_b])
        session.flush()
        args = registry.MemoryWriteArgs(
            titulo="Reusable fact",
            contenido="A fact for the whole project",
            topic_key="agent:fact",
            tipo="decision",
            visibility="global",
        )
        result = registry._write_memory(
            session, args, trusted_thread_id=thread_a.id, proyecto=project_a
        )
        session.commit()

        assert result["written"] is True
        row = tukulpan.get_by_key(
            session,
            scope="agent",
            entity_id=f"agent:{project_a}",
            proyecto=project_a,
            topic_key="agent:fact",
        )
        assert row.producer is MemoryProducer.AGENT
        assert row.origin_thread_id == str(thread_a.id)
        assert row.visibility is MemoryVisibility.GLOBAL
        assert [item.id for item in tukulpan.list_for_entity(
            session, scope="agent", entity_id=f"agent:{project_a}", proyecto=project_a
        )] == [row.id]
        assert registry._read_memory(
            session, registry.MemoryArgs.model_validate({}), trusted_thread_id=thread_b.id,
            proyecto=project_b
        ) == []
        digest = registry._read_memory(
            session, registry.MemoryArgs.model_validate({}), trusted_thread_id=thread_a_other.id,
            proyecto=project_a
        )
        assert [item["id"] for item in digest] == [row.id]
        assert len(digest[0]["contenido"]) <= 500


def test_mem9_global_visibility_is_the_write_default(fake_embedder, migrated_db):
    from app.chat.assistant.tools import registry

    with SessionLocal() as session:
        result = registry._write_memory(
            session,
            registry.MemoryWriteArgs(
                titulo="Thread fact",
                 contenido="Only for this thread",
                 topic_key="agent:thread-fact",
                 tipo="decision",
             ),
            trusted_thread_id=12, proyecto="default",
        )
        session.commit()

        row = tukulpan.get_by_key(
            session,
            scope="agent",
            entity_id="agent:default", proyecto="default",
            topic_key="agent:thread-fact",
        )
        assert result["written"] is True
        assert row.visibility is MemoryVisibility.GLOBAL
        assert row.producer is MemoryProducer.AGENT
        assert row.origin_thread_id == "12"


def test_mem9_coherence_constraint_rejects_global_panel_row(migrated_db, admin_conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        admin_conn.execute(
            "INSERT INTO memories "
            "(scope, entity_id, topic_key, titulo, contenido, embedding, visibility) "
            "VALUES ('panel', 'thread:13', 'invalid', 'Invalid', 'Invalid', %s::vector, 'global')",
            ("[" + ",".join(["0.1"] * 384) + "]",),
        )


# ---------------------------------------------------------------------------
# MEM-12 — Handoff Marker
# ---------------------------------------------------------------------------


def test_mem13_spec_defines_deterministic_autonomous_capture():
    spec = Path("openspec/specs/memory/spec.md").read_text()
    mem13 = spec.split("### Requirement: MEM-13 — Deterministic Autonomous Capture", 1)[1]
    assert "### Requirement:" not in mem13

    for clause in (
        "runtime, not the user and not the model",
        "turn interval",
        "durable write outcome",
        "rotation",
        "blocked cost budget",
        "untrusted thread",
        "per-thread daily budget",
        "no capture and no paid call",
        "at most three items",
        "strict schema",
        "does not validate is dropped",
        "canonical Tukulpan write seam",
        "producer=agent",
        "origin_thread_id",
        "content-hash deduplication",
        "relation judging",
        "failed capture",
        "never fails or blocks the turn",
        "never injects or mutates the assembled panel context",
        "idle-thread sweep",
        "idempotently by its last message",
    ):
        assert clause in mem13, f"MEM-13 is missing: {clause}"

    assert "(MEM-9)" in mem13
    assert "(MEM-1)" in mem13
    assert "(MEM-11)" in mem13
    assert "(MEM-3 stays intact)" in mem13
    assert "#### Scenario:" in mem13
    assert "- GIVEN " in mem13 and "- WHEN " in mem13 and "- THEN " in mem13


def test_mem12_default_handoff_is_false(fake_embedder, migrated_db):
    with SessionLocal() as session:
        row = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="handoff-default",
            topic_key="agent:plain",
            tipo=MemoryType.DECISION,
            titulo="Plain memory",
            contenido="No continuation marker",
        )
        session.commit()

        assert row.handoff is False


def test_mem12_handoff_survives_an_omitted_handoff_and_clears_explicitly(fake_embedder, migrated_db):
    with SessionLocal() as session:
        written = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="handoff-marker",
            topic_key="agent:continuation",
            tipo=MemoryType.DECISION,
            titulo="Continuation point",
            contenido="Resume the migration work here",
            handoff=True,
        )
        session.commit()
        assert written.handoff is True

        repeated = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="handoff-marker",
            topic_key="agent:continuation",
            tipo=MemoryType.DECISION,
            titulo="Continuation point",
            contenido="Resume the migration work here",
        )
        session.commit()
        assert repeated.handoff is True

        cleared = tukulpan.upsert(
            session,
            scope="customer",
            entity_id="handoff-marker",
            topic_key="agent:continuation",
            tipo=MemoryType.DECISION,
            titulo="Continuation point",
            contenido="Resume the migration work here",
            handoff=False,
        )
        session.commit()
        assert cleared.handoff is False
