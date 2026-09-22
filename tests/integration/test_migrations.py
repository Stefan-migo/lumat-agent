"""T1.1 integration tests — schema migration + migrate.sh runner.

Runs `db/migrate.sh` against a reachable pgvector and asserts the design
Data Model acceptance criteria:

- applies cleanly twice (idempotent via schema_migrations)
- all 10 tables exist (+ schema_migrations)
- `customers.phone_e164` UNIQUE
- partial unique index on `messages.wamid` (inbound only)
- HNSW index on `kb_chunks.embedding` (vector_cosine_ops, m=16, ef_construction=64)
- app DB role: INSERT+SELECT only on `audit_log` (append-only, SH-5),
  full CRUD on business tables

The runner connects as the admin role from the shared test database derivation
and creates the least-privilege `app` role itself; tests connect as `app` via
TEST_APP_DB_URL to verify grants.
"""

import filecmp
import os
import shutil
import subprocess
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from _testdb import admin_database_url, database_url, libpq_database_url  # noqa: E402
from tests.integration.conftest import run_migrate  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
ADMIN_DB_URL = admin_database_url()
APP_URL = os.environ.get("TEST_APP_DB_URL") or libpq_database_url(database_url())

EXPECTED_TABLES = {
    "customers",
    "users",
    "conversations",
    "messages",
    "cases",
    "conversation_events",
    "kb_documents",
    "kb_chunks",
    "settings",
    "audit_log",
    "customer_notes",  # 002_customer_notes.sql (CR-4 internal staff notes)
    "memories",  # 009_memory.sql (MEM-1 persistent memory layer)
    "memory_relations",
    "memory_observations",
    "technician_availability",
    "appointments",
    "appointment_history",
    "appointment_calendar_sync",
    "notification_template_versions",
    "notification_operations",
    "notification_attempts",
    "domain_events",
    "automation_rules",
    "automation_executions",
    "panel_notifications",
    "push_subscriptions",
    "internal_chat_threads",
    "internal_chat_messages",
    "assistant_attachments",  # 022_assistant_attachments.sql (assistant file attachments)
    "projects",  # 024_projects.sql (agent-owned project registry)
    "project_aliases",
    "project_audit",
    "schema_migrations",
}


@pytest.fixture()
def admin_conn():
    # autocommit: each statement standalone so raised constraint/privilege
    # errors don't poison a transaction for the following assertions
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        yield conn


@pytest.fixture()
def app_conn():
    with psycopg.connect(APP_URL, autocommit=True) as conn:
        yield conn


@pytest.fixture(scope="module", autouse=True)
def clean_db(migrated_db):
    """Reset all tables before this module's tests (dedicated test DB only)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE notification_attempts, notification_operations, settings, audit_log, kb_chunks, kb_documents, "
            "conversation_events, cases, messages, conversations, users, customers, "
            "customer_notes, memories, memory_relations, memory_observations "
            "RESTART IDENTITY CASCADE"
        )
    yield


# --- idempotency -----------------------------------------------------------

def test_migrate_applies_cleanly_twice(migrated_db):
    """Acceptance: applies cleanly twice (idempotent)."""
    first = run_migrate()
    assert first.returncode == 0, first.stderr
    second = run_migrate()
    assert second.returncode == 0, second.stderr
    # second run must skip (not re-apply) the initial migration
    assert "skip 001_init" in second.stdout


def test_migration_030_preserves_existing_project_rows(tmp_path):
    """Applying 030 to a real 029 database preserves and renames existing rows."""
    admin_parts = conninfo_to_dict(ADMIN_DB_URL)
    database_name = admin_parts["dbname"]
    scratch_name = f"{database_name}_mig030"
    scratch_url = make_conninfo(**{**admin_parts, "dbname": scratch_name})

    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} ").format(sql.Identifier(scratch_name)))
        conn.execute(sql.SQL("CREATE DATABASE {} ").format(sql.Identifier(scratch_name)))

    try:
        runner_copy = tmp_path / "migrate.sh"
        original_runner = REPO_ROOT / "db" / "migrate.sh"
        shutil.copy2(original_runner, runner_copy)
        assert filecmp.cmp(original_runner, runner_copy, shallow=False)

        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()
        for migration in (REPO_ROOT / "db" / "migrations").glob("*.sql"):
            if int(migration.stem.split("_", 1)[0]) < 30:
                (migrations_dir / migration.name).symlink_to(migration)

        migration_env = os.environ.copy()
        migration_env.update(
            {
                "DATABASE_URL": scratch_url,
                "APP_DB_PASSWORD": "app",
                "PYTHON": str(REPO_ROOT / ".venv" / "bin" / "python"),
            }
        )
        scaffold = subprocess.run(
            ["bash", str(runner_copy)],
            env=migration_env,
            capture_output=True,
            text=True,
        )
        assert scaffold.returncode == 0, (
            f"029 scaffold failed:\nstdout={scaffold.stdout}\nstderr={scaffold.stderr}"
        )

        with psycopg.connect(scratch_url, autocommit=True) as conn:
            labels = conn.execute(
                "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = 'memory_visibility' ORDER BY enumsortorder"
            ).fetchall()
            assert labels == [("thread",), ("project",)]
            assert conn.execute(
                "SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = 'memory_visibility' AND enumlabel = 'global'"
            ).fetchone() is None
            assert conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
            ).fetchone() == ("029_memory_relation_resolution",)

            embedding = "[" + ",".join("0.1" for _ in range(384)) + "]"
            agent_id = conn.execute(
                "INSERT INTO memories (scope, entity_id, titulo, contenido, embedding, visibility) "
                "VALUES ('agent', 'agent:default', 'agent row', 'pre-030', %s::vector, 'project') "
                "RETURNING id",
                (embedding,),
            ).fetchone()[0]
            panel_id = conn.execute(
                "INSERT INTO memories (scope, entity_id, titulo, contenido, embedding) "
                "VALUES ('panel', 'thread:1', 'panel row', 'pre-030', %s::vector) RETURNING id",
                (embedding,),
            ).fetchone()[0]
            assert conn.execute("SELECT count(*) FROM memories").fetchone() == (2,)

        migration = subprocess.run(
            ["bash", str(original_runner)],
            env=migration_env,
            capture_output=True,
            text=True,
        )
        assert migration.returncode == 0, (
            f"030 migration failed:\nstdout={migration.stdout}\nstderr={migration.stderr}"
        )

        with psycopg.connect(scratch_url, autocommit=True) as conn:
            labels = conn.execute(
                "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = 'memory_visibility' ORDER BY enumsortorder"
            ).fetchall()
            assert labels == [("thread",), ("global",)]
            assert conn.execute("SELECT count(*) FROM memories").fetchone() == (2,)
            assert conn.execute(
                "SELECT visibility FROM memories WHERE id = %s", (agent_id,)
            ).fetchone() == ("global",)
            assert conn.execute(
                "SELECT visibility FROM memories WHERE id = %s", (panel_id,)
            ).fetchone() == ("thread",)

            constraint = conn.execute(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'memories_visibility_scope_coherence'"
            ).fetchone()[0]
            assert "(visibility = 'global'::memory_visibility)" in constraint
            assert "((scope)::text = 'agent'::text)" in constraint

            assert conn.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = 'memories' AND column_name = 'visibility'"
            ).fetchone() == ("'thread'::memory_visibility",)

            with pytest.raises(psycopg.Error):
                conn.execute(
                    "INSERT INTO memories (scope, entity_id, titulo, contenido, embedding, visibility) "
                    "VALUES ('panel', 'thread:global-rejected', 'rejected', '030', %s::vector, 'global')",
                    (embedding,),
                )
    finally:
        with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} ").format(sql.Identifier(scratch_name)))


def test_schema_migrations_records_version(migrated_db, admin_conn):
    rows = admin_conn.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    ).fetchall()
    assert rows == [
        ("001_init",),
        ("002_customer_notes",),
        ("003_conversation_captured_data",),
        ("004_case_emergency",),
        ("005_case_emergency_ack",),
        ("006_handoff_deriva",),
        ("007_case_created_at",),
        ("008_local_embeddings",),
        ("009_memory",),
        ("010_h2_human_inbox",),
        ("011_h3_scheduling",),
        ("012_h3_calendar_templates",),
        ("013_h3_notifications",),
        ("014_h4_automations_chat_pwa",),
        ("015_h4_automations",),
        ("016_h4_notification_center",),
        ("017_h4_internal_chat",),
        ("018_conversation_realtime",),
        ("019_tecnico_role",),
        ("020_assistant_metadata",),
        ("022_assistant_attachments",),
        ("023_panel_cost_llm",),
        ("024_projects",),
        ("025_internal_chat_thread_title",),
        ("026_memory_provenance",),
        ("027_kb_visibility",),
        ("028_memory_dedup",),
        ("029_memory_relation_resolution",),
        ("030_memory_visibility_global",),
    ]


def test_internal_chat_cost_column_and_app_grants(migrated_db, admin_conn):
    """SS-3: internal cost is nullable and writable by the app role."""
    column = admin_conn.execute(
        "SELECT data_type, numeric_precision, numeric_scale, is_nullable "
        "FROM information_schema.columns WHERE table_name = 'internal_chat_messages' "
        "AND column_name = 'cost_llm'"
    ).fetchone()
    assert column == ("numeric", 12, 6, "YES")
    grants = admin_conn.execute(
        "SELECT privilege_type FROM information_schema.role_table_grants "
        "WHERE grantee = 'app' AND table_name = 'internal_chat_messages' "
        "ORDER BY privilege_type"
    ).fetchall()
    assert [privilege for (privilege,) in grants] == [
        "DELETE", "INSERT", "SELECT", "UPDATE"
    ]


def test_internal_chat_thread_title_is_nullable(migrated_db, admin_conn):
    """Chat thread titles are optional until title generation or rename."""
    column = admin_conn.execute(
        "SELECT data_type, character_maximum_length, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_name = 'internal_chat_threads' AND column_name = 'title'"
    ).fetchone()
    assert column == ("character varying", 255, "YES")


# --- tables ----------------------------------------------------------------

def test_all_tables_exist(migrated_db, admin_conn):
    """Acceptance: \\dt shows all tables (10 design tables + schema_migrations)."""
    rows = admin_conn.execute(
        """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        """
    ).fetchall()
    assert {r[0] for r in rows} == EXPECTED_TABLES


# --- uniqueness constraints ------------------------------------------------

def test_customers_phone_e164_unique(migrated_db, admin_conn):
    """customers.phone_e164 UNIQUE (design Data Model, CR-2 dedup)."""
    admin_conn.execute(
        "INSERT INTO customers (phone_e164) VALUES ('+56912345678')"
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        admin_conn.execute(
            "INSERT INTO customers (phone_e164) VALUES ('+56912345678')"
        )


def test_messages_wamid_partial_unique_inbound_only(migrated_db, admin_conn):
    """Partial unique index: inbound wamid dedup, outbound/other rows free (WH-5)."""
    admin_conn.execute(
        "INSERT INTO customers (phone_e164) VALUES ('+56911111111')"
    )
    customer_id = admin_conn.execute(
        "SELECT id FROM customers WHERE phone_e164 = '+56911111111'"
    ).fetchone()[0]
    admin_conn.execute(
        "INSERT INTO conversations (customer_id, wa_phone) VALUES (%s, '+56911111111')",
        (customer_id,),
    )
    conv_id = admin_conn.execute(
        "SELECT id FROM conversations WHERE customer_id = %s", (customer_id,)
    ).fetchone()[0]

    # two inbound with the same wamid -> second must be rejected
    admin_conn.execute(
        "INSERT INTO messages (conversation_id, direction, msg_type, wamid, status) "
        "VALUES (%s, 'inbound', 'text', 'wamid-dup-1', 'received')",
        (conv_id,),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        admin_conn.execute(
            "INSERT INTO messages (conversation_id, direction, msg_type, wamid, status) "
            "VALUES (%s, 'inbound', 'text', 'wamid-dup-1', 'received')",
            (conv_id,),
        )

    # inbound wamid may equal an outbound wamid (partial index only guards inbound)
    admin_conn.execute(
        "INSERT INTO messages (conversation_id, direction, msg_type, wamid, status) "
        "VALUES (%s, 'outbound', 'text', 'wamid-dup-1', 'processed')",
        (conv_id,),
    )

    # outbound wamid may repeat freely (no unique constraint)
    admin_conn.execute(
        "INSERT INTO messages (conversation_id, direction, msg_type, wamid, status) "
        "VALUES (%s, 'outbound', 'text', 'wamid-out-repeat', 'processed')",
        (conv_id,),
    )
    admin_conn.execute(
        "INSERT INTO messages (conversation_id, direction, msg_type, wamid, status) "
        "VALUES (%s, 'outbound', 'text', 'wamid-out-repeat', 'processed')",
        (conv_id,),
    )


# --- pgvector / HNSW -------------------------------------------------------

def test_kb_chunks_embedding_hnsw_index(migrated_db, admin_conn):
    """HNSW index on kb_chunks.embedding with design params (KB-1)."""
    row = admin_conn.execute(
        """
        SELECT indexdef FROM pg_indexes
        WHERE tablename = 'kb_chunks' AND indexname = 'idx_kb_chunks_embedding_hnsw'
        """
    ).fetchone()
    assert row is not None, "HNSW index missing"
    indexdef = row[0]
    assert "USING hnsw" in indexdef
    assert "vector_cosine_ops" in indexdef
    # pg dumps options quoted (m='16'), so assert the value is present
    assert "m='16'" in indexdef or "m = 16" in indexdef
    assert "ef_construction='64'" in indexdef or "ef_construction = 64" in indexdef


def test_kb_chunks_accepts_384d_vector(migrated_db, admin_conn):
    """vector(384) column accepts a real embedding (pgvector extension active)."""
    admin_conn.execute(
        "INSERT INTO kb_documents (title, format, content) "
        "VALUES ('doc1', 'md', 'content')"
    )
    doc_id = admin_conn.execute(
        "SELECT id FROM kb_documents WHERE title = 'doc1'"
    ).fetchone()[0]
    embedding = "[" + ",".join("0.01" for _ in range(384)) + "]"
    admin_conn.execute(
        "INSERT INTO kb_chunks (document_id, version, chunk_index, content, embedding) "
        "VALUES (%s, 1, 0, 'chunk', %s::vector)",
        (doc_id, embedding),
    )


# --- grants (SH-5 append-only audit) ---------------------------------------

def test_app_role_audit_log_insert_and_select_only(migrated_db, app_conn):
    """App role: INSERT+SELECT on audit_log, UPDATE/DELETE denied (append-only)."""
    app_conn.execute(
        "INSERT INTO audit_log (actor, action, entity, before, after) "
        "VALUES ('test', 'settings.change', 'settings', '{}'::jsonb, '{}'::jsonb)"
    )
    count = app_conn.execute("SELECT count(*) FROM audit_log").fetchone()[0]
    assert count >= 1

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_conn.execute(
            "UPDATE audit_log SET after = '{}'::jsonb WHERE actor = 'test'"
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_conn.execute("DELETE FROM audit_log WHERE actor = 'test'")


def test_app_role_full_crud_on_business_tables(migrated_db, app_conn):
    """App role: full CRUD on business tables (messages, customers, settings)."""
    app_conn.execute(
        "INSERT INTO customers (phone_e164) VALUES ('+56922222222')"
    )
    app_conn.execute(
        "UPDATE customers SET name = 'Test' WHERE phone_e164 = '+56922222222'"
    )
    app_conn.execute(
        "INSERT INTO settings (key, value) VALUES ('scope_rules', '{}'::jsonb)"
    )
    app_conn.execute(
        "UPDATE settings SET value = '{\"x\": 1}'::jsonb WHERE key = 'scope_rules'"
    )
    row = app_conn.execute(
        "SELECT name FROM customers WHERE phone_e164 = '+56922222222'"
    ).fetchone()
    assert row == ("Test",)


# --- enums ----------------------------------------------------------------

def test_enums_materialized(migrated_db, admin_conn):
    """Design enums exist as PG types with the documented labels."""
    rows = admin_conn.execute(
        "SELECT typname, enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
        "WHERE typname IN ('customer_state', 'user_role', 'conversation_state', "
        "'message_direction', 'message_status', 'document_format') "
        "ORDER BY typname, enumsortorder"
    ).fetchall()
    by_type: dict[str, list[str]] = {}
    for typname, label in rows:
        by_type.setdefault(typname, []).append(label)
    assert by_type["customer_state"] == [
        "nuevo", "contactado", "pendiente", "agendado", "en_evaluacion",
        "finalizado", "cancelado", "postventa",
    ]
    assert by_type["user_role"] == ["admin", "operador", "tecnico"]
    assert by_type["conversation_state"] == ["bot", "human", "closed"]
    assert by_type["message_direction"] == ["inbound", "outbound"]
    assert by_type["message_status"] == [
        "received", "processing", "processed", "failed",
    ]
    assert by_type["document_format"] == ["pdf", "md", "csv"]


def test_memory_provenance_schema(migrated_db, admin_conn):
    """Memory rows carry producer, origin, and declared visibility."""
    rows = admin_conn.execute(
        "SELECT typname, enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
        "WHERE typname IN ('memory_producer', 'memory_visibility') "
        "ORDER BY typname, enumsortorder"
    ).fetchall()
    by_type: dict[str, list[str]] = {}
    for typname, label in rows:
        by_type.setdefault(typname, []).append(label)
    assert by_type["memory_producer"] == ["user", "system", "agent", "pipeline"]
    assert by_type["memory_visibility"] == ["thread", "global"]

    columns = admin_conn.execute(
        "SELECT column_name, column_default, is_nullable, udt_name "
        "FROM information_schema.columns WHERE table_name = 'memories' "
        "AND column_name IN ('producer', 'origin_thread_id', 'visibility') "
        "ORDER BY column_name"
    ).fetchall()
    assert columns == [
        ("origin_thread_id", None, "YES", "varchar"),
        ("producer", "'system'::memory_producer", "NO", "memory_producer"),
        ("visibility", "'thread'::memory_visibility", "NO", "memory_visibility"),
    ]


# --- H2 schema/domain contracts --------------------------------------------

def test_h2_conversation_contract_columns_and_indexes(migrated_db, admin_conn):
    columns = admin_conn.execute(
        "SELECT column_name, column_default, is_nullable "
        "FROM information_schema.columns WHERE table_name = 'conversations' "
        "AND column_name IN ('responsible_id', 'version') ORDER BY column_name"
    ).fetchall()
    assert columns == [
        ("responsible_id", None, "YES"),
        ("version", "0", "NO"),
    ]
    index = admin_conn.execute(
        "SELECT indexdef FROM pg_indexes WHERE indexname = "
        "'idx_conversations_responsible_id'"
    ).fetchone()
    assert index is not None


def test_active_conversation_partial_index(migrated_db, admin_conn):
    """CRT-4 active reads have a partial recency index."""
    row = admin_conn.execute(
        "SELECT indexdef FROM pg_indexes WHERE indexname = "
        "'idx_conversations_active_recency'"
    ).fetchone()

    assert row is not None
    assert "last_message_at DESC" in row[0]
    assert "'bot'::conversation_state" in row[0]
    assert "'human'::conversation_state" in row[0]
    assert "last_message_at IS NOT NULL" in row[0]


def test_h2_outbound_contract_and_delivery_enum(migrated_db, admin_conn):
    columns = admin_conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'messages' AND column_name IN "
        "('author_id', 'request_id', 'delivery_status', 'delivery_error', "
        "'delivery_attempts', 'last_attempt_at', 'delivered_at') "
        "ORDER BY column_name"
    ).fetchall()
    assert [column for (column,) in columns] == [
        "author_id", "delivered_at", "delivery_attempts", "delivery_error",
        "delivery_status", "last_attempt_at", "request_id",
    ]
    rows = admin_conn.execute(
        "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
        "WHERE t.typname = 'delivery_status' ORDER BY enumsortorder"
    ).fetchall()
    assert rows == [(label,) for label in ("pending", "sending", "sent", "failed", "unknown")]
    index = admin_conn.execute(
        "SELECT indexdef FROM pg_indexes WHERE indexname = "
        "'uq_messages_outbound_request_id'"
    ).fetchone()
    assert index is not None
    assert "direction = 'outbound'" in index[0]


def test_h2_outbound_request_key_is_unique_only_for_outbound(migrated_db, admin_conn):
    admin_conn.execute("INSERT INTO customers (phone_e164) VALUES ('+56977778888')")
    customer_id = admin_conn.execute(
        "SELECT id FROM customers WHERE phone_e164 = '+56977778888'"
    ).fetchone()[0]
    conversation_id = admin_conn.execute(
        "INSERT INTO conversations (customer_id, wa_phone) VALUES (%s, %s) RETURNING id",
        (customer_id, "+56977778888"),
    ).fetchone()[0]
    values = (conversation_id, "outbound", "text", "request-1")
    admin_conn.execute(
        "INSERT INTO messages (conversation_id, direction, msg_type, request_id) "
        "VALUES (%s, %s, %s, %s)", values
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        admin_conn.execute(
            "INSERT INTO messages (conversation_id, direction, msg_type, request_id) "
            "VALUES (%s, %s, %s, %s)", values
        )
    admin_conn.execute(
        "INSERT INTO messages (conversation_id, direction, msg_type, request_id) "
        "VALUES (%s, 'inbound', 'text', %s)", (conversation_id, "request-1")
    )
