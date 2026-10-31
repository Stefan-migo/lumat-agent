"""Normalize an operator-uploaded audio file into a container Meta accepts.

WhatsApp Cloud API accepts `audio/aac`, `audio/amr`, `audio/mpeg`, `audio/mp4` and `audio/ogg`,
and for ogg it requires the Opus codec. Browsers do not produce all of those: Chromium records
`audio/webm;codecs=opus`, which Meta rejects outright, and that is why the panel could receive an
audio but never send one.

The Opus samples inside a Chromium recording are already valid, so the fix is a *container remux*
(`-c:a copy`): the recording keeps its exact audio and only the wrapper changes. A codec Meta
cannot take at all is decoded once into Opus. Whatever Meta already accepts is returned untouched,
so Firefox (ogg) and Safari (mp4) uploads keep their original bytes.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

# Containers Meta accepts for an audio message (Meta docs: "Audio messages"). For ogg the codec
# must be Opus; the base container alone is explicitly not supported.
ACCEPTED_AUDIO_TYPES = frozenset({"audio/aac", "audio/amr", "audio/mpeg", "audio/mp4", "audio/ogg"})

# Suffix per accepted type: an operator upload is renamed to match what is actually stored, so the
# panel, the audit row and Meta all describe the same file.
AUDIO_SUFFIXES = {
    "audio/aac": ".aac",
    "audio/amr": ".amr",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
}

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


def _run_ffmpeg(source: Path, target: Path, *, copy_audio: bool) -> None:
    args = ["ffmpeg", "-v", "error", "-y", "-i", str(source), "-vn"]
    if copy_audio:
        args += ["-c:a", "copy"]
    else:
        # Opus tops out at 48 kHz; anything Meta would not accept as-is gets one decode here.
        args += ["-c:a", "libopus", "-b:a", "64k", "-ar", "48000"]
    args += ["-f", "ogg", str(target)]
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
    """Return a Meta-acceptable audio file and its content type.

    The original path is returned unchanged when the upload is already acceptable; otherwise a
    new `.ogg` file is written next to it and the caller owns its cleanup.
    """
    path = Path(path)
    # Browsers append codec parameters (`audio/ogg;codecs=opus`, `audio/webm;codecs=opus`), which
    # Meta does not accept in the upload `type` field. The container is what decides.
    base_type = content_type.split(";", 1)[0].strip().lower()
    accepted = base_type in ACCEPTED_AUDIO_TYPES
    codec = audio_codec(path)
    # `audio/ogg` is only acceptable with Opus, so the codec decides even when the container is
    # already in the accepted set. Other accepted containers are taken at face value: Meta is the
    # authority on their codec, and rewriting them would change bytes nobody asked to change.
    if accepted and (base_type != "audio/ogg" or codec == "opus"):
        return path, base_type

    target = path.parent / f"{path.stem}-{uuid.uuid4().hex[:8]}.ogg"
    _run_ffmpeg(path, target, copy_audio=codec == "opus")
    return target, NORMALIZED_CONTENT_TYPE
