from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    Appointment, AppointmentStatus, AutomationInstallation, Case, Customer,
    DomainEvent, NotificationOperation, User, UserRole,
)
from app.services.automation_installations import install
from app.services.recipes import get_recipe
from app.services.time_triggers import evaluate_time_triggers


def _install(session, recipe_id="appointment_review_request", **parameters):
    return install(
        session, recipe_id, {"channel": "whatsapp", **parameters}, actor="test", enabled=True
    )


def _appointment(session, customer, ends_at, status=AppointmentStatus.COMPLETED):
    technician = User(username=f"tech-{uuid4()}", password_hash="test", role=UserRole.TECNICO)
    case = Case(service="service", customer_id=customer.id)
    session.add_all([technician, case])
    session.flush()
    session.add(Appointment(
        service="service", customer_id=customer.id, case_id=case.id, technician_id=technician.id,
        local_start=ends_at.replace(tzinfo=None) - timedelta(hours=1), timezone="UTC",
        starts_at=ends_at - timedelta(hours=1), ends_at=ends_at, duration_minutes=60, status=status,
    ))
    session.flush()
    return session.scalar(select(Appointment).order_by(Appointment.id.desc()))


def _customer(session, phone=None):
    customer = Customer(phone_e164=phone or "+15550000001", email="customer@example.com")
    session.add(customer)
    session.flush()
    return customer


def test_due_review_publishes_and_is_idempotent(migrated_db):
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer = _customer(session)
        appointment = _appointment(session, customer, now - timedelta(days=5))
        installation = _install(session, days_after=3)
        installation.created_at = now - timedelta(days=3)
        session.flush()

        assert evaluate_time_triggers(session, now) == 1
        assert evaluate_time_triggers(session, now) == 1
        events = session.scalars(select(DomainEvent)).all()
        assert len(events) == 1
        event = events[0]
        assert (event.event_type, event.entity_type, event.dedupe_key) == (
            "appointment.review_due", "appointment", f"appointment:{appointment.id}:review"
        )
        assert event.payload["recipient"] == customer.phone_e164
        assert event.payload["customer_id"] == customer.id
        assert event.payload["appointment_id"] == appointment.id


def test_review_not_due_or_before_installation_due_time_floor(migrated_db):
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer = _customer(session)
        _appointment(session, customer, now - timedelta(days=1))
        installation = _install(session, days_after=3)
        installation.created_at = now - timedelta(days=10)
        session.flush()
        assert evaluate_time_triggers(session, now) == 0

        # Anchor predates installation, but due time is after installation.
        appointment = _appointment(session, customer, now - timedelta(days=3))
        installation.created_at = now - timedelta(days=1)
        session.flush()
        assert evaluate_time_triggers(session, now) == 1
        assert session.scalar(select(DomainEvent.dedupe_key)) == f"appointment:{appointment.id}:review"

        _appointment(session, customer, now - timedelta(days=5))
        assert evaluate_time_triggers(session, now) == 1
        assert session.scalar(select(func.count()).select_from(DomainEvent)) == 1


def test_review_skips_missing_contact_and_incomplete_appointments(migrated_db):
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer = _customer(session, "+15550000002")
        customer.phone_e164 = ""
        _appointment(session, customer, now - timedelta(days=5))
        _appointment(session, customer, now - timedelta(days=5), AppointmentStatus.BOOKED)
        installation = _install(session, days_after=3)
        installation.created_at = now - timedelta(days=10)
        session.flush()
        assert evaluate_time_triggers(session, now) == 0
        assert session.scalar(select(func.count()).select_from(DomainEvent)) == 0


def test_maintenance_uses_latest_service_and_date_key(migrated_db):
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer = _customer(session)
        last_service = now - timedelta(days=300)
        _appointment(session, customer, last_service)
        installation = _install(session, "customer_maintenance", months=6)
        installation.created_at = now - timedelta(days=300)
        session.flush()
        assert evaluate_time_triggers(session, now) == 1
        first_key = f"customer:{customer.id}:maintenance:{last_service.date().isoformat()}"
        assert session.scalar(select(DomainEvent.dedupe_key)) == first_key

        recent_customer = _customer(session, "+15550000003")
        _appointment(session, recent_customer, now - timedelta(days=10))
        assert evaluate_time_triggers(session, now) == 1
        assert session.scalar(select(func.count()).select_from(DomainEvent)) == 1

        newer = now - timedelta(days=240)
        _appointment(session, customer, newer)
        assert evaluate_time_triggers(session, now) == 1
        assert set(session.scalars(select(DomainEvent.dedupe_key))) == {
            first_key, f"customer:{customer.id}:maintenance:{newer.date().isoformat()}"
        }


def test_worker_processes_due_review_into_notification_operation(migrated_db):
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer = _customer(session)
        _appointment(session, customer, now - timedelta(days=5))
        installation = _install(session, days_after=3)
        installation.created_at = now - timedelta(days=10)
        session.commit()

    from app.ops.worker import run_cycle

    assert run_cycle() == 1
    with SessionLocal() as session:
        operation = session.scalar(select(NotificationOperation))
        assert operation.recipient == customer.phone_e164
        assert operation.content == get_recipe("appointment_review_request").content
