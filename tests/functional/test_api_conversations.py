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

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

from fastapi import HTTPException
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AuditLog,
    Conversation,
    ConversationState,
    Customer,
    Message,
    MessageDirection,
    MessageType,
    User,
)
from app.services.conversations import change_state


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


def test_conversations_list_requires_login_401_json(client):
    """No session -> GET /conversations answers 401 JSON, never a 302."""
    resp = client.get("/panel/api/conversations", follow_redirects=False)

    assert resp.status_code == 401
    assert "location" not in resp.headers
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "unauthorized"}


# ---------------------------------------------------------------------------
# PDW-API — GET /conversations/{id}: conversation + chronological messages
# ---------------------------------------------------------------------------


def test_conversations_list_returns_serialized_rows_in_activity_order(client, make_user):
    """List is envelope-shaped, read-only, and ordered with nulls last."""
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56944445555", name="Sofía Rojas")
        session.add(customer)
        session.flush()
        rows = [
            Conversation(
                customer_id=customer.id,
                wa_phone=customer.phone_e164,
                last_message_at=datetime(2026, 8, 24, 12, tzinfo=timezone.utc),
            ),
            Conversation(
                customer_id=customer.id,
                wa_phone=customer.phone_e164,
                last_message_at=datetime(2026, 8, 24, 12, tzinfo=timezone.utc),
            ),
            Conversation(customer_id=customer.id, wa_phone=customer.phone_e164),
            Conversation(
                customer_id=customer.id,
                wa_phone=customer.phone_e164,
                last_message_at=datetime(2026, 8, 24, 13, tzinfo=timezone.utc),
            ),
        ]
        session.add_all(rows)
        session.flush()
        expected_ids = [rows[3].id, rows[1].id, rows[0].id, rows[2].id]
        session.commit()

    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/conversations", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"conversations"}
    assert [row["id"] for row in body["conversations"]] == expected_ids
    assert all(
        set(row)
        == {
            "id",
            "customer_id",
            "wa_phone",
            "state",
            "summary",
            "last_message_at",
            "created_at",
            "closed_at",
            "responsible_id",
            "version",
        }
        for row in body["conversations"]
    )
    assert body["conversations"][-1]["last_message_at"] is None


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
    assert conversation["responsible_id"] is None
    assert conversation["version"] == 0
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
    assert messages[0]["author_id"] is None
    assert messages[0]["request_id"] is None
    assert messages[0]["delivery_status"] is None
    assert messages[0]["delivery_attempts"] == 0
    assert messages[0]["delivery_error"] is None
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


def test_state_commands_require_json_auth_and_reject_stale_requests(client, make_user):
    """Commands use JSON 401 and optimistic version conflicts without mutation."""
    _, conversation_id = _seed_conversation(state=ConversationState.BOT)
    response = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "human", "expected_version": 0, "request_id": "take-1"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}

    make_user("oper", "oper-pass", role="operador")
    _login(client)
    response = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "human", "expected_version": 0, "request_id": "take-1"},
    )
    assert response.status_code == 200
    assert response.json()["conversation"]["state"] == "human"
    assert response.json()["conversation"]["responsible_id"] is not None
    assert response.json()["conversation"]["version"] == 1

    stale = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "closed", "expected_version": 0, "request_id": "close-stale"},
    )
    assert stale.status_code == 409
    assert stale.json() == {"detail": "conversation version conflict"}

    with SessionLocal() as session:
        row = session.get(Conversation, conversation_id)
        assert row.state == ConversationState.HUMAN
        assert row.version == 1
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "conversation.state_rejected")
        )
        assert audit is not None
        assert audit.after["request_id"] == "close-stale"


def test_state_command_duplicate_is_idempotent_and_payload_mismatch_conflicts(client, make_user):
    _, conversation_id = _seed_conversation(state=ConversationState.BOT)
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    payload = {"state": "human", "expected_version": 0, "request_id": "same-key"}
    first = client.post(f"/panel/api/conversations/{conversation_id}/state", json=payload)
    duplicate = client.post(f"/panel/api/conversations/{conversation_id}/state", json=payload)
    assert first.status_code == duplicate.status_code == 200
    assert duplicate.json() == first.json()

    mismatch = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "closed", "expected_version": 1, "request_id": "same-key"},
    )
    assert mismatch.status_code == 409
    assert mismatch.json() == {"detail": "request_id already used for another command"}


def test_state_commands_follow_legal_return_and_close_transitions(client, make_user):
    _, conversation_id = _seed_conversation(state=ConversationState.BOT)
    operator_id = make_user("oper", "oper-pass", role="operador")
    _login(client)

    take = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "human", "expected_version": 0, "request_id": "take"},
    )
    returned = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "bot", "expected_version": 1, "request_id": "return"},
    )
    closed = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "human", "expected_version": 2, "request_id": "take-again"},
    )
    closed = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "closed", "expected_version": 3, "request_id": "close"},
    )
    assert take.json()["conversation"]["responsible_id"] == operator_id
    assert returned.json()["conversation"]["state"] == "bot"
    assert returned.json()["conversation"]["responsible_id"] is None
    assert closed.status_code == 200
    assert closed.json()["conversation"]["state"] == "closed"


def test_assignment_enforces_owner_rules_and_audits_denials(client, make_user):
    _, conversation_id = _seed_conversation(state=ConversationState.HUMAN)
    operator_id = make_user("oper", "oper-pass", role="operador")
    other_id = make_user("other", "other-pass", role="operador")
    _login(client)

    forbidden = client.post(
        f"/panel/api/conversations/{conversation_id}/assignment",
        json={"responsible_id": other_id, "expected_version": 0, "request_id": "assign-other"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json() == {"detail": "operators may assign only themselves"}

    taken = client.post(
        f"/panel/api/conversations/{conversation_id}/assignment",
        json={"responsible_id": operator_id, "expected_version": 0, "request_id": "assign-self"},
    )
    assert taken.status_code == 200
    assert taken.json()["conversation"]["responsible_id"] == operator_id

    with SessionLocal() as session:
        inactive = session.get(User, other_id)
        inactive.active = False
        session.commit()
    make_user("admin", "admin-pass", role="admin")
    _login(client, "admin", "admin-pass")
    invalid = client.post(
        f"/panel/api/conversations/{conversation_id}/assignment",
        json={"responsible_id": other_id, "expected_version": 1, "request_id": "inactive"},
    )
    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "assignment target must be an active operator"}


def test_list_supports_state_and_assignee_filters(client, make_user):
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56977778888")
        session.add(customer)
        session.flush()
        rows = [
            Conversation(customer_id=customer.id, wa_phone=customer.phone_e164, state=ConversationState.BOT),
            Conversation(customer_id=customer.id, wa_phone=customer.phone_e164, state=ConversationState.HUMAN),
        ]
        session.add_all(rows)
        session.flush()
        operator = User(username="filter-oper", password_hash="unused", role="operador")
        session.add(operator)
        session.flush()
        rows[1].responsible_id = operator.id
        session.commit()
        human_id, operator_id = rows[1].id, operator.id
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    state = client.get("/panel/api/conversations?state=human")
    assignee = client.get(f"/panel/api/conversations?responsible_id={operator_id}")
    assert [row["id"] for row in state.json()["conversations"]] == [human_id]
    assert [row["id"] for row in assignee.json()["conversations"]] == [human_id]


def test_command_contract_rejects_missing_preconditions_as_json_422(client, make_user):
    _, conversation_id = _seed_conversation(state=ConversationState.BOT)
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    response = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "human", "expected_version": -1, "request_id": ""},
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")


def test_illegal_transition_is_rejected_and_audited(client, make_user):
    _, conversation_id = _seed_conversation(state=ConversationState.BOT)
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    response = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "closed", "expected_version": 0, "request_id": "illegal"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "illegal conversation state transition"}
    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        audit = session.scalar(
            select(AuditLog).where(AuditLog.after["request_id"].as_string() == "illegal")
        )
        assert conversation.state == ConversationState.BOT
        assert conversation.version == 0
        assert audit.action == "conversation.state_rejected"


def test_nonexistent_assignment_target_is_rejected_and_audited(client, make_user):
    _, conversation_id = _seed_conversation()
    make_user("admin", "admin-pass", role="admin")
    _login(client, "admin", "admin-pass")

    response = client.post(
        f"/panel/api/conversations/{conversation_id}/assignment",
        json={"responsible_id": 999999, "expected_version": 0, "request_id": "missing-target"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "assignment target must be an active operator"}
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.after["request_id"].as_string() == "missing-target"
            )
        )
        assert audit.action == "conversation.assignment_rejected"


def test_successful_command_is_audited(client, make_user):
    _, conversation_id = _seed_conversation(state=ConversationState.BOT)
    operator_id = make_user("oper", "oper-pass", role="operador")
    _login(client)

    response = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "human", "expected_version": 0, "request_id": "audited-take"},
    )

    assert response.status_code == 200
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.after["request_id"].as_string() == "audited-take"
            )
        )
        assert audit.action == "conversation.state_changed"
        assert audit.actor == "oper"
        assert audit.after["responsible_id"] == operator_id


def test_mismatched_request_id_is_rejected_and_audited(client, make_user):
    _, conversation_id = _seed_conversation(state=ConversationState.BOT)
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    payload = {"state": "human", "expected_version": 0, "request_id": "reused"}
    assert client.post(f"/panel/api/conversations/{conversation_id}/state", json=payload).status_code == 200

    response = client.post(
        f"/panel/api/conversations/{conversation_id}/state",
        json={"state": "closed", "expected_version": 1, "request_id": "reused"},
    )

    assert response.status_code == 409
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.after["request_id"].as_string() == "reused",
                AuditLog.after["detail"].as_string()
                == "request_id already used for another command",
            )
        )
        assert audit is not None
        assert audit.action == "conversation.request_rejected"


def test_concurrent_state_commands_serialize_on_conversation_row(make_user):
    _, conversation_id = _seed_conversation(state=ConversationState.BOT)
    first_id = make_user("first", "first-pass", role="operador")
    second_id = make_user("second", "second-pass", role="operador")
    barrier = Barrier(2)

    def submit(actor_id: int):
        with SessionLocal() as session:
            actor = session.get(User, actor_id)
            barrier.wait()
            try:
                change_state(
                    session, conversation_id, actor, ConversationState.HUMAN, 0,
                    f"race-{actor_id}",
                )
                session.commit()
                return "ok"
            except HTTPException as error:
                session.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, (first_id, second_id)))

    assert set(results) == {"ok", 409}
    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        assert conversation.state == ConversationState.HUMAN
        assert conversation.version == 1
