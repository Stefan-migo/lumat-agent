#!/usr/bin/env python3
"""Extract message-level provenance from a directory of WhatsApp exports."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_MESSAGE = re.compile(
    r"^\[(\d{1,2})/(\d{1,2})/(\d{2,4}), (\d{1,2}):(\d{2}):(\d{2}) ([AP])M\] (.*)$"
)
_SENDER = re.compile(r"^([^:]+): (.*)$")
_SYSTEM = re.compile(r"^\[(\d{1,2})/(\d{1,2})/(\d{2,4}), (\d{1,2}):(\d{2}):(\d{2}) ([AP])M\] - (.*)$")
_MEDIA = re.compile(r"^<([^<>]+?) omitido>$|^\[(Mensaje de album|Video|Imagen|Audio|Sticker|GIF|Documento|Contacto|Ubicación)\]$", re.I)


def _timestamp(match: re.Match[str]) -> str:
    day, month, year, hour, minute, second, meridiem = match.groups()[:7]
    year_value = int(year)
    if year_value < 100:
        year_value += 2000
    hour_value = int(hour) % 12 + (12 if meridiem == "P" else 0)
    return (
        f"{year_value:04d}-{int(month):02d}-{int(day):02d}T"
        f"{hour_value:02d}:{int(minute):02d}:{int(second):02d}"
    )


def _kind(text: str, *, system: bool = False) -> str:
    if system:
        return "system"
    match = _MEDIA.match(text.strip())
    if not match:
        return "text"
    label = (match.group(1) or match.group(2) or "").casefold()
    if "album" in label:
        return "album"
    if "imagen" in label or "image" in label:
        return "image"
    if "audio" in label:
        return "audio"
    if "video" in label:
        return "video"
    if "document" in label:
        return "document"
    return label


def parse_conversation(folder: Path, raw: bytes) -> dict[str, Any]:
    """Parse one chat.txt, retaining the starting physical line per message."""
    content = raw.decode("utf-8", errors="replace")
    messages: list[dict[str, Any]] = []
    continuation_open = False
    for line_number, source_line in enumerate(content.splitlines(), start=1):
        line = source_line.strip()
        if not line:
            continue
        if _SYSTEM.match(line):
            # WhatsApp status notices are not conversation turns (the existing
            # export parser likewise excludes them from sender/message counts).
            continuation_open = False
            continue
        match = _MESSAGE.match(line)
        if match:
            stamp = _timestamp(match)
            body = match.group(8)
            sender_match = _SENDER.match(body)
            if sender_match:
                sender, text = sender_match.groups()
                sender = sender.strip()
            else:
                sender, text = "system", body
        elif messages and continuation_open:
            messages[-1]["text"] += "\n" + line
            messages[-1]["kind"] = _kind(messages[-1]["text"])
            continue
        else:
            continue
        continuation_open = True
        messages.append(
            {
                "sender": sender,
                "timestamp": stamp,
                "kind": _kind(text),
                "line": line_number,
                "text": text,
            }
        )
    return {"name": folder.name, "messages": messages}


def extract_source(source: Path) -> dict[str, Any]:
    """Read paired exports, deduplicate byte-identical chat.txt files, and count."""
    source = Path(source)
    if not source.is_dir():
        raise ValueError(f"source directory does not exist: {source}")

    folders = sorted(path for path in source.iterdir() if path.is_dir())
    unique: list[dict[str, Any]] = []
    seen: dict[bytes, bytes] = {}
    sender_counts: Counter[str] = Counter()
    duplicates = 0
    for folder in folders:
        text_path, markdown_path = folder / "chat.txt", folder / "chat.md"
        if not text_path.is_file() or not markdown_path.is_file():
            raise ValueError(f"{folder.name}: expected paired chat.txt and chat.md exports")
        raw = text_path.read_bytes()
        digest = hashlib.sha256(raw).digest()
        if digest in seen and seen[digest] == raw:
            duplicates += 1
            continue
        seen[digest] = raw
        conversation = parse_conversation(folder, raw)
        sender_counts.update(message["sender"] for message in conversation["messages"])
        unique.append(conversation)

    return {
        "summary": {
            "folders": len(folders),
            "unique_conversations": len(unique),
            "messages_per_sender": dict(sorted(sender_counts.items())),
            "duplicates_skipped": duplicates,
        },
        "conversations": unique,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="directory containing paired chat.txt/chat.md exports")
    args = parser.parse_args(argv)
    try:
        extract = extract_source(args.source)
    except (OSError, ValueError) as exc:
        print(f"derive_conv_corpus: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(extract["summary"], ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
    json.dump(extract, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
