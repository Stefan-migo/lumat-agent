"""Push fan-out follows the visit audience, not only the admin audience."""

from datetime import date, time

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    Case,
    Customer,
    NotificationOperation,
    PushSubscription,
    User,
    UserRole,
)
from app.services import scheduling
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_notification_push_audience(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE push_subscriptions, panel_notifications, notification_operations, "
            "users, customers, cases RESTART IDENTITY CASCADE"
        )
    yield


def _user(username: str, role: UserRole) -> int:
    with SessionLocal() as session:
        user = User(username=username, password_hash="unused", role=role)
        session.add(user)
        session.commit()
        return user.id


def test_visit_push_targets_assigned_technician_but_not_unassigned_technician():
    admin = _user("push-audience-admin", UserRole.ADMIN)
    assigned = _user("push-audience-assigned", UserRole.TECNICO)
    unassigned = _user("push-audience-unassigned", UserRole.TECNICO)
    with SessionLocal() as session:
        assigned_subscription = PushSubscription(
            user_id=assigned,
            endpoint="https://push.example.test/assigned-visit",
            p256dh="assigned-key",
            auth="assigned-auth",
        )
        unassigned_subscription = PushSubscription(
            user_id=unassigned,
            endpoint="https://push.example.test/no-visit",
            p256dh="unassigned-key",
            auth="unassigned-auth",
        )
        session.add_all([assigned_subscription, unassigned_subscription])
        session.flush()
        assigned_subscription_id = assigned_subscription.id
        unassigned_subscription_id = unassigned_subscription.id

        customer = Customer(phone_e164="+56911114444")
        session.add(customer)
        session.flush()
        case = Case(customer_id=customer.id, service="calefont")
        session.add(case)
        session.flush()
        scheduling.book(
            session,
            service="calefont",
            customer_id=customer.id,
            case_id=case.id,
            technician_id=assigned,
            local_date=date(2027, 8, 10),
            local_time=time(10),
            timezone_name="UTC",
            duration_minutes=60,
            actor="oper",
        )
        session.commit()

        push_recipients = set(session.scalars(
            select(NotificationOperation.recipient).where(
                NotificationOperation.channel == "push"
            )
        ).all())

    assert str(assigned_subscription_id) in push_recipients
    assert str(unassigned_subscription_id) not in push_recipients
    assert admin not in {assigned, unassigned}
