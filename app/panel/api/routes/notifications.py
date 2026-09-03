"""Authenticated operational notification status and recovery actions."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NotificationOperation, PanelNotification, PushSubscription, User
from app.panel.api.deps import require_user_json
from app.panel.api.serializers import to_notification_dict, to_panel_notification_dict
from app.panel.deps import get_db
from app.services.audit import record_audit
from app.services.notifications import list_panel_notifications, mark_notification_read

router = APIRouter(tags=["panel-api-notifications"])

class PushSubscriptionBody(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None = None


@router.get("/notification-operations")
def list_notification_operations(
    session: Session = Depends(get_db), current: User = Depends(require_user_json)
) -> dict:
    rows = session.scalars(select(NotificationOperation).order_by(NotificationOperation.created_at.desc())).all()
    return {"operations": [to_notification_dict(row) for row in rows]}

@router.get("/notifications")
def list_notifications(unread: bool | None = None, status: str | None = None, source: str | None = None, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    return {"notifications": [to_panel_notification_dict(row) for row in list_panel_notifications(session, user_id=current.id, unread=unread, status=status, source=source)]}

@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: int, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    try:
        row = mark_notification_read(session, notification_id, user_id=current.id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="notification not found")
    return {"notification": to_panel_notification_dict(row)}

@router.post("/push-subscription")
def save_push_subscription(body: PushSubscriptionBody, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    row = session.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if row is None:
        session.add(PushSubscription(user_id=current.id, **body.model_dump()))
    else:
        row.user_id, row.p256dh, row.auth, row.user_agent, row.active = current.id, body.p256dh, body.auth, body.user_agent, True
    session.commit()
    return {"ok": True}

@router.delete("/push-subscription")
def delete_push_subscription(endpoint: str, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    row = session.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint, PushSubscription.user_id == current.id))
    if row is not None:
        row.active = False
        session.commit()
    return {"ok": True}


@router.post("/notification-operations/{operation_id}/retry")
def retry_notification_operation(
    operation_id: int, session: Session = Depends(get_db), current: User = Depends(require_user_json)
) -> dict:
    operation = session.get(NotificationOperation, operation_id)
    if operation is None:
        raise HTTPException(status_code=404, detail="notification operation not found")
    if operation.status not in {"retryable", "failed"}:
        raise HTTPException(status_code=409, detail={"code": "notification_not_retryable", "message": "notification is not retryable"})
    operation.status = "pending"
    operation.next_attempt_at = datetime.now(timezone.utc)
    record_audit(session, actor=current.username, action="notification.retry_requested", entity="notification_operation", entity_id=str(operation.id))
    session.commit()
    return {"ok": True, "operation": to_notification_dict(operation)}
