"""Automation recipes declare exact-match conditions and Meta templates (S1+)."""

from datetime import date, time
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    AutomationRule,
    Case,
    Conversation,
    Customer,
    DomainEvent,
    NotificationOperation,
    User,
)
from app.services import recipes, scheduling
from app.services.automation import evaluate_event
from app.services.automation_installations import install
from app.services.events import publish_event
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_automation_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE automation_executions, automation_rules, domain_events, "
            "notification_operations, audit_log RESTART IDENTITY CASCADE"
        )
    yield


def _book(session, *, actor: str):
    suffix = str(uuid4().int)[:10]
    technician = User(username=f"tech-{suffix}", password_hash="unused")
    customer = Customer(phone_e164=f"+56948{suffix[:6]}", name="Cliente Prueba")
    session.add_all([technician, customer])
    session.flush()
    conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
    session.add(conversation)
    session.flush()
    case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont")
    session.add(case)
    session.flush()
    appointment = scheduling.book(
        session, service="calefont", customer_id=customer.id, case_id=case.id,
        technician_id=technician.id, local_date=date(2026, 8, 20), local_time=time(10),
        timezone_name="America/Santiago", duration_minutes=60, actor=actor,
    )
    session.flush()
    return appointment


def test_appointment_confirmation_recipe_declares_panel_origin_condition():
    recipe = recipes.get_recipe("appointment_confirmation")
    fields = recipe.compile_rule_fields({"channel": "whatsapp"})
    assert fields["conditions"] == {"origin": "panel"}


def test_recipe_without_conditions_still_compiles_to_empty_conditions():
    recipe = recipes.get_recipe("appointment_cancellation")
    assert recipe.compile_rule_fields({"channel": "whatsapp"})["conditions"] == {}


def test_confirmation_recipe_fires_only_for_panel_bookings(migrated_db):
    with SessionLocal() as session:
        install(session, "appointment_confirmation", {"channel": "whatsapp"}, actor="admin", enabled=True)
        session.flush()

        assistant = publish_event(
            session, event_type="appointment.booked", entity_type="appointment", entity_id="1",
            payload={"customer_id": 1, "recipient": "+56900000001", "origin": "assistant"},
            dedupe_key="booked:assistant",
        )
        panel = publish_event(
            session, event_type="appointment.booked", entity_type="appointment", entity_id="2",
            payload={"customer_id": 2, "recipient": "+56900000002", "origin": "panel"},
            dedupe_key="booked:panel",
        )
        session.flush()

        assert evaluate_event(session, assistant) == []
        assert evaluate_event(session, panel) != []
        assert session.scalars(select(NotificationOperation.recipient)).all() == ["+56900000002"]
        session.commit()


@pytest.mark.parametrize(("actor", "expected"), [("assistant", "assistant"), ("oper", "panel")])
def test_book_publishes_origin_in_the_event_payload(migrated_db, actor, expected):
    with SessionLocal() as session:
        appointment = _book(session, actor=actor)
        event = session.scalar(
            select(DomainEvent).where(
                DomainEvent.event_type == "appointment.booked",
                DomainEvent.entity_id == str(appointment.id),
            )
        )
        assert event is not None
        assert event.payload["origin"] == expected
        session.commit()
