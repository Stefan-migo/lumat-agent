from datetime import date, time

import pytest

from app.db import SessionLocal
from app.models import Appointment, AppointmentStatus, Case, Conversation, Customer, TechnicianAvailability, User
from app.services import scheduling


def _linked_rows(session, technician_id=1):
    technician = User(username="technician", password_hash="test-password-hash")
    session.add(technician)
    session.flush()
    customer = Customer(phone_e164="+56912345678")
    session.add(customer)
    session.flush()
    conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
    session.add(conversation)
    session.flush()
    case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont")
    session.add(case)
    session.flush()
    return customer, case, technician


def test_booking_history_cancel_and_rebook_free_the_slot():
    with SessionLocal() as session:
        customer, case, technician = _linked_rows(session)
        first = scheduling.book(
            session, service="calefont", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=date(2026, 7, 15), local_time=time(10),
            timezone_name="America/Santiago", duration_minutes=60, actor="oper",
        )
        scheduling.cancel(session, first, actor="oper", reason="customer request")
        second = scheduling.book(
            session, service="calefont", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=date(2026, 7, 15), local_time=time(10),
            timezone_name="America/Santiago", duration_minutes=60, actor="oper",
        )

        assert first.status is AppointmentStatus.CANCELLED
        assert second.status is AppointmentStatus.BOOKED
        assert [entry.action for entry in first.history] == ["booked", "cancelled"]


def test_booking_rejects_unlinked_case_and_overlapping_active_appointment():
    with SessionLocal() as session:
        customer, case, technician = _linked_rows(session)
        with pytest.raises(scheduling.UnlinkedAppointment):
            scheduling.book(
                session, service="calefont", customer_id=customer.id, case_id=999999,
                technician_id=technician.id, local_date=date(2026, 7, 15), local_time=time(10),
                timezone_name="America/Santiago", duration_minutes=60, actor="oper",
            )


def test_configured_availability_rejects_outside_block():
    with SessionLocal() as session:
        customer, case, technician = _linked_rows(session)
        starts, ends = scheduling.local_interval(date(2026, 7, 15), time(10), "America/Santiago", 60)
        scheduling.add_availability(session, technician_id=technician.id, starts_at=starts, ends_at=ends)
        with pytest.raises(ValueError, match="not available"):
            scheduling.book(
                session, service="calefont", customer_id=customer.id, case_id=case.id,
                technician_id=technician.id, local_date=date(2026, 7, 15), local_time=time(12),
                timezone_name="America/Santiago", duration_minutes=60, actor="oper",
            )
        scheduling.book(
            session, service="calefont", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=date(2026, 7, 15), local_time=time(10),
            timezone_name="America/Santiago", duration_minutes=60, actor="oper",
        )
        other = Customer(phone_e164="+56987654321")
        session.add(other)
        session.flush()
        other_case = Case(conversation_id=case.conversation_id, customer_id=other.id)
        session.add(other_case)
        session.flush()
        with pytest.raises(scheduling.AppointmentConflict):
            scheduling.book(
                session, service="calefont", customer_id=other.id, case_id=other_case.id,
                technician_id=technician.id, local_date=date(2026, 7, 15), local_time=time(10, 30),
                timezone_name="America/Santiago", duration_minutes=30, actor="oper",
            )
