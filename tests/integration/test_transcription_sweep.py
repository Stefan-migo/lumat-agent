from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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
from app.ops import transcribe
from app.services import transcription


@contextmanager
def _settings(*, enabled: bool, window_days: int = 7):
    keys = {
        "transcription.enabled": enabled,
        "transcription.window_days": window_days,
        "transcription.max_seconds": 180,
        "transcription.model": "small",
    }
    with SessionLocal() as session:
        previous = {key: session.get(Settings, key) for key in keys}
        previous_values = {
            key: row.value if row is not None else None for key, row in previous.items()
        }
        for key, value in keys.items():
            row = previous[key]
            if row is None:
                session.add(Settings(key=key, value=value))
            else:
                row.value = value
        session.commit()
    try:
        yield
    finally:
        with SessionLocal() as session:
            for key, row in previous.items():
                current = session.get(Settings, key)
                if row is None:
                    if current is not None:
                        session.delete(current)
                elif current is not None:
                    current.value = previous_values[key]
            session.commit()


@pytest.fixture
def audio_factory(tmp_path):
    created: list[tuple[int, int, int]] = []

    def create(*, days_ago=0, attempts=0, transcript=None, exists=True, label="voice"):
        path = tmp_path / f"{label}-{uuid4().hex}.ogg"
        if exists:
            path.write_bytes(b"audio")
        with SessionLocal() as session:
            customer = Customer(phone_e164=f"+569{uuid4().int % 100_000_000:08d}")
            session.add(customer)
            session.flush()
            conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
            session.add(conversation)
            session.flush()
            message = Message(
                conversation_id=conversation.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.AUDIO,
                stored_path=str(path),
                transcript_attempts=attempts,
                transcript=transcript,
                created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
            )
            session.add(message)
            session.commit()
            created.append((message.id, conversation.id, customer.id))
            return message.id

    yield create

    with SessionLocal() as session:
        for message_id, conversation_id, customer_id in created:
            message = session.get(Message, message_id)
            conversation = session.get(Conversation, conversation_id)
            customer = session.get(Customer, customer_id)
            if message is not None:
                session.delete(message)
                session.flush()
            if conversation is not None:
                session.delete(conversation)
            if customer is not None:
                session.delete(customer)
        session.commit()


def _message(message_id):
    with SessionLocal() as session:
        return session.get(Message, message_id)


def test_disabled_sweep_leaves_pending_audio_untouched(audio_factory, monkeypatch):
    message_id = audio_factory()
    monkeypatch.setattr(
        transcription,
        "transcribe_path",
        lambda *args, **kwargs: pytest.fail("disabled sweep transcribed audio"),
    )

    with _settings(enabled=False):
        assert transcribe.run(limit=10) == 0

    message = _message(message_id)
    assert message.transcript is None
    assert message.transcript_attempts == 0


def test_enabled_sweep_transcribes_recent_eligible_audio(audio_factory, monkeypatch):
    message_id = audio_factory()
    monkeypatch.setattr(transcription, "_audio_duration_seconds", lambda path: 1)
    monkeypatch.setattr(
        transcription,
        "transcribe_path",
        lambda path, **kwargs: "necesito coordinar una visita",
    )

    with _settings(enabled=True):
        assert transcribe.run(limit=10) == 1

    message = _message(message_id)
    assert message.transcript == "necesito coordinar una visita"
    assert message.transcript_at is not None
    assert message.transcript_attempts == 0


def test_sweep_never_transcribes_audio_outside_configured_window(audio_factory, monkeypatch):
    message_id = audio_factory(days_ago=8)
    monkeypatch.setattr(
        transcription,
        "transcribe_path",
        lambda *args, **kwargs: pytest.fail("historical audio was transcribed"),
    )

    with _settings(enabled=True, window_days=7):
        assert transcribe.run(limit=10) == 0

    message = _message(message_id)
    assert message.transcript is None
    assert message.transcript_attempts == 0


def test_sweep_skips_audio_with_three_attempts(audio_factory, monkeypatch):
    message_id = audio_factory(attempts=3)
    monkeypatch.setattr(
        transcription,
        "transcribe_path",
        lambda *args, **kwargs: pytest.fail("exhausted audio was transcribed"),
    )

    with _settings(enabled=True):
        assert transcribe.run(limit=10) == 0

    assert _message(message_id).transcript_attempts == 3


def test_bad_audio_rows_do_not_block_a_healthy_row_in_the_batch(audio_factory, monkeypatch):
    too_long_one = audio_factory(label="too-long")
    too_long_two = audio_factory(label="too-long")
    missing = audio_factory(exists=False, label="missing")
    healthy = audio_factory(label="healthy")
    monkeypatch.setattr(
        transcription,
        "_audio_duration_seconds",
        lambda path: 1 if "healthy" in str(path) else 181,
    )
    monkeypatch.setattr(
        transcription,
        "transcribe_path",
        lambda path, **kwargs: "healthy audio transcript",
    )

    with _settings(enabled=True):
        assert transcribe.run(limit=4) == 4

    for message_id in (too_long_one, too_long_two, missing):
        message = _message(message_id)
        assert message.transcript is None
        assert message.transcript_attempts == 1
    assert _message(healthy).transcript == "healthy audio transcript"


def test_sweep_commits_each_message_and_continues_after_one_transaction_fails(
    audio_factory, monkeypatch, caplog
):
    first = audio_factory(label="first")
    failing = audio_factory(label="failing")
    last = audio_factory(label="last")

    def transcribe_one(session, message):
        if message.id == failing:
            message.transcript = "must roll back"
            raise RuntimeError("transaction probe")
        message.transcript = f"transcript-{message.id}"
        return message.transcript

    monkeypatch.setattr(transcribe, "transcribe_message", transcribe_one)

    with _settings(enabled=True):
        assert transcribe.run(limit=3) == 2

    assert _message(first).transcript == f"transcript-{first}"
    assert _message(failing).transcript is None
    assert _message(last).transcript == f"transcript-{last}"
    assert f"message {failing}" in caplog.text
    assert "transaction probe" in caplog.text


def test_sweep_does_not_retranscribe_audio_with_transcript(audio_factory, monkeypatch):
    message_id = audio_factory(transcript="ya transcrito")
    monkeypatch.setattr(
        transcription,
        "transcribe_path",
        lambda *args, **kwargs: pytest.fail("transcript was overwritten"),
    )

    with _settings(enabled=True):
        assert transcribe.run(limit=10) == 0

    message = _message(message_id)
    assert message.transcript == "ya transcrito"
    assert message.transcript_attempts == 0
