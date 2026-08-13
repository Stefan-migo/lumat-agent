"""Panel authentication routes (T5.1; AP-1, AP-2, SH-5).

GET  /panel/login       -> login form (redirects to /panel/ when authed)
POST /panel/login       -> bcrypt verify + signed-cookie session (12 h)
POST /panel/logout      -> clear session (audited)

Login flow: username lookup -> active check -> lock check -> bcrypt verify.
Every outcome is audited (SH-5): auth.login on success, auth.login_failed on
bad credentials/unknown user, auth.login_locked on a locked account,
auth.logout on logout. The session payload carries only
user_id/username/role — the server re-reads the user row on every request
(see deps.get_current_user), so roles are never client-trusted (AP-2).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response
from sqlalchemy.orm import Session

from app.models import User
from app.panel.deps import get_db, require_user, templates
from app.services.audit import record_audit
from app.services.users import (
    get_user_by_username,
    is_locked,
    record_failed_login,
    reset_login_state,
    verify_password,
)

router = APIRouter(tags=["panel-auth"])

# AP-1: signed-session lifetime (Starlette SessionMiddleware max_age, seconds).
SESSION_MAX_AGE = 12 * 60 * 60


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


@router.get("/login")
def login_form(request: Request) -> Response:
    """Render the login form; already-authenticated users go to the panel."""
    if request.session.get("user_id") is not None:
        return RedirectResponse("/panel/", status_code=302)
    return templates.TemplateResponse(
        request, "login.html", {"error": None}
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_db),
) -> Response:
    """Verify credentials and open a signed-cookie session (AP-1)."""
    user = get_user_by_username(session, username)
    if user is None or not user.active:
        # Same generic message for unknown/inactive users (no user oracle).
        _audit(
            session,
            action="auth.login_failed",
            username=username,
            user_id=user.id if user else None,
        )
        return templates.TemplateResponse(
            request, "login.html", {"error": "invalid credentials"}
        )

    if is_locked(user):
        _audit(
            session,
            action="auth.login_locked",
            username=username,
            user_id=user.id,
            after={"locked_until": user.locked_until.isoformat()},
        )
        return templates.TemplateResponse(
            request, "login.html", {"error": "account locked"}
        )

    if not verify_password(password, user.password_hash):
        triggered = record_failed_login(session, user)
        _audit(
            session,
            action="auth.login_failed",
            username=username,
            user_id=user.id,
            after=(
                {"locked": True}
                if triggered
                else {"failed_logins": user.failed_logins}
            ),
        )
        return templates.TemplateResponse(
            request, "login.html", {"error": "invalid credentials"}
        )

    reset_login_state(session, user)
    _audit(
        session,
        action="auth.login",
        username=username,
        user_id=user.id,
        after={"role": user.role.value},
    )
    session.commit()

    request.session.clear()
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role.value
    return RedirectResponse("/panel/", status_code=302)


@router.post("/logout")
def logout(
    request: Request,
    session: Session = Depends(get_db),
    current: User = Depends(require_user),
) -> RedirectResponse:
    """Clear the session and audit the logout (SH-5)."""
    _audit(
        session,
        action="auth.logout",
        username=current.username,
        user_id=current.id,
    )
    session.commit()
    request.session.clear()
    return RedirectResponse("/panel/login", status_code=302)
