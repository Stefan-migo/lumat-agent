from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import NotificationOperation


def test_notification_status_is_authenticated_and_retryable(client, make_user):
    with SessionLocal() as session:
        operation = NotificationOperation(
            recipient="+56911112222", channel="whatsapp", content="Visit reminder",
            source_entity="appointment", source_id="42", idempotency_key=f"test:operation:{datetime.now().timestamp()}",
            status="retryable", attempts=1, error="provider unavailable",
            next_attempt_at=datetime.now(timezone.utc),
        )
        session.add(operation)
        session.commit()
        operation_id = operation.id

    assert client.get("/panel/api/notification-operations").status_code == 401
    make_user("notification-oper", "notification-pass", role="operador")
    assert client.post("/panel/api/login", json={"username": "notification-oper", "password": "notification-pass"}).status_code == 200

    response = client.get("/panel/api/notification-operations")

    assert response.status_code == 200
    item = next(row for row in response.json()["operations"] if row["id"] == operation_id)
    assert item["status"] == "retryable"
    assert item["action"] == "retry"
    retried = client.post(f"/panel/api/notification-operations/{operation_id}/retry")
    assert retried.status_code == 200
    assert retried.json()["operation"]["status"] == "pending"
