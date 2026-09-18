import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

import _testdb


def test_derivation_is_deterministic_and_in_range(monkeypatch):
    monkeypatch.delenv("TEST_DB_PORT", raising=False)
    monkeypatch.delenv("TEST_DB_PROJECT", raising=False)
    worktree_name = Path(_testdb.__file__).resolve().parents[1].name
    if all(char in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in worktree_name):
        slug = worktree_name
    else:
        slug = "".join(
            char.lower()
            if "A" <= char <= "Z"
            else char
            if char in "abcdefghijklmnopqrstuvwxyz0123456789-"
            else "-"
            for char in worktree_name
        )
        slug += "-" + hashlib.sha256(worktree_name.encode()).hexdigest()[:8]
    expected_port = 5432 + int(
        hashlib.sha256(worktree_name.encode()).hexdigest(), 16
    ) % 1000

    assert _testdb.host_port() == expected_port
    assert 5432 <= _testdb.host_port() <= 6431
    assert _testdb.project_name() == f"lumat-test-{slug}"
    assert _testdb.host_port() == _testdb.host_port()
    assert _testdb.project_name() == _testdb.project_name()


def test_slug_distinguishes_punctuation_and_is_ascii_for_unicode():
    assert _testdb._slug("foo_bar") != _testdb._slug("foo-bar")
    assert _testdb._slug("foo.bar") != _testdb._slug("foo-bar")
    unicode_slug = _testdb._slug("worktree-ñ")

    assert unicode_slug.isascii()
    assert all(char in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in unicode_slug)


def test_overrides_are_used(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_ADMIN_DB_URL", raising=False)
    # Deliberately a placeholder, never a plausible-looking password: this file
    # ships in the repository and a realistic literal is what scanners flag.
    password = "change-me"
    monkeypatch.setenv("TEST_POSTGRES_PASSWORD", password)
    monkeypatch.setenv("TEST_DB_PORT", "6001")
    monkeypatch.setenv("TEST_DB_PROJECT", "custom-test-db")

    assert _testdb.host_port() == 6001
    assert _testdb.project_name() == "custom-test-db"
    assert _testdb.database_url() == "postgresql+psycopg://app:app@localhost:6001/lumat"
    assert _testdb.admin_database_url() == (
        f"postgresql://lumat:{password}@localhost:6001/lumat"
    )


def test_explicit_urls_override_derivation(monkeypatch):
    monkeypatch.setenv("TEST_DB_PORT", "6001")
    monkeypatch.delenv("TEST_DB_PROJECT", raising=False)
    monkeypatch.delenv("TEST_ADMIN_DB_URL", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://custom:secret@db.example:6543/test"
    )
    assert _testdb.database_url() == "postgresql+psycopg://custom:secret@db.example:6543/test"
    assert _testdb.admin_database_url() == "postgresql://custom:secret@db.example:6543/test"


def test_declared_database_url_equal_to_default_is_honoured(monkeypatch):
    monkeypatch.setenv("TEST_DB_PORT", "6001")
    monkeypatch.delenv("TEST_ADMIN_DB_URL", raising=False)
    monkeypatch.delenv("TEST_POSTGRES_PASSWORD", raising=False)
    default_url = _testdb._default_database_url()
    monkeypatch.setenv("DATABASE_URL", default_url)

    assert _testdb.database_url() == default_url
    assert _testdb.admin_database_url() == default_url.replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


def test_admin_password_override(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_ADMIN_DB_URL", raising=False)
    monkeypatch.delenv("TEST_DB_PORT", raising=False)
    monkeypatch.delenv("TEST_DB_PROJECT", raising=False)
    monkeypatch.setenv("TEST_POSTGRES_PASSWORD", "secret")
    assert _testdb.admin_database_url() == (
        f"postgresql://lumat:secret@localhost:{_testdb.host_port()}/lumat"
    )


def test_missing_password_fails_loudly_instead_of_guessing(monkeypatch):
    """Regression guard: no password literal may creep back in.

    The default used to live here as well as in infra/.env, which a secret
    scanner flags and which drifts. The password is declared once, in
    infra/.env; when nothing declares it this must fail loudly, never guess.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_ADMIN_DB_URL", raising=False)
    monkeypatch.delenv("TEST_POSTGRES_PASSWORD", raising=False)

    with pytest.raises(_testdb.TestDatabaseConfigError):
        _testdb.admin_database_url()


def test_env_exports_preserve_shell_values_when_evaluated(monkeypatch):
    password = "$(printf pwned >&2)"
    child_env = os.environ.copy()
    child_env.pop("DATABASE_URL", None)
    child_env.pop("TEST_ADMIN_DB_URL", None)
    child_env["TEST_POSTGRES_PASSWORD"] = password

    emitted = subprocess.run(
        [sys.executable, str(Path(_testdb.__file__)) , "env"],
        env=child_env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    result = subprocess.run(
        [
            "bash",
            "-c",
            f"unset TEST_ADMIN_DB_URL; {emitted}printf '%s' \"$TEST_ADMIN_DB_URL\"",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == f"postgresql://lumat:{password}@localhost:{_testdb.host_port()}/lumat"
    assert result.stderr == ""
