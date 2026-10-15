"""Independent verifier probes for odd/tasks/automation-templates.md (S1-S7).

Written by the read-only verifier, NOT by the feature author. Each probe is
self-contained and exercises the public service surface.
"""
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    Appointment, AppointmentStatus, AuditLog, Case, Conversation, Customer,
    DomainEvent, NotificationAttempt, NotificationOperation,
    NotificationTemplateVersion, User, UserRole,
)
from app.services import notifications, notify, recipes, scheduling
from app.services.automation import evaluate_event, create_rule
from app.services.automation_installations import install
from app.services.events import publish_event
from app.services.settings import get_setting
from app.services.time_triggers import evaluate_time_triggers
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def _clean(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE notification_attempts, notification_operations, notification_template_versions, audit_log, "
            "automation_executions, automation_rules, automation_installations, domain_events, "
            "messages, conversations, cases, appointments, appointment_history, customers, users "
            "RESTART IDENTITY CASCADE"
        )
    yield


def _appt(session, *, starts_at, created_at=None, status=AppointmentStatus.BOOKED, email=None):
    s = uuid4().hex[:10]
    tech = User(username=f"vp-tech-{s}", password_hash="x", role=UserRole.TECNICO)
    cust = Customer(phone_e164=f"+5699{s[:7]}", name="Vera", email=email)
    session.add_all([tech, cust])
    session.flush()
    case = Case(customer_id=cust.id, status="open")
    session.add(case)
    session.flush()
    a = Appointment(
        service="V", customer_id=cust.id, case_id=case.id, technician_id=tech.id,
        local_start=starts_at.astimezone(timezone.utc).replace(tzinfo=None), timezone="UTC",
        starts_at=starts_at, ends_at=starts_at + timedelta(hours=1), duration_minutes=60,
        status=status,
    )
    if created_at is not None:
        a.created_at = created_at
    session.add(a)
    session.flush()
    return a, cust


def _install(session, rid, channel="whatsapp", enabled=True):
    return install(session, rid, {"channel": channel}, actor="admin", enabled=enabled)


def _tpl(session, event, approved=True):
    session.add(NotificationTemplateVersion(
        event=event, channel="whatsapp", locale="es", version=1, content="x",
        required_variables=[], approved=approved, smtp_allowed=True, created_by="verifier",
    ))
    session.flush()


def _reminder_ev(session, a):
    return session.scalar(select(DomainEvent).where(
        DomainEvent.event_type == "appointment.reminder_due",
        DomainEvent.entity_id == str(a.id)))


def _appt_op(session, a):
    return session.scalar(select(NotificationOperation).where(
        NotificationOperation.source_entity == "appointment",
        NotificationOperation.source_id == str(a.id)))


# ---------------- S1 ----------------
def test_s1_book_origin_is_assistant_only_for_assistant_actor(migrated_db):
    with SessionLocal() as session:
        for actor, expected in [("assistant", "assistant"), ("admin", "panel"), ("oper", "panel")]:
            s = uuid4().hex[:8]
            tech = User(username=f"b-{s}", password_hash="x")
            cust = Customer(phone_e164=f"+5698{s[:7]}", name="X")
            session.add_all([tech, cust])
            session.flush()
            conv = Conversation(customer_id=cust.id, wa_phone=cust.phone_e164)
            session.add(conv)
            session.flush()
            case = Case(conversation_id=conv.id, customer_id=cust.id, service="c")
            session.add(case)
            session.flush()
            ap = scheduling.book(
                session, service="c", customer_id=cust.id, case_id=case.id, technician_id=tech.id,
                local_date=date(2026, 8, 20), local_time=time(10),
                timezone_name="America/Santiago", duration_minutes=60, actor=actor)
            session.flush()
            ev = session.scalar(select(DomainEvent).where(
                DomainEvent.event_type == "appointment.booked",
                DomainEvent.entity_id == str(ap.id)))
            assert ev.payload["origin"] == expected, (actor, ev.payload)
        session.commit()


def test_s1_confirmation_only_panel_origin(migrated_db):
    with SessionLocal() as session:
        _install(session, "appointment_confirmation")
        cases = [("assistant", 0), ("panel", 1), ("", 0)]
        for origin, expect in cases:
            ev = publish_event(
                session, event_type="appointment.booked", entity_type="appointment",
                entity_id=f"e-{origin or 'empty'}",
                payload={"customer_id": 1, "recipient": f"+5690000{len(origin)}", "origin": origin},
                dedupe_key=f"d-{origin or 'empty'}")
            session.flush()
            assert len(evaluate_event(session, ev)) == expect, origin
        ev = publish_event(
            session, event_type="appointment.booked", entity_type="appointment", entity_id="e-missing",
            payload={"customer_id": 1, "recipient": "+56900009"}, dedupe_key="d-missing")
        session.flush()
        assert evaluate_event(session, ev) == []
        ops = session.scalars(select(NotificationOperation.recipient)).all()
        assert ops == ["+56900005"], ops
        session.commit()


def test_s1_recipe_without_conditions_is_not_origin_filtered(migrated_db):
    with SessionLocal() as session:
        assert recipes.get_recipe("appointment_cancellation").compile_rule_fields(
            {"channel": "whatsapp"})["conditions"] == {}
        _install(session, "appointment_cancellation")
        ev = publish_event(
            session, event_type="appointment.cancelled", entity_type="appointment", entity_id="c1",
            payload={"recipient": "+56900001", "origin": "assistant"}, dedupe_key="dc1")
        session.flush()
        assert evaluate_event(session, ev) != []
        session.commit()


# ---------------- S2 ----------------
def test_s2_every_template_event_has_a_renderer():
    for rid, r in recipes.RECIPES.items():
        if r.template_event is not None:
            assert r.template_event in notifications._TEMPLATE_RENDERERS, rid


def test_s2_whatsapp_operation_routes_to_renderer_not_send_text(migrated_db, monkeypatch):
    calls = []
    with SessionLocal() as session:
        _install(session, "appointment_followup")
        a, _ = _appt(session, starts_at=datetime(2030, 1, 3, 14, 35, tzinfo=timezone.utc),
                     created_at=datetime(2030, 1, 1, tzinfo=timezone.utc))
        scheduling.close(session, a, outcome=AppointmentStatus.COMPLETED, actor="test")
        _tpl(session, "appointment.followup.completed")
        ev = session.scalar(select(DomainEvent).where(DomainEvent.event_type == "appointment.completed"))
        assert evaluate_event(session, ev) != []
        op = _appt_op(session, a)
        monkeypatch.setattr(notify, "send_template",
                            lambda phone, params, *, template_name=None: calls.append("tpl") or "EXT-1")
        monkeypatch.setattr(notifications, "send_text",
                            lambda *a, **k: (_ for _ in ()).throw(AssertionError("send_text used")))
        monkeypatch.setattr(notifications, "send_whatsapp",
                            lambda *a, **k: (_ for _ in ()).throw(AssertionError("send_whatsapp used")))
        assert notifications.process_operation(session, op.id, now=op.next_attempt_at) is True
        assert calls == ["tpl"]
        att = session.scalar(select(NotificationAttempt).order_by(NotificationAttempt.id.desc()))
        assert att.external_id == "EXT-1"
        session.commit()


def test_s2_missing_and_unapproved_template_raise_policy_error_no_freeform(migrated_db, monkeypatch):
    for approved in (None, False):
        with SessionLocal() as session:
            _install(session, "appointment_followup")
            a, _ = _appt(session, starts_at=datetime(2030, 1, 3, 14, 35, tzinfo=timezone.utc),
                         created_at=datetime(2030, 1, 1, tzinfo=timezone.utc))
            scheduling.close(session, a, outcome=AppointmentStatus.COMPLETED, actor="test")
            if approved is not None:
                _tpl(session, "appointment.followup.completed", approved=approved)
            ev = session.scalar(select(DomainEvent).where(DomainEvent.event_type == "appointment.completed"))
            evaluate_event(session, ev)
            op = _appt_op(session, a)
            monkeypatch.setattr(notifications, "send_whatsapp",
                                lambda *a, **k: (_ for _ in ()).throw(AssertionError("free-form used")))
            assert notifications.process_operation(session, op.id, now=op.next_attempt_at) is False
            assert op.error and ("not published" in op.error or "approved" in op.error), (approved, op.error)
            assert op.status in {"retryable", "permanently_failed"}
            session.rollback()


def test_s2_recipe_without_template_event_uses_generic_path(migrated_db, monkeypatch):
    calls = []
    with SessionLocal() as session:
        _install(session, "appointment_cancellation")
        ev = publish_event(session, event_type="appointment.cancelled", entity_type="appointment",
                           entity_id="g1", payload={"recipient": "+56900001"}, dedupe_key="dg1")
        session.flush()
        assert evaluate_event(session, ev) != []
        op = session.scalar(select(NotificationOperation))
        monkeypatch.setattr(notifications, "send_whatsapp", lambda r, c: calls.append(r) or "WAMID")
        assert notifications.process_operation(session, op.id) is True
        assert calls == ["+56900001"]
        session.commit()


def test_s2_manual_rule_without_installation_uses_generic_path(migrated_db, monkeypatch):
    calls = []
    with SessionLocal() as session:
        create_rule(session, {"name": "manual", "event_type": "appointment.cancelled",
                              "channel": "whatsapp", "cooldown_seconds": 0, "conditions": {}}, actor="admin")
        ev = publish_event(session, event_type="appointment.cancelled", entity_type="appointment",
                           entity_id="m1", payload={"recipient": "+56900002", "content": "manual"}, dedupe_key="dm1")
        session.flush()
        assert evaluate_event(session, ev) != []
        op = session.scalar(select(NotificationOperation))
        monkeypatch.setattr(notifications, "send_whatsapp", lambda r, c: calls.append(r) or "W2")
        assert notifications.process_operation(session, op.id) is True
        assert calls == ["+56900002"]
        session.commit()


# ---------------- S3 ----------------
def test_s3_reminder_recipe_fields():
    r = recipes.get_recipe("appointment_reminder")
    assert r is not None
    assert r.event_type == "appointment.reminder_due"
    assert r.template_event == "appointment.reminder.24h"
    assert r.recipient_target == "customer"


@pytest.mark.parametrize("starts_delta,notice_offset,expected", [
    (timedelta(hours=24), -timedelta(days=2), True),
    (timedelta(hours=24, minutes=1), -timedelta(days=2), False),
    (timedelta(0), -timedelta(days=2), False),
    (timedelta(hours=20), -timedelta(hours=24), True),
    (timedelta(hours=20), -timedelta(hours=24) + timedelta(minutes=1), False),
])
def test_s3_reminder_time_and_notice_boundaries(migrated_db, starts_delta, notice_offset, expected):
    now = datetime(2030, 1, 10, 12, 0, tzinfo=timezone.utc)
    starts = now + starts_delta
    with SessionLocal() as session:
        _install(session, "appointment_reminder")
        a, _ = _appt(session, starts_at=starts, created_at=starts + notice_offset)
        evaluate_time_triggers(session, now)
        assert (_reminder_ev(session, a) is not None) is expected
        session.rollback()


def test_s3_cancelled_excluded_and_no_installation_noop(migrated_db):
    now = datetime(2030, 1, 10, 12, 0, tzinfo=timezone.utc)
    with SessionLocal() as session:
        a0, _ = _appt(session, starts_at=now + timedelta(hours=20), created_at=now - timedelta(days=2))
        assert evaluate_time_triggers(session, now) == 0
        assert _reminder_ev(session, a0) is None
        _install(session, "appointment_reminder")
        a, _ = _appt(session, starts_at=now + timedelta(hours=20),
                     created_at=now - timedelta(days=2), status=AppointmentStatus.CANCELLED)
        evaluate_time_triggers(session, now)
        assert _reminder_ev(session, a) is None
        session.rollback()


def test_s3_disabled_installation_is_noop(migrated_db):
    now = datetime(2030, 1, 10, 12, 0, tzinfo=timezone.utc)
    with SessionLocal() as session:
        _install(session, "appointment_reminder", enabled=False)
        a, _ = _appt(session, starts_at=now + timedelta(hours=20), created_at=now - timedelta(days=2))
        evaluate_time_triggers(session, now)
        assert _reminder_ev(session, a) is None
        session.rollback()


# ---------------- S4 ----------------
def test_s4_followup_declares_delay_and_engine_honors_it(migrated_db):
    for rid in ("appointment_followup", "appointment_followup_no_show"):
        assert recipes.get_recipe(rid).delay_seconds == 86400
    with SessionLocal() as session:
        _install(session, "appointment_followup")
        before = datetime.now(timezone.utc)
        ev = publish_event(session, event_type="appointment.completed", entity_type="appointment",
                           entity_id="f1", payload={"recipient": None, "outcome": "completed"},
                           dedupe_key="df1")
        session.flush()
        assert evaluate_event(session, ev) != []
        op = session.scalar(select(NotificationOperation))
        assert abs((op.next_attempt_at - before) - timedelta(seconds=86400)) < timedelta(seconds=60)
        session.commit()


def test_s4_delayless_recipe_leaves_next_attempt_at_untouched(migrated_db):
    with SessionLocal() as session:
        _install(session, "appointment_confirmation")
        before = datetime.now(timezone.utc)
        ev = publish_event(session, event_type="appointment.booked", entity_type="appointment",
                           entity_id="z1", payload={"recipient": "+56900003", "origin": "panel"},
                           dedupe_key="dz1")
        session.flush()
        assert evaluate_event(session, ev) != []
        op = session.scalar(select(NotificationOperation))
        assert abs(op.next_attempt_at - before) < timedelta(seconds=60)
        session.commit()


# ---------------- S5 ----------------
def test_s5_reminder_whatsapp_failure_falls_back_to_customer_email(migrated_db, monkeypatch):
    sent = []
    with SessionLocal() as session:
        _install(session, "appointment_reminder")
        starts = datetime(2030, 1, 3, 14, 35, tzinfo=timezone.utc)
        a, c = _appt(session, starts_at=starts, created_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
                     email="cust@example.com")
        _tpl(session, "appointment.reminder.24h")
        monkeypatch.setattr(notify, "send_template",
                            lambda *a, **k: (_ for _ in ()).throw(OSError("Meta down")))
        monkeypatch.setattr(notify, "send_email",
                            lambda s, to, subject, body: sent.append((to, subject, body)))
        evaluate_time_triggers(session, starts - timedelta(hours=23))
        evaluate_event(session, _reminder_ev(session, a))
        op = _appt_op(session, a)
        assert notifications.process_operation(session, op.id, now=op.next_attempt_at) is True
        assert sent and sent[0][0] == "cust@example.com"
        session.flush()
        assert session.scalar(select(AuditLog).where(
            AuditLog.action == "notification.reminder_email_fallback")) is not None
        session.commit()


def test_s5_reminder_without_email_permanently_fails(migrated_db, monkeypatch):
    with SessionLocal() as session:
        _install(session, "appointment_reminder")
        starts = datetime(2030, 1, 3, 14, 35, tzinfo=timezone.utc)
        a, _ = _appt(session, starts_at=starts, created_at=datetime(2030, 1, 1, tzinfo=timezone.utc))
        _tpl(session, "appointment.reminder.24h")
        monkeypatch.setattr(notify, "send_template",
                            lambda *a, **k: (_ for _ in ()).throw(OSError("Meta down")))
        evaluate_time_triggers(session, starts - timedelta(hours=23))
        evaluate_event(session, _reminder_ev(session, a))
        op = _appt_op(session, a)
        assert notifications.process_operation(session, op.id, now=op.next_attempt_at) is False
        assert op.status == "permanently_failed"
        session.flush()
        assert session.scalar(select(AuditLog).where(
            AuditLog.action == "notification.reminder_no_email")) is not None
        session.commit()


def test_s5_followup_failure_falls_back_to_owner_email(migrated_db, monkeypatch):
    emails = []
    with SessionLocal() as session:
        _install(session, "appointment_followup")
        a, _ = _appt(session, starts_at=datetime(2030, 1, 3, 14, 35, tzinfo=timezone.utc),
                     created_at=datetime(2030, 1, 1, tzinfo=timezone.utc))
        scheduling.close(session, a, outcome=AppointmentStatus.COMPLETED, actor="test")
        _tpl(session, "appointment.followup.completed")
        monkeypatch.setattr(notify, "send_template",
                            lambda *a, **k: (_ for _ in ()).throw(OSError("Meta down")))
        monkeypatch.setattr(notify, "send_email",
                            lambda s, to, subject, body: emails.append((to, subject, body)))
        ev = session.scalar(select(DomainEvent).where(DomainEvent.event_type == "appointment.completed"))
        evaluate_event(session, ev)
        op = _appt_op(session, a)
        assert notifications.process_operation(session, op.id, now=op.next_attempt_at) is True
        assert emails and emails[0][0] == get_setting(session, "notify.owner_email")
        assert emails[0][1] == "Seguimiento de visita Lumat"
        session.flush()
        assert session.scalar(select(AuditLog).where(
            AuditLog.action == "notification.followup_email_fallback")) is not None
        session.commit()


# ---------------- S6 (double send) ----------------
def test_s6_reminder_publishes_once_and_no_legacy_key(migrated_db):
    now = datetime(2030, 1, 10, 12, 0, tzinfo=timezone.utc)
    with SessionLocal() as session:
        _install(session, "appointment_reminder")
        a, _ = _appt(session, starts_at=now + timedelta(hours=20), created_at=now - timedelta(days=2))
        evaluate_time_triggers(session, now)
        evaluate_time_triggers(session, now)
        assert session.scalar(select(func.count()).select_from(DomainEvent).where(
            DomainEvent.event_type == "appointment.reminder_due",
            DomainEvent.entity_id == str(a.id))) == 1
        ev = _reminder_ev(session, a)
        evaluate_event(session, ev)
        evaluate_event(session, ev)
        assert session.scalar(select(func.count()).select_from(NotificationOperation).where(
            NotificationOperation.source_id == str(a.id))) == 1
        keys = session.scalars(select(NotificationOperation.idempotency_key)).all()
        assert not any(k.endswith(":reminder:24h") for k in keys), keys
        session.commit()


def test_s6_close_publishes_followup_once(migrated_db):
    with SessionLocal() as session:
        _install(session, "appointment_followup")
        a, _ = _appt(session, starts_at=datetime.now(timezone.utc) + timedelta(days=2))
        scheduling.close(session, a, outcome=AppointmentStatus.COMPLETED, actor="test")
        ev = session.scalar(select(DomainEvent).where(DomainEvent.event_type == "appointment.completed"))
        evaluate_event(session, ev)
        evaluate_event(session, ev)
        assert session.scalar(select(func.count()).select_from(NotificationOperation).where(
            NotificationOperation.source_id == str(a.id))) == 1
        session.commit()
