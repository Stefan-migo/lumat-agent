"""Authenticated CSV export contracts retained for the SPA (AP-7).

Dashboard KPI assertions live in ``test_api_dashboard.py``; this file keeps
the distinct browser-download contract for the surviving CSV routes.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import Case, Conversation, ConversationState, Customer  # noqa: E402


def _login_oper(client, make_user) -> None:
    make_user("oper", "oper-pass", role="operador")
    resp = client.post(
        "/panel/api/login",
        json={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )
    assert resp.status_code == 200


@pytest.mark.spec("AP-7")
def test_export_clients_csv(client, make_user):
    with SessionLocal() as session:
        session.add_all(
            [
                Customer(
                    phone_e164="+56911112222",
                    name="Ana Martínez",
                    email="ana@example.com",
                    comuna="Providencia",
                    state="agendado",
                ),
                Customer(phone_e164="+56933334444", name="Pedro Soto"),
            ]
        )
        session.commit()
    _login_oper(client, make_user)

    resp = client.get("/panel/export/clients.csv")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    lines = resp.text.strip().splitlines()
    assert lines[0].split(",")[:3] == ["id", "phone_e164", "name"]
    assert any("+56911112222" in line and "Ana Martínez" in line for line in lines)
    assert any("+56933334444" in line and "Pedro Soto" in line for line in lines)


@pytest.mark.spec("AP-7")
def test_export_cases_csv(client, make_user):
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56911112222", name="Ana Martínez")
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id,
            wa_phone=customer.phone_e164,
            state=ConversationState.HUMAN,
        )
        session.add(conversation)
        session.flush()
        session.add(
            Case(
                conversation_id=conversation.id,
                customer_id=customer.id,
                service="calefont",
                status="escalado",
                emergency=True,
                summary="needs a technician",
            )
        )
        session.commit()
    _login_oper(client, make_user)

    resp = client.get("/panel/export/cases.csv")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    lines = resp.text.strip().splitlines()
    assert lines[0].split(",")[:4] == ["id", "customer_name", "customer_phone", "service"]
    assert any("calefont" in line and "needs a technician" in line for line in lines)
