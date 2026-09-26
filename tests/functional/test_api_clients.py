"""Panel JSON API clients (B2/T2.2; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4).

The JSON surface wraps the existing customers service (search / ficha /
state transition / notes) with no new business logic: field names are the
service-layer snake_case keys, datetimes are ISO-8601, and responses are
plain dicts (no ORM leak — PDW-API). Error shape contract (PDW-API-3):
every 400/404 is JSON {"detail": "..."}, never an HTML page. Auth is the
JSON-401 dependency (D4): unauthenticated calls get 401, never a 302
(PDW-AUTH-1). No CORS headers (D1).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AuditLog,
    Case,
    Conversation,
    ConversationState,
    Customer,
    CustomerNote,
    CustomerState,
    MemoryType,
    Message,
    MessageDirection,
    MessageType,
    Appointment,
    AppointmentHistory,
    AppointmentStatus,
)


def _seed_customer(
    *,
    phone: str = "+56911112222",
    name: str = "Ana Martínez",
    state: CustomerState = CustomerState.NUEVO,
    messages: int = 2,
) -> int:
    """Create a customer with one conversation, `messages` messages and a case."""
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone, name=name, state=state)
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id, wa_phone=phone, state=ConversationState.BOT
        )
        session.add(conversation)
        session.flush()
        for i in range(messages):
            direction = (
                MessageDirection.INBOUND if i % 2 == 0 else MessageDirection.OUTBOUND
            )
            session.add(
                Message(
                    conversation_id=conversation.id,
                    direction=direction,
                    msg_type=MessageType.TEXT,
                    text=f"message {i}",
                )
            )
        session.add(
            Case(
                conversation_id=conversation.id,
                customer_id=customer.id,
                service="calefont",
                status="escalado",
                summary="needs a technician",
            )
        )
        session.commit()
        return customer.id


def _login(client, username: str = "oper", password: str = "oper-pass") -> None:
    resp = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"


def _customer_row(customer_id: int) -> Customer:
    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        assert customer is not None
        return customer


# ---------------------------------------------------------------------------
# PDW-AUTH-1 — unauthenticated: 401 JSON, no redirect (all four endpoints)
# ---------------------------------------------------------------------------


def test_clients_endpoints_require_login_401_json(client):
    """No session -> every clients endpoint answers 401 JSON, never a 302."""
    for method, path in [
        ("get", "/panel/api/clients"),
        ("get", "/panel/api/clients/1"),
        ("post", "/panel/api/clients/1/state"),
        ("post", "/panel/api/clients/1/notes"),
    ]:
        resp = getattr(client, method)(path, follow_redirects=False)
        assert resp.status_code == 401, f"{method.upper()} {path} must be 401"
        assert "location" not in resp.headers, f"{path} must not redirect"
        assert resp.headers["content-type"].startswith("application/json"), (
            f"{path} error must be JSON (PDW-API-3)"
        )
        assert resp.json() == {"detail": "unauthorized"}
        assert "access-control-allow-origin" not in resp.headers, "no CORS (D1)"


# ---------------------------------------------------------------------------
# PDW-API — GET /clients?q= wraps search_customers ({"clients", "query"})
# ---------------------------------------------------------------------------


def test_clients_list_returns_wrapped_search(client, make_user):
    _seed_customer(name="Ana Martínez", phone="+56911112222")
    _seed_customer(name="Pedro Soto", phone="+56933334444", state=CustomerState.AGENDADO)
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/clients", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"clients", "query"}
    assert body["query"] == ""
    names = {c["name"] for c in body["clients"]}
    assert names == {"Ana Martínez", "Pedro Soto"}
    # serializer shape: snake_case service keys, state as string, no ORM leak
    pedro = next(c for c in body["clients"] if c["name"] == "Pedro Soto")
    assert pedro["state"] == "agendado"
    assert pedro["phone_e164"] == "+56933334444"
    datetime.fromisoformat(pedro["created_at"])  # ISO-8601, parseable


def test_clients_search_by_name_and_phone(client, make_user):
    _seed_customer(name="Ana Martínez", phone="+56911112222")
    _seed_customer(name="Pedro Soto", phone="+56933334444")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/clients", params={"q": "pedro"}, follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "pedro"
    names = {c["name"] for c in body["clients"]}
    assert names == {"Pedro Soto"}

    # Partial digit match on the E.164 number (service behavior, AP-3).
    resp = client.get("/panel/api/clients", params={"q": "3333"}, follow_redirects=False)
    names = {c["name"] for c in resp.json()["clients"]}
    assert names == {"Pedro Soto"}


def test_clients_search_no_matches_returns_empty_list(client, make_user):
    """Empty result is real (service filtered) — companion to the non-empty test."""
    _seed_customer(name="Ana Martínez", phone="+56911112222")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/clients", params={"q": "zzz-nobody"}, follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert body["clients"] == []
    assert body["query"] == "zzz-nobody"


def test_clients_list_caps_at_limit_100(client, make_user):
    """search_customers limit=100 honored by the API wrapper."""
    with SessionLocal() as session:
        for i in range(101):
            session.add(
                Customer(phone_e164=f"+569100000{i:03d}", name=f"Cliente {i}")
            )
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/clients", follow_redirects=False)

    assert resp.status_code == 200
    assert len(resp.json()["clients"]) == 100, "list must be capped at 100"


# ---------------------------------------------------------------------------
# PDW-API — GET /clients/{id}: customer + history + notes + states
# ---------------------------------------------------------------------------


def test_client_ficha_returns_full_payload(client, make_user):
    customer_id = _seed_customer(messages=2)
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get(f"/panel/api/clients/{customer_id}", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"customer", "history", "notes", "memo", "states", "users"}
    assert all(set(user) == {"id", "username"} for user in body["users"])
    assert {user["username"] for user in body["users"]} >= {"oper"}
    # customer: snake_case service keys, ISO-8601 datetimes, no ORM leak
    customer = body["customer"]
    assert customer["id"] == customer_id
    assert customer["name"] == "Ana Martínez"
    assert customer["phone_e164"] == "+56911112222"
    assert customer["state"] == "nuevo"
    datetime.fromisoformat(customer["created_at"])
    # history from the service dicts (conversations/cases/messages)
    history = body["history"]
    assert len(history["conversations"]) == 1
    assert len(history["cases"]) == 1
    case = history["cases"][0]
    assert case["service"] == "calefont"
    assert set(case) == {
        "id", "conversation_id", "customer_id", "created_at", "service",
        "priority", "status", "summary", "emergency", "responsible_id",
        "escalated_at", "closed_at", "acknowledged_at", "ack_by", "is_open",
    }
    assert case["is_open"] is True
    assert [m["text"] for m in history["messages"]] == ["message 0", "message 1"]
    # states: full lifecycle as strings
    assert body["states"] == [
        "nuevo", "contactado", "pendiente", "agendado",
        "en_evaluacion", "finalizado", "cancelado", "postventa",
    ]


def test_client_ficha_closed_case_is_not_open(client, make_user):
    from app.services.cases import set_case_status

    customer_id = _seed_customer()
    with SessionLocal() as session:
        case = session.scalar(select(Case).where(Case.customer_id == customer_id))
        set_case_status(case, "cerrado")
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    response = client.get(f"/panel/api/clients/{customer_id}")

    assert response.status_code == 200
    case_payload = response.json()["history"]["cases"][0]
    assert case_payload["is_open"] is False
    assert case_payload["closed_at"] is not None


def test_client_ficha_omits_visit_history_but_keeps_appointments(client, make_user):
    customer_id = _seed_customer(messages=0)
    technician = make_user("history-tech", "history-pass", role="operador")
    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        case = session.scalar(select(Case).where(Case.customer_id == customer_id))
        appointment = Appointment(
            service="calefont", customer_id=customer.id, case_id=case.id,
            technician_id=technician, local_start=datetime(2026, 7, 15, 10),
            timezone="America/Santiago", starts_at=datetime.fromisoformat("2026-07-15T14:00:00+00:00"),
            ends_at=datetime.fromisoformat("2026-07-15T15:00:00+00:00"), duration_minutes=60,
        )
        session.add(appointment)
        session.flush()
        session.add_all([
            AppointmentHistory(appointment_id=appointment.id, actor="oper", action="booked",
                               to_status=AppointmentStatus.BOOKED, details={"source": "panel"}),
            AppointmentHistory(appointment_id=appointment.id, actor="oper", action="cancelled",
                               from_status=AppointmentStatus.BOOKED, to_status=AppointmentStatus.CANCELLED,
                               details={"reason": "customer request"}),
        ])
        session.commit()
    _login(client, "history-tech", "history-pass")

    response = client.get(f"/panel/api/clients/{customer_id}")

    assert response.status_code == 200
    history = response.json()["history"]
    assert len(history["appointments"]) == 1
    assert "visit_history" not in history


def test_client_ficha_includes_notes(client, make_user):
    customer_id = _seed_customer()
    with SessionLocal() as session:
        session.add(
            CustomerNote(
                customer_id=customer_id, note="prefiere horario tarde", author="oper"
            )
        )
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get(f"/panel/api/clients/{customer_id}", follow_redirects=False)

    assert resp.status_code == 200
    notes = resp.json()["notes"]
    assert len(notes) == 1
    assert notes[0]["note"] == "prefiere horario tarde"
    assert notes[0]["author"] == "oper"
    assert notes[0]["customer_id"] == customer_id
    datetime.fromisoformat(notes[0]["created_at"])


# ---------------------------------------------------------------------------
# CR-7 — ficha surfaces the living customer_memo distinct from staff notes
# ---------------------------------------------------------------------------


def test_client_ficha_shows_customer_memo(client, make_user):
    """CR-7: the latest customer_memo appears on the ficha, as a string."""
    from app.services import memory

    customer_id = _seed_customer()
    with SessionLocal() as session:
        memory.upsert(
            session,
            scope="customer",
            entity_id=str(customer_id),
            topic_key="customer_memo",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="customer_memo",
            contenido="acta del cierre: cliente pidio recalcular presupuesto",
        )
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get(f"/panel/api/clients/{customer_id}", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert body["memo"] == "acta del cierre: cliente pidio recalcular presupuesto"


def test_client_ficha_memo_empty_when_no_close(client, make_user):
    """CR-7: with no memo yet, the ficha surfaces an empty memo, no error."""
    customer_id = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get(f"/panel/api/clients/{customer_id}", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json()["memo"] == ""


def test_client_ficha_memo_and_notes_coexist(client, make_user):
    """CR-7: auto memo and staff notes are distinct and both retained."""
    from app.services import memory

    customer_id = _seed_customer()
    with SessionLocal() as session:
        memory.upsert(
            session,
            scope="customer",
            entity_id=str(customer_id),
            topic_key="customer_memo",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="customer_memo",
            contenido="memo automatico del cierre",
        )
        session.add(
            CustomerNote(
                customer_id=customer_id, note="nota interna del operador", author="oper"
            )
        )
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get(f"/panel/api/clients/{customer_id}", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert body["memo"] == "memo automatico del cierre"
    notes = body["notes"]
    assert len(notes) == 1
    assert notes[0]["note"] == "nota interna del operador"


def test_client_ficha_missing_returns_404_json(client, make_user):
    """Missing customer -> 404 {"detail":"customer not found"} (PDW-API-3)."""
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/clients/999999", follow_redirects=False)

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "customer not found"}


# ---------------------------------------------------------------------------
# PDW-API — POST /clients/{id}/state (CR-3 transition, audited with actor)
# ---------------------------------------------------------------------------


def test_state_change_valid_transition_audited(client, make_user):
    customer_id = _seed_customer(state=CustomerState.NUEVO)
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/clients/{customer_id}/state",
        json={"state": "agendado"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "state": "agendado"}
    assert _customer_row(customer_id).state == CustomerState.AGENDADO
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "customer.state_change")
        )
    assert audit is not None, "state change must be audited (SH-5)"
    assert audit.actor == "oper"
    assert audit.before == {"state": "nuevo"}
    assert audit.after == {"state": "agendado"}


def test_state_change_invalid_transition_400_json(client, make_user):
    customer_id = _seed_customer(state=CustomerState.NUEVO)
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    # nuevo -> postventa is not a legal CR-3 transition.
    resp = client.post(
        f"/panel/api/clients/{customer_id}/state",
        json={"state": "postventa"},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json"), (
        "error must be JSON (PDW-API-3)"
    )
    assert "invalid" in resp.json()["detail"].lower()
    assert _customer_row(customer_id).state == CustomerState.NUEVO, "state must not change"
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "customer.state_change")
        )
    assert audit is None, "rejected transition must not be audited"


def test_state_change_unknown_state_400_json(client, make_user):
    customer_id = _seed_customer(state=CustomerState.NUEVO)
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/clients/{customer_id}/state",
        json={"state": "not-a-state"},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert "detail" in resp.json()
    assert _customer_row(customer_id).state == CustomerState.NUEVO


def test_state_change_missing_customer_404_json(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        "/panel/api/clients/999999/state",
        json={"state": "agendado"},
        follow_redirects=False,
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "customer not found"}


# ---------------------------------------------------------------------------
# PDW-API — POST /clients/{id}/notes (audited with actor)
# ---------------------------------------------------------------------------


def test_add_note_returns_note_and_audits(client, make_user):
    customer_id = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/clients/{customer_id}/notes",
        json={"note": "cliente prefiere horario tarde"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ok", "note"}
    assert body["ok"] is True
    assert body["note"]["note"] == "cliente prefiere horario tarde"
    assert body["note"]["author"] == "oper"
    assert body["note"]["customer_id"] == customer_id
    datetime.fromisoformat(body["note"]["created_at"])
    with SessionLocal() as session:
        stored = session.scalars(
            select(CustomerNote).where(CustomerNote.customer_id == customer_id)
        ).all()
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "customer.note_added")
        )
    assert len(stored) == 1
    assert stored[0].note == "cliente prefiere horario tarde"
    assert stored[0].author == "oper"
    assert audit is not None, "note must be audited (SH-5)"
    assert audit.actor == "oper"


def test_add_note_empty_rejected_400_json(client, make_user):
    customer_id = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/clients/{customer_id}/notes",
        json={"note": "   "},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert "detail" in resp.json()
    with SessionLocal() as session:
        stored = session.scalars(
            select(CustomerNote).where(CustomerNote.customer_id == customer_id)
        ).all()
    assert stored == [], "empty note must not be stored"


def test_add_note_missing_customer_404_json(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        "/panel/api/clients/999999/notes",
        json={"note": "hola"},
        follow_redirects=False,
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "customer not found"}
