"""Panel JSON API auth dependencies (design D4; PDW-AUTH-1, PDW-API-4).

Parallel to `app/panel/deps.py` but JSON-401 instead of HTML-302: missing or
stale sessions raise 401 `{"detail":"unauthorized"}` (PDW-AUTH-1) so the SPA
never follows a redirect to the login page. The Jinja deps are untouched —
the 302 vs 401 split is by route family, never by `Accept` header.

Reuses `get_db` from `app/panel/deps.py` (same request-scoped session and
commit-on-success contract, no duplication). The user row is re-read from
the DB on every request, so a deactivated account loses access immediately
(identical to the Jinja dep).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException
from starlette.requests import HTTPConnection
from sqlalchemy.orm import Session

from app.models import User
from app.panel.deps import get_db


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="unauthorized")


def get_current_user_json(
    request: HTTPConnection, session: Session = Depends(get_db)
) -> User:
    """Resolve the signed-session user; JSON 401 when absent (PDW-AUTH-1)."""
    user_id = request.session.get("user_id")
    if user_id is None:
        raise _unauthorized()
    user = session.get(User, user_id)
    if user is None or not user.active:
        raise _unauthorized()
    return user


def require_user_json(current: User = Depends(get_current_user_json)) -> User:
    """Any authenticated panel user, including technician agenda users."""
    return current


def require_operator_json(current: User = Depends(get_current_user_json)) -> User:
    if current.role.value not in {"admin", "operador"}:
        raise HTTPException(status_code=403, detail="panel role required")
    return current


def require_dashboard_user(current: User = Depends(require_user_json)) -> User:
    if current.role.value not in {"admin", "operador"}:
        raise HTTPException(status_code=403, detail="dashboard role required")
    return current


def require_tecnico(current: User = Depends(get_current_user_json)) -> User:
    if current.role.value != "tecnico":
        raise HTTPException(status_code=403, detail="tecnico role required")
    return current


def require_admin_json(current: User = Depends(get_current_user_json)) -> User:
    """Admin-only JSON routes (PDW-API-4): operador -> 403 JSON."""
    if current.role.value != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    return current
