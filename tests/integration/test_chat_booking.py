from datetime import date, datetime, time, timedelta, timezone

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.state import get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    Appointment, AppointmentHistory, AuditLog, Case, Conversation, Customer,
    Message, MessageDirection, MessageStatus, MessageType, TechnicianAvailability,
    User, UserRole,
    TechnicianWeeklySchedule,
)
from app.services import scheduling
from app.services.settings import REPLY_TEXT_DEFAULTS, REPLY_TEXTS_KEY, set_setting
from app.services.customers import get_or_create_customer
from _testdb import admin_database_url


@pytest.fixture(autouse=True)
def clean_booking_db(migrated_db):
    with psycopg.connect(admin_database_url(), autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customers, users RESTART IDENTITY CASCADE"
        )


def _seed_conversation(*, captured=None, service="Visita técnica", service_durations=None):
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, customer.phone_e164)
        conv.captured_data = captured or {
            "name": "Ana", "comuna": "Providencia", "address": "Calle 1",
            "equipment": "Calefont", "failure": "No enciende", "evidence": "unknown",
            "availability": "flexible", "_pending": "consent",
        }
        case = Case(conversation_id=conv.id, customer_id=customer.id, service=service)
        technician = User(
            username="booking-technician", password_hash="test", role=UserRole.TECNICO
        )
        session.add_all([case, technician])
        session.flush()
        set_setting(session, "hours.timezone", "UTC")
        if service_durations is not None:
            set_setting(session, "booking.service_durations", service_durations)
        conv_id, customer_id, case_id, technician_id = conv.id, customer.id, case.id, technician.id
        inbound = Message(
            wamid="wamid.booking.seed", conversation_id=conv.id,
            direction=MessageDirection.INBOUND, msg_type=MessageType.TEXT,
            text="quiero una visita", status=MessageStatus.RECEIVED,
        )
        session.add(inbound)
        session.commit()
        return conv_id, customer_id, case_id, technician_id, inbound.id


def _add_message(conv_id, text, wamid):
    with SessionLocal() as session:
        message = Message(
            wamid=wamid, conversation_id=conv_id,
            direction=MessageDirection.INBOUND, msg_type=MessageType.TEXT,
            text=text, status=MessageStatus.RECEIVED,
        )
        session.add(message)
        session.commit()
        return message.id


def _invoke(conv_id, message_id):
    with SessionLocal() as session:
        message = session.get(Message, message_id)
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _available_slot(session, technician_id, now):
    starts = now + timedelta(days=2)
    starts = starts.replace(minute=0, second=0, microsecond=0)
    scheduling.add_availability(
        session, technician_id=technician_id,
        starts_at=starts, ends_at=starts + timedelta(hours=3),
    )
    return starts


def test_customer_confirms_numbered_offer_and_books_with_audit_and_history(
    mock_openai_chat,
):
    conv_id, customer_id, case_id, tech_id, _ = _seed_conversation()
    with SessionLocal() as session:
        _available_slot(session, tech_id, datetime.now(timezone.utc))
        session.commit()

    first_id = _add_message(conv_id, "si", "wamid.booking.ask")
    offer = _invoke(conv_id, first_id)
    assert any("1." in reply for reply in offer)
    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).captured_data["_booking_offer"]
        assert session.query(Appointment).count() == 0

    confirm_id = _add_message(conv_id, "1", "wamid.booking.confirm")
    confirmation = _invoke(conv_id, confirm_id)

    assert any("confirm" in reply.lower() for reply in confirmation)
    with SessionLocal() as session:
        appointment = session.scalar(select(Appointment).where(Appointment.customer_id == customer_id))
        assert appointment is not None and appointment.status.value == "booked"
        assert appointment.case_id == case_id and appointment.technician_id == tech_id
        assert appointment.history[0].actor == "assistant"
        assert session.query(AuditLog).filter_by(action="appointment.booked").count() == 1


@pytest.mark.parametrize(
    ("service_durations", "expected_duration"),
    [({"Caldera": 90}, 90), ({}, 60)],
)
def test_chat_booking_uses_configured_service_duration(
    mock_openai_chat, service_durations, expected_duration
):
    conv_id, customer_id, _, tech_id, _ = _seed_conversation(
        service="Caldera", service_durations=service_durations
    )
    with SessionLocal() as session:
        _available_slot(session, tech_id, datetime.now(timezone.utc))
        session.commit()

    _invoke(conv_id, _add_message(conv_id, "si", "wamid.booking.duration.ask"))
    _invoke(conv_id, _add_message(conv_id, "1", "wamid.booking.duration.confirm"))

    with SessionLocal() as session:
        appointment = session.scalar(
            select(Appointment).where(Appointment.customer_id == customer_id)
        )
        assert appointment.duration_minutes == expected_duration


def test_configured_booking_texts_render_their_slots(mock_openai_chat):
    with SessionLocal() as session:
        set_setting(
            session,
            REPLY_TEXTS_KEY,
            {
                **REPLY_TEXT_DEFAULTS,
                "booking_confirmed": "Quedaste agendado para el {{fecha}}.",
            },
            actor="test",
        )
        session.commit()
    conv_id, customer_id, case_id, tech_id, _ = _seed_conversation()
    with SessionLocal() as session:
        _available_slot(session, tech_id, datetime.now(timezone.utc))
        session.commit()

    offer = _invoke(conv_id, _add_message(conv_id, "si", "wamid.custom.ask"))
    assert any("1." in reply for reply in offer)

    confirmation = _invoke(conv_id, _add_message(conv_id, "1", "wamid.custom.confirm"))

    assert len(confirmation) == 1
    assert confirmation[0].startswith("Quedaste agendado para el ")
    assert "{{" not in confirmation[0]


def test_no_confirmation_does_not_book(mock_openai_chat):
    conv_id, _, _, tech_id, _ = _seed_conversation()
    with SessionLocal() as session:
        _available_slot(session, tech_id, datetime.now(timezone.utc))
        session.commit()
    _invoke(conv_id, _add_message(conv_id, "si", "wamid.booking.noask"))
    clarification = _invoke(conv_id, _add_message(conv_id, "gracias", "wamid.booking.noack"))
    assert any("horario" in reply.lower() for reply in clarification)
    with SessionLocal() as session:
        assert session.query(Appointment).count() == 0


def test_missing_case_hands_off_without_booking(mock_openai_chat):
    conv_id, _, _, tech_id, _ = _seed_conversation()
    with SessionLocal() as session:
        session.query(Case).filter_by(conversation_id=conv_id).delete()
        other = Customer(phone_e164="+56922222222")
        session.add(other)
        session.flush()
        session.add(Case(conversation_id=conv_id, customer_id=other.id, service="test"))
        _available_slot(session, tech_id, datetime.now(timezone.utc))
        session.commit()
    replies = _invoke(conv_id, _add_message(conv_id, "si", "wamid.booking.nocase"))
    assert any("asesor" in reply.lower() for reply in replies)
    with SessionLocal() as session:
        assert session.query(Appointment).count() == 0


def test_slot_taken_before_confirmation_reoffers_without_crashing(mock_openai_chat):
    conv_id, customer_id, case_id, tech_id, _ = _seed_conversation()
    with SessionLocal() as session:
        starts = _available_slot(session, tech_id, datetime.now(timezone.utc))
        other = Customer(phone_e164="+56911111111")
        session.add(other)
        session.flush()
        other_case = Case(conversation_id=None, customer_id=other.id, service="test")
        session.add(other_case)
        session.flush()
        session.commit()
        other_customer_id, other_case_id = other.id, other_case.id
    _invoke(conv_id, _add_message(conv_id, "si", "wamid.booking.raceask"))
    with SessionLocal() as session:
        scheduling.book(
            session, service="test", customer_id=other_customer_id, case_id=other_case_id,
            technician_id=tech_id, local_date=starts.date(), local_time=starts.time(),
            timezone_name="UTC", duration_minutes=60, actor="test",
        )
        session.commit()
    response = _invoke(conv_id, _add_message(conv_id, "1", "wamid.booking.raceconfirm"))
    assert any("1." in reply for reply in response)
    with SessionLocal() as session:
        assert session.query(Appointment).filter_by(customer_id=customer_id).count() == 0


def test_no_technician_availability_hands_off(mock_openai_chat):
    conv_id, _, _, _, _ = _seed_conversation()
    replies = _invoke(conv_id, _add_message(conv_id, "si", "wamid.booking.noavailability"))
    assert any("asesor" in reply.lower() for reply in replies)
    with SessionLocal() as session:
        assert session.query(Appointment).count() == 0


def test_weekly_schedule_alone_produces_chat_slot_offer(mock_openai_chat):
    conv_id, _, _, tech_id, _ = _seed_conversation()
    with SessionLocal() as session:
        session.add_all(TechnicianWeeklySchedule(
            technician_id=tech_id, weekday=weekday,
            opens_at=time(0), closes_at=time(23, 59),
        ) for weekday in range(1, 8))
        session.commit()

    replies = _invoke(conv_id, _add_message(conv_id, "si", "wamid.booking.weekly"))

    assert any("1." in reply for reply in replies)
    with SessionLocal() as session:
        assert session.query(TechnicianAvailability).filter_by(technician_id=tech_id).count() > 0


def _aligned_start(now, days=2):
    return (now + timedelta(days=days)).replace(minute=0, second=0, microsecond=0)


def test_asking_for_more_slots_offers_the_next_page_on_the_same_day(mock_openai_chat):
    """S1 (chatbot-experiencia): "más horarios" pages through the frozen offer.

    Asking for another time is a request the bot can serve, not a failed
    understanding: before this the second message got a clarification and the
    third one handed the customer to a person with the agenda wide open.
    """
    conv_id, _, _, tech_id, _ = _seed_conversation()
    with SessionLocal() as session:
        _available_slot(session, tech_id, datetime.now(timezone.utc))  # five grid slots
        session.commit()

    first = _invoke(conv_id, _add_message(conv_id, "si", "wamid.more.ask"))
    assert any("3." in reply for reply in first)

    second = _invoke(conv_id, _add_message(conv_id, "más horarios", "wamid.more.next"))

    assert len(second) == 1
    assert "1." in second[0] and "2." in second[0]
    assert "3." not in second[0]  # the page carries the two slots left that day
    assert "asesor" not in second[0].lower()
    with SessionLocal() as session:
        assert session.query(Appointment).count() == 0


def test_asking_for_more_slots_says_the_day_is_exhausted_and_offers_other_days(
    mock_openai_chat,
):
    """S1: when that day has nothing left, say it instead of repeating three slots."""
    conv_id, _, _, tech_id, _ = _seed_conversation()
    with SessionLocal() as session:
        starts = _aligned_start(datetime.now(timezone.utc))
        scheduling.add_availability(
            session, technician_id=tech_id, starts_at=starts,
            ends_at=starts + timedelta(hours=2),  # exactly three grid slots
        )
        tomorrow = starts + timedelta(days=1)
        scheduling.add_availability(
            session, technician_id=tech_id, starts_at=tomorrow,
            ends_at=tomorrow + timedelta(hours=2),
        )
        session.commit()

    _invoke(conv_id, _add_message(conv_id, "si", "wamid.exhausted.ask"))
    second = _invoke(
        conv_id, _add_message(conv_id, "no puedo en esos horarios", "wamid.exhausted.next")
    )

    assert len(second) == 1
    assert second[0].startswith("Para ese día no me quedan más horarios.")
    assert "1." in second[0]
    assert "asesor" not in second[0].lower()


def test_asking_for_more_slots_without_any_left_hands_off(mock_openai_chat):
    """S1: only when there is nothing left to offer does the bot escalate."""
    conv_id, _, _, tech_id, _ = _seed_conversation()
    with SessionLocal() as session:
        starts = _aligned_start(datetime.now(timezone.utc))
        scheduling.add_availability(
            session, technician_id=tech_id, starts_at=starts,
            ends_at=starts + timedelta(hours=2),  # the whole offer fits in one page
        )
        session.commit()

    _invoke(conv_id, _add_message(conv_id, "si", "wamid.nomoreslot.ask"))
    second = _invoke(
        conv_id, _add_message(conv_id, "hay otros horarios?", "wamid.nomoreslot.next")
    )

    assert any("asesor" in reply.lower() for reply in second)
    with SessionLocal() as session:
        assert session.query(Appointment).count() == 0
