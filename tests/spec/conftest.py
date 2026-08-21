"""Shared fixtures for the spec suite (OpenSpec requirement scenarios).

Sets the full required environment BEFORE any `app.*` import so that
`app.main`'s module-level `create_app()` succeeds at collection time, and
mirrors the integration-suite harness: migrations applied via `db/migrate.sh`
(shared test DB), full table reset per test, and the local fastembed embedder
swapped for a deterministic fake (no ~130MB model download).
"""

import hashlib
import os
import subprocess
from pathlib import Path

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

TEST_ENV = {
    "APP_SECRET": "test-app-secret",
    "VERIFY_TOKEN": "test-verify-token",
    "DATABASE_URL": "postgresql+psycopg://app:app@localhost:5432/lumat",
    "DEEPSEEK_API_KEY": "sk-test",
    "META_ACCESS_TOKEN": "meta-test-token",
    "META_PHONE_NUMBER_ID": "123456789",
    "PANEL_SESSION_SECRET": "test-panel-session-secret",
    "LANGCHAIN_TRACING_V2": "false",
    "LANGCHAIN_TRACING": "false",
}

for _key, _value in TEST_ENV.items():
    os.environ.setdefault(_key, _value)

# Force the test key — an accidentally unmocked chat call fails fast.
os.environ["DEEPSEEK_API_KEY"] = "sk-test"

from app.services import kb as kb_service  # noqa: E402

ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)

# All business tables + memory tables (reset before each test — shared test DB).
TRUNCATE_TABLES = (
    "settings, audit_log, kb_chunks, kb_documents, conversation_events, "
    "cases, messages, conversations, customer_notes, users, customers, "
    "memories, memory_relations, memory_observations"
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


@pytest.fixture()
def admin_conn():
    # autocommit: assert-only connections for schema inspection tests.
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        yield conn


@pytest.fixture(scope="session")
def migrated_db() -> None:
    """Apply migrations once per session (idempotent runner)."""
    result = run_migrate()
    assert result.returncode == 0, (
        f"migrate.sh failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


@pytest.fixture(autouse=True)
def clean_db(migrated_db) -> None:
    """Reset all tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(f"TRUNCATE {TRUNCATE_TABLES} RESTART IDENTITY CASCADE")
    yield


@pytest.fixture
def fake_embedder(monkeypatch):
    """Swap kb.get_embedder() for a deterministic fake (no model download)."""

    def fake_embedding(text: str) -> list[float]:
        vec = [0.0] * kb_service.EMBED_DIMS
        lowered = text.lower()
        for i in range(len(lowered) - 2):
            bucket = (
                int.from_bytes(hashlib.sha256(lowered[i : i + 3].encode()).digest()[:4], "big")
                % kb_service.EMBED_DIMS
            )
            vec[bucket] = 1.0
        if not any(vec):
            vec[0] = 1.0
        return vec

    class _FakeEmbedder:
        def embed(self, texts):
            return (fake_embedding(t) for t in texts)

    monkeypatch.setattr(kb_service, "get_embedder", lambda: _FakeEmbedder())
