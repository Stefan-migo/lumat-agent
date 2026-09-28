from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.state import get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    Appointment, AppointmentHistory, AppointmentStatus, AuditLog, Case, Conversation,
    Customer, Message, MessageDirection, MessageStatus, MessageType, User, UserRole,
)
from app.services import scheduling
from app.services.customers import get_or_create_customer
from _testdb import admin_database_url


@pytest.fixture(autouse=True)
def clean_manage_db(migrated_db):
    with psycopg.connect(admin_database_url(), autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customers, users RESTART IDENTITY CASCADE"
        )


def _seed_conversation():
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conversation = get_or_create_conversation(session, customer, customer.phone_e164)
        case = Case(conversation_id=conversation.id, customer_id=customer.id, service="Visita técnica")
        technician = User(username="manage-technician", password_hash="test", role=UserRole.TECNICO)
        session.add_all([case, technician])
        session.flush()
        appointment = scheduling.book(
            session, service="Visita técnica", customer_id=customer.id, case_id=case.id,
            technician_id=technician.id, local_date=(datetime.now(timezone.utc) + timedelta(days=2)).date(),
            local_time=datetime.now(timezone.utc).time().replace(minute=0, second=0, microsecond=0),
            timezone_name="UTC", duration_minutes=60, actor="test",
        )
        inbound = Message(
            wamid="wamid.manage.seed", conversation_id=conversation.id,
            direction=MessageDirection.INBOUND, msg_type=MessageType.TEXT,
            text="quiero cancelar mi visita", status=MessageStatus.RECEIVED,
        )
        session.add(inbound)
        session.commit()
        return conversation.id, customer.id, appointment.id


def _add_message(conv_id, text, wamid):
    with SessionLocal() as session:
        message = Message(
            wamid=wamid, conversation_id=conv_id, direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT, text=text, status=MessageStatus.RECEIVED,
        )
        session.add(message)
        session.commit()
        return message.id


def _invoke(conv_id, message_id):
    with SessionLocal() as session:
        replies = run_conversation(session, session.get(Message, message_id))
        session.commit()
        return replies


def test_customer_confirms_cancellation_through_graph(mock_openai_chat, monkeypatch):
    from app.chat.nodes import classify_intent

    monkeypatch.setattr(
        classify_intent, "_llm_classify",
        lambda text, message_id: {"intent": "cancelar_visita", "service": None, "priority": None, "status": None, "injection": False},
    )
    conv_id, customer_id, appointment_id = _seed_conversation()
    offer = _invoke(conv_id, _add_message(conv_id, "quiero cancelar mi visita", "wamid.manage.ask"))
    assert any("confirm" in reply.lower() for reply in offer)
    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).captured_data["_manage_offer"]
        assert session.get(Appointment, appointment_id).status is AppointmentStatus.BOOKED

    replies = _invoke(conv_id, _add_message(conv_id, "sí, confirmo", "wamid.manage.confirm"))
    assert any("cancel" in reply.lower() or "anulad" in reply.lower() for reply in replies)
    with SessionLocal() as session:
        appointment = session.scalar(select(Appointment).where(Appointment.customer_id == customer_id))
        assert appointment.status is AppointmentStatus.CANCELLED
        assert appointment.history[-1].actor == "assistant"
        assert session.query(AuditLog).filter_by(action="appointment.cancelled").count() == 1


def _classify_cancel(monkeypatch):
    from app.chat.nodes import classify_intent

    monkeypatch.setattr(
        classify_intent, "_llm_classify",
        lambda text, message_id: {"intent": "cancelar_visita", "service": None, "priority": None, "status": None, "injection": False},
    )


def test_negative_confirmation_keeps_appointment_booked(mock_openai_chat, monkeypatch):
    _classify_cancel(monkeypatch)
    conv_id, _, appointment_id = _seed_conversation()
    _invoke(conv_id, _add_message(conv_id, "quiero cancelar", "wamid.manage.noask"))
    replies = _invoke(conv_id, _add_message(conv_id, "no", "wamid.manage.no"))
    assert any("mantendremos" in reply.lower() for reply in replies)
    with SessionLocal() as session:
        assert session.get(Appointment, appointment_id).status is AppointmentStatus.BOOKED
        assert session.query(AuditLog).filter_by(action="appointment.cancelled").count() == 0


def test_ambiguous_confirmation_hands_off_without_cancelling(mock_openai_chat, monkeypatch):
    _classify_cancel(monkeypatch)
    conv_id, _, appointment_id = _seed_conversation()
    _invoke(conv_id, _add_message(conv_id, "quiero cancelar", "wamid.manage.ambask"))
    clarification = _invoke(conv_id, _add_message(conv_id, "tal vez", "wamid.manage.ambiguous"))
    assert any("responde sí" in reply.lower() for reply in clarification)
    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).captured_data["_manage_offer"]["attempts"] == 1
    with SessionLocal() as session:
        message = Message(
            wamid="wamid.manage.ambiguous2", conversation_id=conv_id,
            direction=MessageDirection.INBOUND, msg_type=MessageType.TEXT,
            text="quizás", status=MessageStatus.RECEIVED,
        )
        session.add(message)
        session.commit()
        message_id = message.id
    _invoke(conv_id, message_id)
    with SessionLocal() as session:
        assert session.get(Appointment, appointment_id).status is AppointmentStatus.BOOKED
        assert "_manage_offer" not in session.get(Conversation, conv_id).captured_data
        assert session.query(AuditLog).filter_by(action="appointment.cancelled").count() == 0


def test_other_customers_appointment_is_never_offered(mock_openai_chat, monkeypatch):
    _classify_cancel(monkeypatch)
    conv_id, customer_id, _ = _seed_conversation()
    with SessionLocal() as session:
        appointment = session.query(Appointment).filter_by(customer_id=customer_id).one()
        other = get_or_create_customer(session, "+56922222222")
        appointment.customer_id = other.id
        session.commit()
        other_appointment_id = appointment.id
    replies = _invoke(conv_id, _add_message(conv_id, "quiero cancelar", "wamid.manage.owner"))
    assert any("no tienes visitas próximas" in reply.lower() for reply in replies)
    with SessionLocal() as session:
        assert session.get(Appointment, other_appointment_id).status is AppointmentStatus.BOOKED
        assert "_manage_offer" not in session.get(Conversation, conv_id).captured_data
        assert session.query(AuditLog).filter_by(action="appointment.cancelled").count() == 0


def test_started_appointment_is_not_cancellable(mock_openai_chat, monkeypatch):
    _classify_cancel(monkeypatch)
    conv_id, customer_id, appointment_id = _seed_conversation()
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        appointment.starts_at = past
        appointment.ends_at = past + timedelta(hours=1)
        appointment.local_start = past.replace(tzinfo=None)
        session.commit()
    replies = _invoke(conv_id, _add_message(conv_id, "quiero cancelar", "wamid.manage.past"))
    assert any("no tienes visitas próximas" in reply.lower() for reply in replies)
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        assert appointment.customer_id == customer_id
        assert appointment.status is AppointmentStatus.BOOKED
        assert appointment.history[-1].action == "booked"
        assert session.query(AuditLog).filter_by(action="appointment.cancelled").count() == 0


def test_customer_selects_numbered_appointment_before_confirmation(mock_openai_chat, monkeypatch):
    _classify_cancel(monkeypatch)
    conv_id, customer_id, first_id = _seed_conversation()
    with SessionLocal() as session:
        first = session.get(Appointment, first_id)
        second_start = first.starts_at + timedelta(days=1)
        second = Appointment(
            service="Mantención", customer_id=customer_id, case_id=first.case_id,
            technician_id=first.technician_id, local_start=first.local_start + timedelta(days=1),
            timezone=first.timezone, starts_at=second_start,
            ends_at=first.ends_at + timedelta(days=1), duration_minutes=first.duration_minutes,
        )
        session.add(second)
        session.commit()
        second_id = second.id
    offered = _invoke(conv_id, _add_message(conv_id, "quiero cancelar una visita", "wamid.manage.list"))
    assert any("1." in reply and "2." in reply for reply in offered)
    selected = _invoke(conv_id, _add_message(conv_id, "2", "wamid.manage.select"))
    assert any("confirm" in reply.lower() and "mantención" in reply.lower() for reply in selected)
    _invoke(conv_id, _add_message(conv_id, "sí", "wamid.manage.selectedconfirm"))
    with SessionLocal() as session:
        assert session.get(Appointment, first_id).status is AppointmentStatus.BOOKED
        assert session.get(Appointment, second_id).status is AppointmentStatus.CANCELLED
