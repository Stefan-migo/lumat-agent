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
from pathlib import Path

import bcrypt
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Appointment,
    AppointmentStatus,
    AssistantArtifact,
    AssistantAttachment,
    Case,
    Conversation,
    InternalChatThread,
    Memory,
    Message,
    NotificationOperation,
    PanelNotification,
    PanelSecret,
    Project,
    ProjectAlias,
    ProjectFile,
    PushSubscription,
    Settings,
    TechnicianAvailability,
    TechnicianWeeklySchedule,
    User,
    UserRole,
)

# AP-1: lock after this many consecutive failures, for this long.
MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15


def hash_password(password: str) -> str:
    """bcrypt hash for a plaintext panel password (seed script + tests).

    The work factor comes from `settings.panel_bcrypt_rounds`; `verify_password`
    needs no matching change because bcrypt stores the cost inside the hash.
    """
    rounds = get_settings().panel_bcrypt_rounds
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


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


def active_admin_count(session: Session) -> int:
    """Count active administrators for last-admin deletion guards."""
    return session.scalar(
        select(func.count()).select_from(User).where(
            User.role == UserRole.ADMIN, User.active.is_(True)
        )
    ) or 0


class UserDeleteBlocked(Exception):
    """A user cannot be hard-deleted until the named obstacle is resolved."""


def delete_user(session: Session, user: User) -> None:
    """Hard-delete a user: dereference what survives, remove what is theirs.

    A user with `booked` appointments blocks the delete (those business records need a technician,
    so reassign them first). Otherwise every nullable "who did it" reference is nulled so the record
    survives without the author, the user's own rows are deleted, and the user row goes last. The
    assistant threads cascade to their messages/attachments/artifacts; the blobs those rows point to
    are removed first so the cascade never strands a file.
    """
    booked = session.scalar(
        select(func.count()).select_from(Appointment).where(
            Appointment.technician_id == user.id,
            Appointment.status == AppointmentStatus.BOOKED,
        )
    ) or 0
    if booked:
        raise UserDeleteBlocked("reassign the user's appointments before deleting")

    # 1. Dereference the nullable attribution columns; the records survive.
    for model, column in (
        (Project, Project.owner_id),
        (ProjectAlias, ProjectAlias.owner_id),
        (Conversation, Conversation.responsible_id),
        (Message, Message.author_id),
        (Case, Case.responsible_id),
        (Memory, Memory.owner_id),
        (Settings, Settings.updated_by),
        (PanelSecret, PanelSecret.updated_by),
        (NotificationOperation, NotificationOperation.user_id),
        (Appointment, Appointment.technician_id),
        (ProjectFile, ProjectFile.owner_id),
    ):
        session.execute(update(model).where(column == user.id).values(**{column.key: None}))

    # 2. Remove the user's own rows, blobs first (the thread cascade deletes the rows).
    thread_ids = session.scalars(
        select(InternalChatThread.id).where(InternalChatThread.user_id == user.id)
    ).all()
    if thread_ids:
        for blob in session.scalars(
            select(AssistantArtifact.stored_path).where(AssistantArtifact.thread_id.in_(thread_ids))
        ).all():
            Path(blob).unlink(missing_ok=True)
        for blob in session.scalars(
            select(AssistantAttachment.stored_path).where(AssistantAttachment.thread_id.in_(thread_ids))
        ).all():
            Path(blob).unlink(missing_ok=True)

    session.execute(delete(TechnicianAvailability).where(TechnicianAvailability.technician_id == user.id))
    session.execute(delete(TechnicianWeeklySchedule).where(TechnicianWeeklySchedule.technician_id == user.id))
    session.execute(delete(PanelNotification).where(PanelNotification.user_id == user.id))
    session.execute(delete(PushSubscription).where(PushSubscription.user_id == user.id))
    session.execute(delete(InternalChatThread).where(InternalChatThread.user_id == user.id))

    session.delete(user)


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
