"""Audience contracts for durable panel notification fan-out (S2-S6)."""

from datetime import date, time

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Case, Conversation, Customer, NotificationOperation, PanelNotification, User, UserRole
from app.services import scheduling
from app.services.notifications import notify_admins
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_notification_audience(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute("TRUNCATE panel_notifications, notification_operations, users, customers RESTART IDENTITY CASCADE")
    yield


def _user(username: str, role: UserRole = UserRole.OPERADOR, *, active: bool = True) -> int:
    with SessionLocal() as session:
        user = User(username=username, password_hash="unused", role=role, active=active)
        session.add(user)
        session.commit()
        return user.id


def _notify(*, recipients: list[int] | None = None, source: str = "appointment") -> tuple[int, int]:
    with SessionLocal() as session:
        notify_admins(
            session, title="Aviso", content="Aviso de prueba", source=source,
            source_id="17", dedupe_key=f"{source}:17",
            recipient_user_ids=recipients,
        )
        session.commit()
        operation = session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == f"panel:{source}:17"
        ))
        return operation.id, operation.id


def test_visit_fanout_includes_admin_and_assigned_technician_once():
    admin = _user("visit-admin", UserRole.ADMIN)
    technician = _user("visit-technician", UserRole.TECNICO)
    operation_id, _ = _notify(recipients=[technician, admin])
    with SessionLocal() as session:
        rows = session.scalars(select(PanelNotification).where(PanelNotification.operation_id == operation_id)).all()
        assert {row.user_id for row in rows} == {admin, technician}
        assert len(rows) == 2


def test_scheduling_booking_notifies_admin_and_assigned_technician():
    admin = _user("booked-visit-admin", UserRole.ADMIN)
    technician = _user("booked-visit-technician", UserRole.TECNICO)
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56911110002")
        session.add(customer)
        session.flush()
        case = Case(customer_id=customer.id, service="calefont")
        session.add(case)
        session.flush()
        appointment = scheduling.book(
            session, service="calefont", customer_id=customer.id, case_id=case.id,
            technician_id=technician, local_date=date(2027, 7, 15), local_time=time(10),
            timezone_name="UTC", duration_minutes=60, actor="oper",
        )
        operation = session.scalar(select(NotificationOperation).where(
            NotificationOperation.idempotency_key == f"panel:appointment:{appointment.id}:booked"
        ))
        rows = session.scalars(select(PanelNotification).where(
            PanelNotification.operation_id == operation.id
        )).all()
        assert {row.user_id for row in rows} == {admin, technician}
        assert len(rows) == 2


def test_technician_who_is_admin_gets_one_visit_row():
    admin_technician = _user("admin-technician", UserRole.ADMIN)
    operation_id, _ = _notify(recipients=[admin_technician, admin_technician])
    with SessionLocal() as session:
        rows = session.scalars(select(PanelNotification).where(PanelNotification.operation_id == operation_id)).all()
        assert [row.user_id for row in rows] == [admin_technician]


def test_inactive_assigned_technician_does_not_break_or_get_dropped():
    admin = _user("inactive-test-admin", UserRole.ADMIN)
    inactive_technician = _user("inactive-technician", UserRole.TECNICO, active=False)
    operation_id, _ = _notify(recipients=[inactive_technician, admin])
    with SessionLocal() as session:
        assert {row.user_id for row in session.scalars(select(PanelNotification).where(
            PanelNotification.operation_id == operation_id
        )).all()} == {admin, inactive_technician}


def test_emergency_audience_includes_conversation_assignee_only_when_assigned():
    admin = _user("emergency-admin", UserRole.ADMIN)
    assigned = _user("emergency-assigned", UserRole.TECNICO)
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56911110001")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164, assigned_user_id=assigned)
        session.add(conversation)
        session.flush()
        assigned_id = conversation.assigned_user_id
    operation_id, _ = _notify(recipients=[assigned_id], source="emergencia")
    with SessionLocal() as session:
        rows = session.scalars(select(PanelNotification).where(PanelNotification.operation_id == operation_id)).all()
        assert {row.user_id for row in rows} == {admin, assigned}


def test_unassigned_emergency_defaults_to_admins_only():
    admin = _user("unassigned-emergency-admin", UserRole.ADMIN)
    technician = _user("unassigned-emergency-technician", UserRole.TECNICO)
    operation_id, _ = _notify(source="emergencia")
    with SessionLocal() as session:
        rows = session.scalars(select(PanelNotification).where(PanelNotification.operation_id == operation_id)).all()
        assert {row.user_id for row in rows} == {admin}
        assert technician not in {row.user_id for row in rows}


@pytest.mark.parametrize("source", ["cost_alert", "notification_failure"])
def test_admin_only_sources_never_fan_out_to_technician(source):
    admin = _user(f"{source}-admin", UserRole.ADMIN)
    technician = _user(f"{source}-technician", UserRole.TECNICO)
    operation_id, _ = _notify(source=source)
    with SessionLocal() as session:
        rows = session.scalars(select(PanelNotification).where(PanelNotification.operation_id == operation_id)).all()
        assert {row.user_id for row in rows} == {admin}
        assert technician not in {row.user_id for row in rows}


def test_notification_operation_remains_single_on_multi_user_fanout():
    admin = _user("single-operation-admin", UserRole.ADMIN)
    technician = _user("single-operation-tech", UserRole.TECNICO)
    operation_id, _ = _notify(recipients=[technician, admin])
    with SessionLocal() as session:
        assert session.scalar(select(NotificationOperation.id).where(
            NotificationOperation.idempotency_key == "panel:appointment:17"
        )) == operation_id
        assert session.scalar(select(NotificationOperation.id).where(
            NotificationOperation.idempotency_key == "panel:appointment:17"
        )) is not None
        assert session.query(NotificationOperation).filter_by(idempotency_key="panel:appointment:17").count() == 1
