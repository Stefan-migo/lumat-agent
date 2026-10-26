"""Inbound media is stored with its metadata and served by an authenticated endpoint.

The endpoint must serve the stored bytes for the owning conversation and refuse a
missing file, another conversation's message, and a stored path outside the media
directory (a path-traversal attempt in the database must never leak a file).
"""

from types import SimpleNamespace

import httpx
import respx
from sqlalchemy import select

from app.config import get_settings

from app.db import SessionLocal
from app.models import Conversation, Customer, Message, MessageDirection, MessageStatus, MessageType
from app.webhook import ingest


def _login(client):
    from app.models import User, UserRole
    from app.services.users import hash_password
    with SessionLocal() as session:
        session.add(User(username="oper", password_hash=hash_password("oper-pass"), role=UserRole.OPERADOR, active=True))
        session.commit()
    assert client.post("/panel/api/login", json={"username": "oper", "password": "oper-pass"}).status_code == 200


def _seed_media_message():
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56977776666")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        message = Message(wamid="wamid.endpoint", conversation_id=conversation.id,
                          direction=MessageDirection.INBOUND, msg_type=MessageType.IMAGE,
                          media_url="https://lookaside.example/photo", status=MessageStatus.RECEIVED)
        session.add(message)
        session.commit()
        return conversation.id, message.id


def test_downloaded_media_is_stored_and_served_inline(
    client, monkeypatch, tmp_path, migrated_db, mock_openai_chat, mock_meta_send
):
    conversation_id, message_id = _seed_media_message()
    # Both sides must agree on the directory: ingest writes the file and the route
    # serves it only when the stored path resolves inside `settings.media_dir`.
    monkeypatch.setattr(ingest, "get_settings", lambda: SimpleNamespace(
        media_dir=get_settings().media_dir, meta_access_token="test-token"
    ))
    with respx.mock:
        respx.get("https://lookaside.example/photo").mock(
            return_value=httpx.Response(200, content=b"photo-bytes", headers={"content-type": "image/jpeg; charset=binary"})
        )
        ingest.sweep_received()
    _login(client)
    response = client.get(f"/panel/api/conversations/{conversation_id}/messages/{message_id}/media")
    assert response.status_code == 200
    assert response.content == b"photo-bytes"
    assert response.headers["content-type"] == "image/jpeg"
    assert "inline" in response.headers["content-disposition"]
    thread = client.get(f"/panel/api/conversations/{conversation_id}").json()
    item = next(row for row in thread["messages"] if row["id"] == message_id)
    assert item["media_available"] is True
    assert item["media_download_url"].endswith(f"/{message_id}/media")


def test_media_endpoint_rejects_wrong_conversation_missing_and_outside_path(
    client, monkeypatch, tmp_path, migrated_db
):
    conversation_id, message_id = _seed_media_message()
    outside = tmp_path.parent / "secret.bin"
    outside.write_bytes(b"do-not-serve")
    _login(client)
    assert client.get(f"/panel/api/conversations/{conversation_id}/messages/{message_id}/media").status_code == 404
    with SessionLocal() as session:
        customer_id = session.scalar(select(Customer.id).where(Customer.phone_e164 == "+56977776666"))
        other = Conversation(customer_id=customer_id, wa_phone="+56977776666")
        session.add(other)
        session.commit()
        other_id = other.id
    assert client.get(f"/panel/api/conversations/{other_id}/messages/{message_id}/media").status_code == 404
    monkeypatch.setattr(
        "app.panel.api.routes.conversations.get_settings",
        lambda: SimpleNamespace(media_dir=str(tmp_path)),
    )
    with SessionLocal() as session:
        row = session.get(Message, message_id)
        row.stored_path = str(outside)
        session.commit()
    assert client.get(f"/panel/api/conversations/{conversation_id}/messages/{message_id}/media").status_code == 404
