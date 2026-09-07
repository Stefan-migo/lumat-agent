"""Panel shared infrastructure (T5.1; design D7 — AP-1, AP-2).

One module owns the three things every panel route needs:

- `get_db` — request-scoped SQLAlchemy session (commit-on-success, same
  contract as `db.session_scope`).
- `templates` — the shared Jinja2Templates instance (templates/ lives next
  to this package).
- `get_current_user` / `require_user` / `require_admin` — server-side auth
  dependencies. Every panel route (except the login page itself) depends on
  `require_user`; admin-only routes additionally depend on `require_admin`.
  Role enforcement happens HERE, on the server — never in the template or
  the client (AP-2 "server-side only").
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.db import SessionLocal
from app.models import User

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)

LOGIN_PATH = "/panel/login"


def flash(request: Request, message: str) -> None:
    """Store a one-shot notice in the session (shown on the next page)."""
    request.session["flash"] = message


def pop_flash(request: Request) -> str | None:
    """Read and clear the one-shot notice for this request."""
    return request.session.pop("flash", None)


def get_db() -> Generator[Session, None, None]:
    """Request-scoped session: commit on success, rollback on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
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


def require_admin(current: User = Depends(get_current_user)) -> User:
    """Admin-only routes: settings and KB management (AP-2)."""
    if current.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin role required",
        )
    return current
