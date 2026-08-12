#!/usr/bin/env bash
# LumatAgent migration runner (T1.1).
#
# Applies db/migrations/*.sql in lexical order, recording each applied version
# in the schema_migrations table (idempotent — safe to run repeatedly).
# Creates the least-privilege `app` role (INSERT+SELECT on audit_log only,
# full CRUD on business tables; SH-2/SH-5) using APP_DB_PASSWORD from the
# environment — the password is NEVER committed to the repo.
#
# Uses python3 + psycopg (already a project dependency) so it runs both on the
# host and inside the api container without needing the psql binary.
#
# Env:
#   DATABASE_URL      admin connection URL (default: dev compose lumat)
#   APP_DB_PASSWORD   password for the `app` role (default: app)
#   PYTHON            python interpreter override (default: python3)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations"

export DATABASE_URL="${DATABASE_URL:-postgresql://lumat:lumat@localhost:5432/lumat}"
export APP_DB_PASSWORD="${APP_DB_PASSWORD:-app}"

# Prefer the repo's virtualenv (psycopg lives there on the host and in the api
# container after `uv sync`); fall back to an explicit override, then python3.
if [ -x "$SCRIPT_DIR/../.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/../.venv/bin/python"
else
    PYTHON_BIN="${PYTHON:-python3}"
fi

exec "$PYTHON_BIN" - "$MIGRATIONS_DIR" <<'PY'
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

migrations_dir = Path(sys.argv[1])
url = os.environ["DATABASE_URL"]
password = os.environ["APP_DB_PASSWORD"]

with psycopg.connect(url, autocommit=True) as conn:
    # 1. app role — idempotent create, password kept in sync from env
    exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'app'").fetchone()
    if exists is None:
        conn.execute(
            sql.SQL("CREATE ROLE app LOGIN PASSWORD {}").format(sql.Literal(password))
        )
        print("created role app")
    else:
        conn.execute(
            sql.SQL("ALTER ROLE app WITH LOGIN PASSWORD {}").format(sql.Literal(password))
        )

    # 2. connect grant — explicit so prod hardening can revoke PUBLIC
    dbname = conn.info.dbname
    conn.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO app").format(sql.Identifier(dbname))
    )

    # 3. schema_migrations tracking table
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "  version TEXT PRIMARY KEY,"
        "  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()"
        ")"
    )

    # 4. apply pending migrations, each in its own transaction
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    for migration in sorted(migrations_dir.glob("*.sql")):
        version = migration.stem
        if version in applied:
            print(f"skip {version} (already applied)")
            continue
        print(f"applying {version}")
        with conn.transaction():
            conn.execute(migration.read_text())
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)", (version,)
            )

    print("migrations up to date")
PY
