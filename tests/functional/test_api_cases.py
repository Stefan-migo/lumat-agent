"""Panel JSON API cases (B3/T3.2; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4, D8).

Thin JSON wrappers over `app/services/cases.py` + `app/services/notify.py`:

- GET  /cases            -> {"cases": [...], "users": [{id,username}]}
                           open cases (escalated first) with the customer
                           embedded per case (D8 — no /users, no GET /cases/{id})
- POST /cases/{id}/update -> {"ok", "case"} (AP-5 status + nullable
                           responsible, audited with the actor)
- POST /cases/{id}/ack   -> {"ok", "case"} (EM-4 emergency ack, audited)

No new business logic; audits preserved (SH-5). All errors JSON
{"detail": ...} (PDW-API-3): 401 from the JSON-401 dep (D4, PDW-AUTH-1), 404
for a missing case. No redirects, no CORS (D1).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.chat.state import ConversationState as ChatConversationState  # noqa: E402
from app.models import (  # noqa: E402
    AuditLog,
    Case,
    Conversation,
    ConversationState,
    Customer,
    CustomerState,
    Message,
    MessageDirection,
    MessageType,
    User,
    UserRole,
)
from app.services.cases import create_handoff_case  # noqa: E402


def _seed_case(
    *,
    phone: str = "+56911112222",
    name: str = "Ana Martínez",
    emergency: bool = False,
    status: str = "escalado",
    escalated_at: datetime | None = None,
) -> int:
    """Create a customer + conversation + case (with one message)."""
    if escalated_at is None and status == "escalado":
        escalated_at = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone, name=name, state=CustomerState.AGENDADO)
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id, wa_phone=phone, state=ConversationState.HUMAN
        )
        session.add(conversation)
        session.flush()
        session.add(
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="calefont no enciende",
            )
        )
        case = Case(
            conversation_id=conversation.id,
            customer_id=customer.id,
            service="calefont",
            status=status,
            summary="needs a technician",
            emergency=emergency,
            escalated_at=escalated_at,
        )
        session.add(case)
        session.flush()
        case_id = case.id
        session.commit()
        return case_id


def _login(client, username: str = "oper", password: str = "oper-pass") -> None:
    resp = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"


def _case_row(case_id: int) -> Case:
    with SessionLocal() as session:
        case = session.get(Case, case_id)
        assert case is not None
        return case


# ---------------------------------------------------------------------------
# PDW-AUTH-1 — unauthenticated: 401 JSON, no redirect (all three endpoints)
# ---------------------------------------------------------------------------


def test_cases_endpoints_require_login_401_json(client):
    """No session -> every cases endpoint answers 401 JSON, never a 302."""
    for method, path in [
        ("get", "/panel/api/cases"),
        ("post", "/panel/api/cases/1/update"),
        ("post", "/panel/api/cases/1/ack"),
    ]:
        resp = getattr(client, method)(path, follow_redirects=False)
        assert resp.status_code == 401, f"{method.upper()} {path} must be 401"
        assert "location" not in resp.headers, f"{path} must not redirect (PDW-AUTH-1)"
        assert resp.headers["content-type"].startswith("application/json"), (
            f"{path} error must be JSON (PDW-API-3)"
        )
        assert resp.json() == {"detail": "unauthorized"}
        assert "access-control-allow-origin" not in resp.headers, "no CORS (D1)"


# ---------------------------------------------------------------------------
# PDW-API — GET /cases: open cases escalated first, users embedded (D8)
# ---------------------------------------------------------------------------


def test_cases_list_returns_open_cases_with_embedded_customer_and_users(client, make_user):
    _seed_case(name="Ana Martínez", phone="+56911112222", status="escalado")
    _seed_case(name="Pedro Soto", phone="+56933334444", status="pendiente")
    make_user("oper", "oper-pass", role="operador")
    make_user("other", "other-pass", role="operador")
    admin_id = make_user("boss", "boss-pass", role="admin")
    _login(client)

    resp = client.get("/panel/api/cases", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"cases", "users"}
    # users embedded from the User table ({id, username} — D8, no /users endpoint)
    usernames = {u["username"] for u in body["users"]}
    assert usernames == {"oper", "other", "boss"}
    user_ids = [u["id"] for u in body["users"]]
    assert all(isinstance(i, int) for i in user_ids)
    assert admin_id in user_ids
    # open cases only, escalated first (escalado before pendiente)
    cases = body["cases"]
    assert len(cases) == 2
    assert cases[0]["status"] == "escalado"
    assert cases[1]["status"] == "pendiente"
    # customer embedded (D8) via to_customer_dict
    first = cases[0]
    assert first["customer"]["name"] in {"Ana Martínez", "Pedro Soto"}
    assert first["customer"]["phone_e164"].startswith("+569")
    assert first["customer"]["state"] == "agendado"
    # case serializer: snake_case service keys, ISO-8601, no ORM leak
    datetime.fromisoformat(first["created_at"])
    assert not first.get("escalated_at") or datetime.fromisoformat(first["escalated_at"])
    assert first["summary"] == "needs a technician"


def test_cases_list_skips_closed_cases(client, make_user):
    """closed_at set -> case excluded from the open list (HH-4)."""
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56955556666", name="Closed Client")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone="+56955556666")
        session.add(conversation)
        session.flush()
        session.add(
            Case(
                conversation_id=conversation.id,
                customer_id=customer.id,
                status="finalizado",
                summary="closed one",
                closed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/cases", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json()["cases"] == [], "closed case must not appear (HH-4)"


def test_case_update_closes_case_and_removes_it_from_open_list(client, make_user):
    case_id = _seed_case(status="escalado")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    response = client.post(f"/panel/api/cases/{case_id}/update", json={"status": "cerrado"})

    assert response.status_code == 200
    assert _case_row(case_id).closed_at is not None
    cases = client.get("/panel/api/cases").json()["cases"]
    assert all(case["id"] != case_id for case in cases)


def test_case_update_reopening_clears_close_time_and_restores_case(client, make_user):
    case_id = _seed_case(status="escalado")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    closed = client.post(f"/panel/api/cases/{case_id}/update", json={"status": "cerrado"})
    assert closed.status_code == 200
    assert _case_row(case_id).closed_at is not None
    reopened = client.post(f"/panel/api/cases/{case_id}/update", json={"status": "abierto"})

    assert reopened.status_code == 200
    assert _case_row(case_id).closed_at is None
    cases = client.get("/panel/api/cases").json()["cases"]
    assert any(case["id"] == case_id for case in cases)


def test_closed_case_is_excluded_from_dashboard_urgent_cases(client, make_user):
    case_id = _seed_case(status="escalado", emergency=True)
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    response = client.post(f"/panel/api/cases/{case_id}/update", json={"status": "cancelado"})
    assert response.status_code == 200

    dashboard = client.get("/panel/api/dashboard/today?timezone=America/Santiago")

    assert dashboard.status_code == 200
    assert all(case["id"] != case_id for case in dashboard.json()["urgent_cases"])


def test_reescalating_closed_case_restores_it_to_open_list(client, make_user):
    case_id = _seed_case(status="escalado")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    closed = client.post(f"/panel/api/cases/{case_id}/update", json={"status": "cerrado"})
    assert closed.status_code == 200

    with SessionLocal() as session:
        case = session.get(Case, case_id)
        state = ChatConversationState.from_db(session, case.conversation_id)
        reescalated = create_handoff_case(
            session, state, summary_text="The issue returned", reason="repeat_issue"
        )
        session.commit()
        assert reescalated.id == case_id
        assert reescalated.status == "escalado"
        assert reescalated.closed_at is None

    cases = client.get("/panel/api/cases").json()["cases"]
    assert any(case["id"] == case_id for case in cases)


def test_open_status_remains_listed_when_close_timestamp_is_set(client, make_user):
    case_id = _seed_case(status="escalado")
    with SessionLocal() as session:
        case = session.get(Case, case_id)
        case.closed_at = datetime.now(timezone.utc)
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    cases = client.get("/panel/api/cases").json()["cases"]

    assert any(case["id"] == case_id for case in cases)


def test_cases_list_orders_by_escalated_at_within_same_status(client, make_user):
    """Among escalated cases, the newest escalation comes first."""
    def _mk(name):
        with SessionLocal() as session:
            customer = Customer(phone_e164=f"+5697{name}", name=name)
            session.add(customer)
            session.flush()
            conversation = Conversation(customer_id=customer.id, wa_phone=f"+5697{name}")
            session.add(conversation)
            session.flush()
            case = Case(
                conversation_id=conversation.id,
                customer_id=customer.id,
                status="escalado",
                escalated_at=datetime.now(timezone.utc),
            )
            session.add(case)
            session.flush()
            cid = case.id
            session.commit()
        return cid

    older = _mk("older")
    with SessionLocal() as session:
        case = session.get(Case, older)
        case.escalated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        session.commit()
    newer = _mk("newer")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/cases", follow_redirects=False)

    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()["cases"]]
    assert ids == [newer, older], "newest escalation must come first"


# ---------------------------------------------------------------------------
# PDW-API — POST /cases/{id}/update (AP-5, nullable responsible, audited)
# ---------------------------------------------------------------------------


def test_case_update_changes_status_and_responsible_audited(client, make_user):
    case_id = _seed_case(status="escalado")
    make_user("oper", "oper-pass", role="operador")
    with SessionLocal() as session:
        resp_user = User(username="boss", password_hash="x", role=UserRole.ADMIN, active=True)
        session.add(resp_user)
        session.flush()
        responsible_id = resp_user.id
        session.commit()
    _login(client)

    resp = client.post(
        f"/panel/api/cases/{case_id}/update",
        json={"status": "en_atencion", "responsible_id": responsible_id},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ok", "case"}
    assert body["ok"] is True
    assert body["case"]["id"] == case_id
    assert body["case"]["status"] == "en_atencion"
    assert body["case"]["responsible_id"] == responsible_id
    # persisted + audited (AP-5, SH-5)
    assert _case_row(case_id).status == "en_atencion"
    assert _case_row(case_id).responsible_id == responsible_id
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "case.updated")
        )
    assert audit is not None
    assert audit.actor == "oper"
    assert audit.before == {"status": "escalado", "responsible_id": None}
    assert audit.after == {"status": "en_atencion", "responsible_id": responsible_id}


def test_case_update_clears_responsible_with_null(client, make_user):
    """responsible_id:null explicitly clears the assignment (service sentinel)."""
    case_id = _seed_case(status="escalado")
    with SessionLocal() as session:
        user = User(username="oldassign", password_hash="x", role=UserRole.OPERADOR, active=True)
        session.add(user)
        session.flush()
        case = session.get(Case, case_id)
        case.responsible_id = user.id
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/cases/{case_id}/update",
        json={"status": "pendiente", "responsible_id": None},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json()["case"]["responsible_id"] is None
    assert _case_row(case_id).responsible_id is None, "null must clear assignment"
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "case.updated")
        )
    assert audit is not None
    assert audit.before["responsible_id"] is not None
    assert audit.after["responsible_id"] is None


def test_case_update_keeps_fields_when_omitted(client, make_user):
    """No status/responsible in body -> fields unchanged, still audited."""
    case_id = _seed_case(status="escalado")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/cases/{case_id}/update",
        json={},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    case = resp.json()["case"]
    assert case["status"] == "escalado"
    assert case["responsible_id"] is None
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "case.updated")
        )
    assert audit is not None, "update without edits still audited (AP-5)"


def test_case_update_missing_404_json(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        "/panel/api/cases/999999/update",
        json={"status": "en_atencion"},
        follow_redirects=False,
    )

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "case not found"}


# ---------------------------------------------------------------------------
# PDW-API — POST /cases/{id}/ack (EM-4 emergency ack, audited)
# ---------------------------------------------------------------------------


def test_case_ack_emergency_records_ack_and_audits(client, make_user):
    case_id = _seed_case(emergency=True, status="escalado")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(f"/panel/api/cases/{case_id}/ack", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ok", "case"}
    assert body["ok"] is True
    assert body["case"]["id"] == case_id
    assert body["case"]["acknowledged_at"] is not None
    assert body["case"]["ack_by"] == "oper"
    # persisted + audited (EM-4, SH-5)
    assert _case_row(case_id).acknowledged_at is not None
    assert _case_row(case_id).ack_by == "oper"
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "case.acknowledged")
        )
    assert audit is not None
    assert audit.actor == "oper"
    assert audit.after["channel"] == "panel"


def test_case_ack_non_emergency_is_noop(client, make_user):
    """ack on a non-emergency case: 200 ok, but nothing acked/audited."""
    case_id = _seed_case(emergency=False, status="escalado")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(f"/panel/api/cases/{case_id}/ack", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json()["case"]["acknowledged_at"] is None
    assert resp.json()["case"]["ack_by"] is None
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "case.acknowledged")
        )
    assert audit is None, "non-emergency ack must not be audited"


def test_case_ack_missing_404_json(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post("/panel/api/cases/999999/ack", follow_redirects=False)

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "case not found"}
