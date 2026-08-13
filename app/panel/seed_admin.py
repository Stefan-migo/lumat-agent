"""Seed the initial admin panel account (T5.1; AP-1).

Standalone script (NOT a service/daemon — design deploy step 4 seeds settings
+ admin at deploy; T7.2 runs it). Creates the admin user with a bcrypt hash,
idempotently: an existing username is left untouched (first seed wins).

Usage:
    PANEL_ADMIN_USERNAME=admin PANEL_ADMIN_PASSWORD=<secret> \
        .venv/bin/python app/panel/seed_admin.py

Env:
    PANEL_ADMIN_USERNAME   admin username (default "admin")
    PANEL_ADMIN_PASSWORD   required — the initial bcrypt-hashed password
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import select

from app.db import session_scope
from app.models import User, UserRole
from app.services.audit import record_audit
from app.services.users import get_user_by_username, hash_password

DEFAULT_USERNAME = "admin"


def seed_admin(
    username: str | None = None, password: str | None = None
) -> tuple[bool, str]:
    """Create the initial admin user; returns (created, message).

    Idempotent: when the username already exists nothing is changed (first
    seed wins — a re-run after deploy must not reset the admin password).
    """
    username = username or os.environ.get("PANEL_ADMIN_USERNAME", DEFAULT_USERNAME)
    password = password or os.environ.get("PANEL_ADMIN_PASSWORD")
    if not password:
        raise ValueError("PANEL_ADMIN_PASSWORD is required")

    with session_scope() as session:
        existing = get_user_by_username(session, username)
        if existing is not None:
            return False, f"user {username!r} already exists — not overwritten"
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            active=True,
        )
        session.add(user)
        session.flush()
        record_audit(
            session,
            actor="system",
            action="user.seed_admin",
            entity="user",
            entity_id=str(user.id),
            after={"username": username, "role": "admin"},
        )
    return True, f"created admin user {username!r}"


if __name__ == "__main__":
    try:
        created, message = seed_admin()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(message)
