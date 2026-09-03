from app.db import SessionLocal
from app.models import AuditLog, Case, Conversation, Customer


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
