"""T7.2 integration tests — db/seed.sh (design deploy step 4).

Runs the seed runner against the test DB (same pattern as `run_migrate`) and
proves the deploy contract:

- idempotent: two runs insert the settings defaults exactly once, create the
  initial admin exactly once, and write NO audit rows on the second run
- content: every `SETTINGS_DEFAULTS` key (the single source of truth in
  app/services/settings.py) is stored with its default value, and the admin
  user is bcrypt-verifiable with role `admin` (AP-1)
- fail-fast: a missing PANEL_ADMIN_PASSWORD exits non-zero with a clear error

The admin password is supplied via env at seed time — never a literal in the
repo (SH-2; infra/.env.example documents the placeholder).
"""

import os
import subprocess
from pathlib import Path

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import AuditLog, Settings, User
from app.services.settings import SETTINGS_DEFAULTS
from app.services.users import verify_password

REPO_ROOT = Path(__file__).resolve().parents[2]
_seed_admin_db_url = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)
SEED_ADMIN_DB_URL = os.environ.get(
    "TEST_SEED_DB_URL",
    _seed_admin_db_url.replace("postgresql://", "postgresql+psycopg://", 1),
)


def _run_seed(**env_override) -> subprocess.CompletedProcess:
    """Run db/seed.sh against the test DB with a fixed admin bootstrap env."""
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": SEED_ADMIN_DB_URL,
            "PANEL_ADMIN_USERNAME": "seed-admin",
            "PANEL_ADMIN_PASSWORD": "seed-admin-password",
        }
    )
    env.update(env_override)
    env["PYTHON"] = str(REPO_ROOT / ".venv" / "bin" / "python")
    return subprocess.run(
        ["bash", str(REPO_ROOT / "db" / "seed.sh")],
        env=env,
        capture_output=True,
        text=True,
    )


def _count(model) -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(model))


def test_seed_applies_cleanly_twice(migrated_db):
    """Two runs: settings/users inserted once, audit_log untouched on re-run."""
    first = _run_seed()
    assert first.returncode == 0, f"first seed failed:\n{first.stdout}\n{first.stderr}"
    assert "inserted" in first.stdout, first.stdout

    audit_before = _count(AuditLog)
    second = _run_seed()
    assert second.returncode == 0, f"second seed failed:\n{second.stdout}\n{second.stderr}"
    assert "already present" in second.stdout, second.stdout

    assert _count(Settings) == len(SETTINGS_DEFAULTS), "settings duplicated on re-run"
    assert _count(User) == 1, "admin duplicated on re-run"
    assert _count(AuditLog) == audit_before, "re-run must not write audit rows"


def test_seed_inserts_settings_defaults_and_admin(migrated_db):
    """The seeded rows match SETTINGS_DEFAULTS and the admin verifies (AP-1)."""
    result = _run_seed()
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    with SessionLocal() as session:
        stored = {row.key: row.value for row in session.scalars(select(Settings))}
        assert stored == SETTINGS_DEFAULTS, "stored settings drift from defaults"

        admin = session.scalar(select(User).where(User.username == "seed-admin"))
        assert admin is not None, "admin user missing after seed"
        assert admin.role.value == "admin"
        assert verify_password("seed-admin-password", admin.password_hash), (
            "seeded admin password does not verify against the bcrypt hash"
        )


def test_seed_requires_admin_password(migrated_db):
    """Missing PANEL_ADMIN_PASSWORD fails loudly instead of seeding silently."""
    result = _run_seed(PANEL_ADMIN_PASSWORD="")
    assert result.returncode != 0, "seed must fail without the admin password"
    assert "PANEL_ADMIN_PASSWORD is required" in result.stderr, result.stderr
