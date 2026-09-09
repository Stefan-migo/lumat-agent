"""Evidence records emitted by assistant executions."""

from __future__ import annotations


def make_evidence(*, tool: str | None, status: str, detail: str) -> dict:
    return {"tool": tool, "status": status, "detail": detail}
