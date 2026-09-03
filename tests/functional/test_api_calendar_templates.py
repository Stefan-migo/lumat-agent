from app.db import SessionLocal
from app.models import Case, Conversation, Customer


def test_authenticated_calendar_sync_returns_status_and_retry_action(client, make_user):
    technician_id = make_user("calendar-oper", "calendar-pass", role="operador")
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56922223333")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont")
        session.add(case)
        session.commit()
        customer_id, case_id = customer.id, case.id
    assert client.post("/panel/api/login", json={"username": "calendar-oper", "password": "calendar-pass"}).status_code == 200
    booking = client.post("/panel/api/appointments", json={
        "service": "calefont", "customer_id": customer_id, "case_id": case_id,
        "technician_id": technician_id, "local_date": "2026-07-16", "local_time": "10:00",
        "timezone": "America/Santiago", "duration_minutes": 60,
    })
    appointment_id = booking.json()["appointment"]["id"]
    response = client.post(f"/panel/api/appointments/{appointment_id}/calendar/sync")
    assert response.status_code == 200
    assert response.json()["calendar"]["status"] == "synced"


def test_template_api_requires_authentication_and_renders_version(client, make_user):
    assert client.post("/panel/api/templates", json={}).status_code == 401
    make_user("template-oper", "template-pass", role="operador")
    assert client.post("/panel/api/login", json={"username": "template-oper", "password": "template-pass"}).status_code == 200
    published = client.post("/panel/api/templates", json={
        "event": "appointment_booked", "channel": "email", "locale": "es-CL",
        "content": "Hello {name}", "required_variables": ["name"], "approved": True,
    })
    assert published.status_code == 200
    template_id = published.json()["template"]["id"]
    rendered = client.post(f"/panel/api/templates/{template_id}/render", json={"variables": {"name": "Ana"}})
    assert rendered.status_code == 200
    assert rendered.json()["rendered"]["content"] == "Hello Ana"
