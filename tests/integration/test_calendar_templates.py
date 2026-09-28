from datetime import date, time

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Appointment, AppointmentCalendarSync, AppointmentStatus, Case, Conversation, Customer, User
from app.services import calendar, scheduling, templates


def _appointment(session):
    technician = User(username="calendar-tech", password_hash="test-password-hash")
    customer = Customer(phone_e164="+56911112222", name="Ana")
    session.add_all([technician, customer])
    session.flush()
    conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
    session.add(conversation)
    session.flush()
    case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont")
    session.add(case)
    session.flush()
    return scheduling.book(
        session, service="calefont", customer_id=customer.id, case_id=case.id,
        technician_id=technician.id, local_date=date(2026, 7, 15), local_time=time(10),
        timezone_name="America/Santiago", duration_minutes=60, actor="oper",
    )


class FakeProvider:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def sync(self, appointment, *, uid, idempotency_key):
        self.calls.append((appointment.id, uid, idempotency_key, appointment.status))
        if self.fail:
            raise RuntimeError("provider unavailable")
        return calendar.ProviderResult(external_id=uid, payload="BEGIN:VCALENDAR")


def test_calendar_sync_is_idempotent_and_exports_cancellation():
    with SessionLocal() as session:
        appointment = _appointment(session)
        provider = FakeProvider()
        first = calendar.synchronize(session, appointment, provider=provider, actor="oper")
        second = calendar.synchronize(session, appointment, provider=provider, actor="oper")
        assert first.uid == second.uid
        assert first.idempotency_key == second.idempotency_key
        assert len(provider.calls) == 2

        scheduling.cancel(session, appointment, actor="oper")
        cancelled = session.scalar(select(AppointmentCalendarSync).where(
            AppointmentCalendarSync.appointment_id == appointment.id
        ))
        assert cancelled.status == "synced"
        assert cancelled.cancelled is True
        assert "STATUS:CANCELLED" in cancelled.payload
        assert cancelled.attempts == 3


def test_reschedule_updates_an_existing_calendar_export():
    with SessionLocal() as session:
        appointment = _appointment(session)
        sync = calendar.synchronize(session, appointment, provider=calendar.ICSProvider(), actor="oper")

        scheduling.reschedule(
            session, appointment, local_date=date(2026, 7, 16), local_time=time(12),
            timezone_name="America/Santiago", duration_minutes=90,
            technician_id=appointment.technician_id, actor="oper",
        )

        session.flush()
        session.refresh(sync)
        assert sync.status == "synced"
        assert sync.cancelled is False
        assert "DTSTART;TZID=America/Santiago:20260716T120000" in sync.payload
        assert "DTEND;TZID=America/Santiago:20260716T133000" in sync.payload
        assert sync.attempts == 2


def test_calendar_failure_keeps_booking_and_is_retryable():
    with SessionLocal() as session:
        appointment = _appointment(session)
        sync = calendar.synchronize(session, appointment, provider=FakeProvider(fail=True), actor="oper")
        assert appointment.status is AppointmentStatus.BOOKED
        assert sync.status == "failed"
        assert sync.error == "provider unavailable"
        assert sync.attempts == 1


def test_template_versions_are_immutable_and_policy_rejection_is_audited():
    with SessionLocal() as session:
        first = templates.publish(session, event="appointment_booked", channel="whatsapp", locale="es-CL", content="Hola {name}", required_variables=["name"], approved=False, actor="oper")
        second = templates.publish(session, event="appointment_booked", channel="whatsapp", locale="es-CL", content="Hola {name}, confirmado", required_variables=["name"], approved=True, actor="oper")
        assert second.version == first.version + 1
        assert templates.render(session, second.id, {"name": "Ana"}).content == "Hola Ana, confirmado"
        with pytest.raises(templates.TemplatePolicyError):
            templates.render(session, first.id, {"name": "Ana"}, business_initiated=True, actor="oper")
        with pytest.raises(templates.MissingTemplateVariable):
            templates.render(session, second.id, {}, business_initiated=True, actor="oper")
