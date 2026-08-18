"""Panel JSON API conversations (B3/T3.1; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4).

The JSON surface reads one conversation + its messages in chronological
order with linked `media_url` files rendered as plain URLs (PDW-TST-3
pattern — the SPA renders media as links, same as the Jinja thread). No new
business logic; no ORM leak (dicts, snake_case service keys, ISO-8601
datetimes). Error shape contract (PDW-API-3): every 404 is JSON
{"detail": "..."}, never an HTML page. Auth is the JSON-401 dependency (D4):
unauthenticated calls get 401, never a 302 (PDW-AUTH-1). No CORS (D1).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Conversation,
    ConversationState,
    Customer,
    Message,
    MessageDirection,
    MessageType,
)


def _seed_conversation(
    *,
    phone: str = "+56911112222",
    name: str = "Ana Martínez",
    state: ConversationState = ConversationState.HUMAN,
) -> tuple[int, int]:
    """Create a customer + one conversation with 3 messages (1 with media)."""
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone, name=name)
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id, wa_phone=phone, state=state, summary="needs visita"
        )
        session.add(conversation)
        session.flush()
        # Chronological: inbound text, outbound text, inbound image with media_url.
        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="hola, mi calefont no enciende",
                ),
                Message(
                    conversation_id=conversation.id,
                    direction=MessageDirection.OUTBOUND,
                    msg_type=MessageType.TEXT,
                    text="te ayudo con eso",
                ),
                Message(
                    conversation_id=conversation.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.IMAGE,
                    media_url="https://example.com/media/photo.jpg",
                    text="foto de la instalación",
                ),
            ]
        )
        session.commit()
        return customer.id, conversation.id


def _login(client, username: str = "oper", password: str = "oper-pass") -> None:
    resp = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"


# ---------------------------------------------------------------------------
# PDW-AUTH-1 — unauthenticated: 401 JSON, no redirect
# ---------------------------------------------------------------------------


def test_conversation_endpoint_requires_login_401_json(client):
    """No session -> GET /conversations/{id} answers 401 JSON, never a 302."""
    resp = client.get("/panel/api/conversations/1", follow_redirects=False)

    assert resp.status_code == 401
    assert "location" not in resp.headers, "must not redirect (PDW-AUTH-1)"
    assert resp.headers["content-type"].startswith("application/json"), (
        "error must be JSON (PDW-API-3)"
    )
    assert resp.json() == {"detail": "unauthorized"}
    assert "access-control-allow-origin" not in resp.headers, "no CORS (D1)"


# ---------------------------------------------------------------------------
# PDW-API — GET /conversations/{id}: conversation + chronological messages
# ---------------------------------------------------------------------------


def test_conversation_returns_metadata_and_messages_chronological(client, make_user):
    _, conversation_id = _seed_conversation()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get(f"/panel/api/conversations/{conversation_id}", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"conversation", "messages"}
    # conversation metadata: snake_case service keys, ISO-8601, no ORM leak
    conversation = body["conversation"]
    assert conversation["id"] == conversation_id
    assert conversation["state"] == "human"
    assert conversation["summary"] == "needs visita"
    assert conversation["customer_id"] is not None
    datetime.fromisoformat(conversation["created_at"])  # ISO-8601 parseable
    # messages: chronological (created_at then id), media_url as plain URL
    messages = body["messages"]
    assert len(messages) == 3
    assert [m["text"] for m in messages] == [
        "hola, mi calefont no enciende",
        "te ayudo con eso",
        "foto de la instalación",
    ]
    assert messages[0]["direction"] == "inbound"
    assert messages[0]["msg_type"] == "text"
    assert [m["created_at"] for m in messages] == sorted(m["created_at"] for m in messages)
    # media link renders as a URL on the message that carries it (PDW-TST-3 pattern)
    media_message = messages[2]
    assert media_message["media_url"] == "https://example.com/media/photo.jpg"
    assert media_message["msg_type"] == "image"


def test_conversation_messages_keep_order_by_id_when_timestamps_tie(client, make_user):
    """Two messages in the same second still render in insertion order (id asc)."""
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56922223333", name="Pedro Soto")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone="+56922223333")
        session.add(conversation)
        session.flush()
        # Same created_at slice written in reverse message order intentionally.
        session.add(
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                text="reviso con mi colega",
            )
        )
        session.add(
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="mensaje primero en id",
            )
        )
        conversation_id = conversation.id
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get(f"/panel/api/conversations/{conversation_id}", follow_redirects=False)

    assert resp.status_code == 200
    texts = [m["text"] for m in resp.json()["messages"]]
    assert texts == ["reviso con mi colega", "mensaje primero en id"]


def test_conversation_no_messages_returns_empty_list(client, make_user):
    """A conversation with zero messages still answers 200 with an empty list."""
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56933334444", name="Lucía Pérez")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone="+56933334444")
        session.add(conversation)
        session.flush()
        conversation_id = conversation.id
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get(f"/panel/api/conversations/{conversation_id}", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json()["messages"] == []
    assert resp.json()["conversation"]["id"] == conversation_id


def test_conversation_missing_returns_404_json(client, make_user):
    """Missing conversation -> 404 {"detail":"conversation not found"} (PDW-API-3)."""
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/conversations/999999", follow_redirects=False)

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "conversation not found"}
