"""Derive the isolated test database identity for this worktree."""

import hashlib
import os
import sys
from pathlib import Path


_WORKTREE_NAME = Path(__file__).resolve().parents[1].name


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value)


def project_name() -> str:
    return os.environ.get("TEST_DB_PROJECT", f"lumat-test-{_slug(_WORKTREE_NAME)}")


def host_port() -> int:
    override = os.environ.get("TEST_DB_PORT")
    if override is not None:
        return int(override)
    digest = hashlib.sha256(_WORKTREE_NAME.encode()).hexdigest()
    return 5432 + int(digest, 16) % 1000


def _default_database_url() -> str:
    return f"postgresql+psycopg://app:app@localhost:{host_port()}/lumat"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", _default_database_url())


def admin_database_url() -> str:
    explicit = os.environ.get("TEST_ADMIN_DB_URL")
    if explicit:
        return explicit
    configured = os.environ.get("DATABASE_URL")
    if configured and configured != _default_database_url():
        return configured.replace("postgresql+psycopg://", "postgresql://", 1)
    password = os.environ.get("TEST_POSTGRES_PASSWORD", "lumat")
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
            print(f"export {key}={value}")
    else:
        raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
