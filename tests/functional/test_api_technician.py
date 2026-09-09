from datetime import date, time

from app.db import SessionLocal
from app.models import Case, Conversation, Customer
from app.services import scheduling


def _login(client, name="tech", password="tech-pass"):
    assert client.post("/panel/api/login", json={"username": name, "password": password}).status_code == 200


def _appointment(technician_id, phone, day, summary):
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone, name=f"Customer {phone[-2:]}", email="private@example.test", address="Sensitive address 42", comuna="Providencia", consent_status=True)
        session.add(customer); session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation); session.flush()
        case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont", summary=summary, status="open")
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
    assert set(row) == {"id", "service", "local_start", "starts_at", "ends_at", "timezone", "customer", "case_summary"}
    assert set(row["customer"]) == {"name", "address", "comuna", "phone"}
    assert all(value not in response.text for value in ("private@example.test", "consent_status", "history", "sync", "status", "notes"))


def test_technician_agenda_requires_authenticated_session(client):
    response = client.get("/panel/api/technician/agenda")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}
