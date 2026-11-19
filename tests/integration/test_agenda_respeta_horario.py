from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from app.chat.nodes.orchestrate import orchestrate
from app.chat.state import ConversationState
from app.db import SessionLocal
from app.models import (
    Appointment,
    Case,
    Conversation,
    Customer,
    User,
    UserRole,
)
from _testdb import admin_database_url


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(admin_database_url(), autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, technician_availability, technician_weekly_schedule, "
            "appointment_history, appointments, audit_log, conversation_events, "
            "cases, messages, conversations, customers, users RESTART IDENTITY CASCADE"
        )
    yield


def test_s4_orchestrate_uses_database_for_upcoming_appointment():
    question_state = None
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56912345678")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        question_state = ConversationState(
            customer_id=customer.id,
            conversation_id=conversation.id,
            phone=customer.phone_e164,
            intent="reagendar_visita",
            window=[{"id": 1, "text": "¿Pueden agendar una visita?"}],
        )
        session.commit()

    # S4: with no visit to move the turn is a visit request, so capture starts and
    # names the hour back (S3) instead of the answering path offering a kb_miss.
    assert orchestrate(question_state) == {"next_step": "capture"}

    with SessionLocal() as session:
        customer = session.get(Customer, question_state.customer_id)
        case = Case(
            conversation_id=question_state.conversation_id,
            customer_id=customer.id,
            service="Visita técnica",
        )
        technician = User(
            username="s4-technician", password_hash="test", role=UserRole.TECNICO
        )
        session.add_all([case, technician])
        session.flush()
        starts_at = datetime.now(timezone.utc) + timedelta(days=2)
        session.add(
            Appointment(
                service="Visita técnica",
                customer_id=customer.id,
                case_id=case.id,
                technician_id=technician.id,
                local_start=starts_at.replace(tzinfo=None),
                timezone="UTC",
                starts_at=starts_at,
                ends_at=starts_at + timedelta(hours=1),
                duration_minutes=60,
            )
        )
        session.commit()

    assert orchestrate(question_state) == {"next_step": "manage"}


def test_s4_a_time_preference_inside_a_capture_stays_in_capture():
    """S4 with a pending field: measured twice, capture is the only good answer.

    `real-dato-mas-pregunta` turn 3 ("es factible que pases tipo 14 horas?") was
    classified `reagendar_visita` on the `agenda-house-3` run and, because the
    dispatch put S4 behind the mid-capture question path, fell through to the
    answering path: the reply was a kb_miss offer ("No tengo ese dato. ¿Prefieres
    que te tome los datos…?") and the judge capped the scenario at 0.00. The
    sentence is a time preference, not a KB question.
    """
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56912345679")
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id,
            wa_phone=customer.phone_e164,
            captured_data={"_pending": ["failure"], "_asked": {"failure": 1}},
        )
        session.add(conversation)
        session.commit()
        state = ConversationState(
            customer_id=customer.id,
            conversation_id=conversation.id,
            phone=customer.phone_e164,
            intent="reagendar_visita",
            captured={"_pending": ["failure"], "_asked": {"failure": 1}},
            window=[{"id": 1, "text": "es factible que pases tipo 14 horas?"}],
        )

    assert orchestrate(state) == {"next_step": "capture"}
