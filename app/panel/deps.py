"""Shared database session and cookie-auth dependencies for panel exports."""

from __future__ import annotations

from collections.abc import Generator
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User

LOGIN_PATH = "/panel/login"


def get_db() -> Generator[Session, None, None]:
    """Request-scoped session with fail-closed commit uncertainty."""
    session = SessionLocal()
    try:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="request commit outcome is uncertain; recovery is required",
            ) from exc
        try:
            from app.services.realtime import dispatch_staged_events

            dispatch_staged_events(session)
        except Exception:
            session.rollback()
            raise
    finally:
        session.close()


def _redirect_to_login() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": LOGIN_PATH},
    )


def get_current_user(
    request: Request, session: Session = Depends(get_db)
) -> User:
    """Resolve the signed-session user; redirect to login when absent.

    The session cookie holds only user_id/username/role (server-signed); the
    user row is re-read from the DB on every request so a deactivated or
    locked account loses access immediately.
    """
    user_id = request.session.get("user_id")
    if user_id is None:
        raise _redirect_to_login()
    user = session.get(User, user_id)
    if user is None or not user.active:
        raise _redirect_to_login()
    return user


def require_user(current: User = Depends(get_current_user)) -> User:
    """Any authenticated user (admin or operador) — shared routes."""
    return current
