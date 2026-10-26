from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import respx
from fastapi import HTTPException
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Conversation, ConversationState, Customer, DeliveryStatus, Message, MessageDirection, MessageStatus, MessageType, User, UserRole
from app.services.conversations import send_operator_media
from app.services.users import hash_password


def _seed(inbound_age=timedelta(minutes=5), state=ConversationState.HUMAN):
    with SessionLocal() as session:
        actor = session.scalar(select(User).where(User.username == "operator-media"))
        if actor is None:
            actor = User(username="operator-media", password_hash=hash_password("pass"), role=UserRole.OPERADOR)
            session.add(actor)
        customer = Customer(phone_e164=f"+569{datetime.now().microsecond:09d}", name="Ana")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164, state=state)
        session.add(conversation)
        session.flush()
        session.add(Message(conversation_id=conversation.id, direction=MessageDirection.INBOUND, msg_type=MessageType.TEXT, text="hola", status=MessageStatus.PROCESSED, created_at=datetime.now(timezone.utc)-inbound_age))
        session.commit()
        return actor.id, conversation.id


def _send(actor_id, conversation_id, path, request_id="media-1", content_type="image/png"):
    with SessionLocal() as session:
        return send_operator_media(session, conversation_id, path=path, content_type=content_type, filename=path.name, caption="hola", actor=session.get(User, actor_id), request_id=request_id)


def test_operator_image_upload_then_send_records_delivery_and_cost(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "media_dir", str(tmp_path / "media"))
    actor_id, conversation_id = _seed()
    source = tmp_path / "foto.png"
    source.write_bytes(b"image bytes")
    with respx.mock(base_url="https://graph.facebook.com") as router:
        upload = router.post("/v20.0/123456789/media").mock(return_value=httpx.Response(200, json={"id": "media-id"}))
        message = router.post("/v20.0/123456789/messages").mock(return_value=httpx.Response(200, json={"messages": [{"id": "wamid.media"}]}))
        row = _send(actor_id, conversation_id, source)
    assert upload.call_count == message.call_count == 1
    assert upload.calls[0].request.headers["authorization"] == "Bearer meta-test-token"
    assert b"image/png" in upload.calls[0].request.content
    assert b"media-id" in message.calls[0].request.content
    assert b'"type":"image"' in message.calls[0].request.content
    assert row.delivery_status == DeliveryStatus.SENT and row.wamid == "wamid.media"
    assert row.cost_meta is not None


def test_media_delivery_never_falls_back_to_empty_text(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "media_dir", str(tmp_path / "media"))
    actor_id, conversation_id = _seed()
    source = tmp_path / "image.png"
    source.write_bytes(b"x")
    with respx.mock(base_url="https://graph.facebook.com") as router:
        router.post("/v20.0/123456789/media").mock(return_value=httpx.Response(200, json={"id": "mid"}))
        send_route = router.post("/v20.0/123456789/messages").mock(return_value=httpx.Response(200, json={"messages": [{"id": "wid"}]}))
        _send(actor_id, conversation_id, source)
    assert b'"type":"text"' not in send_route.calls[0].request.content


def test_retry_reuses_uploaded_meta_media_id(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "media_dir", str(tmp_path / "media"))
    actor_id, conversation_id = _seed()
    source = tmp_path / "image.png"
    source.write_bytes(b"x")
    with respx.mock(base_url="https://graph.facebook.com") as router:
        upload = router.post("/v20.0/123456789/media").mock(return_value=httpx.Response(200, json={"id": "mid"}))
        sends = router.post("/v20.0/123456789/messages").mock(side_effect=[httpx.Response(400, json={"error": {"message": "no"}}), httpx.Response(200, json={"messages": [{"id": "wid"}]})])
        # A failed Meta send is recorded on the row (the text path behaves the same way);
        # the retry endpoint is what surfaces the failure to the operator.
        _send(actor_id, conversation_id, source)
        with SessionLocal() as session:
            row = session.scalar(select(Message).where(Message.request_id == "media-1"))
            assert row.delivery_status == DeliveryStatus.FAILED
            assert row.meta_media_id == "mid"
            row_id = row.id
        from app.services.conversations import retry_operator_message
        with SessionLocal() as session:
            row = session.get(Message, row_id)
            retry_operator_message(session, conversation_id, row_id, session.get(User, actor_id), "retry-1", "failed")
    assert upload.call_count == 1 and sends.call_count == 2


def test_idempotency_window_and_state_follow_text_rules(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "media_dir", str(tmp_path / "media"))
    actor_id, conversation_id = _seed(inbound_age=timedelta(hours=24, seconds=1))
    source = tmp_path / "x.png"
    source.write_bytes(b"x")
    with respx.mock(base_url="https://graph.facebook.com") as router:
        with pytest.raises(HTTPException) as error:
            _send(actor_id, conversation_id, source)
    assert error.value.status_code == 422 and error.value.detail == "customer reply window expired"
    assert not router.calls
    actor_id, conversation_id = _seed(state=ConversationState.BOT)
    with pytest.raises(HTTPException) as error:
        _send(actor_id, conversation_id, source, "not-human")
    assert error.value.status_code == 422 and error.value.detail == "operator messages require human conversation"


def test_missing_stored_media_fails_closed_without_meta(monkeypatch):
    from app.services.send import deliver_message
    actor_id, conversation_id = _seed()
    with SessionLocal() as session:
        row = Message(conversation_id=conversation_id, author_id=actor_id, request_id="missing", direction=MessageDirection.OUTBOUND, msg_type=MessageType.IMAGE, status=MessageStatus.PROCESSED, delivery_status=DeliveryStatus.PENDING)
        session.add(row)
        session.commit()
        row_id = row.id
    with respx.mock(base_url="https://graph.facebook.com") as router:
        row = deliver_message(row_id)
    assert row.delivery_status == DeliveryStatus.FAILED and row.delivery_error
    assert not router.calls


def test_oversized_media_rejected_before_meta(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "media_dir", str(tmp_path / "media"))
    actor_id, conversation_id = _seed()
    source = tmp_path / "huge.png"
    source.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    with respx.mock(base_url="https://graph.facebook.com") as router:
        with pytest.raises(ValueError, match="5 MB"):
            _send(actor_id, conversation_id, source)
    assert not router.calls
