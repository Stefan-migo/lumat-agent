"""H4 Slice 3 RED tests: notification center read model and push fallback."""

from datetime import datetime, timezone

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, NotificationOperation, PanelNotification, User
from app.services import notifications


@pytest.fixture(autouse=True)
def clean_h4_notifications(migrated_db):
    with psycopg.connect("postgresql://lumat:lumat@localhost:5432/lumat", autocommit=True) as conn:
        conn.execute("TRUNCATE push_subscriptions, panel_notifications, notification_attempts, notification_operations, audit_log, users RESTART IDENTITY CASCADE")
    yield


def _user(username: str) -> int:
    with SessionLocal() as session:
        user = User(username=username, password_hash="unused", role="admin")
        session.add(user)
        session.commit()
        return user.id


def test_notification_center_isolated_read_state_and_filters():
    first, other = _user("first"), _user("other")
    with SessionLocal() as session:
        operation = notifications.create_operation(
            session, recipient="first", channel="email", content="Failure", source_entity="case",
            source_id="1", idempotency_key="case:1", user_id=first,
        )
        notifications.create_panel_notification(session, user_id=other, operation_id=operation.id, title="Other", content="Private", source="case")
        session.commit()
        rows = notifications.list_panel_notifications(session, user_id=first, status="pending", unread=True)
        assert len(rows) == 1
        assert rows[0].user_id == first
        notifications.mark_notification_read(session, rows[0].id, user_id=first, now=datetime.now(timezone.utc))
        session.commit()
        assert session.get(NotificationOperation, operation.id).attempts == 0
        assert session.get(PanelNotification, rows[0].id).read_at is not None
        with pytest.raises(PermissionError):
            notifications.mark_notification_read(session, rows[0].id, user_id=other)


def test_event_fanout_creates_one_panel_notification_and_push_failure_is_audited(monkeypatch):
    user_id = _user("admin")
    with SessionLocal() as session:
        operation = notifications.create_operation(
            session, recipient="admin", channel="push", content="New case", source_entity="case",
            source_id="9", idempotency_key="case:9", user_id=user_id,
        )
        notifications.create_panel_notification(session, user_id=user_id, operation_id=operation.id, title="New case", content="New case", source="case")
        session.commit()
        monkeypatch.setattr(notifications, "send_push", lambda *_: (_ for _ in ()).throw(RuntimeError("unsupported")))
        assert notifications.process_operation(session, operation.id) is False
        session.commit()
        assert session.scalar(select(AuditLog).where(AuditLog.action == "notification.push_failed")) is not None


def test_notification_center_and_push_routes_require_json_auth(client):
    for method, path in (("get", "/panel/api/notifications"), ("post", "/panel/api/push-subscription")):
        response = client.get(path) if method == "get" else client.post(path, json={})
        assert response.status_code in {401, 422}
        if response.status_code == 401:
            assert response.json() == {"detail": "unauthorized"}
