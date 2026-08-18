"""Panel JSON API authentication routes (B1/T1.2; PDW-AUTH-1/2/4, D1, D4).

POST /panel/api/login  -> JSON credentials, sets the same signed session cookie
GET  /panel/api/me     -> current user {username, role} (401 JSON, no redirect)
POST /panel/api/logout -> clears the session (audited)

Mirrors the Jinja route (app/panel/routes/auth.py): same service calls
(get_user_by_username / is_locked / verify_password / record_failed_login /
reset_login_state), same bcrypt + lockout sequence, same audit actions
(auth.login / auth.login_failed / auth.login_locked / auth.logout — SH-5).
Errors are always JSON {"detail": ...} (PDW-API-3); success answers JSON
instead of a 302 (D4). Cookie flags unchanged and no CORS (D1) — same
same_site=lax posture as today: no CSRF tokens, same-origin POSTs only.

Failure branches commit explicitly before raising so the audit rows and the
failed-login counter survive the request (get_db rolls back on exception).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_user_json
from app.panel.deps import get_db
from app.services.audit import record_audit
from app.services.users import (
    get_user_by_username,
    is_locked,
    record_failed_login,
    reset_login_state,
    verify_password,
)

router = APIRouter(tags=["panel-api-auth"])


class LoginBody(BaseModel):
    username: str
    password: str


def _audit(
    session: Session,
    *,
    action: str,
    username: str,
    user_id: int | None = None,
    after: dict | None = None,
) -> None:
    record_audit(
        session,
        actor=username,
        action=action,
        entity="user",
        entity_id=str(user_id) if user_id is not None else None,
        after=after,
    )


@router.post("/login")
def login(
    request: Request,
    body: LoginBody,
    session: Session = Depends(get_db),
) -> dict:
    """Verify credentials and open the same signed-cookie session (PDW-AUTH-4)."""
    user = get_user_by_username(session, body.username)
    if user is None or not user.active:
        # Same generic message for unknown/inactive users (no user oracle).
        _audit(
            session,
            action="auth.login_failed",
            username=body.username,
            user_id=user.id if user else None,
        )
        session.commit()
        raise HTTPException(status_code=401, detail="invalid credentials")

    if is_locked(user):
        _audit(
            session,
            action="auth.login_locked",
            username=body.username,
            user_id=user.id,
            after={"locked_until": user.locked_until.isoformat()},
        )
        session.commit()
        raise HTTPException(status_code=401, detail="account locked")

    if not verify_password(body.password, user.password_hash):
        triggered = record_failed_login(session, user)
        _audit(
            session,
            action="auth.login_failed",
            username=body.username,
            user_id=user.id,
            after=(
                {"locked": True}
                if triggered
                else {"failed_logins": user.failed_logins}
            ),
        )
        session.commit()
        raise HTTPException(status_code=401, detail="invalid credentials")

    reset_login_state(session, user)
    _audit(
        session,
        action="auth.login",
        username=body.username,
        user_id=user.id,
        after={"role": user.role.value},
    )
    session.commit()

    request.session.clear()
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role.value
    return {"ok": True, "role": user.role.value}


@router.get("/me")
def me(current: User = Depends(require_user_json)) -> dict:
    """Current user claims for the SPA route guard (PDW-AUTH-2)."""
    return {"username": current.username, "role": current.role.value}


@router.post("/logout")
def logout(
    request: Request,
    session: Session = Depends(get_db),
    current: User = Depends(require_user_json),
) -> dict:
    """Clear the session and audit the logout (SH-5)."""
    _audit(
        session,
        action="auth.logout",
        username=current.username,
        user_id=current.id,
    )
    session.commit()
    request.session.clear()
    return {"ok": True}
