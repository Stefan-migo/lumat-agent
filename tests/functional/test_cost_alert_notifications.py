from sqlalchemy import select

from app.db import SessionLocal
from app.models import NotificationOperation, PanelNotification, PushSubscription, User, UserRole
from app.services import costs, notifications


def test_cost_alert_fans_out_once_to_admin_panel_and_push_while_email_succeeds(migrated_db, monkeypatch):
    emails = []
    monkeypatch.setattr(costs, "send_email", lambda session, recipient, subject, body: emails.append((recipient, subject, body)))
    with SessionLocal() as session:
        admin = User(username="cost-alert-admin", password_hash="unused", role=UserRole.ADMIN)
        operator = User(username="cost-alert-operator", password_hash="unused", role=UserRole.OPERADOR)
        session.add_all([admin, operator])
        session.flush()
        subscriptions = [
            PushSubscription(user_id=admin.id, endpoint=f"https://push.example.test/{i}", p256dh="key", auth="auth")
            for i in range(2)
        ]
        session.add_all(subscriptions)
        session.flush()
        active_ids = {str(subscription.id) for subscription in subscriptions}
        original_get_setting = costs.get_setting
        monkeypatch.setattr(costs, "get_setting", lambda session, key, **kwargs: (
            "owner@example.test" if key == "notify.owner_email" else original_get_setting(session, key, **kwargs)
        ))

        assert costs.maybe_alert_owner(session, scope="conversation", entity_id="123", percent=80, spend=1.2)
        session.commit()
        assert not costs.maybe_alert_owner(session, scope="conversation", entity_id="123", percent=85, spend=1.28)
        session.commit()

        panel_rows = session.scalars(select(PanelNotification)).all()
        operations = session.scalars(select(NotificationOperation)).all()
        pushes = [operation for operation in operations if operation.channel == "push"]
        assert len(panel_rows) == 1
        assert panel_rows[0].user_id == admin.id
        assert panel_rows[0].source == "cost_alert"
        assert len(pushes) == 2
        assert {operation.recipient for operation in pushes} == active_ids
        assert len(operations) == 3
        assert len(emails) == 1 and emails[0][0] == "owner@example.test"


def test_permanently_failed_operation_creates_one_panel_only_failure_notice(migrated_db):
    with SessionLocal() as session:
        admin = User(username="failed-notice-admin", password_hash="unused", role=UserRole.ADMIN)
        session.add(admin)
        session.flush()
        operation = notifications.create_operation(
            session, recipient="customer", channel="email", content="Customer message",
            source_entity="appointment", source_id="456", idempotency_key="failed:456", max_attempts=1,
        )
        operation_id = operation.id
        session.commit()

        assert not notifications.process_operation(session, operation_id, deliver=lambda *_: (_ for _ in ()).throw(OSError("offline")))
        session.commit()
        assert session.get(NotificationOperation, operation_id).status == "permanently_failed"
        notices = session.scalars(select(PanelNotification).where(PanelNotification.source == "notification_failure")).all()
        assert len(notices) == 1
        assert notices[0].user_id == admin.id
        assert str(operation_id) in notices[0].content
        assert session.scalar(select(NotificationOperation.id).where(NotificationOperation.channel == "push")) is None

        assert not notifications.process_operation(session, operation_id)
        session.commit()
        assert session.scalars(select(PanelNotification).where(PanelNotification.source == "notification_failure")).all() == notices
        assert session.scalar(select(NotificationOperation.id).where(NotificationOperation.channel == "push")) is None


def test_cost_alert_email_transport_failure_does_not_propagate(migrated_db, monkeypatch):
    original_get_setting = costs.get_setting
    monkeypatch.setattr(costs, "get_setting", lambda session, key, **kwargs: (
        "owner@example.test" if key == "notify.owner_email" else original_get_setting(session, key, **kwargs)
    ))
    monkeypatch.setattr(costs, "send_email", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("SMTP unavailable")))
    with SessionLocal() as session:
        assert costs.maybe_alert_owner(session, scope="daily", entity_id="2030-01-01", percent=80, spend=4)
        session.commit()
