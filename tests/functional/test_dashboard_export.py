"""Dashboard KPIs + CSV export (T5.5; AP-7, AP-8).

Functional suite: the dashboard renders contacts / motivos / derived cases /
visit-request counts as SQL aggregates over the configured time window (AP-8,
no chart library), and the CSV exports stream clients and cases with the
panel-visible fields (AP-7, stdlib csv).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    Conversation,
    ConversationState,
    Customer,
    CustomerNote,
    Message,
    MessageDirection,
    MessageType,
)
from app.services.users import hash_password  # noqa: E402


def _login_oper(client, make_user) -> None:
    make_user("oper", "oper-pass", role="operador")
    client.post(
        "/panel/login",
        data={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )


def _seed_kpi_data() -> None:
    """Seed a deterministic KPI dataset (all within the default 7-day window):
    - 2 customers with 1 conversation each (2 inbound contacts)
    - 3 cases created in window: calefont (2: one escalated, one open),
      visita (1, escalated) -> motivos calefont=2, visita=1; derivados=2
      (escalated_at set on calefont#1 + visita); visit_requests=1.
    """
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer_a = Customer(phone_e164="+56911112222", name="Ana Martínez")
        customer_b = Customer(phone_e164="+56933334444", name="Pedro Soto")
        session.add_all([customer_a, customer_b])
        session.flush()
        conv_a = Conversation(customer_id=customer_a.id, wa_phone="+56911112222", state=ConversationState.HUMAN)
        conv_b = Conversation(customer_id=customer_b.id, wa_phone="+56933334444", state=ConversationState.BOT)
        session.add_all([conv_a, conv_b])
        session.flush()
        session.add_all(
            [
                Message(
                    conversation_id=conv_a.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="hola",
                    created_at=now - timedelta(days=1),
                ),
                Message(
                    conversation_id=conv_b.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="hola",
                    created_at=now - timedelta(days=2),
                ),
            ]
        )
        session.add_all(
            [
                Case(
                    conversation_id=conv_a.id,
                    customer_id=customer_a.id,
                    service="calefont",
                    status="escalado",
                    escalated_at=now - timedelta(days=1),
                    created_at=now - timedelta(days=1),
                ),
                Case(
                    conversation_id=conv_b.id,
                    customer_id=customer_b.id,
                    service="calefont",
                    status="abierto",
                    created_at=now - timedelta(days=2),
                ),
                Case(
                    conversation_id=conv_b.id,
                    customer_id=customer_b.id,
                    service="visita",
                    status="escalado",
                    escalated_at=now - timedelta(hours=5),
                    created_at=now - timedelta(hours=6),
                ),
            ]
        )
        session.commit()


# ---------------------------------------------------------------------------
# AP-8 — dashboard KPIs
# ---------------------------------------------------------------------------


@pytest.mark.spec("AP-8")
def test_dashboard_shows_kpi_counts(client, make_user):
    _seed_kpi_data()
    _login_oper(client, make_user)

    resp = client.get("/panel/")

    assert resp.status_code == 200
    assert "Contacts" in resp.text
    assert "Derived cases" in resp.text
    assert "Visit requests" in resp.text
    assert "Motivos" in resp.text
    # contacts = 2 distinct conversations with inbound messages in window
    assert "2" in resp.text
    # derived = 2 escalated cases in window
    # visit requests = 1 (service 'visita')
    assert "1" in resp.text


@pytest.mark.spec("AP-8")
def test_dashboard_motivos_table_breaks_down_by_service(client, make_user):
    _seed_kpi_data()
    _login_oper(client, make_user)

    resp = client.get("/panel/")

    assert resp.status_code == 200
    # motivos table rows: calefont=2, visita=1
    assert "calefont" in resp.text
    assert "visita" in resp.text


@pytest.mark.spec("AP-8")
def test_dashboard_respects_settings_time_window(client, make_user):
    # Window = 2 days via settings; seed one case 3 days old (OUTSIDE) and
    # one inside -> only the inside one counts.
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56911112222", name="Ana")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56911112222", state=ConversationState.BOT)
        session.add(conv)
        session.flush()
        session.add_all(
            [
                Message(
                    conversation_id=conv.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="old",
                    created_at=now - timedelta(days=3),
                ),
                Case(
                    conversation_id=conv.id,
                    customer_id=customer.id,
                    service="calefont",
                    status="escalado",
                    escalated_at=now - timedelta(days=3),
                    created_at=now - timedelta(days=3),
                ),
            ]
        )
        session.commit()
    # Narrow the KPI window to 2 days (default is 7).
    with SessionLocal() as session:
        from app.models import Settings

        session.merge(Settings(key="kpi.window_days", value=2))
        session.commit()
    _login_oper(client, make_user)

    resp = client.get("/panel/")

    assert resp.status_code == 200
    # The 3-day-old contact + case fall OUTSIDE the 2-day window: the motivos
    # table is empty and the derived/contact KPI values are zero.
    assert "calefont" not in resp.text, "out-of-window case must not count"
    assert "Motivos" in resp.text


@pytest.mark.spec("AP-8")
def test_dashboard_empty_state_shows_zero_kpis(client, make_user):
    _login_oper(client, make_user)

    resp = client.get("/panel/")

    assert resp.status_code == 200
    assert "Contacts" in resp.text
    assert "Motivos" in resp.text


# ---------------------------------------------------------------------------
# AP-7 — CSV export (stdlib csv, streaming)
# ---------------------------------------------------------------------------


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
    assert "Content-Disposition" in resp.headers
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
        conv = Conversation(customer_id=customer.id, wa_phone="+56911112222", state=ConversationState.HUMAN)
        session.add(conv)
        session.flush()
        session.add(
            Case(
                conversation_id=conv.id,
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


# ---------------------------------------------------------------------------
# Auth — dashboard + exports require login
# ---------------------------------------------------------------------------


@pytest.mark.spec("AP-2")
def test_dashboard_and_export_require_login(client):
    resp = client.get("/panel/", follow_redirects=False)
    assert resp.status_code == 302

    resp = client.get("/panel/export/clients.csv", follow_redirects=False)
    assert resp.status_code == 302

    resp = client.get("/panel/export/cases.csv", follow_redirects=False)
    assert resp.status_code == 302
