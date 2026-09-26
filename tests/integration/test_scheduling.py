from datetime import date, time

import pytest

from app.db import SessionLocal
from app.models import Appointment, AppointmentHistory, AppointmentStatus, AuditLog, Case, Conversation, Customer, TechnicianAvailability, User
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


@pytest.mark.parametrize("outcome", [AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW])
def test_close_records_outcome_history_and_audit(outcome):
    with SessionLocal() as session:
        customer, case, technician = _linked_rows(session)
        appointment = scheduling.book(
            session, service="calefont", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=date(2026, 7, 15), local_time=time(10),
            timezone_name="America/Santiago", duration_minutes=60, actor="oper",
        )

        closed = scheduling.close(session, appointment, outcome=outcome, actor="oper", reason="visit ended")
        session.flush()

        assert closed.status is outcome
        history = session.query(AppointmentHistory).filter_by(appointment_id=closed.id).order_by(AppointmentHistory.id).all()
        assert [entry.action for entry in history] == ["booked", outcome.value]
        assert history[-1].from_status is AppointmentStatus.BOOKED
        assert session.query(AuditLog).filter_by(action=f"appointment.{outcome.value}").count() == 1


def test_close_rejects_non_booked_appointment():
    with SessionLocal() as session:
        customer, case, technician = _linked_rows(session)
        appointment = scheduling.book(
            session, service="calefont", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=date(2026, 7, 15), local_time=time(10),
            timezone_name="America/Santiago", duration_minutes=60, actor="oper",
        )
        scheduling.close(session, appointment, outcome=AppointmentStatus.COMPLETED, actor="oper")

        with pytest.raises(ValueError, match="only booked appointments can be closed"):
            scheduling.close(session, appointment, outcome=AppointmentStatus.NO_SHOW, actor="oper")


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
