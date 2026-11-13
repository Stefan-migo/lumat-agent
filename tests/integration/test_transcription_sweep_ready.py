from uuid import uuid4

import pytest

from app.db import SessionLocal
from app.models import (
    Conversation,
    Customer,
    Message,
    MessageDirection,
    MessageType,
    Settings,
)
from app.services import transcription


def _message(
    session,
    tmp_path,
    *,
    msg_type=MessageType.AUDIO,
    direction=MessageDirection.INBOUND,
    attempts=0,
    stored_path=None,
):
    customer = Customer(phone_e164=f"+569{uuid4().int % 100_000_000:08d}")
    session.add(customer)
    session.flush()
    conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
    session.add(conversation)
    session.flush()
    path = stored_path
    if path is None:
        path = tmp_path / "voice.ogg"
        path.write_bytes(b"audio")
    message = Message(
        conversation_id=conversation.id,
        direction=direction,
        msg_type=msg_type,
        stored_path=str(path),
        transcript_attempts=attempts,
    )
    session.add(message)
    session.flush()
    return message


def _enable(session):
    session.add(Settings(key="transcription.enabled", value=True))
    session.add(Settings(key="transcription.max_seconds", value=180))
    session.add(Settings(key="transcription.model", value="small"))
    session.flush()


def test_flag_off_returns_none_without_changes(tmp_path):
    with SessionLocal() as session:
        message = _message(session, tmp_path, attempts=1)
        before = (message.transcript, message.transcript_at, message.transcript_attempts)

        assert transcription.transcribe_message(session, message) is None
        assert (message.transcript, message.transcript_at, message.transcript_attempts) == before


def test_inbound_audio_transcribes_and_stamps_without_attempt_increment(monkeypatch, tmp_path):
    with SessionLocal() as session:
        _enable(session)
        message = _message(session, tmp_path)
        monkeypatch.setattr(transcription, "_audio_duration_seconds", lambda path: 1)
        monkeypatch.setattr(transcription, "transcribe_path", lambda path, **kwargs: "hola")

        assert transcription.transcribe_message(session, message) == "hola"
        assert message.transcript == "hola"
        assert message.transcript_at is not None
        assert message.transcript_attempts == 0


def test_transcription_failure_increments_attempt_and_does_not_raise(monkeypatch, tmp_path):
    with SessionLocal() as session:
        _enable(session)
        message = _message(session, tmp_path, attempts=1)
        monkeypatch.setattr(transcription, "_audio_duration_seconds", lambda path: 1)
        monkeypatch.setattr(
            transcription,
            "transcribe_path",
            lambda path, **kwargs: (_ for _ in ()).throw(RuntimeError("model failed")),
        )

        assert transcription.transcribe_message(session, message) is None
        assert message.transcript_attempts == 2
        assert message.transcript is None
        assert message.transcript_at is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"attempts": 3},
        {"msg_type": MessageType.TEXT},
        {"direction": MessageDirection.OUTBOUND},
    ],
)
def test_ineligible_messages_are_skipped(monkeypatch, tmp_path, kwargs):
    with SessionLocal() as session:
        _enable(session)
        message = _message(session, tmp_path, **kwargs)
        before = (message.transcript, message.transcript_at, message.transcript_attempts)
        monkeypatch.setattr(
            transcription,
            "transcribe_path",
            lambda path, **kw: pytest.fail("unexpected transcription"),
        )

        assert transcription.transcribe_message(session, message) is None
        assert (message.transcript, message.transcript_at, message.transcript_attempts) == before


def test_missing_stored_path_is_skipped(monkeypatch, tmp_path):
    with SessionLocal() as session:
        _enable(session)
        message = _message(session, tmp_path)
        message.stored_path = None
        before = (message.transcript, message.transcript_at, message.transcript_attempts)
        monkeypatch.setattr(
            transcription,
            "transcribe_path",
            lambda path, **kwargs: pytest.fail("unexpected transcription"),
        )

        assert transcription.transcribe_message(session, message) is None
        assert (message.transcript, message.transcript_at, message.transcript_attempts) == before


def test_missing_audio_file_is_skipped(monkeypatch, tmp_path):
    with SessionLocal() as session:
        _enable(session)
        message = _message(session, tmp_path, stored_path=tmp_path / "missing.ogg")
        before = (message.transcript, message.transcript_at, message.transcript_attempts)
        monkeypatch.setattr(
            transcription,
            "transcribe_path",
            lambda path, **kwargs: pytest.fail("unexpected transcription"),
        )

        assert transcription.transcribe_message(session, message) is None
        assert (message.transcript, message.transcript_at, message.transcript_attempts) == before
