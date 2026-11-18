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

from fastapi import Depends, HTTPException, Response
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from sqlalchemy.orm import Session

from app.models import User
from app.panel.deps import get_db, restore_panel_user


def _unauthorized(response: Response | None = None) -> HTTPException:
    headers = MutableHeaders(raw=response.raw_headers if response is not None else [])
    return HTTPException(status_code=401, detail="unauthorized", headers=headers)


def get_current_user_json(
    request: HTTPConnection,
    response: Response,
    session: Session = Depends(get_db),
) -> User:
    """Resolve signed auth or restore it; unauthenticated callers get JSON 401."""
    user = restore_panel_user(request, session, response)
    if user is None:
        raise _unauthorized(response)
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


# agent-role-access D1/D6: every panel role reaches the internal agent chat and
# its own project namespaces. Declared explicitly (D8) so a future role is denied
# by default instead of silently granted; tool execution stays the fail-closed
# per-role boundary via ROLE_TOOL_ALLOWLIST.
AGENT_SURFACE_ROLES = frozenset({"admin", "operador", "tecnico"})


def require_agent_surface_json(current: User = Depends(get_current_user_json)) -> User:
    if current.role.value not in AGENT_SURFACE_ROLES:
        raise HTTPException(status_code=403, detail="agent surface role required")
    return current
