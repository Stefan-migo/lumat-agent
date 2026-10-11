from datetime import datetime, timezone

import pytest

from app.db import SessionLocal
from app.models import (
    Appointment,
    AppointmentCalendarSync,
    AppointmentHistory,
    AppointmentStatus,
    AuditLog,
    Case,
    Conversation,
    Customer,
    TechnicianAvailability,
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


def test_operator_can_read_replace_and_validate_technician_schedule(client, make_user):
    technician_id = make_user("schedule-tech", "schedule-pass", role="tecnico")
    make_user("schedule-oper", "schedule-oper-pass", role="operador")
    assert client.post("/panel/api/login", json={
        "username": "schedule-oper", "password": "schedule-oper-pass"
    }).status_code == 200

    url = f"/panel/api/technicians/{technician_id}/schedule"
    assert client.get(url).json() == {"technician_id": technician_id, "schedule": []}
    response = client.put(url, json={"schedule": [
        {"weekday": 2, "opens_at": "09:00", "closes_at": "17:00"},
    ]})
    assert response.status_code == 200
    assert response.json() == {"technician_id": technician_id, "schedule": [
        {"weekday": 2, "opens_at": "09:00:00", "closes_at": "17:00:00"},
    ]}
    assert client.get(url).json() == response.json()

    invalid = client.put(url, json={"schedule": [
        {"weekday": 8, "opens_at": "09:00", "closes_at": "17:00"},
    ]})
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "invalid_schedule"


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
    customer = Customer(phone_e164="+56911111111", name="Ana Customer", address="Calle Uno 123", comuna="Providencia")
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
    assert rows[1]["customer_address"] == "Calle Uno 123"
    assert rows[1]["customer_comuna"] == "Providencia"
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


def _appointment_detail_rows(session, *, with_conversation=True, summary="Conversation summary"):
    technician = User(username="detail-tech", password_hash="unused")
    customer = Customer(phone_e164="+56933333333", name="Detail Customer", address="Pasaje Dos 45", comuna="Ñuñoa")
    session.add_all([technician, customer])
    session.flush()
    conversation = None
    if with_conversation:
        conversation = Conversation(
            customer_id=customer.id, wa_phone=customer.phone_e164, summary=summary
        )
        session.add(conversation)
        session.flush()
    case = Case(
        customer_id=customer.id,
        conversation_id=conversation.id if conversation else None,
        service="calefont",
    )
    session.add(case)
    session.flush()
    appointment = Appointment(
        service="calefont", customer_id=customer.id, case_id=case.id,
        technician_id=technician.id,
        local_start=datetime(2026, 7, 15, 10), timezone="America/Santiago",
        starts_at=datetime(2026, 7, 15, 14, tzinfo=timezone.utc),
        ends_at=datetime(2026, 7, 15, 15, tzinfo=timezone.utc), duration_minutes=60,
    )
    session.add(appointment)
    session.commit()
    return appointment.id, customer.id, customer.name, case.id, case.conversation_id


def _get_appointment_detail(client, make_user, appointment_setup):
    make_user("detail-oper", "detail-pass", role="operador")
    with SessionLocal() as session:
        appointment_id, *expected = appointment_setup(session)
    assert client.post(
        "/panel/api/login", json={"username": "detail-oper", "password": "detail-pass"}
    ).status_code == 200
    return client.get(f"/panel/api/appointments/{appointment_id}"), expected


def test_appointment_detail_embeds_conversation_summary_and_related_records(client, make_user):
    response, expected = _get_appointment_detail(
        client, make_user, lambda session: _appointment_detail_rows(session)
    )

    assert response.status_code == 200
    payload = response.json()
    customer_id, customer_name, case_id, conversation_id = expected
    assert payload["conversation_summary"] == "Conversation summary"
    assert payload["customer"] == {"id": customer_id, "name": customer_name, "address": "Pasaje Dos 45", "comuna": "Ñuñoa"}
    assert payload["case"] == {"id": case_id, "conversation_id": conversation_id}
    assert conversation_id is not None
    assert set(payload["appointment"]) == {
        "id", "service", "customer_id", "case_id", "technician_id", "local_start",
        "timezone", "starts_at", "ends_at", "duration_minutes", "status", "history",
    }


def test_appointment_detail_manual_case_has_no_conversation_summary(client, make_user):
    response, expected = _get_appointment_detail(
        client, make_user,
        lambda session: _appointment_detail_rows(session, with_conversation=False),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_summary"] is None
    assert payload["case"]["conversation_id"] is None
    assert payload["customer"]["id"] == expected[0]


def test_appointment_detail_conversation_without_summary_is_successful(client, make_user):
    response, expected = _get_appointment_detail(
        client, make_user,
        lambda session: _appointment_detail_rows(session, summary=None),
    )

    assert response.status_code == 200
    assert response.json()["conversation_summary"] is None
    assert response.json()["case"]["conversation_id"] == expected[3]


def test_appointment_detail_unknown_id_is_not_found(client, make_user):
    make_user("detail-oper", "detail-pass", role="operador")
    assert client.post(
        "/panel/api/login", json={"username": "detail-oper", "password": "detail-pass"}
    ).status_code == 200

    response = client.get("/panel/api/appointments/999999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "appointment not found"


@pytest.mark.parametrize("outcome", ["completed", "no_show"])
def test_operator_can_close_booked_appointment_and_unknown_outcome_is_rejected(client, make_user, outcome):
    make_user("close-oper", "close-pass", role="operador")
    with SessionLocal() as session:
        appointment_id, *_ = _appointment_detail_rows(session)
    assert client.post("/panel/api/login", json={"username": "close-oper", "password": "close-pass"}).status_code == 200

    response = client.post(f"/panel/api/appointments/{appointment_id}/close", json={"outcome": outcome, "reason": "finished"})
    assert response.status_code == 200
    assert response.json()["appointment"]["status"] == outcome
    assert client.post(f"/panel/api/appointments/{appointment_id}/close", json={"outcome": "unknown"}).status_code == 422
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        history = session.query(AppointmentHistory).filter_by(appointment_id=appointment_id).order_by(AppointmentHistory.id).all()
        assert [entry.action for entry in history] == [outcome]
        assert session.query(AuditLog).filter_by(action=f"appointment.{outcome}", entity_id=str(appointment_id)).count() == 1


def test_close_rejects_non_booked_and_unknown_appointments(client, make_user):
    make_user("close-oper", "close-pass", role="operador")
    with SessionLocal() as session:
        appointment_id, *_ = _appointment_detail_rows(session)
        session.query(Appointment).filter_by(id=appointment_id).update({"status": AppointmentStatus.CANCELLED})
        session.commit()
    assert client.post("/panel/api/login", json={"username": "close-oper", "password": "close-pass"}).status_code == 200

    refused = client.post(f"/panel/api/appointments/{appointment_id}/close", json={"outcome": "no_show"})
    assert refused.status_code == 409
    assert refused.json()["detail"] == {"code": "invalid_lifecycle", "message": "only booked appointments can be closed"}
    missing = client.post("/panel/api/appointments/999999999/close", json={"outcome": "completed"})
    assert missing.status_code == 404
    assert missing.json()["detail"] == "appointment not found"


def test_operator_can_reschedule_appointment_through_patch(client, make_user):
    make_user("reschedule-oper", "reschedule-pass", role="operador")
    with SessionLocal() as session:
        appointment_id, *_ = _appointment_detail_rows(session)
        technician_id = session.get(Appointment, appointment_id).technician_id
    assert client.post("/panel/api/login", json={"username": "reschedule-oper", "password": "reschedule-pass"}).status_code == 200

    response = client.patch(f"/panel/api/appointments/{appointment_id}", json={
        "local_date": "2035-12-15", "local_time": "10:30", "timezone": "America/Santiago",
        "duration_minutes": 90, "technician_id": technician_id,
    })

    assert response.status_code == 200
    assert response.json()["appointment"]["local_start"].startswith("2035-12-15T10:30:00")


def _reschedule_setup(client, make_user):
    make_user("reschedule-oper", "reschedule-pass", role="operador")
    with SessionLocal() as session:
        appointment_id, *_ = _appointment_detail_rows(session)
        technician_id = session.get(Appointment, appointment_id).technician_id
    assert client.post("/panel/api/login", json={"username": "reschedule-oper", "password": "reschedule-pass"}).status_code == 200
    return appointment_id, technician_id


def _reschedule_body(technician_id, **overrides):
    body = {"local_date": "2026-07-16", "local_time": "11:00", "timezone": "America/Santiago", "duration_minutes": 60, "technician_id": technician_id}
    body.update(overrides)
    return body


def test_reschedule_rejects_terminal_and_unknown_appointments(client, make_user):
    appointment_id, technician_id = _reschedule_setup(client, make_user)
    with SessionLocal() as session:
        session.query(Appointment).filter_by(id=appointment_id).update({"status": AppointmentStatus.CANCELLED})
        session.commit()

    refused = client.patch(f"/panel/api/appointments/{appointment_id}", json=_reschedule_body(technician_id))
    assert refused.status_code == 409
    assert refused.json()["detail"] == {"code": "invalid_lifecycle", "message": "only booked appointments can be rescheduled"}

    missing = client.patch("/panel/api/appointments/999999999", json=_reschedule_body(technician_id))
    assert missing.status_code == 404
    assert missing.json()["detail"] == "appointment not found"


def test_reschedule_maps_slot_errors_to_actionable_codes(client, make_user):
    appointment_id, technician_id = _reschedule_setup(client, make_user)
    url = f"/panel/api/appointments/{appointment_id}"

    for moment in ({"local_date": "2026-09-06", "local_time": "00:30"}, {"local_date": "2026-04-04", "local_time": "23:30"}):
        response = client.patch(url, json=_reschedule_body(technician_id, **moment))
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "invalid_local_time"

    unknown_zone = client.patch(url, json=_reschedule_body(technician_id, timezone="not/a-zone"))
    assert unknown_zone.status_code == 400
    assert unknown_zone.json()["detail"]["code"] == "invalid_timezone"

    assert client.patch(url, json=_reschedule_body(technician_id, duration_minutes=0)).status_code == 422


def test_reschedule_reports_conflict_and_unavailable_slots(client, make_user):
    appointment_id, technician_id = _reschedule_setup(client, make_user)
    url = f"/panel/api/appointments/{appointment_id}"
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56900000009", name="Otra Cliente")
        session.add(customer)
        session.flush()
        case = Case(customer_id=customer.id, service="calefont")
        session.add(case)
        session.flush()
        session.add(Appointment(
            service="calefont", customer_id=customer.id, case_id=case.id, technician_id=technician_id,
            local_start=datetime(2026, 7, 16, 10, 30), timezone="America/Santiago",
            starts_at=datetime(2026, 7, 16, 14, 30, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 16, 15, 30, tzinfo=timezone.utc), duration_minutes=60,
        ))
        session.commit()

    conflict = client.patch(url, json=_reschedule_body(technician_id))
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "appointment_conflict"

    with SessionLocal() as session:
        session.add(TechnicianAvailability(
            technician_id=technician_id,
            starts_at=datetime(2026, 7, 20, 8, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 12, tzinfo=timezone.utc),
        ))
        session.commit()

    unavailable = client.patch(url, json=_reschedule_body(technician_id, local_date="2026-07-18", local_time="10:00"))
    assert unavailable.status_code == 409
    assert unavailable.json()["detail"]["code"] == "technician_unavailable"
