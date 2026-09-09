"""Panel user auth helpers (T5.1; AP-1, AP-2).

Minimal surface for the login flow and the seed script: bcrypt hash/verify,
username lookup, and the failed-login / lockout bookkeeping on `users`
(`failed_logins`/`locked_until` — 5 fails -> 15-minute lock, AP-1). Kept thin
on purpose: no CRUD, no roles beyond the model enum — the panel routes and
deps own the HTTP concerns.

All functions take an explicit session; the caller commits (matches
app/services/customers.py / audit.py style).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserRole

# AP-1: lock after this many consecutive failures, for this long.
MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15


def hash_password(password: str) -> str:
    """bcrypt hash for a plaintext panel password (seed script + tests)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time bcrypt check of a plaintext password against a hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        # Malformed/legacy hash — treat as mismatch, never crash the login.
        return False


def get_user_by_username(session: Session, username: str) -> User | None:
    """One user by exact username (usernames are unique)."""
    return session.scalar(select(User).where(User.username == username))


def is_locked(user: User, now: datetime | None = None) -> bool:
    """True while the account is inside its lock window (AP-1)."""
    if user.locked_until is None:
        return False
    return user.locked_until > (now or datetime.now(timezone.utc))


def record_failed_login(session: Session, user: User) -> bool:
    """Register one failed attempt; lock the account at the 5th (AP-1).

    Returns True when this failure TRIGGERED the lock. The counter resets to
    0 at the lock so the 15-minute ban is a clean window: when it expires the
    user gets a fresh set of attempts. The caller commits and audits.
    """
    user.failed_logins += 1
    if user.failed_logins >= MAX_FAILED_LOGINS:
        user.failed_logins = 0
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)
        return True
    return False


def reset_login_state(session: Session, user: User) -> None:
    """Clear the failed-login counter and any lock on success (AP-1)."""
    user.failed_logins = 0
    user.locked_until = None


def list_users(session: Session) -> list[User]:
    """Return panel users in the stable administrative order."""
    return list(session.scalars(select(User).order_by(User.username.asc(), User.id.asc())))


def create_user(session: Session, username: str, password: str, role: str) -> User:
    """Create a panel user; callers validate input and commit the session."""
    if session.scalar(select(User).where(User.username == username)) is not None:
        raise ValueError("username already exists")
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=UserRole(role),
        active=True,
    )
    session.add(user)
    session.flush()
    return user


def set_user_active(session: Session, user: User, active: bool) -> User:
    """Set a user's active state; callers commit the session."""
    user.active = active
    return user


def reset_password(session: Session, user: User, password: str) -> User:
    """Replace a user's password with a bcrypt hash; callers commit."""
    user.password_hash = hash_password(password)
    return user
