"""Privacy-bounded technician agenda API (TECH-AGENDA-1/TECH-PRIVACY-1)."""

from datetime import date, time

from app.db import SessionLocal
from app.models import Case, Conversation, Customer
from app.services import scheduling


def _login(client, username: str, password: str) -> None:
    response = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 200


def _appointment(technician_id: int, phone: str, day: date, summary: str) -> int:
    with SessionLocal() as session:
        customer = Customer(
            phone_e164=phone,
            name=f"Customer {phone[-2:]}",
            email="private@example.test",
            address="Sensitive address 42",
            comuna="Providencia",
            consent_status=True,
        )
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        case = Case(
            conversation_id=conversation.id,
            customer_id=customer.id,
            service="calefont",
            summary=summary,
            status="open",
        )
        session.add(case)
        session.flush()
        appointment = scheduling.book(
            session,
            service="calefont",
            customer_id=customer.id,
            case_id=case.id,
            technician_id=technician_id,
            local_date=day,
            local_time=time(10),
            timezone_name="America/Santiago",
            duration_minutes=60,
            actor="oper",
        )
        session.commit()
        return appointment.id


def test_technician_gets_owned_past_today_future_in_chronological_order(client, make_user):
    technician_id = make_user("tech", "tech-pass", role="tecnico")
    other_id = make_user("other-tech", "other-pass", role="tecnico")
    _appointment(technician_id, "+56900000001", date(2026, 1, 2), "past")
    today = _appointment(technician_id, "+56900000002", date(2026, 1, 3), "today")
    _appointment(technician_id, "+56900000003", date(2026, 1, 4), "future")
    _appointment(other_id, "+56900000004", date(2026, 1, 1), "unowned")
    _login(client, "tech", "tech-pass")

    response = client.get("/panel/api/technician/agenda")

    assert response.status_code == 200
    appointments = response.json()["appointments"]
    assert [row["case_summary"] for row in appointments] == ["past", "today", "future"]
    assert appointments[1]["id"] == today


def test_technician_cannot_forge_ownership_or_receive_sensitive_fields(client, make_user):
    technician_id = make_user("tech", "tech-pass", role="tecnico")
    other_id = make_user("other-tech", "other-pass", role="tecnico")
    _appointment(other_id, "+56900000011", date(2026, 1, 1), "do not leak")
    _appointment(technician_id, "+56900000012", date(2026, 1, 2), "allowed")
    _login(client, "tech", "tech-pass")

    response = client.get(
        "/panel/api/technician/agenda",
        params={"technician_id": other_id, "appointment_id": 1},
    )

    assert response.status_code == 200
    appointments = response.json()["appointments"]
    assert [row["case_summary"] for row in appointments] == ["allowed"]
    assert set(appointments[0]) == {
        "id", "service", "local_start", "starts_at", "ends_at", "timezone",
        "customer", "case_summary",
    }
    assert set(appointments[0]["customer"]) == {"name", "address", "comuna", "phone"}
    payload = response.text
    for forbidden in ("private@example.test", "consent_status", "history", "sync", "status", "notes"):
        assert forbidden not in payload


def test_technician_agenda_requires_authenticated_session(client):
    response = client.get("/panel/api/technician/agenda")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}
