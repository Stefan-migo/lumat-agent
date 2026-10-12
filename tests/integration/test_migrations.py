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
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

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
    "conversation_events",
    "kb_documents",
    "kb_chunks",
    "settings",
    "audit_log",
    "customer_notes",  # 002_customer_notes.sql (CR-4 internal staff notes)
    "customer_equipment",  # 035_customer_equipment.sql (D5)
    "cases",
    "memories",  # 009_memory.sql (MEM-1 persistent memory layer)
    "memory_relations",
    "memory_observations",
    "technician_availability",
    "technician_weekly_schedule",
    "appointments",
    "appointment_history",
    "appointment_calendar_sync",
    "notification_template_versions",
    "notification_operations",
    "notification_attempts",
    "domain_events",
    "automation_rules",
    "automation_executions",
    "automation_installations",  # 045_automation_installations.sql (recipe installations)
    "panel_notifications",
    "push_subscriptions",
    "internal_chat_threads",
    "internal_chat_messages",
    "assistant_attachments",  # 022_assistant_attachments.sql (assistant file attachments)
    "projects",  # 024_projects.sql (agent-owned project registry)
    "project_aliases",
    "project_audit",
    "project_files",  # 042_project_files.sql (durable project-scoped file store)
    "assistant_artifacts",  # 044_assistant_artifacts.sql (assistant-produced files)
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


def _migration_number(migration: Path) -> int:
    return int(migration.stem.split("_", 1)[0])


def _runner_dir(root: Path, migrations: list[Path]) -> Path:
    """A directory holding the real migrate.sh (byte-identical) beside the given migrations.

    The runner anchors its migration directory to its own location (`db/migrate.sh:21`), so a
    byte-identical copy beside a chosen subset is the only way to reach a schema below the latest
    one without touching the runner or the migrations themselves.
    """
    original = REPO_ROOT / "db" / "migrate.sh"
    runner = root / "migrate.sh"
    root.mkdir()
    shutil.copy2(original, runner)
    assert filecmp.cmp(original, runner, shallow=False)
    directory = root / "migrations"
    directory.mkdir()
    for migration in migrations:
        (directory / migration.name).symlink_to(migration)
    return runner


@contextmanager
def _scratch_migration_db(tmp_path: Path, before: int, target: int):
    """Yield an isolated database scaffolded before target, plus its migration runner."""
    admin_parts = conninfo_to_dict(ADMIN_DB_URL)
    scratch_name = f"{admin_parts['dbname']}_mig{target:03}_{uuid4().hex}"
    scratch_url = make_conninfo(**{**admin_parts, "dbname": scratch_name})
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(scratch_name)))
    migrations = sorted((REPO_ROOT / "db" / "migrations").glob("*.sql"))
    migration_env = os.environ.copy()
    migration_env.update({
        "DATABASE_URL": scratch_url, "APP_DB_PASSWORD": "app",
        "PYTHON": str(REPO_ROOT / ".venv" / "bin" / "python"),
    })

    def migrate(runner: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(runner)], env=migration_env, capture_output=True,
            text=True, timeout=60,
        )

    try:
        scaffold = migrate(_runner_dir(
            tmp_path / "scaffold",
            [m for m in migrations if _migration_number(m) <= before],
        ))
        assert scaffold.returncode == 0, f"scaffold failed:\n{scaffold.stdout}\n{scaffold.stderr}"
        target_runner = _runner_dir(
            tmp_path / "target", [m for m in migrations if _migration_number(m) == target]
        )
        with psycopg.connect(scratch_url, autocommit=True) as conn:
            yield conn, lambda: migrate(target_runner), migrations
    finally:
        with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(scratch_name)))


def test_migration_030_preserves_existing_project_rows(tmp_path):
    """Applying 030 to a real 029 database preserves and renames existing rows."""
    admin_parts = conninfo_to_dict(ADMIN_DB_URL)
    database_name = admin_parts["dbname"]
    # Unpredictable per run, and never pre-dropped: DROP DATABASE IF EXISTS against a guessable name
    # could destroy a database this test never created. The name is dropped only after the test has
    # created it.
    scratch_name = f"{database_name}_mig030_{uuid4().hex}"
    scratch_url = make_conninfo(**{**admin_parts, "dbname": scratch_name})

    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} ").format(sql.Identifier(scratch_name)))

    try:
        target = 30
        migrations = sorted((REPO_ROOT / "db" / "migrations").glob("*.sql"))
        migration_env = os.environ.copy()
        migration_env.update(
            {
                "DATABASE_URL": scratch_url,
                "APP_DB_PASSWORD": "app",
                "PYTHON": str(REPO_ROOT / ".venv" / "bin" / "python"),
            }
        )

        def migrate(runner: Path, label: str) -> None:
            result = subprocess.run(
                ["bash", str(runner)],
                env=migration_env,
                capture_output=True,
                text=True,
                timeout=45,
            )
            assert result.returncode == 0, (
                f"{label} failed:\nstdout={result.stdout}\nstderr={result.stderr}"
            )

        migrate(
            _runner_dir(
                tmp_path / "scaffold",
                [m for m in migrations if _migration_number(m) < target],
            ),
            "029 scaffold",
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

        # Only 030 travels in this directory, so a later migration can never be applied here and
        # change this test's outcome.
        migrate(
            _runner_dir(
                tmp_path / "final",
                [m for m in migrations if _migration_number(m) == target],
            ),
            "030 migration",
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


def test_migration_031_binds_existing_threads_to_default(tmp_path):
    """Applying 031 to a populated 030 database backfills the default namespace."""
    admin_parts = conninfo_to_dict(ADMIN_DB_URL)
    database_name = admin_parts["dbname"]
    scratch_name = f"{database_name}_mig031_{uuid4().hex}"
    scratch_url = make_conninfo(**{**admin_parts, "dbname": scratch_name})

    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} ").format(sql.Identifier(scratch_name)))

    try:
        migrations = sorted((REPO_ROOT / "db" / "migrations").glob("*.sql"))
        migration_env = os.environ.copy()
        migration_env.update(
            {
                "DATABASE_URL": scratch_url,
                "APP_DB_PASSWORD": "app",
                "PYTHON": str(REPO_ROOT / ".venv" / "bin" / "python"),
            }
        )

        def migrate(runner: Path, label: str) -> None:
            result = subprocess.run(
                ["bash", str(runner)],
                env=migration_env,
                capture_output=True,
                text=True,
                timeout=45,
            )
            assert result.returncode == 0, (
                f"{label} failed:\nstdout={result.stdout}\nstderr={result.stderr}"
            )

        migrate(
            _runner_dir(
                tmp_path / "scaffold",
                [m for m in migrations if _migration_number(m) <= 30],
            ),
            "030 scaffold",
        )

        with psycopg.connect(scratch_url, autocommit=True) as conn:
            user_id = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES ('migration-031', 'test') "
                "RETURNING id"
            ).fetchone()[0]
            thread_id = conn.execute(
                "INSERT INTO internal_chat_threads (user_id) VALUES (%s) RETURNING id",
                (user_id,),
            ).fetchone()[0]
            before = conn.execute(
                "SELECT column_name, data_type, character_maximum_length, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_name = 'internal_chat_threads' "
                "ORDER BY ordinal_position"
            ).fetchall()

        migrate(
            _runner_dir(
                tmp_path / "final",
                [m for m in migrations if _migration_number(m) == 31],
            ),
            "031 migration",
        )

        with psycopg.connect(scratch_url, autocommit=True) as conn:
            assert conn.execute(
                "SELECT proyecto FROM internal_chat_threads WHERE id = %s", (thread_id,)
            ).fetchone() == ("default",)
            project_column = conn.execute(
                "SELECT data_type, character_maximum_length, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_name = 'internal_chat_threads' "
                "AND column_name = 'proyecto'"
            ).fetchone()
            assert project_column == (
                "character varying", 100, "NO", "'default'::character varying"
            )
            after = conn.execute(
                "SELECT column_name, data_type, character_maximum_length, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_name = 'internal_chat_threads' "
                "AND column_name <> 'proyecto' ORDER BY ordinal_position"
            ).fetchall()
            assert after == before
    finally:
        with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} ").format(sql.Identifier(scratch_name)))


@pytest.mark.parametrize("admin_count", [1, 2])
def test_migration_034_backfills_only_owned_project_axis_memory(tmp_path, admin_count):
    """D9 assigns legacy project and panel/agent memory only when one admin exists."""
    admin_parts = conninfo_to_dict(ADMIN_DB_URL)
    scratch_name = f"{admin_parts['dbname']}_mig034_{uuid4().hex}"
    scratch_url = make_conninfo(**{**admin_parts, "dbname": scratch_name})
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} ").format(sql.Identifier(scratch_name)))

    try:
        migrations = sorted((REPO_ROOT / "db" / "migrations").glob("*.sql"))
        migration_env = os.environ.copy()
        migration_env.update({
            "DATABASE_URL": scratch_url,
            "APP_DB_PASSWORD": "app",
            "PYTHON": str(REPO_ROOT / ".venv" / "bin" / "python"),
        })

        def migrate(runner: Path, label: str) -> None:
            result = subprocess.run(
                ["bash", str(runner)], env=migration_env, capture_output=True,
                text=True, timeout=60,
            )
            assert result.returncode == 0, (
                f"{label} failed:\nstdout={result.stdout}\nstderr={result.stderr}"
            )

        migrate(
            _runner_dir(tmp_path / "pre034", [m for m in migrations if _migration_number(m) <= 33]),
            "033 scaffold",
        )
        with psycopg.connect(scratch_url, autocommit=True) as conn:
            user_ids = [conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, 'test', 'admin') RETURNING id",
                (f"migration-034-admin-{i}",),
            ).fetchone()[0] for i in range(admin_count)]
            embedding = "[" + ",".join("0.1" for _ in range(384)) + "]"
            conn.execute(
                "INSERT INTO projects (slug, name, purpose, purpose_embedding) "
                "VALUES ('legacy-project', 'Legacy', 'Legacy project', %s::vector)", (embedding,),
            )
            memory_ids = {}
            for label, project, scope, entity in (
                ("panel", "legacy-project", "panel", "thread:legacy"),
                ("agent", "legacy-project", "agent", "agent:legacy-project"),
                ("customer", "legacy-project", "customer", "customer:1"),
                ("default", "default", "agent", "agent:default"),
            ):
                memory_ids[label] = conn.execute(
                    "INSERT INTO memories (proyecto, scope, entity_id, titulo, contenido, embedding, visibility) "
                    "VALUES (%s, %s, %s, %s, 'legacy', %s::vector, %s) RETURNING id",
                    (project, scope, entity, label, embedding, "global" if scope == "agent" else "thread"),
                ).fetchone()[0]

        migration = next(m for m in migrations if _migration_number(m) == 34)
        migrate(_runner_dir(tmp_path / "034", [migration]), "034 migration")
        with psycopg.connect(scratch_url, autocommit=True) as conn:
            expected_owner = user_ids[0] if admin_count == 1 else None
            assert conn.execute("SELECT owner_id FROM projects WHERE slug='legacy-project'").fetchone() == (expected_owner,)
            owners = dict(conn.execute(
                "SELECT titulo, owner_id FROM memories WHERE id = ANY(%s)",
                (list(memory_ids.values()),),
            ).fetchall())
            assert owners == {
                "panel": expected_owner,
                "agent": expected_owner,
                "customer": None,
                "default": None,
            }
            # Re-applying the SQL itself is a no-op, including the multi-admin case.
            conn.execute(migration.read_text())
            assert dict(conn.execute(
                "SELECT titulo, owner_id FROM memories WHERE id = ANY(%s)",
                (list(memory_ids.values()),),
            ).fetchall()) == owners
    finally:
        with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} ").format(sql.Identifier(scratch_name)))


def test_migration_034_backfills_alias_owner_from_project_and_leaves_default_unowned(tmp_path):
    with _scratch_migration_db(tmp_path, 33, 34) as (conn, apply_034, _):
        admin = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES ('alias-admin', 'test', 'admin') RETURNING id"
        ).fetchone()[0]
        vector = "[" + ",".join("0.0" for _ in range(384)) + "]"
        legacy = conn.execute(
            "INSERT INTO projects (slug, name, purpose, purpose_embedding) VALUES ('legacy-owned', 'Legacy', 'p', %s::vector) RETURNING id",
            (vector,),
        ).fetchone()[0]
        # The 033 scaffold already seeds the business-shared `default` project.
        default = conn.execute("SELECT id FROM projects WHERE slug = 'default'").fetchone()[0]
        conn.execute(
            "INSERT INTO project_aliases (project_id, alias) VALUES (%s, 'legacy-owned'), (%s, 'default-alias')",
            (legacy, default),
        )
        result = apply_034()
        assert result.returncode == 0, f"034 failed:\n{result.stdout}\n{result.stderr}"
        assert dict(conn.execute(
            "SELECT alias, owner_id FROM project_aliases ORDER BY alias"
        ).fetchall()) == {
            "default-alias": None, "legacy-owned": admin,
        }


def test_migration_034_alias_unique_constraint_is_owner_scoped(tmp_path):
    with _scratch_migration_db(tmp_path, 33, 34) as (conn, apply_034, _):
        owners = [conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, 'test') RETURNING id",
            (f"alias-unique-{i}",),
        ).fetchone()[0] for i in range(2)]
        vector = "[" + ",".join("0.0" for _ in range(384)) + "]"
        projects = [conn.execute(
            "INSERT INTO projects (slug, name, purpose, purpose_embedding) VALUES (%s, 'p', 'p', %s::vector) RETURNING id",
            (f"alias-project-{i}", vector),
        ).fetchone()[0] for i in range(2)]
        result = apply_034()
        assert result.returncode == 0, f"034 failed:\n{result.stdout}\n{result.stderr}"
        for owner, project in zip(owners, projects):
            conn.execute(
                "INSERT INTO project_aliases (project_id, alias, owner_id) VALUES (%s, 'shared-alias', %s)",
                (project, owner),
            )
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(
                "INSERT INTO project_aliases (project_id, alias, owner_id) VALUES (%s, 'shared-alias', %s)",
                (projects[0], owners[0]),
            )


def test_migration_034_collision_premises_are_unreachable_in_legacy_schema(tmp_path):
    """Legacy uniqueness makes the 034 alias/composite-key collision risks in odd/tasks/usuarios-aislamiento.md structurally unreachable."""
    with _scratch_migration_db(tmp_path, 33, 34) as (conn, _, _):
        vector = "[" + ",".join("0.0" for _ in range(384)) + "]"
        projects = [conn.execute(
            "INSERT INTO projects (slug, name, purpose, purpose_embedding) VALUES (%s, 'p', 'p', %s::vector) RETURNING id",
            (f"legacy-collision-project-{i}", vector),
        ).fetchone()[0] for i in range(2)]
        conn.execute("INSERT INTO project_aliases (project_id, alias) VALUES (%s, 'legacy-collision')", (projects[0],))
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute("INSERT INTO project_aliases (project_id, alias) VALUES (%s, 'legacy-collision')", (projects[1],))

        memory = (
            "INSERT INTO memories (proyecto, scope, entity_id, topic_key, titulo, contenido, embedding, visibility) "
            "VALUES ('legacy-collision', 'agent', 'agent:collision', 'same-topic', %s, 'legacy', %s::vector, 'global')"
        )
        conn.execute(memory, ("first", vector))
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(memory, ("second", vector))


def test_migration_034_rollback_precondition_fails_when_owners_share_a_slug(tmp_path):
    """Evidence: 034's documented rollback requires no two owners to share a slug."""
    with _scratch_migration_db(tmp_path, 33, 34) as (conn, apply_034, _):
        owners = [conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, 'test') RETURNING id",
            (f"rollback-slug-owner-{i}",),
        ).fetchone()[0] for i in range(2)]
        vector = "[" + ",".join("0.0" for _ in range(384)) + "]"
        result = apply_034()
        assert result.returncode == 0, f"034 failed:\n{result.stdout}\n{result.stderr}"
        for owner in owners:
            conn.execute(
                "INSERT INTO projects (slug, name, purpose, purpose_embedding, owner_id) "
                "VALUES ('same-slug', 'p', 'p', %s::vector, %s)",
                (vector, owner),
            )
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(
                "CREATE UNIQUE INDEX uq_projects_normalized_slug ON projects (lower(btrim(slug)))"
            )


def test_migration_037_rejects_same_owner_duplicate_normalized_hash(tmp_path):
    with _scratch_migration_db(tmp_path, 36, 37) as (conn, apply_037, _):
        owners = [conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, 'test') RETURNING id",
            (f"dedup-owner-{uuid4().hex}",),
        ).fetchone()[0] for _ in range(2)]
        vector = "[" + ",".join("0.0" for _ in range(384)) + "]"
        result = apply_037()
        assert result.returncode == 0, f"037 failed:\n{result.stdout}\n{result.stderr}"
        for owner in owners:
            conn.execute(
                "INSERT INTO memories (owner_id, proyecto, scope, entity_id, topic_key, titulo, contenido, embedding, normalized_hash, visibility) "
                "VALUES (%s, 'dedup-project', 'agent', 'agent:dedup', %s, 'fact', 'same', %s::vector, 'same-hash', 'global')",
                (owner, f"topic-{owner}", vector),
            )
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(
                "INSERT INTO memories (owner_id, proyecto, scope, entity_id, topic_key, titulo, contenido, embedding, normalized_hash, visibility) "
                "VALUES (%s, 'dedup-project', 'agent', 'agent:dedup', 'another-topic', 'fact', 'same', %s::vector, 'same-hash', 'global')",
                (owners[0], vector),
            )


def test_migration_037_documented_rollback_fails_with_cross_owner_hash_duplicates(tmp_path):
    """Evidence: 037's documented rollback fails when cross-owner hash duplicates exist."""
    with _scratch_migration_db(tmp_path, 36, 37) as (conn, apply_037, migrations):
        owners = [conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, 'test') RETURNING id",
            (f"rollback-owner-{uuid4().hex}",),
        ).fetchone()[0] for _ in range(2)]
        vector = "[" + ",".join("0.0" for _ in range(384)) + "]"
        result = apply_037()
        assert result.returncode == 0, f"037 failed:\n{result.stdout}\n{result.stderr}"
        for owner in owners:
            conn.execute(
                "INSERT INTO memories (owner_id, proyecto, scope, entity_id, topic_key, titulo, contenido, embedding, normalized_hash, visibility) "
                "VALUES (%s, 'rollback-project', 'agent', 'agent:rollback', %s, 'fact', 'same', %s::vector, 'rollback-hash', 'global')",
                (owner, f"topic-{owner}", vector),
            )
        rollback = "\n".join(line.split("-- Rollback: ", 1)[1] for line in next(
            migration for migration in migrations if _migration_number(migration) == 37
        ).read_text().splitlines() if line.startswith("-- Rollback: "))
        with pytest.raises(psycopg.errors.UniqueViolation) as error:
            conn.execute(rollback)
        assert "uq_memories_normalized_content" in str(error.value)


def test_migration_039_user_profile_constraints_and_rollback(tmp_path):
    with _scratch_migration_db(tmp_path, 38, 39) as (conn, apply_039, migrations):
        result = apply_039()
        assert result.returncode == 0, f"039 failed:\n{result.stdout}\n{result.stderr}"
        columns = conn.execute(
            "SELECT column_name, character_maximum_length, is_nullable "
            "FROM information_schema.columns WHERE table_name='users' "
            "AND column_name IN ('email', 'name', 'phone', 'position') ORDER BY column_name"
        ).fetchall()
        assert columns == [
            ("email", 200, "YES"), ("name", 200, "YES"),
            ("phone", 30, "YES"), ("position", 120, "YES"),
        ]
        indexes = conn.execute(
            "SELECT indexdef FROM pg_indexes WHERE indexname='uq_users_lower_email'"
        ).fetchone()
        assert indexes and "lower((email)::text)" in indexes[0] and "WHERE (email IS NOT NULL)" in indexes[0]
        conn.execute("INSERT INTO users (username, password_hash, email) VALUES ('profile-039-a', 'x', 'Case@Example.com')")
        conn.execute("INSERT INTO users (username, password_hash) VALUES ('profile-039-null-a', 'x'), ('profile-039-null-b', 'x')")
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute("INSERT INTO users (username, password_hash, email) VALUES ('profile-039-b', 'x', 'case@example.COM')")
        migration = next(item for item in migrations if _migration_number(item) == 39)
        rollback = "\n".join(
            line.split("-- Rollback: ", 1)[1]
            for line in migration.read_text().splitlines()
            if line.startswith("-- Rollback: ")
        )
        conn.execute(rollback)
        assert conn.execute(
            "SELECT count(*) FROM information_schema.columns WHERE table_name='users' "
            "AND column_name IN ('email', 'name', 'phone', 'position')"
        ).fetchone() == (0,)
        assert conn.execute(
            "SELECT count(*) FROM pg_indexes WHERE indexname='uq_users_lower_email'"
        ).fetchone() == (0,)


def test_migration_047_calendar_sync_cascades_for_app_role(tmp_path):
    with _scratch_migration_db(tmp_path, 46, 47) as (conn, apply_047, _):
        customer_id = conn.execute(
            "INSERT INTO customers (phone_e164) VALUES ('+56904700001') RETURNING id"
        ).fetchone()[0]
        user_id = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, 'test') RETURNING id",
            (f"migration-047-{uuid4().hex}",),
        ).fetchone()[0]
        case_id = conn.execute(
            "INSERT INTO cases (customer_id, service) VALUES (%s, 'visit') RETURNING id",
            (customer_id,),
        ).fetchone()[0]
        appointment_id = conn.execute(
            "INSERT INTO appointments (service, customer_id, case_id, technician_id, local_start, timezone, "
            "starts_at, ends_at, duration_minutes) VALUES ('visit', %s, %s, %s, now(), 'UTC', now(), "
            "now() + interval '1 hour', 60) RETURNING id",
            (customer_id, case_id, user_id),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO appointment_calendar_sync (appointment_id, uid, idempotency_key, timezone) "
            "VALUES (%s, 'migration-047@example.test', 'migration-047', 'UTC')",
            (appointment_id,),
        )
        result = apply_047()
        assert result.returncode == 0, f"047 failed:\n{result.stdout}\n{result.stderr}"

        app_parts = conninfo_to_dict(conn.info.dsn)
        app_parts.update(user="app", password="app")
        with psycopg.connect(make_conninfo(**app_parts), autocommit=True) as app_conn:
            app_conn.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
        assert conn.execute(
            "SELECT count(*) FROM appointment_calendar_sync WHERE appointment_id = %s", (appointment_id,)
        ).fetchone() == (0,)


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
        ("031_internal_chat_thread_project",),
        ("032_case_conversation_nullable",),
        ("033_customer_archived_at",),
        ("034_project_owners",),
        ("035_customer_equipment",),
        ("036_case_amount",),
        ("037_memory_owner_dedup",),
        ("038_customer_merge",),
        ("039_user_profile",),
        ("040_project_config",),
        ("041_kb_project_scope",),
        ("042_project_files",),
        ("043_document_format_docx_xlsx",),
        ("044_assistant_artifacts",),
        ("045_automation_installations",),
        ("046_automation_rule_target_content",),
        ("047_appointment_calendar_sync_cascade",),
        ("048_technician_weekly_schedule",),
        ("049_drop_automation_rule_template_event",),
    ]


def test_memory_dedup_index_includes_owner_and_allows_cross_owner_duplicates(migrated_db, admin_conn):
    index = admin_conn.execute(
        "SELECT indexdef FROM pg_indexes WHERE tablename='memories' "
        "AND indexname='uq_memories_normalized_content'"
    ).fetchone()
    assert index is not None
    assert "(owner_id, proyecto, scope, entity_id, normalized_hash)" in index[0]
    embedding = "[" + ",".join("0.1" for _ in range(384)) + "]"
    owners = [admin_conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (%s, 'test') RETURNING id",
        (f"memory-dedup-{uuid4().hex}",),
    ).fetchone()[0] for _ in range(2)]
    for owner_id in owners:
        admin_conn.execute(
            "INSERT INTO memories (owner_id, proyecto, scope, entity_id, topic_key, titulo, contenido, "
            "embedding, normalized_hash, visibility) VALUES (%s, 'casa', 'agent', 'agent:casa', %s, 'fact', "
            "'same content', %s::vector, 'same-hash', 'global')",
            (owner_id, f"fact-{owner_id}", embedding),
        )


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


def test_cases_conversation_id_is_nullable(migrated_db, admin_conn):
    """Cases created outside conversations do not require a conversation."""
    column = admin_conn.execute(
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_name = 'cases' AND column_name = 'conversation_id'"
    ).fetchone()
    assert column == ("YES",)


def test_case_amount_is_nullable_numeric_without_default(migrated_db, admin_conn):
    column = admin_conn.execute(
        "SELECT data_type, is_nullable, column_default FROM information_schema.columns "
        "WHERE table_name = 'cases' AND column_name = 'amount'"
    ).fetchone()
    assert column == ("numeric", "YES", None)


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


def test_customers_merge_tombstone_column(migrated_db, admin_conn):
    column = admin_conn.execute(
        "SELECT data_type, is_nullable FROM information_schema.columns "
        "WHERE table_name = 'customers' AND column_name = 'merged_into_customer_id'"
    ).fetchone()
    assert column == ("bigint", "YES")
    fk = admin_conn.execute(
        "SELECT ccu.table_name, ccu.column_name FROM information_schema.constraint_column_usage ccu "
        "JOIN information_schema.key_column_usage kcu ON ccu.constraint_name = kcu.constraint_name "
        "WHERE kcu.table_name = 'customers' AND kcu.column_name = 'merged_into_customer_id'"
    ).fetchone()
    assert fk == ("customers", "id")
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


def test_app_role_full_crud_on_customer_equipment(migrated_db, app_conn):
    app_conn.execute(
        "INSERT INTO customers (phone_e164) VALUES ('+56922222223')"
    )
    customer_id = app_conn.execute(
        "SELECT id FROM customers WHERE phone_e164 = '+56922222223'"
    ).fetchone()[0]
    app_conn.execute(
        "INSERT INTO customer_equipment (customer_id, details) VALUES (%s, 'capture')",
        (customer_id,),
    )
    app_conn.execute(
        "UPDATE customer_equipment SET brand = 'Bosch' WHERE customer_id = %s",
        (customer_id,),
    )
    row = app_conn.execute(
        "SELECT brand FROM customer_equipment WHERE customer_id = %s", (customer_id,)
    ).fetchone()
    assert row == ("Bosch",)
    app_conn.execute("DELETE FROM customer_equipment WHERE customer_id = %s", (customer_id,))


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
    assert by_type["document_format"] == ["pdf", "md", "csv", "docx", "xlsx"]


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
