"""Lazy local audio transcription for inbound WhatsApp voice messages."""

from __future__ import annotations

import logging
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import MessageDirection, MessageType
from app.services.settings import (
    get_transcription_enabled,
    get_transcription_max_seconds,
    get_transcription_model,
)

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()
DEFAULT_MODEL = "small"


def get_model(model_name: str | None = None):
    """Return the process-wide WhisperModel, loading it once under a lock.

    Tests replace this seam with a fake model. Importing this module does not
    import faster-whisper or load model files; both happen only on first use.
    """
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel

            _model = WhisperModel(
                model_name or DEFAULT_MODEL,
                device="cpu",
                compute_type="int8",
            )
    return _model


def transcribe_path(path: str | Path, *, model_name: str | None = None) -> str:
    """Transcribe one audio file and return its text, or an empty string."""
    segments, _info = get_model(model_name).transcribe(str(path))
    return " ".join(
        segment.text.strip()
        for segment in segments
        if isinstance(getattr(segment, "text", None), str) and segment.text.strip()
    ).strip()


def _audio_duration_seconds(path: str | Path) -> float:
    """Read duration without decoding or truncating the audio."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        check=True,
        text=True,
        timeout=15,
    )
    return float(result.stdout.strip())


def _record_untranscribed_attempt(message, reason: str) -> None:
    """Retire a failed/skipped attempt so it cannot starve newer sweep rows."""
    message.transcript_attempts = (message.transcript_attempts or 0) + 1
    logger.warning(
        "Skipping audio transcription for message %s: %s (attempt %s)",
        message.id,
        reason,
        message.transcript_attempts,
    )


def transcribe_message(session: Session, message) -> str | None:
    """Transcribe eligible inbound audio, counting untranscribed exits as attempts.

    Missing files and overlong audio have no transcript to persist. Counting
    those skips is still necessary: otherwise they remain at the head of the
    sweep's bounded, creation-ordered batch and can starve newer audio forever.
    """
    if message.transcript is not None:
        return None
    if not get_transcription_enabled(session):
        return None
    if message.direction != MessageDirection.INBOUND or message.msg_type != MessageType.AUDIO:
        return None
    if not message.stored_path or (message.transcript_attempts or 0) >= 3:
        return None

    path = Path(message.stored_path)
    if not path.is_file():
        _record_untranscribed_attempt(message, "stored audio file does not exist")
        return None

    try:
        duration = _audio_duration_seconds(path)
        max_seconds = get_transcription_max_seconds(session)
        if duration > max_seconds:
            _record_untranscribed_attempt(
                message,
                f"duration {duration:.2f}s exceeds maximum {max_seconds}s",
            )
            return None
        transcript = transcribe_path(path, model_name=get_transcription_model(session))
    except Exception:
        message.transcript_attempts = (message.transcript_attempts or 0) + 1
        logger.exception(
            "Audio transcription failed for message %s (attempt %s)",
            message.id,
            message.transcript_attempts,
        )
        return None

    message.transcript = transcript
    message.transcript_at = datetime.now(timezone.utc)
    return transcript
