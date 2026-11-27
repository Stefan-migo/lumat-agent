"""The deterministic answer about the visit the customer already holds.

Measured production case (2026-11-27, conversation 50): the customer asked which
technician was coming to her Monday visit and read free hours; her next message
("tengo una hora agendada") was stored as a preference and answered "todavía no
queda agendada". The appointment was `booked` the whole time.

Owner decisions this file pins: the technician is always named, every upcoming
visit is named, and an appointment with nobody assigned says so instead of
deriving to a person.
"""

from datetime import datetime, time, timedelta, timezone

import psycopg
import pytest

from app.chat.nodes import configured_answers
from app.chat.slot_window import when_label
from app.chat.state import ConversationState
from app.db import SessionLocal
from app.models import Appointment, Case, User, UserRole
from app.services import scheduling
from app.services.customers import get_or_create_customer
from app.services.settings import set_setting
from _testdb import admin_database_url

PHONE = "+5492972542298"


@pytest.fixture(autouse=True)
def clean_appointment_status_db(migrated_db):
    with psycopg.connect(admin_database_url(), autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customers, users RESTART IDENTITY CASCADE"
        )


def _state(text: str) -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone=PHONE,
        turn=2,
        intent="consulta",
        window=[{"id": 1, "text": text}],
        captured={},
    )


def _seed_visits(visits: list[tuple[int, str | None]]) -> list[int]:
    """Book one visit per `(days_ahead, technician_name)` at 14:00 local time.

    `technician_name=None` books the visit the way the panel can leave it with no
    name loaded, which is the S2.3 shape.
    """
    with SessionLocal() as session:
        set_setting(
            session,
            "hours.schedule",
            [{"days": [1, 2, 3, 4, 5, 6, 7], "open": "00:00", "close": "23:59"}],
        )
        customer = get_or_create_customer(session, PHONE)
        case = Case(service="Visita técnica", customer_id=customer.id)
        technicians = []
        for index, (_, technician_name) in enumerate(visits):
            technicians.append(
                User(
                    username=f"status-technician-{index}",
                    password_hash="test",
                    role=UserRole.TECNICO,
                    name=technician_name,
                )
            )
        session.add_all([case, *technicians])
        session.flush()
        today = datetime.now(timezone.utc).date()
        for technician, (days_ahead, _) in zip(technicians, visits):
            day = today + timedelta(days=days_ahead)
            scheduling.add_availability(
                session,
                technician_id=technician.id,
                starts_at=datetime.combine(day, time(8, 0), tzinfo=timezone.utc),
                ends_at=datetime.combine(day, time(23, 0), tzinfo=timezone.utc),
            )
        session.flush()
        appointment_ids = []
        for technician, (days_ahead, _) in zip(technicians, visits):
            appointment = scheduling.book(
                session,
                service="Visita técnica",
                customer_id=customer.id,
                case_id=case.id,
                technician_id=technician.id,
                local_date=today + timedelta(days=days_ahead),
                local_time=time(14, 0),
                timezone_name="America/Santiago",
                duration_minutes=60,
                actor="integration-test",
            )
            appointment_ids.append(appointment.id)
        session.commit()
        return appointment_ids


def _reply(text: str) -> str | None:
    with SessionLocal() as session:
        return configured_answers.appointment_status_reply(session, _state(text))


def test_the_booked_visit_answers_with_its_date_service_and_technician():
    _seed_visits([(3, "Max Escanilla")])
    with SessionLocal() as session:
        appointment = session.get(Appointment, 1)
        expected_label = when_label(appointment.local_start)

    reply = _reply("Tengo una visita para el lunes, puedes confirmarme que tecnico va?")

    assert reply is not None
    assert expected_label in reply
    assert "Visita técnica" in reply
    assert "Max Escanilla" in reply
    # The defect itself: free hours must never answer a question about a held visit.
    assert "horas libres" not in reply


def test_every_upcoming_visit_is_named_and_numbered():
    _seed_visits([(3, "Max Escanilla"), (5, "Stefan Miranda")])

    reply = _reply("Tengo una hora agendada para el lunes")

    assert reply is not None
    assert "1." in reply and "2." in reply
    assert "Max Escanilla" in reply
    assert "Stefan Miranda" in reply


def test_a_visit_without_a_technician_says_it_is_pending_instead_of_deriving():
    _seed_visits([(3, None)])

    reply = _reply("me confirmas a que hora es mi visita?")

    assert reply is not None
    assert "por asignar" in reply


def test_no_upcoming_visit_is_answered_with_that_fact():
    _seed_visits([])

    reply = _reply("Tengo una visita para el lunes, puedes confirmarme que tecnico va?")

    assert reply is not None
    assert "No tienes visitas agendadas" in reply


def test_a_past_visit_is_not_named_as_an_upcoming_one():
    _seed_visits([(-2, "Max Escanilla")])

    reply = _reply("Tengo una hora agendada para el lunes")

    assert reply is not None
    assert "No tienes visitas agendadas" in reply


def test_an_availability_question_keeps_its_own_answer_even_with_a_booked_visit():
    """The precedence that caused the defect: availability still answers availability."""
    _seed_visits([(3, "Max Escanilla")])

    with SessionLocal() as session:
        state = _state("¿tienen hora el lunes?")
        assert configured_answers.appointment_status_reply(session, state) is None
        reply = configured_answers.configuration_reply(session, state)

    assert reply is not None
    assert "visita agendada" not in reply


def test_a_change_request_is_left_to_appointment_management():
    _seed_visits([(3, "Max Escanilla")])

    assert _reply("quiero reagendar mi visita") is None
