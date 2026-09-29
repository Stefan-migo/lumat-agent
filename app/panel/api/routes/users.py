from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.panel.api.deps import require_admin_json, require_operator_json, require_user_json
from app.panel.api.serializers import to_admin_user_dict, to_user_dict
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


class UserProfileBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str | None = Field(default=None, max_length=200)
    name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    position: str | None = Field(default=None, max_length=120)


class SelfPasswordBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str
    new_password: str


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


@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    return {"user": to_admin_user_dict(_get_user(session, user_id))}


@router.patch("/users/{user_id}")
def update_user_profile(
    user_id: int,
    body: UserProfileBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    user = _get_user(session, user_id)
    changes = {field: getattr(body, field) for field in body.model_fields_set}
    for field, value in changes.items():
        if value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(status_code=400, detail="profile fields cannot be empty")
            if field == "email":
                value = value.lower()
        changes[field] = value
    before = {field: getattr(user, field) for field, value in changes.items() if getattr(user, field) != value}
    after = {field: changes[field] for field in before}
    for field, value in changes.items():
        setattr(user, field, value)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="email already exists") from exc
    safe_user = to_admin_user_dict(user)
    if before:
        record_audit(session, actor=current.username, action="user.profile_update", entity="user", entity_id=str(user.id), before=before, after=after)
    session.commit()
    return {"user": safe_user}


@router.post("/me/password")
def change_own_password(
    body: SelfPasswordBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_user_json),
) -> dict:
    user = _get_user(session, current.id)
    if not users.verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="password change failed")
    password = _validate_password(body.new_password)
    user.password_hash = users.hash_password(password)
    users.reset_login_state(session, user)
    record_audit(session, actor=current.username, action="user.change_password", entity="user", entity_id=str(user.id), before={"password": "[redacted]"}, after={"password": "[redacted]"})
    session.commit()
    return {"ok": True}


@router.post("/users/{user_id}/unlock")
def unlock_user(
    user_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    user = _get_user(session, user_id)
    before = {"locked_until": user.locked_until.isoformat() if user.locked_until else None, "failed_logins": user.failed_logins}
    users.reset_login_state(session, user)
    safe_user = to_admin_user_dict(user)
    record_audit(session, actor=current.username, action="user.unlock", entity="user", entity_id=str(user.id), before=before, after={"locked_until": None, "failed_logins": 0})
    session.commit()
    return {"user": safe_user}


@router.get("/users")
def list_users(
    session: Session = Depends(get_db), current: User = Depends(require_admin_json)
) -> dict:
    return {"users": [to_admin_user_dict(user) for user in users.list_users(session)]}


@router.get("/technicians")
def list_technicians(
    session: Session = Depends(get_db), current: User = Depends(require_operator_json)
) -> dict:
    technicians = session.scalars(
        select(User).where(User.role == UserRole.TECNICO).order_by(User.username)
    ).all()
    return {"technicians": [to_user_dict(user) for user in technicians]}


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
