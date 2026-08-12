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

The runner connects as the admin role (env TEST_ADMIN_DB_URL, default
`postgresql://lumat:lumat@localhost:5432/lumat` — the compose dev/test DB) and
creates the least-privilege `app` role itself; tests connect as `app` via
TEST_APP_DB_URL to verify grants.
"""

import os

import psycopg
import pytest

from tests.integration.conftest import ADMIN_DB_URL, run_migrate  # noqa: E402

APP_URL = os.environ.get(
    "TEST_APP_DB_URL", "postgresql://app:app@localhost:5432/lumat"
)

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
            "TRUNCATE settings, audit_log, kb_chunks, kb_documents, "
            "conversation_events, cases, messages, conversations, users, customers "
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


def test_schema_migrations_records_version(migrated_db, admin_conn):
    rows = admin_conn.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    ).fetchall()
    assert rows == [("001_init",)]


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


def test_kb_chunks_accepts_1536d_vector(migrated_db, admin_conn):
    """vector(1536) column accepts a real embedding (pgvector extension active)."""
    admin_conn.execute(
        "INSERT INTO kb_documents (title, format, content) "
        "VALUES ('doc1', 'md', 'content')"
    )
    doc_id = admin_conn.execute(
        "SELECT id FROM kb_documents WHERE title = 'doc1'"
    ).fetchone()[0]
    embedding = "[" + ",".join("0.01" for _ in range(1536)) + "]"
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
    assert by_type["user_role"] == ["admin", "operador"]
    assert by_type["conversation_state"] == ["bot", "human", "closed"]
    assert by_type["message_direction"] == ["inbound", "outbound"]
    assert by_type["message_status"] == [
        "received", "processing", "processed", "failed",
    ]
    assert by_type["document_format"] == ["pdf", "md", "csv"]
