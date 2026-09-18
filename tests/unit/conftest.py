"""DB-free unit test harness (config-agente-lumat, PR 1).

Unit tests assert that `agent/*.md` content matches untouched node constants
(AC-3/AC-6) and that `agent/registry.yaml` parses to exactly one `orchestrator`
(AC-4). They never touch a database, so this conftest only guarantees env vars
that app modules require before import and exposes the repo root for reading
`agent/` files. No DB fixtures here on purpose.
"""

import os
from pathlib import Path
from _testdb import admin_database_url, database_url

# Required by pydantic-settings before any `app.*` import. Values are inert
# test placeholders — the unit suite never opens a DB connection.
for _key, _value in {
    "APP_SECRET": "test-app-secret",
    "VERIFY_TOKEN": "test-verify-token",
    "DATABASE_URL": database_url(),
    "DEEPSEEK_API_KEY": "sk-test",
    "META_ACCESS_TOKEN": "meta-test-token",
    "META_PHONE_NUMBER_ID": "123456789",
    "PANEL_SESSION_SECRET": "test-panel-session-secret",
}.items():
    os.environ.setdefault(_key, _value)

ADMIN_DB_URL = admin_database_url()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


import pytest  # noqa: E402


# The top-level tests/conftest.py declares an autouse per-test `clean_db`
# (which depends on a real `migrated_db` Postgres reset). Those fixtures must
# NOT run for this DB-free unit suite, or every assertion would require a
# reachable database (the DIFF between "DB-free" here and the integration
# harness). Pytest resolves fixtures by nearest definition, so these no-op
# overrides win for tests under tests/unit/.
@pytest.fixture(scope="session")
def migrated_db():
    """No-op override — this suite never touches Postgres."""
    yield


@pytest.fixture(autouse=True)
def clean_db():
    """No-op override — nothing to reset for a DB-free unit suite."""
    yield


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return _repo_root()
