"""H4 Slice 3 RED tests: notification center read model and push fallback."""

from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from pywebpush import WebPushException
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, AutomationExecution, AutomationRule, DomainEvent, NotificationOperation, PanelNotification, PushSubscription, User, UserRole
from app.services.events import publish_event
from app.services import notifications
from app.services import push
from app.services.push import PushUnavailable
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_h4_notifications(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
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


def test_notify_admins_fans_out_and_stages_notification_envelope():
    admin_ids = [_user("panel-admin-one"), _user("panel-admin-two")]
    with SessionLocal() as session:
        operator = User(username="panel-operator", password_hash="unused", role=UserRole.OPERADOR)
        session.add(operator)
        session.flush()
        notifications.notify_admins(
            session, title="Nueva visita", content="Se agendó una visita.", source="appointment",
            source_id=17, dedupe_key="appointment:17:booked",
        )
        session.commit()

        rows = session.scalars(select(PanelNotification).order_by(PanelNotification.user_id)).all()
        operation = session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == "panel:appointment:17:booked"
        ))
        assert [row.user_id for row in rows] == sorted(admin_ids)
        assert all(row.operation_id == operation.id for row in rows)
        assert operation.channel == "panel"
        assert operation.status == "sent"
        assert operation.delivered_at is not None
        assert session.info["realtime_events"][-1].type == "notification"


def test_notify_admins_replay_does_not_duplicate_rows_or_operations():
    first, second = _user("panel-replay-one"), _user("panel-replay-two")
    with SessionLocal() as session:
        for _ in range(2):
            notifications.notify_admins(
                session, title="Visita reagendada", content="Se actualizó una visita.",
                source="appointment", source_id="23", dedupe_key="appointment:23:rescheduled",
            )
        session.commit()

        assert session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == "panel:appointment:23:rescheduled"
        )) is not None
        assert session.scalar(select(PanelNotification).where(PanelNotification.user_id == first)).operation_id == session.scalar(
            select(PanelNotification).where(PanelNotification.user_id == second)
        ).operation_id
        assert session.scalar(select(PanelNotification.id).where(PanelNotification.user_id == first)) is not None
        assert session.scalar(select(PanelNotification.id).where(PanelNotification.user_id == second)) is not None
        assert len(session.scalars(select(PanelNotification)).all()) == 2


def test_notify_admins_enqueues_one_push_per_active_admin_subscription_and_dedupes():
    admin_id = _user("push-fanout-admin")
    operator_id = _user("push-fanout-operator")
    with SessionLocal() as session:
        session.get(User, operator_id).role = UserRole.OPERADOR
        session.add_all([
            PushSubscription(user_id=admin_id, endpoint="https://push.example.test/active-a", p256dh="a", auth="a"),
            PushSubscription(user_id=admin_id, endpoint="https://push.example.test/active-b", p256dh="b", auth="b"),
            PushSubscription(user_id=admin_id, endpoint="https://push.example.test/inactive", p256dh="x", auth="x", active=False),
            PushSubscription(user_id=operator_id, endpoint="https://push.example.test/operator", p256dh="o", auth="o"),
        ])
        session.flush()
        active_ids = session.scalars(select(PushSubscription.id).where(PushSubscription.user_id == admin_id, PushSubscription.active.is_(True))).all()
        for _ in range(2):
            notifications.notify_admins(
                session, title="New visit", content="Visit booked.", source="appointment",
                source_id=41, dedupe_key="appointment:41:booked",
            )
        session.commit()

        operations = session.scalars(select(NotificationOperation).where(NotificationOperation.channel == "push")).all()
        assert len(operations) == 2
        assert {operation.recipient for operation in operations} == {str(identifier) for identifier in active_ids}
        assert all(operation.user_id is None for operation in operations)
        assert all(operation.status == "pending" and operation.delivered_at is None for operation in operations)
        assert all(operation.source_id == "panel:41" for operation in operations)
        assert {operation.idempotency_key for operation in operations} == {
            f"panel:appointment:41:booked:push:{identifier}" for identifier in active_ids
        }


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
            created_by="admin",
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
    monkeypatch.setattr(notifications, "send_email", lambda session, recipient, content: sent.append((recipient, content)))
    with SessionLocal() as session:
        event = publish_event(
            session, event_type="case.created", entity_type="case", entity_id="fallback-email",
            payload={"email": "ops@example.test", "content": "Email fallback"},
            dedupe_key="case:fallback-email:created",
        )
        rule = AutomationRule(
            name="Fallback email", event_type="case.created", conditions={}, channel="email",
            created_by="admin",
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


def test_send_push_requires_vapid_configuration(monkeypatch):
    monkeypatch.setattr(push, "get_settings", lambda: type("Settings", (), {
        "vapid_public_key": None, "vapid_private_key": None, "vapid_subject": None,
    })())
    with pytest.raises(PushUnavailable):
        push.send_push("1", "hello")


def test_send_push_uses_stored_subscription(monkeypatch):
    user_id = _user("push-send")
    with SessionLocal() as session:
        subscription = PushSubscription(user_id=user_id, endpoint="https://push.example.test/1", p256dh="public", auth="secret")
        session.add(subscription)
        session.commit()
        subscription_id = subscription.id
    monkeypatch.setattr(push, "get_settings", lambda: type("Settings", (), {
        "vapid_public_key": "public-key", "vapid_private_key": "private.pem", "vapid_subject": "mailto:ops@example.test",
    })())
    calls = []
    monkeypatch.setattr(push, "webpush", lambda *args, **kwargs: calls.append((args, kwargs)))

    assert push.send_push(str(subscription_id), "hello") == f"push:{subscription_id}"
    assert calls == [(({"endpoint": "https://push.example.test/1", "keys": {"p256dh": "public", "auth": "secret"}},), {
        "data": "hello", "vapid_private_key": "private.pem", "vapid_claims": {"sub": "mailto:ops@example.test"},
    })]


def test_send_push_deactivates_subscription_on_gone_response(monkeypatch):
    user_id = _user("push-gone")
    with SessionLocal() as session:
        subscription = PushSubscription(user_id=user_id, endpoint="https://push.example.test/gone", p256dh="public", auth="secret")
        session.add(subscription)
        session.commit()
        subscription_id = subscription.id
    monkeypatch.setattr(push, "get_settings", lambda: type("Settings", (), {
        "vapid_public_key": "public-key", "vapid_private_key": "private.pem", "vapid_subject": "mailto:ops@example.test",
    })())
    monkeypatch.setattr(push, "webpush", lambda *args, **kwargs: (_ for _ in ()).throw(
        WebPushException("gone", response=type("Response", (), {"status_code": 410})())
    ))

    with pytest.raises(WebPushException):
        push.send_push(str(subscription_id), "hello")

    with SessionLocal() as session:
        assert session.get(PushSubscription, subscription_id).active is False


@pytest.mark.parametrize("active", [True, False])
def test_send_push_missing_or_inactive_subscription_is_unavailable(monkeypatch, active):
    user_id = _user(f"push-inactive-{active}")
    with SessionLocal() as session:
        subscription = PushSubscription(user_id=user_id, endpoint=f"https://push.example.test/{active}", p256dh="public", auth="secret", active=active)
        session.add(subscription)
        session.commit()
        subscription_id = subscription.id
    monkeypatch.setattr(push, "get_settings", lambda: type("Settings", (), {
        "vapid_public_key": "public-key", "vapid_private_key": "private.pem", "vapid_subject": "mailto:ops@example.test",
    })())
    with pytest.raises(PushUnavailable):
        push.send_push(str(subscription_id if not active else 999999999), "hello")


def test_notification_center_and_push_routes_require_json_auth(client):
    for method, path in (("get", "/panel/api/notifications"), ("post", "/panel/api/push-subscription"), ("get", "/panel/api/push-config")):
        response = client.get(path) if method == "get" else client.post(path, json={})
        assert response.status_code in {401, 422}
        if response.status_code == 401:
                assert response.json() == {"detail": "unauthorized"}


def test_push_config_returns_public_key_to_authenticated_user(client, monkeypatch):
    from app.config import get_settings

    user_id = _user("push-config-user")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        from app.services.users import hash_password
        user.password_hash = hash_password("push-config-pass")
        session.commit()
    monkeypatch.setattr(get_settings(), "vapid_public_key", "public-vapid-key")
    response = client.post("/panel/api/login", json={"username": "push-config-user", "password": "push-config-pass"})
    assert response.status_code == 200

    response = client.get("/panel/api/push-config")
    assert response.status_code == 200
    assert response.json() == {"public_key": "public-vapid-key"}
