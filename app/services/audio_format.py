"""Normalize operator audio to the measured WhatsApp-safe container, Ogg/Opus.

Production files measured on 2026-11-06 were AAC 48 kHz mono, 5.38 seconds and 124 KB, with
fragmented MP4 boxes ordered `ftyp`, `moov`, `moof`, `mdat`. Meta accepted the upload but rejected
the send with 131053. Remuxing that file produced Ogg/Opus at 48 kHz mono, 5.38 seconds and
42,378 bytes. The documented list of accepted containers was not sufficient evidence that every
file in those containers could be sent; this is why those passthroughs were removed.

Ogg/Opus uploads already have the measured output shape and remain untouched. Other Opus audio
(such as browser WebM recordings) is remuxed with `-c:a copy`, preserving its encoded samples;
other codecs are encoded to Opus.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

# Only this measured-and-normalized output container is passed through to Meta.
ACCEPTED_AUDIO_TYPES = frozenset({"audio/ogg"})

# Suffixes for the containers normalize_audio may return; the stored filename matches the bytes.
AUDIO_SUFFIXES = {"audio/ogg": ".ogg"}

NORMALIZED_CONTENT_TYPE = "audio/ogg"
FFMPEG_TIMEOUT_SECONDS = 120.0


class AudioNormalizationError(ValueError):
    """The uploaded audio cannot be turned into something Meta accepts."""


def audio_codec(path: Path) -> str | None:
    """Return the first audio stream's codec name, or None when it cannot be read."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=FFMPEG_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        return None
    codec = result.stdout.strip().splitlines()[0].strip() if result.stdout.strip() else ""
    return codec or None


def _run_ffmpeg(args: list[str]) -> None:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECONDS)
    except FileNotFoundError as exc:  # pragma: no cover - image dependency, asserted in Dockerfile
        raise AudioNormalizationError("audio conversion requires ffmpeg, which is missing on this host") from exc
    except subprocess.TimeoutExpired as exc:
        raise AudioNormalizationError("audio conversion timed out") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        raise AudioNormalizationError(
            "the uploaded audio could not be read" + (f": {detail[-1]}" if detail else "")
        )


def normalize_audio(path: Path, content_type: str) -> tuple[Path, str]:
    """Return an Ogg/Opus audio file and its content type.

    Ogg/Opus is returned unchanged; all other uploads are written to a new `.ogg` file beside
    the source, and the caller owns its cleanup.

    The conversion runs in TWO steps, through PCM, and that is the fix for a measured failure:
    decoding a browser recording straight into libopus produced files that ffprobe, ffmpeg and
    this module all read as valid Ogg/Opus -- identical duration, loudness, page count and
    end-of-stream flag to a working file -- while Meta answered 131053 "on processing it is of
    type application/octet-stream" every time. The same input through an intermediate WAV was
    accepted every time, interleaved with the one-step failures so timing could not explain it.
    The browser's container starts at a negative timestamp (encoder delay); a direct remux keeps
    that origin, and an intermediate PCM file does not.

    The cost is a second pass and losing bit-exact samples for Opus inputs, which is why the
    copy path is gone: reproduction beat byte-fidelity at the only judge that matters here.
    """
    path = Path(path)
    # Browsers append codec parameters (`audio/ogg;codecs=opus`, `audio/webm;codecs=opus`), which
    # Meta does not accept in the upload `type` field. The container is what decides.
    base_type = content_type.split(";", 1)[0].strip().lower()
    if base_type in ACCEPTED_AUDIO_TYPES and audio_codec(path) == "opus":
        return path, base_type

    stem = uuid.uuid4().hex[:8]
    pcm = path.parent / f"{path.stem}-{stem}.wav"
    target = path.parent / f"{path.stem}-{stem}.ogg"
    try:
        # Step 1: decode and resample once, to a format no muxer can misinterpret.
        _run_ffmpeg([
            "ffmpeg", "-v", "error", "-y", "-i", str(path), "-vn",
            "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(pcm),
        ])
        # Step 2: encode the clean samples. Opus tops out at 48 kHz.
        _run_ffmpeg([
            "ffmpeg", "-v", "error", "-y", "-i", str(pcm),
            "-c:a", "libopus", "-b:a", "64k", "-ar", "48000", "-f", "ogg", str(target),
        ])
    finally:
        pcm.unlink(missing_ok=True)
    return target, NORMALIZED_CONTENT_TYPE
