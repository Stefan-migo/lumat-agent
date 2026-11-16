from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import NotificationOperation


def test_notification_operations_and_retry_are_admin_only(client, make_user):
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

    operations_url = "/panel/api/notification-operations"
    retry_url = f"{operations_url}/{operation_id}/retry"
    assert client.get(operations_url).status_code == 401

    for role in ("operador", "tecnico"):
        username = f"notification-{role}"
        password = f"notification-{role}-pass"
        make_user(username, password, role=role)
        assert client.post("/panel/api/login", json={"username": username, "password": password}).status_code == 200
        assert client.get(operations_url).status_code == 403
        assert client.post(retry_url).status_code == 403
        client.post("/panel/api/logout")

    make_user("notification-admin", "notification-admin-pass", role="admin")
    assert client.post("/panel/api/login", json={"username": "notification-admin", "password": "notification-admin-pass"}).status_code == 200
    response = client.get(operations_url)
    assert response.status_code == 200
    item = next(row for row in response.json()["operations"] if row["id"] == operation_id)
    assert item["status"] == "retryable"
    assert item["action"] == "retry"
    retried = client.post(retry_url)
    assert retried.status_code == 200
    assert retried.json()["operation"]["status"] == "pending"


def test_notification_operations_pagination_and_stable_order(client, make_user):
    with SessionLocal() as session:
        for index in range(51):
            session.add(NotificationOperation(
                recipient="ops", channel="email", content=f"Operation {index}",
                source_entity="appointment", source_id=str(index),
                idempotency_key=f"page:{index}", status="sent",
                next_attempt_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ))
        session.commit()
        expected = session.query(NotificationOperation.id).order_by(
            NotificationOperation.created_at.desc(), NotificationOperation.id.desc()
        ).all()
        expected_ids = [row[0] for row in expected]

    make_user("pagination-admin", "pagination-pass", role="admin")
    assert client.post("/panel/api/login", json={"username": "pagination-admin", "password": "pagination-pass"}).status_code == 200
    default_page = client.get("/panel/api/notification-operations")
    assert default_page.status_code == 200
    default_ids = [row["id"] for row in default_page.json()["operations"]]
    assert len(default_ids) == 50
    assert default_ids == expected_ids[:50]
    assert client.get("/panel/api/notification-operations?limit=201").status_code == 422
    page = client.get("/panel/api/notification-operations?limit=10&offset=10")
    assert page.status_code == 200
    assert [row["id"] for row in page.json()["operations"]] == expected_ids[10:20]


def test_push_subscription_for_same_user_updates_existing_keys(client, make_user):
    make_user("push-same-owner", "push-same-pass", role="tecnico")
    assert client.post("/panel/api/login", json={"username": "push-same-owner", "password": "push-same-pass"}).status_code == 200
    body = {"endpoint": "https://push.example.test/same-owner", "p256dh": "first", "auth": "first"}
    assert client.post("/panel/api/push-subscription", json=body).status_code == 200
    response = client.post("/panel/api/push-subscription", json={**body, "p256dh": "updated", "auth": "updated"})
    assert response.status_code == 200
    with SessionLocal() as session:
        from app.models import PushSubscription
        rows = session.query(PushSubscription).filter_by(endpoint=body["endpoint"]).all()
        assert len(rows) == 1
        assert rows[0].p256dh == "updated"
        assert rows[0].auth == "updated"
        assert rows[0].active is True


def test_push_subscription_endpoint_cannot_be_claimed_from_another_user(client, make_user):
    make_user("push-original", "push-original-pass", role="tecnico")
    make_user("push-claimant", "push-claimant-pass", role="operador")
    with SessionLocal() as session:
        from app.models import PushSubscription, User
        owner = session.query(User).filter_by(username="push-original").one()
        session.add(PushSubscription(
            user_id=owner.id, endpoint="https://push.example.test/owned", p256dh="old-key", auth="old-auth"
        ))
        session.commit()
        original_user_id = owner.id

    assert client.post("/panel/api/login", json={"username": "push-claimant", "password": "push-claimant-pass"}).status_code == 200
    response = client.post("/panel/api/push-subscription", json={
        "endpoint": "https://push.example.test/owned", "p256dh": "new-key", "auth": "new-auth"
    })
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "push_subscription_owned_by_another_user"
    with SessionLocal() as session:
        from app.models import PushSubscription
        row = session.query(PushSubscription).filter_by(endpoint="https://push.example.test/owned").one()
        assert row.user_id == original_user_id
