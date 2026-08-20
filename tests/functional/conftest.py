"""Shared fixtures for the functional suite (T5.1 panel; AP-1..AP-8 flows).

Sets the full required environment BEFORE any `app.*` import so that
`app.main`'s module-level `create_app()` succeeds at collection time (same
pattern as tests/integration/conftest.py). The panel adds one required env
var on top of the integration env: PANEL_SESSION_SECRET (AP-1 signed-cookie
sessions — the cookie would be unsigned/untrusted without it).

The functional suite runs against the SAME shared test DB as integration,
so `clean_db` truncates the full table set (including `users` — panel
accounts) before every test, and `migrated_db` applies the migrations once
per session via db/migrate.sh (idempotent).
"""

import os
import subprocess
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]

TEST_ENV = {
    "APP_SECRET": "test-app-secret",
    "VERIFY_TOKEN": "test-verify-token",
    "DATABASE_URL": "postgresql+psycopg://app:app@localhost:5432/lumat",
    "DEEPSEEK_API_KEY": "sk-test",
    "META_ACCESS_TOKEN": "meta-test-token",
    "META_PHONE_NUMBER_ID": "123456789",
    # AP-1: panel session cookie signing secret (required at boot).
    "PANEL_SESSION_SECRET": "test-panel-session-secret",
    # LangGraph auto-tracing (langsmith) must never hit the network in tests.
    "LANGCHAIN_TRACING_V2": "false",
    "LANGCHAIN_TRACING": "false",
}

for _key, _value in TEST_ENV.items():
    os.environ.setdefault(_key, _value)

# The dev shell may carry a real DEEPSEEK_API_KEY — the panel tests must never
# use it (unmocked chat calls would spend real tokens). Force the test key.
os.environ["DEEPSEEK_API_KEY"] = "sk-test"

from app.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402

ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)

# Tables truncated before each test (full set incl. users — panel accounts).
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


@pytest.fixture(scope="session")
def migrated_db() -> None:
    """Apply migrations once per session (idempotent runner)."""
    result = run_migrate()
    assert result.returncode == 0, (
        f"migrate.sh failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


@pytest.fixture(autouse=True)
def clean_db(migrated_db) -> None:
    """Reset all panel + business tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            f"TRUNCATE {TRUNCATE_TABLES} RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture
def client() -> TestClient:
    """A TestClient over a freshly built app with the test environment."""
    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.fixture
def make_user():
    """Factory creating a panel user row directly (bcrypt hash) in a session."""

    def _make(username: str, password: str, role: str = "operador") -> int:
        from app.db import SessionLocal
        from app.models import User, UserRole
        from app.services.users import hash_password

        with SessionLocal() as session:
            user = User(
                username=username,
                password_hash=hash_password(password),
                role=UserRole(role),
                active=True,
            )
            session.add(user)
            session.flush()
            user_id = user.id
            session.commit()
            return user_id

    return _make


# ---------------------------------------------------------------------------
# Local embedder fake (deterministic — KB ingest/update embed via the seam)
# ---------------------------------------------------------------------------

EMBED_DIMS = 384


def _fake_embedding(text: str) -> list[float]:
    """Deterministic one-hot vector from char-trigram buckets (KB tests)."""
    import hashlib

    vec = [0.0] * EMBED_DIMS
    lowered = text.lower()
    for i in range(len(lowered) - 2):
        bucket = (
            int.from_bytes(hashlib.sha256(lowered[i : i + 3].encode()).digest()[:4], "big")
            % EMBED_DIMS
        )
        vec[bucket] = 1.0
    if not any(vec):
        vec[0] = 1.0
    return vec


@pytest.fixture(autouse=True)
def fake_embedder(monkeypatch):
    """Swap kb.get_embedder() for a deterministic fake (no model download).

    Autouse: S2 runs the graph through run_conversation on every turn, which
    persists per-turn memory (an embedding). The project contract is that the
    suite NEVER downloads the ~130MB model, so the seam is mounted by default
    for every functional test that drives the conversation flow through the
    client/ingest path.
    """
    from app.services import kb as kb_service

    class _FakeEmbedder:
        def embed(self, texts):
            return (_fake_embedding(t) for t in texts)

    monkeypatch.setattr(kb_service, "get_embedder", lambda: _FakeEmbedder())


@pytest.fixture
def login():
    """Login helper: authenticate as the given user through the login form."""

    def _login(client, username: str, password: str) -> None:
        resp = client.post(
            "/panel/login",
            data={"username": username, "password": password},
            follow_redirects=False,
        )
        assert resp.status_code == 302, "login must succeed"

    return _login


@pytest.fixture
def api_login():
    """JSON login helper (PDW-AUTH-4): authenticate via POST /panel/api/login.

    No redirects allowed — the JSON API must answer 200 JSON, never a 302 to
    the HTML login page (PDW-AUTH-1), so follow_redirects=False proves it.
    """

    def _login(client, username: str, password: str) -> None:
        resp = client.post(
            "/panel/api/login",
            json={"username": username, "password": password},
            follow_redirects=False,
        )
        assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"
        assert resp.headers["content-type"].startswith("application/json"), (
            "api login must answer JSON, not HTML"
        )

    return _login
