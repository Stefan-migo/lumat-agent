"""NT-1/NT-2 integration tests for durable notification delivery."""

from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import AuditLog, Customer, NotificationAttempt, NotificationOperation
from app.services import notifications
from app.services.customers import get_or_create_customer
from _testdb import admin_database_url


ADMIN_DB_URL = admin_database_url()
FOLLOWUP_NOW = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def clean_notifications_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE notification_attempts, notification_operations, audit_log, "
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
        "idempotency_key": "appointment:42:reminder:24h",
    }
    values.update(overrides)
    with SessionLocal() as session:
        operation = notifications.create_operation(session, **values)
        session.commit()
        return operation.id


def test_operation_is_persisted_before_delivery_and_duplicate_is_safe(migrated_db, monkeypatch):
    calls = []
    monkeypatch.setattr(notifications, "send_whatsapp", lambda recipient, content: calls.append((recipient, content)) or "wamid-1")

    operation_id = _operation()
    with SessionLocal() as session:
        operation = session.get(NotificationOperation, operation_id)
        assert operation.status == "pending"
        assert operation.recipient == "+56911111111"
        assert operation.content == "Appointment reminder"
        assert operation.idempotency_key == "appointment:42:reminder:24h"
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
    from app.models import Appointment, AppointmentStatus, Case
    from app.services import scheduling
    from app.models import User, UserRole

    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56933333333")
        technician = User(username="reminder-tech", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        appointment = scheduling.book(
            session, service="Visita técnica", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=datetime(2030, 1, 2).date(),
            local_time=datetime.strptime("12:00", "%H:%M").time(), timezone_name="UTC",
            duration_minutes=60, actor="test",
        )
        session.flush()
        reminder = session.scalar(select(NotificationOperation).where(
            NotificationOperation.source_id == str(appointment.id)
        ))
        assert reminder is not None
        assert reminder.idempotency_key == f"appointment:{appointment.id}:reminder:24h"
        assert reminder.next_attempt_at == appointment.starts_at - timedelta(hours=24)
        assert reminder.next_attempt_at.tzinfo is not None
        assert session.scalar(select(func.count()).select_from(NotificationOperation).where(
            NotificationOperation.idempotency_key == reminder.idempotency_key
        )) == 1
        session.commit()


def test_cancelled_appointment_invalidates_its_pending_reminder(migrated_db):
    from app.models import Appointment, Case, User, UserRole
    from app.services import scheduling

    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56933333334")
        technician = User(username="cancel-tech", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        appointment = scheduling.book(
            session, service="Visit", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=datetime(2030, 1, 2).date(),
            local_time=datetime.strptime("12:00", "%H:%M").time(), timezone_name="UTC",
            duration_minutes=60, actor="test",
        )
        scheduling.cancel(session, appointment, actor="test")
        reminder = session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == f"appointment:{appointment.id}:reminder:24h"
        ))
        assert reminder.status == "permanently_failed"


def test_appointment_reminder_dispatches_approved_template_then_customer_email_fallback(migrated_db, monkeypatch):
    from app.models import Case, NotificationTemplateVersion, User, UserRole
    from app.services import scheduling, notify

    sent = []
    monkeypatch.setattr(notify, "send_template", lambda phone, params, *, template_name=None: (_ for _ in ()).throw(OSError("Meta down")))
    monkeypatch.setattr(notify, "send_email", lambda session, to, subject, body: sent.append((to, subject, body)))
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56933333335")
        customer.email = "customer@example.com"
        technician = User(username="delivery-tech", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        local_date = datetime.now(timezone.utc).date() + timedelta(days=3)
        appointment = scheduling.book(
            session, service="Visit", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=local_date,
            local_time=datetime.strptime("12:00", "%H:%M").time(), timezone_name="UTC",
            duration_minutes=60, actor="test",
        )
        template = NotificationTemplateVersion(
            event="appointment.reminder.24h", channel="whatsapp", locale="es", version=1,
            content="Visita {date} {time}", required_variables=["date", "time"], approved=True,
            smtp_allowed=True, created_by="test",
        )
        session.add(template)
        session.flush()
        operation = session.scalar(select(NotificationOperation).where(
            NotificationOperation.source_id == str(appointment.id)
        ))
        assert notifications.process_operation(session, operation.id, now=operation.next_attempt_at) is True
        assert sent and sent[0][0] == "customer@example.com"
        assert local_date.strftime("%d/%m/") in sent[0][2]


def test_appointment_reminder_without_customer_email_permanently_fails(migrated_db, monkeypatch):
    from app.models import Case, NotificationTemplateVersion, User, UserRole, AuditLog
    from app.services import scheduling, notify

    monkeypatch.setattr(notify, "send_template", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("Meta down")))
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56933333336")
        technician = User(username="no-email-tech", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        appointment = scheduling.book(
            session, service="Visit", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=datetime.now(timezone.utc).date() + timedelta(days=3),
            local_time=datetime.strptime("12:00", "%H:%M").time(), timezone_name="UTC",
            duration_minutes=60, actor="test",
        )
        session.add(NotificationTemplateVersion(
            event="appointment.reminder.24h", channel="whatsapp", locale="es", version=1,
            content="Visita {date} {time}", required_variables=["date", "time"], approved=True,
            smtp_allowed=True, created_by="test",
        ))
        session.flush()
        operation = session.scalar(select(NotificationOperation).where(NotificationOperation.source_id == str(appointment.id)))
        notifications.process_operation(session, operation.id, now=operation.next_attempt_at)
        assert operation.status == "permanently_failed"
        assert session.scalar(select(AuditLog).where(AuditLog.action == "notification.reminder_no_email")) is not None


def test_booking_inside_the_24h_window_creates_no_reminder(migrated_db):
    from app.models import Case, User, UserRole
    from app.services import scheduling

    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56933333337")
        technician = User(username="short-window-tech", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        starts = datetime.now(timezone.utc) + timedelta(hours=2)
        appointment = scheduling.book(
            session, service="Visit", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=starts.date(), local_time=starts.time().replace(tzinfo=None),
            timezone_name="UTC", duration_minutes=60, actor="test",
        )
        key = f"appointment:{appointment.id}:reminder:24h"
        assert appointment.starts_at - datetime.now(timezone.utc) < timedelta(hours=24)
        assert session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == key
        )) is None
        assert session.scalar(select(NotificationOperation).where(
            NotificationOperation.source_entity == "appointment",
            NotificationOperation.source_id == str(appointment.id),
        )) is None


def test_reschedule_moves_the_pending_reminder(migrated_db):
    from app.models import Case, User, UserRole
    from app.services import scheduling

    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56933333338")
        technician = User(username="move-reminder-tech", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        first = datetime.now(timezone.utc) + timedelta(days=3)
        appointment = scheduling.book(
            session, service="Visit", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=first.date(), local_time=first.time().replace(tzinfo=None),
            timezone_name="UTC", duration_minutes=60, actor="test",
        )
        key = f"appointment:{appointment.id}:reminder:24h"
        operation = session.scalar(select(NotificationOperation).where(NotificationOperation.idempotency_key == key))
        operation_id = operation.id
        assert operation.next_attempt_at == appointment.starts_at - timedelta(hours=24)

        new_start = datetime.now(timezone.utc) + timedelta(days=5)
        scheduling.reschedule(
            session, appointment, local_date=new_start.date(), local_time=new_start.time().replace(tzinfo=None),
            timezone_name="UTC", duration_minutes=60, technician_id=technician.id, actor="test",
        )
        moved = session.scalar(select(NotificationOperation).where(NotificationOperation.idempotency_key == key))
        assert moved.id == operation_id
        assert moved.idempotency_key == key
        assert session.scalar(select(func.count()).select_from(NotificationOperation).where(
            NotificationOperation.idempotency_key == key
        )) == 1
        assert moved.next_attempt_at == appointment.starts_at - timedelta(hours=24)

        near_start = datetime.now(timezone.utc) + timedelta(hours=2)
        scheduling.reschedule(
            session, appointment, local_date=near_start.date(), local_time=near_start.time().replace(tzinfo=None),
            timezone_name="UTC", duration_minutes=60, technician_id=technician.id, actor="test",
        )
        assert moved.status == "permanently_failed"


def test_appointment_reminder_sends_configured_template_and_local_datetime_params(migrated_db, monkeypatch):
    from app.models import Case, NotificationTemplateVersion, User, UserRole
    from app.services import scheduling, notify
    from app.services.settings import set_setting

    calls = []
    monkeypatch.setattr(notify, "send_template", lambda phone, params, *, template_name="emergency_alert":
                        calls.append((phone, params, template_name)) or "wamid-reminder")
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56933333339")
        technician = User(username="template-success-tech", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        set_setting(session, "notify.reminder_template_name", "recordatorio_prueba")
        local_date = datetime.now(timezone.utc).date() + timedelta(days=3)
        local_time = datetime.strptime("14:35", "%H:%M").time()
        appointment = scheduling.book(
            session, service="Visit", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=local_date, local_time=local_time,
            timezone_name="UTC", duration_minutes=60, actor="test",
        )
        session.add(NotificationTemplateVersion(
            event="appointment.reminder.24h", channel="whatsapp", locale="es", version=1,
            content="Visita {date} {time}", required_variables=["date", "time"], approved=True,
            smtp_allowed=True, created_by="test",
        ))
        session.flush()
        operation = session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == f"appointment:{appointment.id}:reminder:24h"
        ))
        assert notifications.process_operation(session, operation.id, now=operation.next_attempt_at) is True
        assert calls == [(customer.phone_e164, [local_date.strftime("%d/%m/%Y"), "14:35"], "recordatorio_prueba")]
        assert len(calls[0][1]) == 2
        assert operation.status == "sent"
        assert operation.delivered_at is not None


@pytest.mark.parametrize("outcome", ["completed", "no_show"])
def test_close_schedules_followup_and_publishes_outcome_event(migrated_db, outcome):
    from app.models import AppointmentStatus, Case, DomainEvent, User, UserRole
    from app.services import scheduling
    from app.services.settings import get_setting

    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56933333340")
        technician = User(username=f"followup-{outcome}", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        appointment = scheduling.book(
            session, service="Visit", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=FOLLOWUP_NOW.date() + timedelta(days=2),
            local_time=datetime.strptime("14:35", "%H:%M").time(), timezone_name="UTC",
            duration_minutes=60, actor="test",
        )
        scheduling.close(session, appointment, outcome=AppointmentStatus(outcome), actor="test", now=FOLLOWUP_NOW)
        key = f"appointment:{appointment.id}:followup:{outcome}"
        operation = session.scalar(select(NotificationOperation).where(NotificationOperation.idempotency_key == key))
        assert operation is not None
        assert operation.next_attempt_at == FOLLOWUP_NOW + timedelta(hours=24)
        assert operation.recipient == get_setting(session, "notify.owner_whatsapp")
        assert operation.status == "pending"
        assert session.scalar(select(func.count()).select_from(NotificationOperation).where(NotificationOperation.idempotency_key == key)) == 1
        event_type = f"appointment.{outcome}"
        event = session.scalar(select(DomainEvent).where(DomainEvent.event_type == event_type, DomainEvent.entity_id == str(appointment.id)))
        assert event is not None
        assert event.dedupe_key == f"appointment:{appointment.id}:{outcome}"
        assert event.payload == {
            "customer_id": customer.id, "case_id": case.id,
            "recipient": customer.phone_e164, "outcome": outcome,
        }


def test_close_cannot_schedule_followup_twice(migrated_db):
    from app.models import AppointmentStatus, Case, User, UserRole
    from app.services import scheduling

    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56933333341")
        technician = User(username="followup-once", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        appointment = scheduling.book(
            session, service="Visit", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=FOLLOWUP_NOW.date() + timedelta(days=2),
            local_time=datetime.strptime("14:35", "%H:%M").time(), timezone_name="UTC",
            duration_minutes=60, actor="test",
        )
        scheduling.close(session, appointment, outcome=AppointmentStatus.COMPLETED, actor="test", now=FOLLOWUP_NOW)
        with pytest.raises(ValueError):
            scheduling.close(session, appointment, outcome=AppointmentStatus.COMPLETED, actor="test", now=FOLLOWUP_NOW)
        key = f"appointment:{appointment.id}:followup:completed"
        assert session.scalar(select(func.count()).select_from(NotificationOperation).where(NotificationOperation.idempotency_key == key)) == 1


@pytest.mark.parametrize(
    "outcome,template_event,setting_key,template_name",
    [
        ("completed", "appointment.followup.completed", "notify.followup_template_name", "appointment_followup"),
        ("no_show", "appointment.followup.no_show", "notify.followup_no_show_template_name", "appointment_followup_no_show"),
    ],
)
def test_followup_dispatch_uses_outcome_specific_template_and_parameters(
    migrated_db, monkeypatch, outcome, template_event, setting_key, template_name,
):
    from app.models import AppointmentStatus, Case, NotificationTemplateVersion, User, UserRole
    from app.services import scheduling, notify
    from app.services.settings import set_setting

    calls = []
    monkeypatch.setattr(notify, "send_template", lambda phone, params, *, template_name=None:
                        calls.append((phone, params, template_name)) or "wamid-followup")
    with SessionLocal() as session:
        customer = get_or_create_customer(session, f"+5693333334{0 if outcome == 'completed' else 2}")
        customer.name = "Ana"
        technician = User(username=f"dispatch-followup-{outcome}", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        set_setting(session, setting_key, template_name)
        appointment = scheduling.book(
            session, service="Visit", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=FOLLOWUP_NOW.date() + timedelta(days=2),
            local_time=datetime.strptime("14:35", "%H:%M").time(), timezone_name="UTC",
            duration_minutes=60, actor="test",
        )
        scheduling.close(session, appointment, outcome=AppointmentStatus(outcome), actor="test", now=FOLLOWUP_NOW)
        session.add(NotificationTemplateVersion(
            event=template_event, channel="whatsapp", locale="es", version=1,
            content="Follow-up {customer_name} {date} {time}",
            required_variables=["customer_name", "date", "time"], approved=True,
            smtp_allowed=True, created_by="test",
        ))
        session.flush()
        operation = session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == f"appointment:{appointment.id}:followup:{outcome}"
        ))
        assert notifications.process_operation(session, operation.id, now=operation.next_attempt_at) is True
        assert calls == [(operation.recipient, ["Ana", "03/01/2030", "14:35"], template_name)]


def test_followup_whatsapp_failure_falls_back_to_team_email_and_audits(migrated_db, monkeypatch):
    from app.models import AppointmentStatus, Case, NotificationTemplateVersion, User, UserRole
    from app.services import scheduling, notify
    from app.services.settings import get_setting

    emails = []
    monkeypatch.setattr(notify, "send_template", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("Meta down")))
    monkeypatch.setattr(notify, "send_email", lambda session, to, subject, body: emails.append((to, subject, body)))
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56933333343")
        technician = User(username="fallback-followup", password_hash="x", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        case = Case(customer_id=customer.id, status="open")
        session.add(case)
        session.flush()
        appointment = scheduling.book(
            session, service="Visit", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=FOLLOWUP_NOW.date() + timedelta(days=2),
            local_time=datetime.strptime("14:35", "%H:%M").time(), timezone_name="UTC",
            duration_minutes=60, actor="test",
        )
        scheduling.close(session, appointment, outcome=AppointmentStatus.COMPLETED, actor="test", now=FOLLOWUP_NOW)
        session.add(NotificationTemplateVersion(
            event="appointment.followup.completed", channel="whatsapp", locale="es", version=1,
            content="Follow-up", required_variables=[], approved=True, smtp_allowed=True, created_by="test",
        ))
        session.flush()
        operation = session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == f"appointment:{appointment.id}:followup:completed"
        ))
        assert notifications.process_operation(session, operation.id, now=operation.next_attempt_at) is True
        address = get_setting(session, "notify.owner_email")
        assert emails and emails[0][0] == address
        session.flush()
        assert session.scalar(select(AuditLog).where(
            AuditLog.action == "notification.followup_email_fallback"
        )) is not None
