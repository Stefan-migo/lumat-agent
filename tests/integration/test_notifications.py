"""NT-1/NT-2 integration tests for durable notification delivery."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    Appointment,
    AppointmentStatus,
    AuditLog,
    Case,
    Customer,
    DomainEvent,
    NotificationAttempt,
    NotificationOperation,
    NotificationTemplateVersion,
    User,
    UserRole,
)
from app.services import notifications, notify, scheduling
from app.services.automation import evaluate_event
from app.services.automation_installations import install
from app.services.customers import get_or_create_customer
from app.services.settings import get_setting, set_setting
from app.services.time_triggers import evaluate_time_triggers
from _testdb import admin_database_url


ADMIN_DB_URL = admin_database_url()
FOLLOWUP_DELAY = timedelta(hours=24)


@pytest.fixture(autouse=True)
def clean_notifications_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE notification_attempts, notification_operations, audit_log, "
            "automation_executions, automation_rules, automation_installations, domain_events, "
            "cases, messages, conversations, customers RESTART IDENTITY CASCADE"
        )
    yield


def _operation(**overrides):
    values = {
        "recipient": "+56911111111",
        "channel": "whatsapp",
        "content": "Appointment reminder",
        "source_entity": "appointment",
        "source_id": "42",
        "idempotency_key": "appointment:42:manual",
    }
    values.update(overrides)
    with SessionLocal() as session:
        operation = notifications.create_operation(session, **values)
        session.commit()
        return operation.id


def _install_recipe(session, recipe_id, channel="whatsapp"):
    return install(session, recipe_id, {"channel": channel}, actor="admin", enabled=True)


def _booked_appointment(session, *, starts_at, created_at=None, status=AppointmentStatus.BOOKED, name="Ana"):
    suffix = uuid4().hex[:10]
    technician = User(username=f"notif-tech-{suffix}", password_hash="x", role=UserRole.TECNICO)
    customer = Customer(phone_e164=f"+569{suffix[:8]}", name=name)
    session.add_all([technician, customer])
    session.flush()
    case = Case(customer_id=customer.id, status="open")
    session.add(case)
    session.flush()
    appointment = Appointment(
        service="Visit", customer_id=customer.id, case_id=case.id, technician_id=technician.id,
        local_start=starts_at.astimezone(timezone.utc).replace(tzinfo=None), timezone="UTC",
        starts_at=starts_at, ends_at=starts_at + timedelta(hours=1), duration_minutes=60,
        status=status,
    )
    if created_at is not None:
        appointment.created_at = created_at
    session.add(appointment)
    session.flush()
    return appointment, customer


def _scan_reminders(session, now):
    """Run the 24h reminder scan and evaluate its events through the engine."""
    evaluate_time_triggers(session, now)
    for event in session.scalars(
        select(DomainEvent).where(DomainEvent.event_type == "appointment.reminder_due")
    ):
        evaluate_event(session, event)
    session.flush()


def _reminder_event(session, appointment):
    return session.scalar(select(DomainEvent).where(
        DomainEvent.event_type == "appointment.reminder_due",
        DomainEvent.entity_id == str(appointment.id),
    ))


def _appointment_operation(session, appointment, channel="whatsapp"):
    return session.scalar(select(NotificationOperation).where(
        NotificationOperation.source_entity == "appointment",
        NotificationOperation.source_id == str(appointment.id),
        NotificationOperation.channel == channel,
    ))


def _approved_reminder_template(session):
    session.add(NotificationTemplateVersion(
        event="appointment.reminder.24h", channel="whatsapp", locale="es", version=1,
        content="Visita {date} {time}", required_variables=["date", "time"], approved=True,
        smtp_allowed=True, created_by="test",
    ))
    session.flush()


def test_operation_is_persisted_before_delivery_and_duplicate_is_safe(migrated_db, monkeypatch):
    calls = []
    monkeypatch.setattr(notifications, "send_whatsapp", lambda recipient, content: calls.append((recipient, content)) or "wamid-1")

    operation_id = _operation()
    with SessionLocal() as session:
        operation = session.get(NotificationOperation, operation_id)
        assert operation.status == "pending"
        assert operation.recipient == "+56911111111"
        assert operation.content == "Appointment reminder"
        assert operation.idempotency_key == "appointment:42:manual"
        duplicate = notifications.create_operation(
            session,
            recipient=operation.recipient,
            channel=operation.channel,
            content=operation.content,
            source_entity=operation.source_entity,
            source_id=operation.source_id,
            idempotency_key=operation.idempotency_key,
        )
        session.commit()
        assert duplicate.id == operation_id
        assert len(session.scalars(select(NotificationOperation)).all()) == 1
        assert notifications.process_operation(session, operation_id) is True
        session.commit()

    assert calls == [("+56911111111", "Appointment reminder")]
    with SessionLocal() as session:
        operation = session.get(NotificationOperation, operation_id)
        assert operation.status == "sent"
        assert operation.attempts == 1
        assert len(session.scalars(select(NotificationAttempt)).all()) == 1


def test_failed_operation_is_retryable_then_permanently_exhausted(migrated_db, monkeypatch):
    monkeypatch.setattr(notifications, "send_whatsapp", lambda recipient, content: (_ for _ in ()).throw(OSError("offline")))
    operation_id = _operation(max_attempts=2)

    with SessionLocal() as session:
        assert notifications.process_operation(session, operation_id) is False
        session.commit()
    with SessionLocal() as session:
        operation = session.get(NotificationOperation, operation_id)
        assert operation.status == "retryable"
        assert operation.attempts == 1
        assert operation.next_attempt_at is not None
        assert notifications.process_operation(session, operation_id, now=operation.next_attempt_at) is False
        session.commit()

    with SessionLocal() as session:
        operation = session.get(NotificationOperation, operation_id)
        assert operation.status == "permanently_failed"
        assert operation.attempts == 2
        assert notifications.process_operation(session, operation_id, now=datetime.now(timezone.utc) + timedelta(days=1)) is False
        assert len(session.scalars(select(NotificationAttempt)).all()) == 2
        assert session.scalar(
            select(AuditLog).where(AuditLog.action == "notification.exhausted")
        ) is not None


def test_due_reminder_is_idempotent_and_sweep_is_bounded(migrated_db, monkeypatch):
    calls = []
    monkeypatch.setattr(notifications, "send_whatsapp", lambda recipient, content: calls.append(recipient) or "wamid")
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56922222222")
        session.commit()
        operation_id = notifications.create_due_reminder(
            session, customer_id=customer.id, reminder_kind="24h", due_at=datetime.now(timezone.utc)
        ).id
        notifications.create_due_reminder(
            session, customer_id=customer.id, reminder_kind="48h", due_at=datetime.now(timezone.utc)
        )
        session.commit()

    assert notifications.sweep_due_operations(limit=1) == 1
    assert notifications.sweep_due_operations(limit=1) == 1
    assert notifications.sweep_due_operations(limit=1) == 0
    assert calls == ["+56922222222", "+56922222222"]
    with SessionLocal() as session:
        pending = session.scalar(
            select(NotificationOperation).where(NotificationOperation.id != operation_id)
        )
        assert pending.status == "sent"


def test_appointment_reminder_is_appointment_keyed_and_due_in_utc(migrated_db):
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        _install_recipe(session, "appointment_reminder")
        starts_at = now + timedelta(days=3)
        appointment, customer = _booked_appointment(
            session, starts_at=starts_at, created_at=now - timedelta(days=1)
        )
        scan_now = starts_at - timedelta(hours=23)
        _scan_reminders(session, scan_now)

        event = _reminder_event(session, appointment)
        assert event is not None
        assert (event.entity_type, event.entity_id) == ("appointment", str(appointment.id))
        assert event.dedupe_key == f"appointment:{appointment.id}:reminder:24h"
        assert event.payload == {
            "customer_id": customer.id,
            "appointment_id": appointment.id,
            "recipient": customer.phone_e164,
        }

        operation = _appointment_operation(session, appointment)
        assert operation is not None
        assert operation.next_attempt_at is not None
        assert operation.next_attempt_at.tzinfo is not None

        # A second scan reuses the same event and never creates a second operation.
        _scan_reminders(session, scan_now)
        assert session.scalar(select(func.count()).select_from(DomainEvent).where(
            DomainEvent.event_type == "appointment.reminder_due",
            DomainEvent.entity_id == str(appointment.id),
        )) == 1
        assert session.scalar(select(func.count()).select_from(NotificationOperation).where(
            NotificationOperation.source_id == str(appointment.id)
        )) == 1
        session.commit()


def test_cancelled_appointment_is_never_reminded(migrated_db):
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        _install_recipe(session, "appointment_reminder")
        starts_at = now + timedelta(days=3)
        appointment, _ = _booked_appointment(
            session, starts_at=starts_at, created_at=now - timedelta(days=1)
        )
        scheduling.cancel(session, appointment, actor="test")
        _scan_reminders(session, starts_at - timedelta(hours=23))
        assert _reminder_event(session, appointment) is None
        assert _appointment_operation(session, appointment) is None


def test_appointment_reminder_dispatches_approved_template_then_customer_email_fallback(migrated_db, monkeypatch):
    sent = []
    monkeypatch.setattr(notify, "send_template", lambda phone, params, *, template_name=None: (_ for _ in ()).throw(OSError("Meta down")))
    monkeypatch.setattr(notify, "send_email", lambda session, to, subject, body: sent.append((to, subject, body)))
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        _install_recipe(session, "appointment_reminder")
        starts_at = now + timedelta(days=3)
        appointment, customer = _booked_appointment(
            session, starts_at=starts_at, created_at=now - timedelta(days=1)
        )
        customer.email = "customer@example.com"
        _approved_reminder_template(session)
        _scan_reminders(session, starts_at - timedelta(hours=23))
        operation = _appointment_operation(session, appointment)
        assert notifications.process_operation(session, operation.id, now=operation.next_attempt_at) is True
        assert sent and sent[0][0] == "customer@example.com"
        assert appointment.local_start.strftime("%d/%m/") in sent[0][2]


def test_appointment_reminder_without_customer_email_permanently_fails(migrated_db, monkeypatch):
    monkeypatch.setattr(notify, "send_template", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("Meta down")))
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        _install_recipe(session, "appointment_reminder")
        starts_at = now + timedelta(days=3)
        appointment, _ = _booked_appointment(
            session, starts_at=starts_at, created_at=now - timedelta(days=1)
        )
        _approved_reminder_template(session)
        _scan_reminders(session, starts_at - timedelta(hours=23))
        operation = _appointment_operation(session, appointment)
        assert notifications.process_operation(session, operation.id, now=operation.next_attempt_at) is False
        assert operation.status == "permanently_failed"
        assert session.scalar(select(AuditLog).where(AuditLog.action == "notification.reminder_no_email")) is not None


def test_booking_inside_the_24h_window_creates_no_reminder(migrated_db):
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        _install_recipe(session, "appointment_reminder")
        # Booked now for a visit only two hours ahead: less than 24h notice.
        starts_at = now + timedelta(hours=2)
        appointment, _ = _booked_appointment(session, starts_at=starts_at)
        _scan_reminders(session, now)
        assert starts_at - now < FOLLOWUP_DELAY
        assert _reminder_event(session, appointment) is None
        assert _appointment_operation(session, appointment) is None


def test_reschedule_uses_the_appointment_current_start_time(migrated_db):
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        _install_recipe(session, "appointment_reminder")
        first = now + timedelta(days=5)
        appointment, _ = _booked_appointment(session, starts_at=first)

        # Far from its start: outside the 24h horizon, nothing is due yet.
        assert evaluate_time_triggers(session, now) == 0
        assert _reminder_event(session, appointment) is None

        # Rescheduled into the horizon: the scan reads the new starts_at.
        second = now + timedelta(days=2)
        scheduling.reschedule(
            session, appointment, local_date=second.date(), local_time=second.time().replace(tzinfo=None),
            timezone_name="UTC", duration_minutes=60, technician_id=appointment.technician_id, actor="test",
        )
        assert evaluate_time_triggers(session, second - timedelta(hours=23)) == 1
        assert _reminder_event(session, appointment) is not None

        # Rescheduled to less than 24h notice: the created_at guard excludes it.
        near = now + timedelta(hours=2)
        scheduling.reschedule(
            session, appointment, local_date=near.date(), local_time=near.time().replace(tzinfo=None),
            timezone_name="UTC", duration_minutes=60, technician_id=appointment.technician_id, actor="test",
        )
        assert evaluate_time_triggers(session, now) == 0


def test_appointment_reminder_sends_configured_template_and_local_datetime_params(migrated_db, monkeypatch):
    calls = []
    monkeypatch.setattr(notify, "send_template", lambda phone, params, *, template_name="emergency_alert":
                        calls.append((phone, params, template_name)) or "wamid-reminder")
    with SessionLocal() as session:
        set_setting(session, "notify.reminder_template_name", "recordatorio_prueba")
        _install_recipe(session, "appointment_reminder")
        starts_at = datetime(2030, 1, 3, 14, 35, tzinfo=timezone.utc)
        appointment, customer = _booked_appointment(
            session, starts_at=starts_at, created_at=datetime(2030, 1, 1, tzinfo=timezone.utc)
        )
        _approved_reminder_template(session)
        _scan_reminders(session, starts_at - timedelta(hours=23))
        operation = _appointment_operation(session, appointment)
        assert notifications.process_operation(session, operation.id, now=operation.next_attempt_at) is True
        assert calls == [(customer.phone_e164, ["03/01/2030", "14:35"], "recordatorio_prueba")]
        assert len(calls[0][1]) == 2
        assert operation.status == "sent"
        assert operation.delivered_at is not None


@pytest.mark.parametrize(
    "outcome,recipe_id",
    [("completed", "appointment_followup"), ("no_show", "appointment_followup_no_show")],
)
def test_close_publishes_outcome_event_and_followup_recipe_delays_delivery(migrated_db, outcome, recipe_id):
    with SessionLocal() as session:
        _install_recipe(session, recipe_id)
        before = datetime.now(timezone.utc)
        appointment, customer = _booked_appointment(
            session, starts_at=datetime.now(timezone.utc) + timedelta(days=2)
        )
        scheduling.close(session, appointment, outcome=AppointmentStatus(outcome), actor="test")

        event = session.scalar(select(DomainEvent).where(
            DomainEvent.event_type == f"appointment.{outcome}",
            DomainEvent.entity_id == str(appointment.id),
        ))
        assert event is not None
        assert event.dedupe_key == f"appointment:{appointment.id}:{outcome}"
        assert event.payload == {
            "customer_id": customer.id, "case_id": appointment.case_id,
            "recipient": customer.phone_e164, "outcome": outcome,
        }

        assert evaluate_event(session, event) != []
        operation = _appointment_operation(session, appointment)
        assert operation is not None
        assert operation.recipient == get_setting(session, "notify.owner_whatsapp")
        assert operation.status == "pending"
        assert abs(operation.next_attempt_at - (before + FOLLOWUP_DELAY)) < timedelta(seconds=60)
        assert session.scalar(select(func.count()).select_from(NotificationOperation).where(
            NotificationOperation.source_id == str(appointment.id),
            NotificationOperation.channel == "whatsapp",
        )) == 1


def test_close_cannot_schedule_followup_twice(migrated_db):
    with SessionLocal() as session:
        _install_recipe(session, "appointment_followup")
        appointment, _ = _booked_appointment(
            session, starts_at=datetime.now(timezone.utc) + timedelta(days=2)
        )
        scheduling.close(session, appointment, outcome=AppointmentStatus.COMPLETED, actor="test")
        with pytest.raises(ValueError):
            scheduling.close(session, appointment, outcome=AppointmentStatus.COMPLETED, actor="test")

        event = session.scalar(select(DomainEvent).where(
            DomainEvent.event_type == "appointment.completed",
            DomainEvent.entity_id == str(appointment.id),
        ))
        assert evaluate_event(session, event) != []
        # Re-evaluating the same event reuses the execution and creates no duplicate.
        assert evaluate_event(session, event) != []
        assert session.scalar(select(func.count()).select_from(NotificationOperation).where(
            NotificationOperation.source_id == str(appointment.id),
            NotificationOperation.channel == "whatsapp",
        )) == 1


@pytest.mark.parametrize(
    "outcome,recipe_id,template_event,setting_key,template_name",
    [
        ("completed", "appointment_followup", "appointment.followup.completed", "notify.followup_template_name", "appointment_followup"),
        ("no_show", "appointment_followup_no_show", "appointment.followup.no_show", "notify.followup_no_show_template_name", "appointment_followup_no_show"),
    ],
)
def test_followup_dispatch_uses_outcome_specific_template_and_parameters(
    migrated_db, monkeypatch, outcome, recipe_id, template_event, setting_key, template_name,
):
    calls = []
    monkeypatch.setattr(notify, "send_template", lambda phone, params, *, template_name=None:
                        calls.append((phone, params, template_name)) or "wamid-followup")
    with SessionLocal() as session:
        _install_recipe(session, recipe_id)
        set_setting(session, setting_key, template_name)
        appointment, customer = _booked_appointment(
            session, starts_at=datetime(2030, 1, 3, 14, 35, tzinfo=timezone.utc),
            created_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        scheduling.close(session, appointment, outcome=AppointmentStatus(outcome), actor="test")
        session.add(NotificationTemplateVersion(
            event=template_event, channel="whatsapp", locale="es", version=1,
            content="Follow-up {customer_name} {date} {time}",
            required_variables=["customer_name", "date", "time"], approved=True,
            smtp_allowed=True, created_by="test",
        ))
        session.flush()
        event = session.scalar(select(DomainEvent).where(
            DomainEvent.event_type == f"appointment.{outcome}",
            DomainEvent.entity_id == str(appointment.id),
        ))
        assert evaluate_event(session, event) != []
        operation = _appointment_operation(session, appointment)
        assert notifications.process_operation(session, operation.id, now=operation.next_attempt_at) is True
        assert calls == [(operation.recipient, ["Ana", "03/01/2030", "14:35"], template_name)]


@pytest.mark.parametrize(
    "outcome,recipe_id",
    [("completed", "appointment_followup"), ("no_show", "appointment_followup_no_show")],
)
def test_followup_whatsapp_failure_falls_back_to_team_email_and_audits(migrated_db, monkeypatch, outcome, recipe_id):
    emails = []
    monkeypatch.setattr(notify, "send_template", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("Meta down")))
    monkeypatch.setattr(notify, "send_email", lambda session, to, subject, body: emails.append((to, subject, body)))
    with SessionLocal() as session:
        _install_recipe(session, recipe_id)
        appointment, _ = _booked_appointment(
            session, starts_at=datetime(2030, 1, 3, 14, 35, tzinfo=timezone.utc),
            created_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        scheduling.close(session, appointment, outcome=AppointmentStatus(outcome), actor="test")
        session.add(NotificationTemplateVersion(
            event=f"appointment.followup.{outcome}", channel="whatsapp", locale="es", version=1,
            content="Follow-up", required_variables=[], approved=True, smtp_allowed=True, created_by="test",
        ))
        session.flush()
        event = session.scalar(select(DomainEvent).where(
            DomainEvent.event_type == f"appointment.{outcome}",
            DomainEvent.entity_id == str(appointment.id),
        ))
        assert evaluate_event(session, event) != []
        operation = _appointment_operation(session, appointment)
        assert notifications.process_operation(session, operation.id, now=operation.next_attempt_at) is True
        address = get_setting(session, "notify.owner_email")
        assert emails and emails[0][0] == address
        assert emails[0][1] == "Seguimiento de visita Lumat"
        if outcome == "completed":
            assert emails[0][2] == (
                "La visita de Ana del 03/01/2030 a las 14:35 quedó cerrada como completada. "
                "Contacta al cliente para hacer el seguimiento."
            )
        else:
            assert emails[0][2] == (
                "La visita de Ana del 03/01/2030 a las 14:35 quedó marcada como no asistida. "
                "Contacta al cliente para reagendar."
            )
        session.flush()
        assert session.scalar(select(AuditLog).where(
            AuditLog.action == "notification.followup_email_fallback"
        )) is not None
