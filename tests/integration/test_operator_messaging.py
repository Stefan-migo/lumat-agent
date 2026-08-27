"""OM-1..OM-4 integration contracts for operator Meta delivery."""

from datetime import datetime, timedelta, timezone
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import httpx
import pytest
import respx
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    AuditLog,
    Conversation,
    ConversationState,
    Customer,
    DeliveryStatus,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    User,
    UserRole,
)
from app.services.users import hash_password
from app.services.conversations import send_operator_message
def _seed(operator_role=UserRole.OPERADOR, inbound_age=timedelta(minutes=5), phone="+56912345678"):
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == "operator"))
        if user is None:
            user = User(username="operator", password_hash=hash_password("pass"), role=operator_role)
            session.add(user)
        customer = Customer(phone_e164=phone, name="Ana")
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id,
            wa_phone=customer.phone_e164,
            state=ConversationState.HUMAN,
            last_message_at=datetime.now(timezone.utc),
        )
        session.add(conversation)
        session.flush()
        inbound = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text="Necesito ayuda",
            status=MessageStatus.PROCESSED,
            created_at=datetime.now(timezone.utc) - inbound_age,
        )
        session.add(inbound)
        session.commit()
        return user.id, conversation.id
def _login(client):
    response = client.post("/panel/api/login", json={"username": "operator", "password": "pass"})
    assert response.status_code == 200
def _rows(conversation_id):
    with SessionLocal() as session:
        return list(session.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)))
def test_operator_message_commits_before_exact_meta_call_without_secret_logging(client, caplog):
    _, conversation_id = _seed()
    _login(client)
    observed = []
    with respx.mock(base_url="https://graph.facebook.com") as router:
        def send(request):
            observed.extend(_rows(conversation_id))
            return httpx.Response(200, json={"messages": [{"id": "wamid.operator"}]})
        route = router.post("/v20.0/123456789/messages").mock(side_effect=send)
        with caplog.at_level(logging.DEBUG):
            response = client.post(
                f"/panel/api/conversations/{conversation_id}/messages",
                json={"text": "Voy en camino", "request_id": "reply-1"},
            )
    assert response.status_code == 200
    row = [row for row in _rows(conversation_id) if row.direction == MessageDirection.OUTBOUND][0]
    assert row.author_id is not None
    assert row.request_id == "reply-1"
    assert row.delivery_status == DeliveryStatus.SENT
    assert row.wamid == "wamid.operator"
    assert row.delivery_attempts == 1
    assert observed and observed[-1].delivery_status == DeliveryStatus.SENDING
    assert route.calls[0].request.content == (
        b'{"messaging_product":"whatsapp","to":"+56912345678","type":"text","text":{"body":"Voy en camino"}}'
    )
    assert "meta-test-token" not in caplog.text


def test_latest_customer_inbound_controls_window_and_denial_is_audited(client):
    _, conversation_id = _seed(inbound_age=timedelta(hours=24, seconds=1))
    _login(client)
    response = client.post(
        f"/panel/api/conversations/{conversation_id}/messages",
        json={"text": "Todavía disponible", "request_id": "stale-1"},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "customer reply window expired"}
    assert not [row for row in _rows(conversation_id) if row.direction == MessageDirection.OUTBOUND]
    with SessionLocal() as session:
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "message.send_rejected"))
        assert audit is not None
        assert audit.after["request_id"] == "stale-1"


def test_invalid_message_is_non_mutating_and_non_human_is_rejected(client):
    _, conversation_id = _seed()
    _login(client)
    blank = client.post(
        f"/panel/api/conversations/{conversation_id}/messages",
        json={"text": "   ", "request_id": "blank-1"},
    )
    assert blank.status_code == 422
    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        conversation.state = ConversationState.BOT
        session.commit()
    closed = client.post(
        f"/panel/api/conversations/{conversation_id}/messages",
        json={"text": "No corresponde", "request_id": "bot-1"},
    )
    assert closed.status_code == 422
    assert not [row for row in _rows(conversation_id) if row.direction == MessageDirection.OUTBOUND]


def test_definite_failure_is_retryable_once_and_unknown_is_not(client):
    _, conversation_id = _seed()
    _login(client)
    with respx.mock(base_url="https://graph.facebook.com") as router:
        route = router.post("/v20.0/123456789/messages")
        route.mock(return_value=httpx.Response(400, json={"error": {"message": "invalid recipient"}}))
        failed = client.post(
            f"/panel/api/conversations/{conversation_id}/messages",
            json={"text": "Primero", "request_id": "retry-source"},
        )
        assert failed.status_code == 502
        message_id = [row for row in _rows(conversation_id) if row.direction == MessageDirection.OUTBOUND][0].id
        route.mock(return_value=httpx.Response(200, json={"messages": [{"id": "wamid.retry"}]}))
        retried = client.post(
            f"/panel/api/conversations/{conversation_id}/messages/{message_id}/retry",
            json={"request_id": "retry-1", "expected_status": "failed"},
        )
        assert retried.status_code == 200
        duplicate = client.post(
            f"/panel/api/conversations/{conversation_id}/messages/{message_id}/retry",
            json={"request_id": "retry-1", "expected_status": "failed"},
        )
        assert duplicate.status_code == 200
        assert route.call_count == 2
    row = [row for row in _rows(conversation_id) if row.direction == MessageDirection.OUTBOUND][0]
    assert row.delivery_status == DeliveryStatus.SENT
    assert row.delivery_attempts == 2
    assert row.wamid == "wamid.retry"

    _, unknown_conversation_id = _seed(phone="+56987654321")
    with respx.mock(base_url="https://graph.facebook.com") as router:
        router.post("/v20.0/123456789/messages").mock(side_effect=httpx.ReadTimeout("ambiguous"))
        unknown = client.post(
            f"/panel/api/conversations/{unknown_conversation_id}/messages",
            json={"text": "No duplicar", "request_id": "unknown-source"},
        )
        assert unknown.status_code == 502
    unknown_row = [row for row in _rows(unknown_conversation_id) if row.direction == MessageDirection.OUTBOUND][0]
    assert unknown_row.delivery_status == DeliveryStatus.UNKNOWN
    blocked = client.post(
        f"/panel/api/conversations/{unknown_conversation_id}/messages/{unknown_row.id}/retry",
        json={"request_id": "unknown-retry", "expected_status": "failed"},
    )
    assert blocked.status_code == 409
    assert blocked.json() == {"detail": "outcome unknown; manual reconciliation required"}


def test_concurrent_same_request_claims_one_meta_operation(monkeypatch):
    user_id, conversation_id = _seed()
    with SessionLocal() as session:
        actor = session.get(User, user_id)
    entered = Event()
    release = Event()
    calls = []

    def fake_send(phone, text):
        calls.append((phone, text))
        entered.set()
        release.wait(timeout=5)
        return "wamid.concurrent"

    monkeypatch.setattr("app.services.send.send_text", fake_send)

    def submit():
        with SessionLocal() as session:
            return send_operator_message(session, conversation_id, actor, "Una sola vez", "same-key")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(submit)
        assert entered.wait(timeout=5)
        second = pool.submit(submit)
        second_error = second.exception(timeout=5)
        release.set()
        first_result = first.result(timeout=5)

    assert len(calls) == 1
    assert second_error.detail == "message delivery in progress"
    assert first_result.delivery_status == DeliveryStatus.SENT
    assert len([row for row in _rows(conversation_id) if row.direction == MessageDirection.OUTBOUND]) == 1
