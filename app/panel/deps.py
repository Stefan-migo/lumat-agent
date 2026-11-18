"""Shared database session and cookie-auth dependencies for panel exports."""

from __future__ import annotations

from collections.abc import Generator
from fastapi import Depends, HTTPException, Request, Response, status
from starlette.datastructures import MutableHeaders
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User
from app.services import panel_sessions
from app.services.audit import record_audit
from app.services.users import is_locked

REMEMBER_COOKIE = "lumat_remember"
REMEMBER_MAX_AGE = 90 * 24 * 60 * 60

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


def _redirect_to_login(response: Response | None = None) -> HTTPException:
    headers = MutableHeaders(raw=response.raw_headers if response is not None else [])
    headers.append("Location", LOGIN_PATH)
    return HTTPException(
        status_code=status.HTTP_302_FOUND,
        headers=headers,
    )


def set_remember_cookie(response: Response, token: str) -> None:
    # secure=False matches SessionMiddleware's https_only=False behind TLS-terminating nginx.
    response.set_cookie(
        REMEMBER_COOKIE,
        token,
        max_age=REMEMBER_MAX_AGE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,
    )


def clear_panel_cookies(response: Response) -> None:
    response.delete_cookie("session", path="/")
    response.delete_cookie(REMEMBER_COOKIE, path="/")


def restore_panel_user(request, session: Session, response: Response | None = None) -> User | None:
    """Resolve the signed session or silently refill it from one remember token."""
    user_id = request.session.get("user_id")
    raw_token = request.cookies.get(REMEMBER_COOKIE)
    if user_id is not None:
        user = session.get(User, user_id)
        if user is None or not user.active:
            return None
        if raw_token:
            record = panel_sessions.resolve(session, raw_token)
            if record is not None and record.user_id == user.id:
                request.state.panel_session_record = record
            elif (
                (revoked := panel_sessions.find_revoked(session, raw_token)) is not None
                and revoked.user_id == user.id
                and revoked.revoked_at is not None
            ):
                request.session.clear()
                if response is not None:
                    clear_panel_cookies(response)
                return None
        return user

    if not raw_token:
        return None
    record = panel_sessions.resolve(session, raw_token)
    if record is None:
        revoked = panel_sessions.find_revoked(session, raw_token)
        if revoked is not None and revoked.revoked_at is not None:
            panel_sessions.revoke_all(session, revoked.user_id)
            record_audit(
                session,
                actor=str(revoked.user_id),
                action="auth.session_reuse",
                entity="user",
                entity_id=str(revoked.user_id),
            )
            session.commit()
        if response is not None:
            clear_panel_cookies(response)
        return None

    user = session.get(User, record.user_id)
    if user is None or not user.active or is_locked(user):
        if response is not None:
            clear_panel_cookies(response)
        return None

    # A WebSocket handshake cannot carry a Set-Cookie, so rotating here would revoke the token the
    # browser still holds and turn the next HTTP request into a reuse alarm -- one live connection
    # after a twelve-hour lapse would sign the operator out of every device. A non-HTTP connection
    # borrows the credential read-only; the next HTTP request rotates it and delivers the replacement.
    if request.scope.get("type") != "http":
        request.state.panel_session_record = record
        return user

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role.value
    token = panel_sessions.rotate(session, record)
    request.state.panel_session_record = panel_sessions.resolve(session, token)
    record_audit(
        session,
        actor=user.username,
        action="auth.session_restored",
        entity="user",
        entity_id=str(user.id),
    )
    if response is not None:
        set_remember_cookie(response, token)
    return user


def get_current_user(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
) -> User:
    """Resolve signed auth or restore it from the per-device remember token."""
    user = restore_panel_user(request, session, response)
    if user is None:
        raise _redirect_to_login(response)
    return user


def require_user(current: User = Depends(get_current_user)) -> User:
    """Any authenticated user (admin or operador) — shared routes."""
    return current
