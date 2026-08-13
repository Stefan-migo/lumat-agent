"""Clients + conversations panel views (T5.2; AP-3, AP-4, CR-3, CR-4, CR-5).

Functional suite: clients list/search (AP-3), the ficha with full history
(CR-5), internal notes (CR-4), lifecycle state change with audit and invalid-
transition rejection (CR-3), and the read-only conversation thread with media
links (AP-4). All routes require login (require_user — enforced server-side).
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
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
)
from app.services.users import hash_password  # noqa: E402


@pytest.fixture
def logged_client(client, make_user):
    """A TestClient already authenticated as an operador."""
    make_user("oper", "oper-pass", role="operador")
    client.post(
        "/panel/login",
        data={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )
    return client


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


def _login_oper(client, make_user) -> None:
    make_user("oper", "oper-pass", role="operador")
    client.post(
        "/panel/login",
        data={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# AP-3 — clients list + search
# ---------------------------------------------------------------------------


@pytest.mark.spec("AP-3")
def test_clients_list_lists_customers_with_state(client, make_user):
    _seed_customer(name="Ana Martínez", phone="+56911112222")
    _seed_customer(name="Pedro Soto", phone="+56933334444", state=CustomerState.AGENDADO)
    _login_oper(client, make_user)

    resp = client.get("/panel/clients")

    assert resp.status_code == 200
    assert "Ana Martínez" in resp.text
    assert "Pedro Soto" in resp.text
    assert "nuevo" in resp.text
    assert "agendado" in resp.text


@pytest.mark.spec("AP-3")
def test_clients_search_by_name(client, make_user):
    _seed_customer(name="Ana Martínez", phone="+56911112222")
    _seed_customer(name="Pedro Soto", phone="+56933334444")
    _login_oper(client, make_user)

    resp = client.get("/panel/clients", params={"q": "pedro"})

    assert resp.status_code == 200
    assert "Pedro Soto" in resp.text
    assert "Ana Martínez" not in resp.text


@pytest.mark.spec("AP-3")
def test_clients_search_by_phone_digits(client, make_user):
    _seed_customer(name="Ana Martínez", phone="+56911112222")
    _seed_customer(name="Pedro Soto", phone="+56933334444")
    _login_oper(client, make_user)

    # Partial digit match on the E.164 number.
    resp = client.get("/panel/clients", params={"q": "3333"})

    assert resp.status_code == 200
    assert "Pedro Soto" in resp.text
    assert "Ana Martínez" not in resp.text


@pytest.mark.spec("AP-3")
def test_clients_search_no_matches(client, make_user):
    _seed_customer(name="Ana Martínez", phone="+56911112222")
    _login_oper(client, make_user)

    resp = client.get("/panel/clients", params={"q": "zzz-nobody"})

    assert resp.status_code == 200
    assert "Ana Martínez" not in resp.text


# ---------------------------------------------------------------------------
# AP-3 / CR-5 — ficha: history
# ---------------------------------------------------------------------------


@pytest.mark.spec("CR-5")
def test_ficha_lists_history(client, make_user):
    customer_id = _seed_customer(messages=3)
    _login_oper(client, make_user)

    resp = client.get(f"/panel/clients/{customer_id}")

    assert resp.status_code == 200
    assert "Ana Martínez" in resp.text
    # history: the conversation, its case and every message
    assert "calefont" in resp.text
    assert "needs a technician" in resp.text
    assert "message 0" in resp.text
    assert "message 1" in resp.text
    assert "message 2" in resp.text


# ---------------------------------------------------------------------------
# CR-4 — internal notes (staff only)
# ---------------------------------------------------------------------------


@pytest.mark.spec("CR-4")
def test_add_internal_note(client, make_user):
    customer_id = _seed_customer()
    _login_oper(client, make_user)

    resp = client.post(
        f"/panel/clients/{customer_id}/notes",
        data={"note": "cliente prefiere horario tarde"},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    assert "cliente prefiere horario tarde" in resp.text
    from app.models import CustomerNote

    with SessionLocal() as session:
        notes = session.scalars(
            select(CustomerNote).where(CustomerNote.customer_id == customer_id)
        ).all()
    assert len(notes) == 1
    assert notes[0].note == "cliente prefiere horario tarde"
    assert notes[0].author == "oper"


# ---------------------------------------------------------------------------
# CR-3 — lifecycle state change (audited, validated)
# ---------------------------------------------------------------------------


@pytest.mark.spec("CR-3")
def test_state_change_updates_and_audits(client, make_user):
    customer_id = _seed_customer(state=CustomerState.NUEVO)
    _login_oper(client, make_user)

    resp = client.post(
        f"/panel/clients/{customer_id}/state",
        data={"state": "agendado"},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        assert customer.state.value == "agendado"
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "customer.state_change")
        )
        assert audit is not None
        assert audit.actor == "oper"
        assert audit.before == {"state": "nuevo"}
        assert audit.after == {"state": "agendado"}


@pytest.mark.spec("CR-3")
def test_invalid_state_transition_rejected(client, make_user):
    customer_id = _seed_customer(state=CustomerState.NUEVO)
    _login_oper(client, make_user)

    # nuevo -> postventa is not a legal CR-3 transition.
    resp = client.post(
        f"/panel/clients/{customer_id}/state",
        data={"state": "postventa"},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    assert "invalid" in resp.text.lower()
    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        assert customer.state.value == "nuevo", "state must not change"
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "customer.state_change")
        )
        assert audit is None, "rejected transition must not be audited"


# ---------------------------------------------------------------------------
# AP-4 — conversation thread (read-only) + media links
# ---------------------------------------------------------------------------


@pytest.mark.spec("AP-4")
def test_conversation_thread_shows_messages_in_order(client, make_user):
    customer_id = _seed_customer(messages=2)
    _login_oper(client, make_user)
    with SessionLocal() as session:
        conversation_id = session.scalar(
            select(Conversation).where(Conversation.customer_id == customer_id)
        ).id

    resp = client.get(f"/panel/conversations/{conversation_id}")

    assert resp.status_code == 200
    assert "message 0" in resp.text
    assert "message 1" in resp.text
    # order: message 0 (index) before message 1 (index)
    assert resp.text.index("message 0") < resp.text.index("message 1")


@pytest.mark.spec("AP-4")
def test_conversation_thread_renders_media_links(client, make_user):
    customer_id = _seed_customer(messages=0)
    _login_oper(client, make_user)
    with SessionLocal() as session:
        conversation = session.scalar(
            select(Conversation).where(Conversation.customer_id == customer_id)
        )
        session.add(
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.IMAGE,
                text="foto de la instalación",
                media_url="/media/evidence/abc123.jpg",
            )
        )
        session.commit()
        conversation_id = conversation.id

    resp = client.get(f"/panel/conversations/{conversation_id}")

    assert resp.status_code == 200
    assert "/media/evidence/abc123.jpg" in resp.text
    assert "foto de la instalación" in resp.text


# ---------------------------------------------------------------------------
# Auth — every clients/conversations route requires login (server-side)
# ---------------------------------------------------------------------------


@pytest.mark.spec("AP-2")
def test_clients_routes_require_login(client):
    resp = client.get("/panel/clients", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/panel/login"

    resp = client.get("/panel/clients/1", follow_redirects=False)
    assert resp.status_code == 302

    resp = client.get("/panel/conversations/1", follow_redirects=False)
    assert resp.status_code == 302

    resp = client.post("/panel/clients/1/state", data={"state": "x"}, follow_redirects=False)
    assert resp.status_code == 302

    resp = client.post("/panel/clients/1/notes", data={"note": "x"}, follow_redirects=False)
    assert resp.status_code == 302
