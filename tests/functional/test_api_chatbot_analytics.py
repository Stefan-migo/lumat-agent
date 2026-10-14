"""Panel JSON API chatbot analytics (Frente 2, unit 5 — UI).

Admin-only read-only JSON wrappers over `app/services/analytics.py`
(`chatbot_metrics`, `chatbot_conversations`) — no new business logic:

- GET /panel/api/analytics/chatbot               -> chatbot_metrics(window_days)
- GET /panel/api/analytics/chatbot/conversations -> chatbot_conversations(window_days, signal, limit)

Role enforcement server-side (PDW-API-4): admin 200, operador -> 403 JSON
{"detail":"admin role required"}; unauthenticated -> 401 JSON
{"detail":"unauthorized"} with no redirect (PDW-AUTH-1). Errors are always
JSON {"detail": ...} (PDW-API-3).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import (
    Conversation,
    ConversationEvent,
    ConversationState,
    Message,
    MessageDirection,
)
from app.services.customers import get_or_create_customer


def _login(client, username: str, password: str) -> None:
    resp = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"


def _seed_metrics_fixture() -> None:
    """One handed-off conversation + one contained conversation inside the window."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56911110001")
        handed_off = Conversation(
            customer_id=customer.id, wa_phone="+56911110001",
            state=ConversationState.CLOSED, closed_at=now - timedelta(days=1),
        )
        contained = Conversation(
            customer_id=customer.id, wa_phone="+56911110001",
            state=ConversationState.CLOSED, closed_at=now - timedelta(days=2),
        )
        session.add_all([handed_off, contained])
        session.flush()
        session.add_all([
            Message(
                conversation_id=handed_off.id, direction=MessageDirection.INBOUND,
                created_at=now - timedelta(days=1), cost_llm=0.2, cost_meta=0.1,
            ),
            Message(
                conversation_id=contained.id, direction=MessageDirection.INBOUND,
                created_at=now - timedelta(days=2), cost_llm=0.2, cost_meta=0.0,
            ),
            ConversationEvent(
                conversation_id=handed_off.id, event="escalation",
                cause="handoff:kb_miss", created_at=now - timedelta(days=1),
            ),
            ConversationEvent(
                conversation_id=contained.id, event="unknown_intent",
                created_at=now - timedelta(days=2),
            ),
        ])
        session.commit()


def test_chatbot_metrics_endpoint_returns_service_shape(client, make_user):
    _seed_metrics_fixture()
    make_user("adm", "adm-pass", role="admin")
    _login(client, "adm", "adm-pass")

    resp = client.get("/panel/api/analytics/chatbot?window_days=7", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert body["conversations"] == 2
    assert body["handoffs"] == 1
    assert body["handoff_rate"] == 0.5
    assert body["containment_rate"] == 0.5
    assert body["handoff_reasons"] == {"kb_miss": 1}
    assert body["unknown_intents"] == 1
    assert body["window_days"] == 7


def test_chatbot_metrics_endpoint_defaults_window_to_seven(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client, "adm", "adm-pass")

    resp = client.get("/panel/api/analytics/chatbot", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json()["window_days"] == 7


def test_chatbot_conversations_endpoint_filters_by_signal(client, make_user):
    _seed_metrics_fixture()
    make_user("adm", "adm-pass", role="admin")
    _login(client, "adm", "adm-pass")

    resp = client.get(
        "/panel/api/analytics/chatbot/conversations?signal=unknown_intent&window_days=7",
        follow_redirects=False,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["signal"] == "unknown_intent"
    assert body["window_days"] == 7
    assert len(body["conversations"]) == 1
    row = body["conversations"][0]
    assert row["signals"]["unknown_intent"] == 1
    assert row["signals"]["escalation"] == 0


def test_chatbot_conversations_endpoint_refuses_unknown_signal(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client, "adm", "adm-pass")

    resp = client.get(
        "/panel/api/analytics/chatbot/conversations?signal=bogus", follow_redirects=False
    )

    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")


def test_chatbot_analytics_endpoints_denied_403_for_operador_json(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")

    for path in (
        "/panel/api/analytics/chatbot",
        "/panel/api/analytics/chatbot/conversations",
    ):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 403, f"GET {path} must be 403 for operador"
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json() == {"detail": "admin role required"}


def test_chatbot_analytics_endpoints_unauthenticated_401_json(client):
    for path in (
        "/panel/api/analytics/chatbot",
        "/panel/api/analytics/chatbot/conversations",
    ):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 401, f"GET {path} must be 401 unauthenticated"
        assert "location" not in resp.headers, f"{path} must not redirect (PDW-AUTH-1)"
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json() == {"detail": "unauthorized"}
