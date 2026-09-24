from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import (
    Appointment,
    AppointmentCalendarSync,
    AppointmentStatus,
    AuditLog,
    Case,
    Conversation,
    Customer,
    User,
)


def test_appointment_mutations_require_authentication(client):
    response = client.post("/panel/api/appointments", json={})

    assert response.status_code == 401
    with SessionLocal() as session:
        assert session.query(AuditLog).count() == 0


def test_operator_can_book_and_conflict_is_actionable(client, make_user):
    operator_id = make_user("oper", "oper-pass", role="operador")
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56912345678")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont")
        session.add(case)
        session.commit()
        customer_id, case_id = customer.id, case.id

    login = client.post("/panel/api/login", json={"username": "oper", "password": "oper-pass"})
    assert login.status_code == 200
    response = client.post(
        "/panel/api/appointments",
        json={"service": "calefont", "customer_id": customer_id, "case_id": case_id,
              "technician_id": operator_id, "local_date": "2026-07-15", "local_time": "10:00",
              "timezone": "America/Santiago", "duration_minutes": 60},
    )

    assert response.status_code == 200
    conflict = client.post(
        "/panel/api/appointments",
        json={"service": "calefont", "customer_id": customer_id, "case_id": case_id,
              "technician_id": operator_id, "local_date": "2026-07-15", "local_time": "10:00",
              "timezone": "America/Santiago", "duration_minutes": 60},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "appointment_conflict"


def test_operator_cannot_book_with_an_invalid_timezone(client, make_user):
    operator_id = make_user("oper", "oper-pass", role="operador")
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56912345679")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont")
        session.add(case)
        session.commit()
        customer_id, case_id = customer.id, case.id

    assert client.post("/panel/api/login", json={"username": "oper", "password": "oper-pass"}).status_code == 200
    response = client.post(
        "/panel/api/appointments",
        json={"service": "calefont", "customer_id": customer_id, "case_id": case_id,
              "technician_id": operator_id, "local_date": "2026-07-15", "local_time": "10:00",
              "timezone": "Not/AZone", "duration_minutes": 60},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_timezone"


def _agenda_rows(session):
    technician = User(username="tech", password_hash="unused")
    customer = Customer(phone_e164="+56911111111", name="Ana Customer")
    session.add_all([technician, customer])
    session.flush()
    conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
    session.add(conversation)
    session.flush()
    case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont")
    session.add(case)
    session.flush()
    appointments = [
        Appointment(
            service="late", customer_id=customer.id, case_id=case.id, technician_id=technician.id,
            local_start=datetime(2026, 7, 15, 10), timezone="America/Santiago",
            starts_at=datetime(2026, 7, 15, 14, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 15, 15, tzinfo=timezone.utc), duration_minutes=60,
        ),
        Appointment(
            service="early", customer_id=customer.id, case_id=case.id, technician_id=technician.id,
            local_start=datetime(2026, 7, 15, 9), timezone="America/Santiago",
            starts_at=datetime(2026, 7, 15, 13, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 15, 14, tzinfo=timezone.utc), duration_minutes=60,
            status=AppointmentStatus.CANCELLED,
        ),
        Appointment(
            service="failed", customer_id=customer.id, case_id=case.id, technician_id=technician.id,
            local_start=datetime(2026, 7, 16, 9), timezone="America/Santiago",
            starts_at=datetime(2026, 7, 16, 13, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 16, 14, tzinfo=timezone.utc), duration_minutes=60,
            status=AppointmentStatus.COMPLETED,
        ),
    ]
    session.add_all(appointments)
    session.flush()
    session.add(AppointmentCalendarSync(
        appointment_id=appointments[0].id, provider="ics", uid="uid-1", idempotency_key="key-1", status="synced",
        timezone="America/Santiago",
    ))
    session.add(AppointmentCalendarSync(
        appointment_id=appointments[2].id, provider="ics", uid="uid-2", idempotency_key="key-2", status="failed",
        timezone="America/Santiago", error="provider unavailable",
    ))
    session.commit()


def test_appointments_range_requires_authentication_and_does_not_mutate(client):
    response = client.get("/panel/api/appointments?from=2026-07-15&to=2026-07-15&timezone=America/Santiago")

    assert response.status_code == 401
    with SessionLocal() as session:
        assert session.query(AuditLog).count() == 0


def test_appointments_range_joins_orders_and_keeps_lifecycle_and_sync_independent(client, make_user):
    make_user("oper", "oper-pass")
    with SessionLocal() as session:
        _agenda_rows(session)

    assert client.post("/panel/api/login", json={"username": "oper", "password": "oper-pass"}).status_code == 200
    response = client.get("/panel/api/appointments?from=2026-07-15&to=2026-07-16&timezone=America/Santiago")

    assert response.status_code == 200
    rows = response.json()["appointments"]
    assert [row["service"] for row in rows] == ["early", "late", "failed"]
    assert rows[0]["status"] == "cancelled"
    assert rows[0]["sync"] == {"status": "pending", "error": None, "retry": True}
    assert rows[1]["customer_name"] == "Ana Customer"
    assert rows[1]["technician_name"] == "tech"
    assert rows[1]["starts_at"] == "2026-07-15T14:00:00+00:00"
    assert rows[1]["local_start"] == "2026-07-15T10:00:00-04:00"
    assert rows[2]["sync"] == {"status": "failed", "error": "provider unavailable", "retry": True}


def test_appointments_range_rejects_timezone_and_bounds_without_mutation(client, make_user):
    make_user("oper", "oper-pass")
    assert client.post("/panel/api/login", json={"username": "oper", "password": "oper-pass"}).status_code == 200
    with SessionLocal() as session:
        audit_count = session.query(AuditLog).count()

    for query, code in (
        ("from=2026-07-15&to=2026-07-15&timezone=Not/AZone", "invalid_timezone"),
        ("from=2026-07-16&to=2026-07-15&timezone=UTC", "invalid_range"),
        ("from=2026-07-01&to=2026-08-01&timezone=UTC", "invalid_range"),
    ):
        response = client.get(f"/panel/api/appointments?{query}")
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == code

    with SessionLocal() as session:
        assert session.query(AuditLog).count() == audit_count


def test_appointments_range_uses_dst_aware_local_bounds(client, make_user):
    make_user("oper", "oper-pass")
    with SessionLocal() as session:
        technician = User(username="dst-tech", password_hash="unused")
        customer = Customer(phone_e164="+56922222222", name="DST Customer")
        session.add_all([technician, customer])
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        case = Case(conversation_id=conversation.id, customer_id=customer.id)
        session.add(case)
        session.flush()
        session.add(Appointment(
            service="dst", customer_id=customer.id, case_id=case.id, technician_id=technician.id,
            local_start=datetime(2026, 3, 8, 3, 30), timezone="America/New_York",
            starts_at=datetime(2026, 3, 8, 7, 30, tzinfo=timezone.utc),
            ends_at=datetime(2026, 3, 8, 8, 30, tzinfo=timezone.utc), duration_minutes=60,
        ))
        session.commit()

    assert client.post("/panel/api/login", json={"username": "oper", "password": "oper-pass"}).status_code == 200
    response = client.get("/panel/api/appointments?from=2026-03-08&to=2026-03-08&timezone=America/New_York")

    assert response.status_code == 200
    row = response.json()["appointments"][0]
    assert row["local_start"] == "2026-03-08T03:30:00-04:00"
    assert row["starts_at"] == "2026-03-08T07:30:00+00:00"
