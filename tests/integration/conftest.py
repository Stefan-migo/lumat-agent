"""Shared fixtures for the integration suite (T0.2; extended by T1.2/T6.1).

Sets the full required environment BEFORE any `app.*` import so that
`app.main`'s module-level `create_app()` succeeds at collection time.

Batch 1 additions:
- DATABASE_URL now points at the real test DB (`lumat`, app role) — Batch 0
  never connected, so this is a no-op for B0 tests.
- `run_migrate()` / `migrated_db` fixture: apply schema via db/migrate.sh
  (idempotent) so integration tests run against the migrated schema.
"""

import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]

TEST_ENV = {
    "APP_SECRET": "test-app-secret",
    "VERIFY_TOKEN": "test-verify-token",
    "DATABASE_URL": "postgresql+psycopg://app:app@localhost:5432/lumat",
    "OPENAI_API_KEY": "sk-test",
    "META_ACCESS_TOKEN": "meta-test-token",
    "META_PHONE_NUMBER_ID": "123456789",
}

for _key, _value in TEST_ENV.items():
    os.environ.setdefault(_key, _value)

from app.config import get_settings  # noqa: E402  (env must be set first)
from app.main import create_app  # noqa: E402

ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)


def run_migrate() -> subprocess.CompletedProcess:
    """Run db/migrate.sh against the test DB (idempotent)."""
    env = os.environ.copy()
    env["DATABASE_URL"] = ADMIN_DB_URL
    env["APP_DB_PASSWORD"] = "app"
    env["PYTHON"] = str(REPO_ROOT / ".venv" / "bin" / "python")
    return subprocess.run(
        ["bash", str(REPO_ROOT / "db" / "migrate.sh")],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def migrated_db() -> None:
    """Apply migrations once per session (idempotent runner)."""
    result = run_migrate()
    assert result.returncode == 0, (
        f"migrate.sh failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


@pytest.fixture
def client() -> TestClient:
    """A TestClient over a freshly built app with the test environment."""
    get_settings.cache_clear()
    return TestClient(create_app())
