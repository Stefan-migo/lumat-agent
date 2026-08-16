#!/usr/bin/env bash
# LumatAgent seed runner (T7.2; design deploy step 4).
#
# Seeds the two things a fresh deployment needs to be usable:
#
#   1. settings defaults (SS-1..5, EM-1/3/4, SS-3, AP-8) — every key in
#      app/services/settings.py SETTINGS_DEFAULTS (the single source of truth;
#      no values duplicated here), inserted only when missing.
#   2. the initial admin panel user (AP-1) — bcrypt hash from the password in
#      PANEL_ADMIN_PASSWORD, supplied via env at seed time (NEVER a literal in
#      the repo; placeholder in infra/.env.example — SH-2).
#
# Idempotent: existing settings rows and an existing admin username are left
# untouched (first seed wins) and a re-run writes no new audit rows, so it is
# safe to run on every deploy. Runs inside the api container
# (`docker compose ... exec api db/seed.sh`) where the venv + env vars live,
# or from the repo root with a .venv.
#
# Env:
#   DATABASE_URL          admin or app-role connection URL (default: local dev)
#   PANEL_ADMIN_USERNAME  initial admin username (default: "admin")
#   PANEL_ADMIN_PASSWORD  REQUIRED initial admin password (seed time only)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://lumat:lumat@localhost:5432/lumat}"
export SEED_REPO_ROOT="$REPO_ROOT"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
else
    PYTHON_BIN="${PYTHON:-python3}"
fi

exec "$PYTHON_BIN" - <<'PY'
import os
import sys

sys.path.insert(0, os.environ["SEED_REPO_ROOT"])

from app.db import session_scope
from app.models import Settings
from app.panel.seed_admin import seed_admin
from app.services.audit import record_audit
from app.services.settings import SETTINGS_DEFAULTS

# 1. settings defaults — insert only missing keys, audit only new inserts so a
#    re-run never grows audit_log (idempotence; SH-5 actor = system bootstrap).
with session_scope() as session:
    inserted = 0
    for key, value in SETTINGS_DEFAULTS.items():
        if session.get(Settings, key) is None:
            session.add(Settings(key=key, value=value))
            record_audit(
                session,
                actor="system",
                action="settings.seed",
                entity="settings",
                entity_id=key,
                after={"value": value},
            )
            inserted += 1
    print(f"settings: {inserted} inserted, {len(SETTINGS_DEFAULTS) - inserted} already present")

# 2. initial admin (AP-1, bcrypt) — first seed wins; password from env only.
try:
    created, message = seed_admin()
except ValueError as exc:
    print(f"error: {exc}", file=sys.stderr)
    sys.exit(1)
print(f"admin: {message}")
PY
