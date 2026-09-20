"""Authenticated panel WebSocket contract (CRT-1, CRT-2, CRT-3)."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from starlette.testclient import WebSocketDenialResponse
from starlette.websockets import WebSocket

from app.db import SessionLocal
from app.models import Case, Conversation, Customer, ConversationState
from app.panel.api.deps import get_current_user_json
from app.panel.api.routes.realtime import panel_websocket, realtime_user
from app.services.realtime import RealtimeEnvelope, publisher


def _login(client, username: str, password: str) -> None:
    response = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 200


def _seed_conversation() -> int:
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56999990000", name="Realtime Customer")
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id,
            wa_phone=customer.phone_e164,
            state=ConversationState.BOT,
        )
        session.add(conversation)
        session.commit()
        return conversation.id


def test_panel_websocket_mount_sends_snapshot_before_live_events(client, make_user):
    """An authorized panel client receives the database snapshot first."""
    conversation_id = _seed_conversation()
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")

    with client.websocket_connect("/panel/ws") as websocket:
        frame = websocket.receive_json()

        assert frame["type"] == "snapshot"
        assert frame["conversation_id"] is None
        assert frame["data"]["conversations"][0]["id"] == conversation_id
        assert frame["data"]["items"] == frame["data"]["conversations"]
        assert set(frame["data"]["counts"]) == {"all", "human", "emergency", "case", "closed"}
        assert publisher.subscriber_count == 1

    assert publisher.subscriber_count == 0


def test_panel_websocket_snapshot_has_rest_equivalent_case_context(client, make_user):
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56999990001", name="Snapshot Client")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164, summary="snapshot summary")
        session.add(conversation)
        session.flush()
        case = Case(conversation_id=conversation.id, customer_id=customer.id, emergency=True, status="escalado")
        session.add(case)
        session.commit()
        conversation_id = conversation.id
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")

    with client.websocket_connect("/panel/ws") as websocket:
        row = next(row for row in websocket.receive_json()["data"]["items"] if row["id"] == conversation_id)

    assert row["case_id"] == case.id
    assert row["emergency"] is True
    assert row["case_status"] == "escalado"


def test_admin_panel_websocket_also_receives_snapshot(client, make_user):
    """The other authorized panel role uses the same snapshot contract."""
    make_user("admin", "admin-pass", role="admin")
    _login(client, "admin", "admin-pass")

    with client.websocket_connect("/panel/ws") as websocket:
        assert websocket.receive_json()["type"] == "snapshot"


def test_panel_websocket_rejects_missing_session(client):
    """A missing session is denied during the WebSocket handshake."""
    with pytest.raises(WebSocketDenialResponse) as denied:
        with client.websocket_connect("/panel/ws"):
            pass

    assert denied.value.status_code == 401


def test_panel_websocket_rejects_unauthorized_role(client):
    """A session whose role is outside the panel role set is denied."""
    app = client.app
    app.dependency_overrides[get_current_user_json] = lambda: SimpleNamespace(
        role=SimpleNamespace(value="viewer"), active=True
    )
    try:
        with pytest.raises(WebSocketDenialResponse) as denied:
            with client.websocket_connect("/panel/ws"):
                pass
    finally:
        app.dependency_overrides.pop(get_current_user_json, None)

    assert denied.value.status_code == 403


def test_tecnico_websocket_is_denied(client, make_user):
    make_user("tech", "tech-pass", role="tecnico")
    _login(client, "tech", "tech-pass")

    with pytest.raises(WebSocketDenialResponse) as denied:
        with client.websocket_connect("/panel/ws"):
            pass

    assert denied.value.status_code == 403


def _operator() -> SimpleNamespace:
    """The minimal `current` the handler's role guard reads."""
    return SimpleNamespace(role=SimpleNamespace(value="operador"), active=True)


def _socket_whose_peer_disconnects() -> tuple[WebSocket, list[dict]]:
    """A starlette WebSocket whose peer shakes hands and then leaves.

    Frame one is the handshake `accept()` consumes; frame two is the disconnect.
    A closed socket never speaks again, and neither does this one.
    """
    sent: list[dict] = []
    calls = 0

    async def receive() -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"type": "websocket.connect"}
        return {"type": "websocket.disconnect", "code": 1000}

    async def send(message: dict) -> None:
        sent.append(message)

    scope = {
        "type": "websocket",
        "path": "/panel/ws",
        "raw_path": b"/panel/ws",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("panel", 1000),
        "server": ("api", 8000),
        "state": {},
        "subprotocols": [],
    }
    return WebSocket(scope, receive=receive, send=send), sent


def test_panel_websocket_task_ends_when_the_client_disconnects():
    """The handler must end on its own once the peer is gone.

    `test_panel_websocket_mount_sends_snapshot_before_live_events` cannot see
    this. It asserts `subscriber_count == 0` and passes with the bug live,
    because starlette's `WebSocketTestSession` cancels the ASGI task when its
    `with` block exits (`starlette/testclient.py` registers `portal.call(cs.cancel)`
    in its ExitStack) — so a handler that never ends still looks finished.

    Here the handler is driven directly and nothing cancels it: if it does not
    return on its own, `wait_for` is the failure. A task left parked past the
    connection is what makes `uvicorn --reload` wait forever at shutdown.
    """
    websocket, sent = _socket_whose_peer_disconnects()

    async def drive() -> None:
        with SessionLocal() as session:
            await asyncio.wait_for(
                panel_websocket(websocket, session, _operator()), timeout=5
            )

    asyncio.run(drive())

    assert sent[0] == {"type": "websocket.accept", "subprotocol": None, "headers": []}
    assert json.loads(sent[1]["text"])["type"] == "snapshot"
    assert publisher.subscriber_count == 0


def test_published_envelope_reaches_the_attached_client(client, make_user):
    """A characterization lock, not this unit's RED: it passes before and after.

    Nothing drove `publisher.publish` through the handler to a client frame —
    the forwarding loop was uncovered — and that is the loop this change
    rewrites. It stays a lock on the wire contract: same envelopes, in order,
    to an attached authorized client.
    """
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")

    with client.websocket_connect("/panel/ws") as websocket:
        assert websocket.receive_json()["type"] == "snapshot"

        websocket.portal.call(
            publisher.publish,
            RealtimeEnvelope(type="message", conversation_id=7, data={"n": 1}),
        )

        assert websocket.receive_json() == {
            "type": "message",
            "conversation_id": 7,
            "data": {"n": 1},
        }

    assert publisher.subscriber_count == 0
