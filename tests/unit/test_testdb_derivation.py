import hashlib
from pathlib import Path

import _testdb


def test_derivation_is_deterministic_and_in_range():
    worktree_name = Path(_testdb.__file__).resolve().parents[1].name
    expected_port = 5432 + int(
        hashlib.sha256(worktree_name.encode()).hexdigest(), 16
    ) % 1000

    assert _testdb.host_port() == expected_port
    assert 5432 <= _testdb.host_port() <= 6431
    assert _testdb.project_name() == "lumat-test-lumat-agent-odd-test-db-isolation"
    assert _testdb.host_port() == _testdb.host_port()
    assert _testdb.project_name() == _testdb.project_name()


def test_overrides_are_used(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_ADMIN_DB_URL", raising=False)
    monkeypatch.setenv("TEST_DB_PORT", "6001")
    monkeypatch.setenv("TEST_DB_PROJECT", "custom-test-db")

    assert _testdb.host_port() == 6001
    assert _testdb.project_name() == "custom-test-db"
    assert _testdb.database_url() == "postgresql+psycopg://app:app@localhost:6001/lumat"
    assert _testdb.admin_database_url() == "postgresql://lumat:lumat@localhost:6001/lumat"


def test_explicit_urls_override_derivation(monkeypatch):
    monkeypatch.setenv("TEST_DB_PORT", "6001")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://custom:secret@db.example:6543/test"
    )
    assert _testdb.database_url() == "postgresql+psycopg://custom:secret@db.example:6543/test"
    assert _testdb.admin_database_url() == "postgresql://custom:secret@db.example:6543/test"


def test_admin_password_override(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_ADMIN_DB_URL", raising=False)
    monkeypatch.setenv("TEST_POSTGRES_PASSWORD", "secret")
    assert _testdb.admin_database_url() == (
        f"postgresql://lumat:secret@localhost:{_testdb.host_port()}/lumat"
    )
