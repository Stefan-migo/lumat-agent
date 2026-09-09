"""Authenticated panel WebSocket contract (CRT-1, CRT-2, CRT-3)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from starlette.testclient import WebSocketDenialResponse

from app.db import SessionLocal
from app.models import Conversation, Customer, ConversationState
from app.panel.api.deps import get_current_user_json
from app.panel.api.routes.realtime import realtime_user
from app.services.realtime import publisher


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
        assert publisher.subscriber_count == 1

    assert publisher.subscriber_count == 0


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
