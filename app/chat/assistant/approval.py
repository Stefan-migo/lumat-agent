"""Exact-plan approval helpers for the assistant boundary."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone


def arguments_digest(tool: str | None, arguments: dict) -> str:
    payload = json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def canonical_sdb_payload(payload: dict) -> dict:
    """Select the phase/spec/tasks fields that an SDB approval covers."""
    return {
        "phase": payload.get("phase"),
        "spec": payload.get("spec") or {},
        "tasks": payload.get("tasks") or [],
    }


def canonical_sdb_digest(payload: dict) -> str:
    """Return a fixed-size digest for the complete canonical SDB payload."""
    encoded = json.dumps(
        canonical_sdb_payload(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def issue_approval(plan: dict, *, expires_at: datetime | None = None) -> dict:
    token = secrets.token_urlsafe(24)
    expiry = expires_at or (datetime.now(timezone.utc) + timedelta(minutes=15))
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    approval = {
        "token": token,
        "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
        "tool": plan.get("tool"),
        "arguments": plan.get("arguments", {}),
        "arguments_sha256": arguments_digest(plan.get("tool"), plan.get("arguments", {})),
        "expires_at": expiry.isoformat(),
        "status": "pending",
    }
    sdb = plan.get("sdb")
    if isinstance(sdb, dict):
        approval["sdb_sha256"] = canonical_sdb_digest(sdb)
        approval["spec_sha256"] = sdb.get("spec", {}).get("sha256", "")
    return approval


def validate_approval(plan: dict, approval: dict, token: str) -> bool:
    expected = hashlib.sha256(token.encode()).hexdigest()
    try:
        expires_at = datetime.fromisoformat(approval.get("expires_at", ""))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return False
    valid = (
        approval.get("status") == "pending"
        and datetime.now(timezone.utc) < expires_at
        and secrets.compare_digest(approval.get("token_sha256", ""), expected)
        and secrets.compare_digest(
            approval.get("arguments_sha256", ""),
            arguments_digest(plan.get("tool"), plan.get("arguments", {})),
        )
    )
    sdb = plan.get("sdb")
    if isinstance(sdb, dict):
        valid = valid and secrets.compare_digest(
            approval.get("sdb_sha256", ""), canonical_sdb_digest(sdb)
        )
        valid = valid and secrets.compare_digest(
            str(approval.get("spec_sha256", "")), str(sdb.get("spec", {}).get("sha256", ""))
        )
    return valid


def consume_approval(approval: dict, token: str) -> bool:
    """Consume an approval once after validating its token and exact payload."""
    if not validate_approval(
        {"tool": approval.get("tool"), "arguments": approval.get("arguments", {})},
        approval,
        token,
    ):
        return False
    approval["status"] = "consumed"
    approval["consumed_at"] = datetime.now(timezone.utc).isoformat()
    return True


def validate_execution(plan: dict, approval: dict) -> bool:
    """Require a consumed approval matching the persisted plan exactly."""
    valid = (
        approval.get("status") == "consumed"
        and secrets.compare_digest(
            approval.get("arguments_sha256", ""),
            arguments_digest(plan.get("tool"), plan.get("arguments", {})),
        )
    )
    sdb = plan.get("sdb")
    if isinstance(sdb, dict):
        valid = valid and secrets.compare_digest(
            approval.get("sdb_sha256", ""), canonical_sdb_digest(sdb)
        )
        valid = valid and secrets.compare_digest(
            str(approval.get("spec_sha256", "")), str(sdb.get("spec", {}).get("sha256", ""))
        )
    return valid
