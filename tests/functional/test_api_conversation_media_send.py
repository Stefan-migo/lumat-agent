from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import respx
from httpx import Response
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import ConversationState, Message, MessageDirection
from tests.functional.test_api_conversations import _login, _seed_conversation


MEDIA_UPLOAD = "https://graph.facebook.com/v20.0/" + get_settings().meta_phone_number_id + "/media"
MEDIA_SEND = "https://graph.facebook.com/v20.0/" + get_settings().meta_phone_number_id + "/messages"


def _upload(client, conversation_id, request_id="media-1", content=b"png-bytes", filename="photo.png", caption="Here it is"):
    return client.post(
        f"/panel/api/conversations/{conversation_id}/media",
        data={"request_id": request_id, "caption": caption},
        files={"file": (filename, content, "image/png")},
    )


def _mock_meta(router):
    upload = router.post(MEDIA_UPLOAD).mock(return_value=Response(200, json={"id": "media-id"}))
    send = router.post(MEDIA_SEND).mock(return_value=Response(200, json={"messages": [{"id": "wamid.test"}]}))
    return upload, send


def test_operator_media_upload_delivers_and_returns_message(client, make_user):
    _, conversation_id = _seed_conversation()
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    with respx.mock(assert_all_called=True) as router:
        upload, send = _mock_meta(router)
        response = _upload(client, conversation_id)

    assert response.status_code == 200
    message = response.json()["message"]
    assert response.json()["ok"] is True
    assert message["msg_type"] == "image"
    assert message["media_download_url"].endswith(f"/conversations/{conversation_id}/messages/{message['id']}/media")
    assert b"png-bytes" in upload.calls[0].request.content
    assert b"image/png" in upload.calls[0].request.content
    assert b'"type":"image"' in send.calls[0].request.content
    with SessionLocal() as session:
        stored = Path(session.get(Message, message["id"]).stored_path)
    assert stored.is_file()
    assert stored.parent.resolve() == Path(get_settings().media_dir).resolve()


def test_operator_media_requires_operator_session(client, make_user):
    _, conversation_id = _seed_conversation()
    response = _upload(client, conversation_id)
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}

    make_user("tech", "tech-pass", role="tecnico")
    _login(client, "tech", "tech-pass")
    response = _upload(client, conversation_id)
    assert response.status_code == 403


def test_operator_media_rejects_duplicate_request_id(client, make_user):
    _, conversation_id = _seed_conversation()
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    with respx.mock(assert_all_called=True) as router:
        _mock_meta(router)
        assert _upload(client, conversation_id).status_code == 200
        duplicate = _upload(client, conversation_id, caption="different payload")
    assert duplicate.status_code == 409


def test_operator_media_rejects_nonhuman_and_expired_conversation(client, make_user):
    _, bot_id = _seed_conversation(phone="+56911112223", state=ConversationState.BOT)
    _, expired_id = _seed_conversation(phone="+56911112224")
    with SessionLocal() as session:
        inbound_rows = session.scalars(select(Message).where(Message.conversation_id == expired_id, Message.direction == MessageDirection.INBOUND)).all()
        for inbound in inbound_rows:
            inbound.created_at -= timedelta(hours=25)
        session.commit()
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    assert _upload(client, bot_id).status_code == 422
    expired = _upload(client, expired_id)
    assert expired.status_code == 422
    assert expired.json() == {"detail": "customer reply window expired"}


def test_oversized_operator_media_leaves_no_file(client, make_user):
    _, conversation_id = _seed_conversation()
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    media_dir = Path(get_settings().media_dir)
    before = set(media_dir.iterdir()) if media_dir.exists() else set()
    response = _upload(client, conversation_id, content=b"x" * (5 * 1024 * 1024 + 1))
    assert response.status_code == 422
    assert set(media_dir.iterdir()) == before


def test_operator_media_requires_nonempty_file_and_request_id(client, make_user):
    _, conversation_id = _seed_conversation()
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    missing = client.post(f"/panel/api/conversations/{conversation_id}/media", data={"request_id": "missing"})
    assert missing.status_code == 422
    empty = _upload(client, conversation_id, content=b"")
    assert empty.status_code == 422
    no_request_id = client.post(
        f"/panel/api/conversations/{conversation_id}/media",
        files={"file": ("photo.png", b"png", "image/png")},
    )
    assert no_request_id.status_code == 422


def test_failed_media_delivery_returns_the_row_like_the_text_path(client, make_user):
    """S4: a Meta rejection is recorded on the row, not turned into a 502.

    The text endpoint answers 200 with `delivery_status: failed` so the operator sees the
    failed bubble and its retry action; media must behave the same way instead of
    reporting a delivery failure the SPA cannot attach to a message.
    """
    _, conversation_id = _seed_conversation()
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    with respx.mock(assert_all_called=True) as router:
        router.post(MEDIA_UPLOAD).mock(return_value=Response(200, json={"id": "media-id"}))
        router.post(MEDIA_SEND).mock(return_value=Response(400, json={"error": {"message": "rejected"}}))
        response = _upload(client, conversation_id, request_id="media-fail")

    assert response.status_code == 200
    message = response.json()["message"]
    assert message["delivery_status"] == "failed"
    assert message["media_download_url"] is not None
    with SessionLocal() as session:
        row = session.scalar(select(Message).where(Message.request_id == "media-fail"))
        assert row.delivery_status.value == "failed"
        assert Path(row.stored_path).is_file()
