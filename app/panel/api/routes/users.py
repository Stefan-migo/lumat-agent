from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_admin_json
from app.panel.api.serializers import to_admin_user_dict
from app.panel.deps import get_db
from app.services import users
from app.services.audit import record_audit

router = APIRouter(tags=["panel-api-users"])


class UserBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    password: str
    role: str


class PasswordBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str


def _validate_username(username: str) -> str:
    value = username.strip()
    if not value:
        raise HTTPException(status_code=422, detail="username must not be blank")
    return value


def _validate_password(password: str) -> str:
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters")
    return password


def _get_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.get("/users")
def list_users(
    session: Session = Depends(get_db), current: User = Depends(require_admin_json)
) -> dict:
    return {"users": [to_admin_user_dict(user) for user in users.list_users(session)]}


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    username = _validate_username(body.username)
    password = _validate_password(body.password)
    if body.role not in {"admin", "operador", "tecnico"}:
        raise HTTPException(status_code=422, detail="role is invalid")
    try:
        user = users.create_user(session, username, password, body.role)
    except ValueError:
        raise HTTPException(status_code=409, detail="username already exists")
    safe_user = to_admin_user_dict(user)
    record_audit(
        session,
        actor=current.username,
        action="user.create",
        entity="user",
        entity_id=str(user.id),
        after=safe_user,
    )
    session.commit()
    return {"user": safe_user}


@router.post("/users/{user_id}/toggle-active")
def toggle_active(
    user_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    user = _get_user(session, user_id)
    if user.id == current.id:
        raise HTTPException(status_code=403, detail="admins cannot toggle their own account")
    before = to_admin_user_dict(user)
    users.set_user_active(session, user, not user.active)
    safe_user = to_admin_user_dict(user)
    record_audit(
        session,
        actor=current.username,
        action="user.toggle_active",
        entity="user",
        entity_id=str(user.id),
        before=before,
        after=safe_user,
    )
    session.commit()
    return {"user": safe_user}


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    body: PasswordBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    user = _get_user(session, user_id)
    if user.id == current.id:
        raise HTTPException(status_code=403, detail="admins cannot reset their own password")
    password = _validate_password(body.password)
    users.reset_password(session, user, password)
    safe_user = to_admin_user_dict(user)
    record_audit(
        session,
        actor=current.username,
        action="user.reset_password",
        entity="user",
        entity_id=str(user.id),
        after=safe_user,
    )
    session.commit()
    return {"user": safe_user}
