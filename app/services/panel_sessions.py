"""Per-device, rotating remember credentials for signed panel sessions."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import PanelSession

TOKEN_LIFETIME = timedelta(days=90)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def issue(session: Session, user_id: int, user_agent: str | None = None) -> str:
    """Create a remember token, storing only its SHA-256 hash."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    session.add(
        PanelSession(
            user_id=user_id,
            token_hash=hash_token(token),
            user_agent=user_agent,
            created_at=now,
            last_used_at=now,
            expires_at=now + TOKEN_LIFETIME,
        )
    )
    return token


def _matching_row(session: Session, raw_token: str) -> PanelSession | None:
    candidate = hash_token(raw_token)
    rows = session.scalars(select(PanelSession).where(PanelSession.token_hash == candidate)).all()
    for row in rows:
        if secrets.compare_digest(row.token_hash, candidate):
            return row
    return None


def resolve(session: Session, raw_token: str) -> PanelSession | None:
    """Return a current token row only while active and within its lifetime."""
    row = _matching_row(session, raw_token)
    if row is None or row.revoked_at is not None:
        return None
    if row.expires_at <= datetime.now(timezone.utc):
        return None
    return row


def rotate(session: Session, record: PanelSession) -> str:
    """Revoke the presented token and issue its replacement."""
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    record.revoked_at = now
    record.replaced_by_hash = hash_token(token)
    record.last_used_at = now
    session.add(
        PanelSession(
            user_id=record.user_id,
            token_hash=record.replaced_by_hash,
            user_agent=record.user_agent,
            created_at=now,
            last_used_at=now,
            expires_at=now + TOKEN_LIFETIME,
        )
    )
    session.flush()
    return token


def revoke(session: Session, record: PanelSession) -> None:
    if record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)


def revoke_all(session: Session, user_id: int, *, keep_id: int | None = None) -> None:
    now = datetime.now(timezone.utc)
    statement = update(PanelSession).where(
        PanelSession.user_id == user_id,
        PanelSession.revoked_at.is_(None),
    )
    if keep_id is not None:
        statement = statement.where(PanelSession.id != keep_id)
    session.execute(statement.values(revoked_at=now))


def find_revoked(session: Session, raw_token: str) -> PanelSession | None:
    """Find a known credential that can no longer restore access."""
    row = _matching_row(session, raw_token)
    if row is None:
        return None
    if row.revoked_at is not None or row.expires_at <= datetime.now(timezone.utc):
        return row
    return None


def list_active(session: Session, user_id: int) -> list[PanelSession]:
    now = datetime.now(timezone.utc)
    return list(
        session.scalars(
            select(PanelSession)
            .where(
                PanelSession.user_id == user_id,
                PanelSession.revoked_at.is_(None),
                PanelSession.expires_at > now,
            )
            .order_by(PanelSession.created_at, PanelSession.id)
        )
    )
