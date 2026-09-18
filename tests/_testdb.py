"""Derive the isolated test database identity for this worktree."""

import hashlib
import os
import shlex
import sys
from pathlib import Path


_WORKTREE_NAME = Path(__file__).resolve().parents[1].name


def _slug(value: str) -> str:
    if value and all(char in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in value):
        return value
    base = "".join(
        char.lower()
        if "A" <= char <= "Z"
        else char
        if char in "abcdefghijklmnopqrstuvwxyz0123456789-"
        else "-"
        for char in value
    )
    return f"{base}-{hashlib.sha256(value.encode()).hexdigest()[:8]}"


def _derive_worktree(name: str) -> tuple[str, int]:
    digest = hashlib.sha256(name.encode()).hexdigest()
    return _slug(name), 5432 + int(digest, 16) % 1000


def project_name() -> str:
    return os.environ.get("TEST_DB_PROJECT", f"lumat-test-{_derive_worktree(_WORKTREE_NAME)[0]}")


def host_port() -> int:
    override = os.environ.get("TEST_DB_PORT")
    if override is not None:
        return int(override)
    return _derive_worktree(_WORKTREE_NAME)[1]


def _default_database_url() -> str:
    return f"postgresql+psycopg://app:app@localhost:{host_port()}/lumat"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", _default_database_url())


def libpq_database_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


class TestDatabaseConfigError(RuntimeError):
    """The admin connection cannot be derived and nothing declared it."""


def admin_database_url() -> str:
    explicit = os.environ.get("TEST_ADMIN_DB_URL")
    if explicit:
        return explicit
    configured = os.environ.get("DATABASE_URL")
    if configured:
        return libpq_database_url(configured)
    # No password literal here on purpose. The value is declared once, in
    # infra/.env, which is also the file compose reads through --env-file; a
    # second copy in Python is what a secret scanner flags and what drifts.
    password = os.environ.get("TEST_POSTGRES_PASSWORD")
    if not password:
        raise TestDatabaseConfigError(
            "TEST_POSTGRES_PASSWORD is not set, so the admin database URL cannot be "
            "derived. Declare it in infra/.env, run `eval \"$(infra/test-db.sh env)\"`, "
            "or set TEST_ADMIN_DB_URL explicitly."
        )
    return f"postgresql://lumat:{password}@localhost:{host_port()}/lumat"


def env() -> dict[str, str]:
    return {
        "DATABASE_URL": database_url(),
        "TEST_ADMIN_DB_URL": admin_database_url(),
    }


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "env"
    if command == "port":
        print(host_port())
    elif command == "project":
        print(project_name())
    elif command == "env":
        for key, value in env().items():
            print(f"export {key}={shlex.quote(value)}")
    else:
        raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
