"""Tolerant reader for the planner's JSON payload.

The provider is asked for `response_format={"type": "json_object"}`, but DeepSeek does not honour it
reliably: two real turns failed with a raw control character inside a string (thread 79) and with a
valid object followed by prose (thread 80). A turn that lost its plan to a stray newline is a lost
turn, so the payload is read defensively before it is validated strictly.
"""

from __future__ import annotations

import json

_CONTROL_ESCAPES = {
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
}


def _escape_control_characters(candidate: str) -> str:
    """Escape raw control characters that sit inside a JSON string literal.

    JSON forbids unescaped control characters (U+0000 through U+001F) inside a string, and
    `json.loads` rejects the whole document for one stray newline. Outside a string the same
    characters are ordinary whitespace, so only string literals are rewritten.
    """
    out: list[str] = []
    in_string = False
    escaped = False
    for char in candidate:
        if in_string:
            if escaped:
                escaped = False
                out.append(char)
                continue
            if char == "\\":
                escaped = True
                out.append(char)
                continue
            if char == '"':
                in_string = False
                out.append(char)
                continue
            if ord(char) < 0x20:
                out.append(_CONTROL_ESCAPES.get(char, f"\\u{ord(char):04x}"))
                continue
            out.append(char)
            continue
        if char == '"':
            in_string = True
        out.append(char)
    return "".join(out)


def _first_object_span(text: str) -> str | None:
    """Return the first balanced `{...}` object, ignoring braces inside strings."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _strip_code_fence(text: str) -> str:
    """Unwrap a ```json ... ``` answer the model added on its own."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    body = stripped[3:]
    if body[:4].lower() == "json":
        body = body[4:]
    end = body.rfind("```")
    if end != -1:
        body = body[:end]
    return body.strip()


def load_planner_payload(raw_text: str) -> object:
    """Read one planner JSON object out of a provider answer.

    Raises `json.JSONDecodeError` when no object can be read, so the caller keeps its existing
    `invalid_json` diagnosis and its bounded fallback.
    """
    text = _strip_code_fence(raw_text)
    candidate = _first_object_span(text) or text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as original:
        repaired = _escape_control_characters(candidate)
        if repaired == candidate:
            raise
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            raise original from None
