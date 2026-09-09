"""H4 Slice 3 RED tests: notification center read model and push fallback."""

from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, AutomationExecution, AutomationRule, DomainEvent, NotificationOperation, PanelNotification, User
from app.services.events import publish_event
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


def test_mark_all_notifications_read_is_scoped_to_user():
    first, other = _user("bulk-first"), _user("bulk-other")
    with SessionLocal() as session:
        for user_id, key in ((first, "bulk:first:one"), (first, "bulk:first:two"), (other, "bulk:other")):
            notifications.create_operation(
                session, recipient="user", channel="email", content="Unread", source_entity="case",
                source_id=key, idempotency_key=key, user_id=user_id,
            )
        session.commit()
        count = notifications.mark_all_notifications_read(session, user_id=first)
        session.commit()
        first_rows = session.scalars(select(PanelNotification).where(PanelNotification.user_id == first)).all()
        other_rows = session.scalars(select(PanelNotification).where(PanelNotification.user_id == other)).all()
        assert count == 2
        assert all(row.read_at is not None for row in first_rows)
        assert all(row.read_at is None for row in other_rows)


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


def test_push_failure_creates_and_delivers_policy_fallback(monkeypatch):
    user_id = _user("fallback-admin")
    delivered = []
    monkeypatch.setattr(notifications, "send_push", lambda *_: (_ for _ in ()).throw(RuntimeError("unsupported")))
    monkeypatch.setattr(notifications, "send_whatsapp", lambda recipient, content: delivered.append((recipient, content)) or "fallback-wamid")
    with SessionLocal() as session:
        event = publish_event(
            session, event_type="case.created", entity_type="case", entity_id="fallback-1",
            payload={"recipient": "+56944444444", "content": "Fallback case"},
            dedupe_key="case:fallback-1:created",
        )
        rule = AutomationRule(
            name="Fallback WhatsApp", event_type="case.created", conditions={}, channel="whatsapp",
            template_event="case.created", created_by="admin",
        )
        session.add(rule)
        session.flush()
        operation = notifications.create_operation(
            session, recipient="+56944444444", channel="push", content="Fallback case",
            source_entity="case", source_id="fallback-1", idempotency_key="case:fallback-1:push",
            event_id=event.id, user_id=user_id,
        )
        session.add(AutomationExecution(
            rule_id=rule.id, event_id=event.id, execution_key="automation:fallback-1",
            outcome="enqueued", reason="matched", operation_id=operation.id,
        ))
        session.commit()
        assert notifications.process_operation(session, operation.id) is False
        session.commit()

        fallback = session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == "case:fallback-1:push:fallback:whatsapp"
        ))
        assert fallback is not None
        assert fallback.channel == "whatsapp"
        assert fallback.status == "sent"
        assert delivered == [("+56944444444", "Fallback case")]
        actions = session.scalars(select(AuditLog.action)).all()
        assert "notification.push_failed" in actions
        assert "notification.fallback_attempt" in actions
        assert "notification.operation_sent" in actions
        assert notifications.process_operation(session, operation.id, now=datetime.now(timezone.utc) + timedelta(days=1)) is False
        session.commit()
        assert session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == "case:fallback-1:push:fallback:whatsapp"
        )).attempts == 1
        assert delivered == [("+56944444444", "Fallback case")]


def test_notification_ordering_handles_mixed_results():
    user_id = _user("ordering-admin")
    with SessionLocal() as session:
        for number, status in ((1, "sent"), (2, "retryable"), (3, "permanently_failed")):
            operation = notifications.create_operation(
                session, recipient="admin", channel="email", content=f"Result {number}",
                source_entity="case", source_id=str(number), idempotency_key=f"ordering:{number}",
                user_id=user_id, status=status,
            )
            operation.created_at = datetime(2026, 1, number, tzinfo=timezone.utc)
        session.commit()
        rows = notifications.list_panel_notifications(session, user_id=user_id)
        assert [row.content for row in rows] == ["Result 3", "Result 2", "Result 1"]
        assert [row.status for row in rows] == ["permanently_failed", "retryable", "sent"]


def test_push_failure_uses_configured_email_fallback(monkeypatch):
    user_id = _user("email-fallback-admin")
    sent = []
    monkeypatch.setattr(notifications, "send_push", lambda *_: (_ for _ in ()).throw(RuntimeError("denied")))
    monkeypatch.setattr(notifications, "send_email", lambda recipient, content: sent.append((recipient, content)))
    with SessionLocal() as session:
        event = publish_event(
            session, event_type="case.created", entity_type="case", entity_id="fallback-email",
            payload={"email": "ops@example.test", "content": "Email fallback"},
            dedupe_key="case:fallback-email:created",
        )
        rule = AutomationRule(
            name="Fallback email", event_type="case.created", conditions={}, channel="email",
            template_event="case.created", created_by="admin",
        )
        session.add(rule)
        session.flush()
        operation = notifications.create_operation(
            session, recipient="ops@example.test", channel="push", content="Email fallback",
            source_entity="case", source_id="fallback-email", idempotency_key="case:fallback-email:push",
            event_id=event.id, user_id=user_id,
        )
        session.add(AutomationExecution(
            rule_id=rule.id, event_id=event.id, execution_key="automation:fallback-email",
            outcome="enqueued", operation_id=operation.id,
        ))
        session.commit()
        assert notifications.process_operation(session, operation.id) is False
        session.commit()
        fallback = session.scalar(select(NotificationOperation).where(NotificationOperation.channel == "email"))
        assert fallback.status == "sent"
        assert sent == [("ops@example.test", "Email fallback")]


def test_notification_center_and_push_routes_require_json_auth(client):
    for method, path in (("get", "/panel/api/notifications"), ("post", "/panel/api/push-subscription")):
        response = client.get(path) if method == "get" else client.post(path, json={})
        assert response.status_code in {401, 422}
        if response.status_code == 401:
            assert response.json() == {"detail": "unauthorized"}
