"""Exact-plan approval helpers for the assistant boundary."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone


def arguments_digest(tool: str | None, arguments: dict) -> str:
    payload = json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def issue_approval(plan: dict, *, expires_at: datetime | None = None) -> dict:
    token = secrets.token_urlsafe(24)
    expiry = expires_at or (datetime.now(timezone.utc) + timedelta(minutes=15))
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return {
        "token": token,
        "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
        "arguments_sha256": arguments_digest(plan.get("tool"), plan.get("arguments", {})),
        "expires_at": expiry.isoformat(),
        "status": "pending",
    }


def validate_approval(plan: dict, approval: dict, token: str) -> bool:
    expected = hashlib.sha256(token.encode()).hexdigest()
    try:
        expires_at = datetime.fromisoformat(approval.get("expires_at", ""))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return False
    return (
        approval.get("status") == "pending"
        and datetime.now(timezone.utc) < expires_at
        and secrets.compare_digest(approval.get("token_sha256", ""), expected)
        and secrets.compare_digest(
            approval.get("arguments_sha256", ""),
            arguments_digest(plan.get("tool"), plan.get("arguments", {})),
        )
    )
