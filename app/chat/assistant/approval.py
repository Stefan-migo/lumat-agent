"""Exact-plan approval helpers for the assistant boundary."""

from __future__ import annotations

import hashlib
import json
import secrets


def arguments_digest(tool: str | None, arguments: dict) -> str:
    payload = json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def issue_approval(plan: dict) -> dict:
    token = secrets.token_urlsafe(24)
    return {
        "token": token,
        "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
        "arguments_sha256": arguments_digest(plan.get("tool"), plan.get("arguments", {})),
        "status": "pending",
    }


def validate_approval(plan: dict, approval: dict, token: str) -> bool:
    expected = hashlib.sha256(token.encode()).hexdigest()
    return (
        approval.get("status") == "pending"
        and secrets.compare_digest(approval.get("token_sha256", ""), expected)
        and secrets.compare_digest(
            approval.get("arguments_sha256", ""),
            arguments_digest(plan.get("tool"), plan.get("arguments", {})),
        )
    )
