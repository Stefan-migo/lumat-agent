"""S9/S10: the operation behind a panel row must name the business entity, not the channel.

The seam this file exists for: `notify_admins` used to stamp every panel operation with
`source_entity="panel"` and `source_id="panel:<id>"`. The mapping in the frontend was correct and
never resolved, because a channel identity is not a destination. The suites that passed did not see
it -- they either called `create_operation` directly or fabricated the field in the client -- so these
tests go through the emitters the product actually runs.
"""

from datetime import date, time

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Case, Conversation, Customer, NotificationOperation, PanelNotification, User, UserRole
from app.services import scheduling
from app.services.notifications import notify_admins
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_notification_destination(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE panel_notifications, notification_operations, users, customers, cases, conversations "
            "RESTART IDENTITY CASCADE"
        )
    yield


def _admin() -> int:
    with SessionLocal() as session:
        user = User(username="destination-admin", password_hash="unused", role=UserRole.ADMIN)
        session.add(user)
        session.commit()
        return user.id


def _technician() -> int:
    with SessionLocal() as session:
        user = User(username="destination-tech", password_hash="unused", role=UserRole.TECNICO)
        session.add(user)
        session.commit()
        return user.id


def _customer() -> int:
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56911112222")
        session.add(customer)
        session.commit()
        return customer.id


def _operation_for(user_id: int) -> NotificationOperation:
    with SessionLocal() as session:
        row = session.scalar(
            select(PanelNotification)
            .where(PanelNotification.user_id == user_id)
            .order_by(PanelNotification.id.desc())
        )
        assert row is not None, "the emitter created no panel row for this user"
        return row.operation


def test_a_booked_visit_points_at_the_appointment_it_is_about():
    admin_id, technician_id, customer_id = _admin(), _technician(), _customer()
    with SessionLocal() as session:
        case = Case(customer_id=customer_id, service="calefont")
        session.add(case)
        session.flush()
        appointment = scheduling.book(
            session, service="calefont", customer_id=customer_id, case_id=case.id,
            technician_id=technician_id, local_date=date(2027, 1, 4), local_time=time(9),
            timezone_name="UTC", duration_minutes=60, actor="oper",
        )
        session.commit()
        appointment_id = appointment.id

    operation = _operation_for(admin_id)

    assert (operation.source_entity, operation.source_id) == ("appointment", str(appointment_id))


def test_an_emergency_points_at_the_conversation_where_it_happened():
    admin_id, customer_id = _admin(), _customer()
    with SessionLocal() as session:
        case = Case(customer_id=customer_id, service="calefont")
        session.add(case)
        conversation = Conversation(customer_id=customer_id, wa_phone="+56911112222")
        session.add(conversation)
        session.flush()
        # The exact call `app/chat/nodes/emergency.py` makes: the category is `emergencia`, the
        # source row is the case, and the place to act on it is the conversation.
        notify_admins(
            session, title="Emergencia detectada", content=f"Se detectó una emergencia en el caso #{case.id}.",
            source="emergencia", source_id=case.id, dedupe_key=f"emergencia:{case.id}",
            destination_entity="conversation", destination_id=conversation.id,
        )
        session.commit()
        conversation_id = conversation.id

    operation = _operation_for(admin_id)

    assert (operation.source_entity, operation.source_id) == ("conversation", str(conversation_id))


def test_a_cost_alert_has_no_destination_and_does_not_pretend_to_have_one():
    admin_id = _admin()
    with SessionLocal() as session:
        notify_admins(
            session, title="Alerta de costo", content="Se superó el umbral diario.",
            source="cost_alert", source_id="daily", dedupe_key="cost:daily",
        )
        session.commit()

    operation = _operation_for(admin_id)

    # No destination entity: the panel row stays a plain row instead of a link to a broken route.
    assert operation.source_entity == "panel"
    assert operation.source_id.startswith("panel:")
