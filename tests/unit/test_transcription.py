import ast
from pathlib import Path

import pytest

from app.services import transcription
from app.services.settings import (
    SETTINGS_DEFAULTS,
    get_transcription_enabled,
    get_transcription_max_seconds,
    get_transcription_model,
    get_transcription_window_days,
)


class FakeSession:
    def get(self, model, key):
        return None


def test_faster_whisper_import_is_nested_inside_the_lazy_accessor():
    tree = ast.parse(Path(transcription.__file__).read_text())
    top_level_imports = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("faster_whisper")
            or isinstance(node, ast.Import)
            and any(alias.name.startswith("faster_whisper") for alias in node.names)
        )
    ]
    accessor = next(
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "get_model"
    )
    lazy_imports = [
        node for node in ast.walk(accessor)
        if isinstance(node, ast.ImportFrom) and node.module == "faster_whisper"
    ]

    assert top_level_imports == []
    assert len(lazy_imports) == 1


def test_transcribe_path_uses_the_injectable_model(monkeypatch, tmp_path):
    audio = tmp_path / "voice.ogg"
    audio.write_bytes(b"audio")
    calls = []

    class FakeModel:
        def transcribe(self, path):
            calls.append(path)
            return iter([type("Segment", (), {"text": " Hola "})()]), object()

    monkeypatch.setattr(transcription, "get_model", lambda model_name=None: FakeModel())

    assert transcription.transcribe_path(audio) == "Hola"
    assert calls == [str(audio)]


def test_transcribe_path_returns_empty_string_when_model_returns_no_segments(monkeypatch, tmp_path):
    audio = tmp_path / "voice.ogg"
    audio.write_bytes(b"audio")

    class EmptyModel:
        def transcribe(self, path):
            return iter(()), object()

    monkeypatch.setattr(transcription, "get_model", lambda model_name=None: EmptyModel())

    assert transcription.transcribe_path(audio) == ""


def test_transcription_settings_default_to_documented_values():
    session = FakeSession()

    assert SETTINGS_DEFAULTS["transcription.enabled"] is False
    assert SETTINGS_DEFAULTS["transcription.model"] == "small"
    assert SETTINGS_DEFAULTS["transcription.window_days"] == 7
    assert SETTINGS_DEFAULTS["transcription.max_seconds"] == 180
    assert get_transcription_enabled(session) is False
    assert get_transcription_model(session) == "small"
    assert get_transcription_window_days(session) == 7
    assert get_transcription_max_seconds(session) == 180


def test_transcribe_message_skips_audio_longer_than_configured_limit(monkeypatch, tmp_path):
    audio = tmp_path / "long.ogg"
    audio.write_bytes(b"audio")
    message = type("Message", (), {"id": 1, "direction": "inbound", "msg_type": "audio", "stored_path": str(audio), "transcript": None, "transcript_attempts": 0})()
    session = type("Session", (), {"get": lambda self, model, key: type("Setting", (), {"value": True if key == "transcription.enabled" else 180})()})()
    monkeypatch.setattr(transcription, "_audio_duration_seconds", lambda path: 181)
    monkeypatch.setattr(transcription, "get_model", lambda: pytest.fail("must not load model"))

    assert transcription.transcribe_message(session, message) is None
    assert message.transcript_attempts == 1
