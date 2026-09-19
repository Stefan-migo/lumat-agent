"""Remove native tool-call markup from text-only assistant responses."""

import re


_BAR = r"(?:\uff5c{1,2}|\|)"
_KIND = r"(?:tool_calls|function_calls?|tool_use_error)"
_OPEN_PREFIX = rf"<{_BAR}?"
_CLOSE_PREFIX = rf"<(?:/{_BAR}?|{_BAR}?/)"
_WRAPPER_OPEN = rf"{_OPEN_PREFIX}\s*(?P<kind>{_KIND})(?:\s+[^<>]*)?\s*{_BAR}?>"
_WRAPPER_CLOSE = rf"{_CLOSE_PREFIX}\s*(?P<close_kind>{_KIND})(?:\s+[^<>]*)?\s*{_BAR}?>"
_INVOKE_OPEN = rf'{_OPEN_PREFIX}\s*invoke\s+name\s*=\s*["\'][^"\']*["\']\s*{_BAR}?>'
_INVOKE_CLOSE = rf"{_CLOSE_PREFIX}\s*invoke\s*{_BAR}?>"
_PARAMETER_OPEN = rf'{_OPEN_PREFIX}\s*parameter\s+name\s*=\s*["\'][^"\']*["\']\s+string\s*=\s*["\'](?:true|false)["\']\s*{_BAR}?>'
_PARAMETER_CLOSE = rf"{_CLOSE_PREFIX}\s*parameter\s*{_BAR}?>"

_WRAPPER_COMPLETE = re.compile(
    rf"{_OPEN_PREFIX}\s*(?P<kind>{_KIND})(?:\s+[^<>]*)?\s*{_BAR}?>"
    rf".*?{_CLOSE_PREFIX}\s*(?P=kind)(?:\s+[^<>]*)?\s*{_BAR}?>",
    re.IGNORECASE | re.DOTALL,
)
_WRAPPER_OPEN_TO_END = re.compile(rf"{_WRAPPER_OPEN}.*\Z", re.IGNORECASE | re.DOTALL)
_INVOKE_COMPLETE = re.compile(
    rf"{_INVOKE_OPEN}.*?{_INVOKE_CLOSE}",
    re.IGNORECASE | re.DOTALL,
)
_INVOKE_OPEN_TO_END = re.compile(rf"{_INVOKE_OPEN}.*\Z", re.IGNORECASE | re.DOTALL)
_MARKER = re.compile(
    rf"(?:{_WRAPPER_OPEN}|{_WRAPPER_CLOSE}|{_INVOKE_OPEN}|{_INVOKE_CLOSE}|"
    rf"{_PARAMETER_OPEN}|{_PARAMETER_CLOSE})",
    re.IGNORECASE,
)
_STREAM_OPEN = re.compile(rf"(?:{_WRAPPER_OPEN}|{_INVOKE_OPEN})", re.IGNORECASE)
_WRAPPER_END = re.compile(_WRAPPER_CLOSE, re.IGNORECASE)
_INVOKE_END = re.compile(_INVOKE_CLOSE, re.IGNORECASE)


def strip_tool_call_markup(text: str) -> str:
    """Strip complete DSML blocks, incomplete wrappers, and marker tags."""
    text = _WRAPPER_COMPLETE.sub("", text)
    text = _INVOKE_COMPLETE.sub("", text)
    text = _WRAPPER_OPEN_TO_END.sub("", text)
    text = _INVOKE_OPEN_TO_END.sub("", text)
    return _MARKER.sub("", text)


class ToolCallMarkupSanitizer:
    """Sanitize chunks while retaining a bounded possible marker suffix."""

    _TAIL_LIMIT = 512
    _SUPPRESS_TAIL_LIMIT = 256

    def __init__(self) -> None:
        self._tail = ""
        self._suppressing = False
        self._suppressing_invoke = False

    def feed(self, chunk: str) -> str:
        if self._suppressing:
            end_pattern = _INVOKE_END if self._suppressing_invoke else _WRAPPER_END
            combined = self._tail + chunk
            end = end_pattern.search(combined)
            if end is None:
                self._tail = combined[-self._SUPPRESS_TAIL_LIMIT:]
                return ""
            self._tail = ""
            self._suppressing = False
            self._suppressing_invoke = False
            return self.feed(combined[end.end():])

        combined = self._tail + chunk
        stream_start = _STREAM_OPEN.search(combined)
        if stream_start is not None:
            is_invoke = "invoke" in stream_start.group().lower()
            end_pattern = _INVOKE_END if is_invoke else _WRAPPER_END
            if end_pattern.search(combined, stream_start.end()) is None:
                self._tail = ""
                self._suppressing = True
                self._suppressing_invoke = is_invoke
                return strip_tool_call_markup(combined[:stream_start.start()])

        cleaned = strip_tool_call_markup(combined)
        marker_start = cleaned.rfind("<")
        if marker_start < 0:
            self._tail = ""
            return cleaned
        possible_tail = cleaned[marker_start:]
        if len(possible_tail) <= self._TAIL_LIMIT and ">" not in possible_tail:
            self._tail = possible_tail
            return cleaned[:marker_start]
        self._tail = ""
        return cleaned

    def flush(self) -> str:
        tail = self._tail
        self._tail = ""
        self._suppressing = False
        self._suppressing_invoke = False
        return strip_tool_call_markup(tail)
