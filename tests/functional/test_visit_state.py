from datetime import date, time, timedelta

import pytest

from app.db import SessionLocal
from app.models import (
    Appointment,
    AppointmentHistory,
    AppointmentStatus,
    AuditLog,
    Case,
    Conversation,
    Customer,
    TechnicianVisitState,
)
from app.services import scheduling, visit_state


def _booked(technician_id: int) -> int:
    with SessionLocal() as session:
        customer = Customer(
            phone_e164="+56900000201", name="Cliente", email="private@example.test",
            address="Calle 1", comuna="Providencia", consent_status=True,
        )
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont", summary="s", status="open")
        session.add(case)
        session.flush()
        appointment = scheduling.book(
            session, service="calefont", customer_id=customer.id, case_id=case.id,
            technician_id=technician_id, local_date=date(2026, 5, 4), local_time=time(10),
            timezone_name="America/Santiago", duration_minutes=60, actor="oper",
        )
        session.commit()
        return appointment.id


def test_en_route_window_opens_at_t_minus_60(make_user):
    appointment_id = _booked(make_user("tech", "tech-pass", role="tecnico"))
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)

        assert visit_state.is_available(appointment, TechnicianVisitState.EN_ROUTE, appointment.starts_at - timedelta(minutes=60, seconds=1)) is False
        assert visit_state.is_available(appointment, TechnicianVisitState.EN_ROUTE, appointment.starts_at - timedelta(minutes=60)) is True
        assert visit_state.is_available(appointment, TechnicianVisitState.EN_ROUTE, appointment.starts_at) is True


def test_arrived_window_opens_at_t_minus_15(make_user):
    appointment_id = _booked(make_user("tech", "tech-pass", role="tecnico"))
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)

        assert visit_state.is_available(appointment, TechnicianVisitState.ARRIVED, appointment.starts_at - timedelta(minutes=16)) is False
        assert visit_state.is_available(appointment, TechnicianVisitState.ARRIVED, appointment.starts_at - timedelta(minutes=15)) is True


def test_skipping_en_route_is_allowed(make_user):
    appointment_id = _booked(make_user("tech", "tech-pass", role="tecnico"))
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)

        visit_state.mark(session, appointment, state=TechnicianVisitState.ARRIVED, actor="tech", now=appointment.starts_at - timedelta(minutes=15))
        session.commit()

        assert appointment.technician_state is TechnicianVisitState.ARRIVED


def test_window_closes_at_ends_at(make_user):
    appointment_id = _booked(make_user("tech", "tech-pass", role="tecnico"))
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)

        assert visit_state.is_available(appointment, TechnicianVisitState.ARRIVED, appointment.ends_at - timedelta(seconds=1)) is True
        assert visit_state.is_available(appointment, TechnicianVisitState.ARRIVED, appointment.ends_at) is False


def test_a_closed_visit_closes_the_window(make_user):
    appointment_id = _booked(make_user("tech", "tech-pass", role="tecnico"))
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        appointment.status = AppointmentStatus.COMPLETED

        assert visit_state.is_available(appointment, TechnicianVisitState.ARRIVED, appointment.starts_at) is False


def test_transitions_are_forward_only(make_user):
    appointment_id = _booked(make_user("tech", "tech-pass", role="tecnico"))
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        now = appointment.starts_at - timedelta(minutes=15)
        visit_state.mark(session, appointment, state=TechnicianVisitState.ARRIVED, actor="tech", now=now)

        assert visit_state.is_available(appointment, TechnicianVisitState.EN_ROUTE, now) is False
        with pytest.raises(visit_state.VisitStateUnavailable):
            visit_state.mark(session, appointment, state=TechnicianVisitState.EN_ROUTE, actor="tech", now=now)


def test_repeating_a_state_is_allowed_within_the_window(make_user):
    appointment_id = _booked(make_user("tech", "tech-pass", role="tecnico"))
    first = None
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        first = appointment.starts_at - timedelta(minutes=60)
        second = appointment.starts_at - timedelta(minutes=50)
        visit_state.mark(session, appointment, state=TechnicianVisitState.EN_ROUTE, actor="tech", now=first)
        visit_state.mark(session, appointment, state=TechnicianVisitState.EN_ROUTE, actor="tech", now=second)
        session.commit()

    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        assert appointment.technician_state is TechnicianVisitState.EN_ROUTE
        assert appointment.technician_state_at == second
        assert session.query(AuditLog).filter_by(action="appointment.en_route", entity_id=str(appointment_id)).count() == 2


def test_mark_persists_the_state_and_audits_without_touching_history(make_user):
    appointment_id = _booked(make_user("tech", "tech-pass", role="tecnico"))
    moment = None
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        moment = appointment.starts_at - timedelta(minutes=60)
        visit_state.mark(session, appointment, state=TechnicianVisitState.EN_ROUTE, actor="tech", now=moment)
        session.commit()

    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        assert appointment.technician_state is TechnicianVisitState.EN_ROUTE
        assert appointment.technician_state_at == moment
        assert session.query(AuditLog).filter_by(action="appointment.en_route", entity="appointment", entity_id=str(appointment_id)).count() == 1
        # Field-state events never go to appointment_history: its to_status is
        # NOT NULL on the appointment_status enum (state machine design).
        assert [row.action for row in session.query(AppointmentHistory).filter_by(appointment_id=appointment_id)] == ["booked"]


def test_mark_rejects_an_unavailable_transition_and_leaves_state_unchanged(make_user):
    appointment_id = _booked(make_user("tech", "tech-pass", role="tecnico"))
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        with pytest.raises(visit_state.VisitStateUnavailable):
            visit_state.mark(session, appointment, state=TechnicianVisitState.EN_ROUTE, actor="tech", now=appointment.starts_at - timedelta(minutes=61))
        session.commit()

    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        assert appointment.technician_state is None
        assert appointment.technician_state_at is None
        assert session.query(AuditLog).filter_by(entity_id=str(appointment_id)).count() == 1  # only appointment.booked
