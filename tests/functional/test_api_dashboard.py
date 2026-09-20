"""Panel JSON API dashboard KPIs (B2/T2.1; PDW-API, PDW-AUTH-1, D1, D4).

GET /panel/api/kpis answers the same dict the Jinja dashboard renders
(`compute_kpis` from app/panel/routes/dashboard.py): contacts / motivos /
derived / visit_requests over the configured `kpi.window_days` window,
plus the window metadata. JSON errors only (D4): unauthenticated calls get
401 {"detail":"unauthorized"} — never a 302 to the HTML login page
(PDW-AUTH-1). No CORS headers on any API response (D1).

KPI values are asserted exactly from a deterministic seed (same dataset as
the Jinja dashboard suite) so the JSON surface mirrors the template view.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.db import SessionLocal  # noqa: E402
from app.panel.api.deps import require_dashboard_user  # noqa: E402
from app.models import (  # noqa: E402
    Appointment,
    AppointmentStatus,
    Case,
    Conversation,
    ConversationState,
    Customer,
    Message,
    MessageDirection,
    MessageType,
)


def _seed_kpi_data() -> None:
    """Deterministic KPI dataset (all within the default 7-day window):
    - 2 customers with 1 conversation each (2 inbound contacts)
    - 3 cases created in window: calefont (2: one escalated, one open),
      visita (1, escalated) -> motivos calefont=2, visita=1; derived=2
      (escalated_at set on calefont#1 + visita); visit_requests=1.
    """
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer_a = Customer(phone_e164="+56911112222", name="Ana Martínez")
        customer_b = Customer(phone_e164="+56933334444", name="Pedro Soto")
        session.add_all([customer_a, customer_b])
        session.flush()
        conv_a = Conversation(
            customer_id=customer_a.id, wa_phone="+56911112222", state=ConversationState.HUMAN
        )
        conv_b = Conversation(
            customer_id=customer_b.id, wa_phone="+56933334444", state=ConversationState.BOT
        )
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


def _login(client, username: str = "oper", password: str = "oper-pass") -> None:
    resp = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"


@pytest.mark.parametrize("path", [
    "/panel/api/kpis",
    "/panel/api/dashboard/summary?start=2026-08-01T00:00:00Z&end=2026-08-03T00:00:00Z&timezone=UTC",
    "/panel/api/dashboard/trend?start=2026-08-01T00:00:00Z&end=2026-08-03T00:00:00Z&timezone=UTC&metric=cases",
    "/panel/api/dashboard/drilldown?start=2026-08-01T00:00:00Z&end=2026-08-03T00:00:00Z&timezone=UTC&metric=cases&bucket_start=2026-08-01",
])
def test_dashboard_role_boundary(client, make_user, path):
    make_user("tech", "tech-pass", role="tecnico")
    _login(client, "tech", "tech-pass")
    assert client.get(path).status_code == 403


@pytest.mark.parametrize("role,username,password", [
    ("admin", "admin", "admin-pass"),
    ("operador", "oper", "oper-pass"),
])
@pytest.mark.parametrize("path", [
    "/panel/api/kpis",
    "/panel/api/dashboard/summary?start=2026-08-01T00:00:00Z&end=2026-08-03T00:00:00Z&timezone=UTC",
    "/panel/api/dashboard/trend?start=2026-08-01T00:00:00Z&end=2026-08-03T00:00:00Z&timezone=UTC&metric=cases",
    "/panel/api/dashboard/drilldown?start=2026-08-01T00:00:00Z&end=2026-08-03T00:00:00Z&timezone=UTC&metric=cases&bucket_start=2026-08-01",
])
def test_dashboard_roles_keep_access(client, make_user, role, username, password, path):
    make_user(username, password, role=role)
    _login(client, username, password)
    assert client.get(path).status_code == 200


# ---------------------------------------------------------------------------
# PDW-AUTH-1 — unauthenticated: 401 JSON, no redirect, no CORS (D1)
# ---------------------------------------------------------------------------


def test_kpis_without_session_returns_401_json_no_redirect(client):
    """No session cookie -> 401 {"detail":"unauthorized"}, never a 302."""
    resp = client.get("/panel/api/kpis", follow_redirects=False)

    assert resp.status_code == 401, "must be 401, not a redirect"
    assert "location" not in resp.headers, "must not redirect to the login page"
    assert resp.headers["content-type"].startswith("application/json"), (
        "error must be JSON (PDW-API-3)"
    )
    assert resp.json() == {"detail": "unauthorized"}


def test_kpis_without_session_has_no_cors_headers(client):
    """D1: same-origin only — no CORS headers on API responses."""
    resp = client.get("/panel/api/kpis", follow_redirects=False)

    assert "access-control-allow-origin" not in resp.headers


# ---------------------------------------------------------------------------
# PDW-API — 200 shape matches the compute_kpis service dict (seeded values)
# ---------------------------------------------------------------------------


def test_kpis_returns_exact_seeded_values(client, make_user):
    """Seeded dataset -> exact KPI counts, motivos breakdown, window metadata."""
    _seed_kpi_data()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/kpis", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    # contacts = 2 distinct conversations with inbound messages in window
    assert body["contacts"] == 2
    # motivos ordered by count desc, then service: calefont=2, visita=1
    assert body["motivos"] == [["calefont", 2], ["visita", 1]]
    # derived = 2 escalated cases in window; visit_requests = 1 (service 'visita')
    assert body["derived"] == 2
    assert body["visit_requests"] == 1
    assert body["new_customers"] == 2
    # window metadata from the default kpi.window_days (7)
    assert body["window_days"] == 7
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", body["window_start"]), (
        "window_start must be an ISO-8601 date"
    )


def test_kpis_empty_db_returns_zeros(client, make_user):
    """No data at all -> zero counts and an empty motivos breakdown."""
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/kpis", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert body["contacts"] == 0
    assert body["derived"] == 0
    assert body["visit_requests"] == 0
    assert body["new_customers"] == 0
    assert body["motivos"] == []
    assert body["window_days"] == 7


def test_kpis_respects_configured_window(client, make_user):
    """Narrowing kpi.window_days pushes out-of-window data out of the KPIs."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56911112222", name="Ana")
        session.add(customer)
        session.flush()
        conv = Conversation(
            customer_id=customer.id, wa_phone="+56911112222", state=ConversationState.BOT
        )
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
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/kpis", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert body["window_days"] == 2, "window metadata must reflect the setting"
    # The 3-day-old contact + case fall OUTSIDE the 2-day window.
    assert body["contacts"] == 0
    assert body["derived"] == 0
    assert body["visit_requests"] == 0
    assert body["motivos"] == []


def test_today_requires_json_auth_and_valid_timezone(client, make_user):
    response = client.get("/panel/api/dashboard/today?timezone=America/Santiago", follow_redirects=False)
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}

    make_user("admin", "admin-pass", role="admin")
    _login(client, "admin", "admin-pass")
    response = client.get("/panel/api/dashboard/today?timezone=Not/AZone", follow_redirects=False)
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid timezone"

    make_user("other", "other-pass", role="operador")
    other = client.post("/panel/api/login", json={"username": "other", "password": "other-pass"})
    assert other.status_code == 200


def test_today_projection_uses_local_bounds_and_operational_predicates(client, make_user):
    # Anchored to 12:00 UTC of the CURRENT local day: the appointment is seeded
    # at +1h/+2h, so a wall-clock "now" late in the local evening would push it
    # across local midnight and out of the day window the route projects.
    # Deriving the anchor from the local date keeps the assertion stable
    # no matter when the suite runs.
    local_today = datetime.now(ZoneInfo("America/Santiago"))
    now = datetime(local_today.year, local_today.month, local_today.day, 12, 0, tzinfo=timezone.utc)
    make_user("oper", "oper-pass", role="operador")
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56977770000", name="Hoy Cliente", created_at=now)
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164, state=ConversationState.HUMAN)
        session.add(conversation)
        session.flush()
        case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont", summary="No enciende", emergency=True, created_at=now)
        session.add_all([Message(conversation_id=conversation.id, direction=MessageDirection.INBOUND, msg_type=MessageType.TEXT, text="ayuda", created_at=now - timedelta(minutes=5)), case])
        session.flush()
        session.add(Appointment(service="visita", customer_id=customer.id, case_id=case.id, technician_id=1, local_start=datetime.now(), timezone="America/Santiago", starts_at=now + timedelta(hours=1), ends_at=now + timedelta(hours=2), duration_minutes=60))
        session.commit()
    _login(client)
    response = client.get("/panel/api/dashboard/today?timezone=America/Santiago")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"tz", "local_date", "appointments_today", "unanswered_conversations", "urgent_cases"}
    assert body["tz"] == "America/Santiago"
    assert body["unanswered_conversations"][0]["customer_name"] == "Hoy Cliente"
    assert body["urgent_cases"][0]["summary"] == "No enciende"
    assert body["appointments_today"][0]["service"] == "visita"


def test_today_excludes_cancelled_and_replied_rows_and_caps_each_projection(client, make_user):
    # Anchored to 12:00 UTC of the CURRENT local day: the 21 appointments span
    # up to +10.35h, so a wall-clock "now" late in the day would push the tail
    # across the local midnight. Deriving the anchor from the local date keeps
    # the cap assertion stable no matter which day the suite runs.
    local_today = datetime.now(ZoneInfo("America/Santiago"))
    now = datetime(local_today.year, local_today.month, local_today.day, 12, 0, tzinfo=timezone.utc)
    make_user("oper", "oper-pass", role="operador")
    with SessionLocal() as session:
        for index in range(21):
            customer = Customer(phone_e164=f"+5698888{index:04d}", name=f"Cliente {index}", created_at=now)
            session.add(customer)
            session.flush()
            conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164, state=ConversationState.BOT)
            session.add(conversation)
            session.flush()
            session.add(Message(conversation_id=conversation.id, direction=MessageDirection.INBOUND, msg_type=MessageType.TEXT, text="hola", created_at=now - timedelta(minutes=index + 1)))
            case = Case(conversation_id=conversation.id, customer_id=customer.id, service="urgente", emergency=True, created_at=now, escalated_at=now - timedelta(minutes=index))
            session.add(case)
            session.flush()
            session.add(Appointment(service="visita", customer_id=customer.id, case_id=case.id, technician_id=1, local_start=datetime.now(), timezone="America/Santiago", starts_at=now + timedelta(minutes=index * 31 + 1), ends_at=now + timedelta(minutes=index * 31 + 31), duration_minutes=30, status=AppointmentStatus.CANCELLED if index == 0 else AppointmentStatus.BOOKED))
        session.flush()
        session.add(Message(conversation_id=1, direction=MessageDirection.OUTBOUND, msg_type=MessageType.TEXT, text="respondido", created_at=now))
        session.commit()
    _login(client)
    body = client.get("/panel/api/dashboard/today?timezone=America/Santiago").json()
    assert len(body["appointments_today"]) == 20
    assert len(body["unanswered_conversations"]) == 20
    assert len(body["urgent_cases"]) == 20
    assert all(row["customer_name"] != "Cliente 0" for row in body["unanswered_conversations"])


def test_today_rejects_non_dashboard_roles():
    with pytest.raises(Exception) as error:
        require_dashboard_user(SimpleNamespace(role=SimpleNamespace(value="tecnico")))
    assert error.value.status_code == 403
