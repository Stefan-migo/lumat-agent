import subprocess
from pathlib import Path

import pytest

from app.services.audio_format import AudioNormalizationError, normalize_audio


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True)


def _probe(path: Path, entries: str) -> str:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", entries, "-of", "csv=p=0", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _packet_hashes(path: Path) -> list[str]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_packets", "-show_data_hash", "sha256", "-show_entries", "packet=data_hash", "-of", "csv=p=0", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.split(",", 1)[0] for line in result.stdout.strip().splitlines()]


def _start_time(path: Path) -> float:
    raw = _probe(path, "format=start_time")
    return float(raw) if raw and raw != "N/A" else 0.0


def test_fragmented_mp4_is_normalized_to_ogg_opus(tmp_path):
    source = tmp_path / "fragmented.mp4"
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=0.4", "-c:a", "aac", "-movflags", "frag_keyframe+empty_moov", str(source))

    output, content_type = normalize_audio(source, "audio/mp4")

    assert content_type == "audio/ogg"
    assert output != source
    assert _probe(output, "format=format_name") == "ogg"
    assert _probe(output, "stream=codec_name") == "opus"


def test_ogg_opus_is_returned_untouched(tmp_path):
    source = tmp_path / "voice.ogg"
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=0.4", "-c:a", "libopus", str(source))

    output, content_type = normalize_audio(source, "audio/ogg")

    assert output == source
    assert content_type == "audio/ogg"
    assert _probe(output, "format=format_name") == "ogg"
    assert _probe(output, "stream=codec_name") == "opus"


def test_webm_opus_is_re_encoded_to_ogg_through_pcm(tmp_path):
    """The copy path is gone on purpose.

    Copying Opus samples out of a browser container kept the source's negative start
    timestamp, and that shape is what Meta refused with 131053 while identical audio
    through an intermediate WAV was accepted. Bit-exactness was the wrong trade.
    """
    source = tmp_path / "voice.webm"
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=0.4", "-c:a", "libopus", str(source))
    source_packets = _packet_hashes(source)

    output, content_type = normalize_audio(source, "audio/webm;codecs=opus")

    assert content_type == "audio/ogg"
    assert output != source
    assert _probe(output, "format=format_name") == "ogg"
    assert _probe(output, "stream=codec_name") == "opus"
    assert _packet_hashes(output) != source_packets


def test_a_browser_recording_is_normalized_to_a_zero_origin(tmp_path):
    """The property the failing production file violated.

    A real `MediaRecorder` MP4 reports a negative start time (encoder delay). Encoding
    it straight into libopus kept that origin and Meta answered 131053 every time;
    two steps through PCM start at zero and Meta accepted it. A synthetic fixture does
    not reproduce the delay, so this pins the output property that the two-step path
    guarantees, and the docstring keeps the measurement it stands for.
    """
    source = tmp_path / "recording.mp4"
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=0.4", "-c:a", "aac",
            "-movflags", "frag_keyframe+empty_moov", str(source))

    output, _ = normalize_audio(source, "audio/mp4")

    assert _start_time(output) == 0
    assert _probe(output, "format=format_name") == "ogg"


def test_unreadable_audio_raises_normalization_error(tmp_path):
    source = tmp_path / "not-audio.mp4"
    source.write_bytes(b"not an audio file")

    with pytest.raises(AudioNormalizationError, match="uploaded audio could not be read"):
        normalize_audio(source, "audio/mp4")
