from datetime import date, time

from app.db import SessionLocal
from app.models import Appointment, Case, Conversation, Customer
from app.services import scheduling


def _login(client, name="tech", password="tech-pass"):
    assert client.post("/panel/api/login", json={"username": name, "password": password}).status_code == 200


def _appointment(technician_id, phone, day, summary, *, emergency=False, priority=None):
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone, name=f"Customer {phone[-2:]}", email="private@example.test", address="Sensitive address 42", comuna="Providencia", consent_status=True)
        session.add(customer); session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation); session.flush()
        case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont", summary=summary, status="open", emergency=emergency, priority=priority)
        session.add(case); session.flush()
        appointment = scheduling.book(session, service="calefont", customer_id=customer.id, case_id=case.id, technician_id=technician_id, local_date=day, local_time=time(10), timezone_name="America/Santiago", duration_minutes=60, actor="oper")
        session.commit()
        return appointment.id


def test_technician_gets_owned_past_today_future_in_chronological_order(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    other = make_user("other-tech", "other-pass", role="tecnico")
    for index, summary in enumerate(("past", "today", "future"), 2):
        _appointment(technician, f"+5690000000{index}", date(2026, 1, index), summary)
    _appointment(other, "+56900000005", date(2026, 1, 1), "unowned")
    _login(client)
    response = client.get("/panel/api/technician/agenda")
    assert response.status_code == 200
    assert [row["case_summary"] for row in response.json()["appointments"]] == ["past", "today", "future"]


def test_technician_cannot_forge_ownership_or_receive_sensitive_fields(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    other = make_user("other-tech", "other-pass", role="tecnico")
    _appointment(other, "+56900000011", date(2026, 1, 1), "do not leak")
    _appointment(technician, "+56900000012", date(2026, 1, 2), "allowed")
    _login(client)
    response = client.get("/panel/api/technician/agenda", params={"technician_id": other, "appointment_id": 1})
    row = response.json()["appointments"][0]
    assert [row["case_summary"]] == ["allowed"]
    assert set(row) == {"id", "service", "local_start", "starts_at", "ends_at", "timezone", "status", "emergency", "priority", "customer", "case_summary"}
    assert set(row["customer"]) == {"name", "address", "comuna"}
    assert row["status"] in {"booked", "cancelled", "completed", "no_show"}
    assert row["emergency"] is False
    assert row["priority"] is None
    assert all(value not in response.text for value in ("private@example.test", "consent_status", "history", "sync", "notes", "+56900000012"))


def test_technician_receives_visit_safety_fields(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000014", date(2026, 1, 4), "emergency visit", emergency=True, priority="alta")
    _login(client)

    response = client.get("/panel/api/technician/agenda")

    assert response.status_code == 200
    row = next(item for item in response.json()["appointments"] if item["id"] == appointment_id)
    assert row["emergency"] is True
    assert row["priority"] == "alta"


def test_cancelled_appointment_stays_visible_and_marked(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000013", date(2026, 1, 3), "cancelled visit")
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        scheduling.cancel(session, appointment, actor="oper", reason="dispatch cancelled")
        session.commit()
    _login(client)
    response = client.get("/panel/api/technician/agenda")
    assert response.status_code == 200
    row = next(item for item in response.json()["appointments"] if item["id"] == appointment_id)
    assert row["status"] == "cancelled"


def test_technician_agenda_requires_authenticated_session(client):
    response = client.get("/panel/api/technician/agenda")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_technician_reads_owned_appointment_detail_allow_list(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000021", date(2026, 1, 5), "detalle propio")
    _login(client)

    response = client.get(f"/panel/api/technician/appointments/{appointment_id}")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"appointment", "customer", "case"}
    assert set(body["appointment"]) == {
        "id", "service", "customer_id", "case_id", "technician_id", "local_start",
        "timezone", "starts_at", "ends_at", "duration_minutes", "status",
    }
    assert set(body["customer"]) == {"id", "name", "address", "comuna"}
    assert set(body["case"]) == {"id", "conversation_id"}
    assert body["appointment"]["id"] == appointment_id
    assert body["appointment"]["service"] == "calefont"
    assert all(
        value not in response.text
        for value in ("private@example.test", "consent_status", "history", "sync", "notes", "phone", "conversation_summary", "+56900000021")
    )


def test_technician_detail_hides_foreign_and_unknown_appointments_as_not_found(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    other = make_user("other-tech", "other-pass", role="tecnico")
    foreign_id = _appointment(other, "+56900000031", date(2026, 1, 6), "ajena")
    _login(client)

    assert client.get(f"/panel/api/technician/appointments/{foreign_id}").status_code == 404
    assert client.get("/panel/api/technician/appointments/999999").status_code == 404


def test_technician_detail_rejects_non_technician_role(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000041", date(2026, 1, 7), "solo tecnico")
    _login(client, "oper", "oper-pass")

    assert client.get(f"/panel/api/technician/appointments/{appointment_id}").status_code == 403


def test_technician_detail_requires_authenticated_session(client):
    response = client.get("/panel/api/technician/appointments/1")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_technician_cannot_reach_the_operator_detail_endpoint(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000051", date(2026, 1, 8), "propia")
    _login(client)

    assert client.get(f"/panel/api/appointments/{appointment_id}").status_code == 403
