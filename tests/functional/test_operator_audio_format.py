"""S1/S2 — an operator recording must reach Meta in a container it accepts.

Chromium records `audio/webm;codecs=opus`; Meta accepts only aac, amr, mpeg, mp4 and
ogg-with-Opus. The codec is already Opus, so the fix is a container remux, and the audio
inside the file must survive byte-for-byte. The accepted native formats (Firefox records
ogg, Safari records mp4) must pass through untouched.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Message
from tests.functional.test_api_conversations import _login, _seed_conversation

MEDIA_UPLOAD = "https://graph.facebook.com/v20.0/" + get_settings().meta_phone_number_id + "/media"
MEDIA_SEND = "https://graph.facebook.com/v20.0/" + get_settings().meta_phone_number_id + "/messages"


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", *args], check=True, capture_output=True)


@pytest.fixture(scope="module")
def webm_opus(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A 0.4s Opus recording inside a WebM container — exactly what Chromium produces."""
    path = tmp_path_factory.mktemp("audio") / "recording.webm"
    _ffmpeg(
        "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4",
        "-c:a", "libopus", "-b:a", "24k", "-ac", "1", "-ar", "48000",
        "-f", "webm", str(path),
    )
    return path


@pytest.fixture(scope="module")
def ogg_opus(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The same recording in Ogg — what Firefox produces and Meta accepts natively."""
    path = tmp_path_factory.mktemp("audio") / "recording.ogg"
    _ffmpeg(
        "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4",
        "-c:a", "libopus", "-b:a", "24k", "-ac", "1", "-ar", "48000",
        "-f", "ogg", str(path),
    )
    return path


def _upload_audio(client, conversation_id: int, source: Path, content_type: str, request_id: str = "audio-1", caption: str | None = None):
    data = {"request_id": request_id}
    if caption:
        data["caption"] = caption
    return client.post(
        f"/panel/api/conversations/{conversation_id}/media",
        data=data,
        files={"file": (source.name, source.read_bytes(), content_type)},
    )


def _mock_meta(router):
    upload = router.post(MEDIA_UPLOAD).mock(return_value=Response(200, json={"id": "media-id"}))
    send = router.post(MEDIA_SEND).mock(return_value=Response(200, json={"messages": [{"id": "wamid.test"}]}))
    return upload, send


def test_webm_recording_is_remuxed_to_ogg_opus_before_upload(client, make_user, webm_opus):
    _, conversation_id = _seed_conversation()
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    with respx.mock(assert_all_called=True) as router:
        upload, send = _mock_meta(router)
        response = _upload_audio(client, conversation_id, webm_opus, "audio/webm", caption="te mando un audio")

    assert response.status_code == 200
    message = response.json()["message"]
    assert message["msg_type"] == "audio"
    assert message["delivery_status"] == "sent"

    with SessionLocal() as session:
        row = session.get(Message, message["id"])
    assert row.content_type == "audio/ogg"
    assert row.filename == "audio-1.ogg"
    stored = Path(row.stored_path)
    assert stored.is_file()
    assert stored.suffix == ".ogg"
    assert stored.read_bytes().startswith(b"OggS"), "the stored blob must be an Ogg container, not the WebM upload"

    # Meta must receive the Ogg container and the audio type — never the WebM bytes.
    upload_body = upload.calls[0].request.content
    assert b"audio/ogg" in upload_body
    assert b"OggS" in upload_body
    send_body = send.calls[0].request.content
    assert b'"type":"audio"' in send_body
    assert b"caption" not in send_body, "Meta rejects a caption on an audio message"


def test_ogg_recording_passes_through_without_reencoding(client, make_user, ogg_opus):
    _, conversation_id = _seed_conversation()
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    with respx.mock(assert_all_called=True) as router:
        upload, _ = _mock_meta(router)
        response = _upload_audio(client, conversation_id, ogg_opus, "audio/ogg;codecs=opus", request_id="audio-2")

    assert response.status_code == 200
    with SessionLocal() as session:
        row = session.get(Message, response.json()["message"]["id"])
    assert row.content_type == "audio/ogg"
    assert row.filename == "audio-2.ogg"
    assert Path(row.stored_path).read_bytes() == ogg_opus.read_bytes(), "an accepted format must not be rewritten"
    assert ogg_opus.read_bytes() in upload.calls[0].request.content


def test_undecodable_audio_is_rejected_and_leaves_no_stored_file(client, make_user, tmp_path):
    _, conversation_id = _seed_conversation()
    make_user("oper", "oper-pass", role="operador")
    _login(client)
    broken = tmp_path / "broken.webm"
    broken.write_bytes(b"not-an-audio-stream")
    media_dir = Path(get_settings().media_dir)
    before = {path.name for path in media_dir.iterdir()} if media_dir.exists() else set()

    with respx.mock(assert_all_called=False) as router:
        _mock_meta(router)
        response = _upload_audio(client, conversation_id, broken, "audio/webm", request_id="audio-3")

    assert response.status_code == 422
    assert response.json()["detail"], "the operator needs a reason the upload was rejected"
    with SessionLocal() as session:
        stored = session.scalars(select(Message).where(Message.request_id == "audio-3")).all()
    assert stored == [], "a rejected upload must not leave a message row"
    after = {path.name for path in media_dir.iterdir()} if media_dir.exists() else set()
    assert after == before, "a rejected upload must not leave a file behind"
