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


def test_webm_opus_is_remuxed_to_ogg_without_changing_samples(tmp_path):
    source = tmp_path / "voice.webm"
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=0.4", "-c:a", "libopus", str(source))
    source_packets = _packet_hashes(source)

    output, content_type = normalize_audio(source, "audio/webm;codecs=opus")

    assert content_type == "audio/ogg"
    assert output != source
    assert _probe(output, "format=format_name") == "ogg"
    assert _probe(output, "stream=codec_name") == "opus"
    assert _packet_hashes(output) == source_packets


def test_unreadable_audio_raises_normalization_error(tmp_path):
    source = tmp_path / "not-audio.mp4"
    source.write_bytes(b"not an audio file")

    with pytest.raises(AudioNormalizationError, match="uploaded audio could not be read"):
        normalize_audio(source, "audio/mp4")
