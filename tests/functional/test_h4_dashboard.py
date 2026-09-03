"""AD-1/AD-2 dashboard contracts."""

from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import Case, Conversation, ConversationState, Customer, Message, MessageDirection, MessageType


PERIOD = {"start": "2026-08-01T04:00:00Z", "end": "2026-08-04T04:00:00Z", "timezone": "America/Santiago"}


def _login(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    response = client.post("/panel/api/login", json={"username": "oper", "password": "oper-pass"})
    assert response.status_code == 200


def _seed_case(created_at: datetime) -> None:
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56911112222", name="Ana")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164, state=ConversationState.BOT)
        session.add(conversation)
        session.flush()
        session.add_all([
            Message(conversation_id=conversation.id, direction=MessageDirection.INBOUND, msg_type=MessageType.TEXT, text="hola", created_at=created_at),
            Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont", status="abierto", created_at=created_at),
        ])
        session.commit()


def test_dashboard_summary_is_timezone_aware_and_aggregates_operational_data(client, make_user):
    _seed_case(datetime(2026, 8, 2, 15, 0, tzinfo=timezone.utc))
    _login(client, make_user)
    response = client.get("/panel/api/dashboard/summary", params=PERIOD)
    assert response.status_code == 200
    body = response.json()
    assert body["period"] == PERIOD
    assert body["metrics"]["contacts"] == 1
    assert body["metrics"]["cases"] == 1
    assert body["metrics"]["appointments"] == 0
    assert "notification_health" in body["metrics"]
    assert "automation_outcomes" in body["metrics"]


def test_dashboard_rejects_invalid_or_unbounded_period_before_query(client, make_user):
    _login(client, make_user)
    response = client.get("/panel/api/dashboard/summary", params={"start": "2026-08-04T00:00:00Z", "end": "2026-08-01T00:00:00Z", "timezone": "UTC"})
    assert response.status_code == 422
    assert "period" in response.json()["detail"].lower()


def test_dashboard_trend_zero_fills_buckets_and_drilldown_matches_bucket(client, make_user):
    _seed_case(datetime(2026, 8, 2, 15, 0, tzinfo=timezone.utc))
    _login(client, make_user)
    trend = client.get("/panel/api/dashboard/trend", params={**PERIOD, "metric": "cases", "bucket": "day"})
    assert trend.status_code == 200
    assert trend.json()["buckets"] == [{"start": "2026-08-01", "count": 0}, {"start": "2026-08-02", "count": 1}, {"start": "2026-08-03", "count": 0}]
    drilldown = client.get("/panel/api/dashboard/drilldown", params={**PERIOD, "metric": "cases", "bucket_start": "2026-08-02"})
    assert drilldown.status_code == 200
    assert [row["service"] for row in drilldown.json()["rows"]] == ["calefont"]
