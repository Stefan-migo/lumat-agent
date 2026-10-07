"""Exact-plan approval helpers for the assistant boundary."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone


def arguments_digest(tool: str | None, arguments: dict, *, order: int | None = None, task_id: str | None = None) -> str:
    payload = {"tool": tool, "arguments": arguments}
    if order is not None or task_id is not None:
        payload = {"order": order, "task_id": task_id, **payload}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _bound_tool_arguments(plan: dict) -> tuple[str | None, dict]:
    return plan.get("tool"), plan.get("arguments") or {}


def canonical_project_payload(payload: dict) -> dict:
    """Select the exact project operation covered by an approval."""
    explicit = payload.get("project_payload")
    if isinstance(explicit, dict):
        return explicit
    tool = payload.get("tool") or ""
    return {
        "operation": tool.removeprefix("project.") if tool.startswith("project.") else tool,
        "arguments": payload.get("arguments") or {},
    }


def canonical_project_digest(payload: dict) -> str:
    encoded = json.dumps(
        canonical_project_payload(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def issue_approval(plan: dict, *, expires_at: datetime | None = None) -> dict:
    token = secrets.token_urlsafe(24)
    expiry = expires_at or (datetime.now(timezone.utc) + timedelta(minutes=15))
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    tool = plan.get("tool")
    arguments = plan.get("arguments") or {}
    approval = {
        "token": token,
        "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
        "tool": tool,
        "arguments": arguments,
        "arguments_sha256": arguments_digest(tool, arguments),
        "expires_at": expiry.isoformat(),
        "status": "pending",
    }
    if str(plan.get("tool", "")).startswith("project."):
        approval["project_payload"] = canonical_project_payload(plan)
        approval["project_sha256"] = canonical_project_digest(plan)
    return approval


def validate_approval(plan: dict, approval: dict, token: str) -> bool:
    expected = hashlib.sha256(token.encode()).hexdigest()
    try:
        expires_at = datetime.fromisoformat(approval.get("expires_at", ""))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return False
    tool, arguments = _bound_tool_arguments(plan)
    valid = (
        approval.get("status") == "pending"
        and datetime.now(timezone.utc) < expires_at
        and secrets.compare_digest(approval.get("token_sha256", ""), expected)
    )
    valid = valid and secrets.compare_digest(
        approval.get("arguments_sha256", ""), arguments_digest(tool, arguments)
    )
    if str(plan.get("tool", "")).startswith("project."):
        valid = valid and secrets.compare_digest(
            approval.get("project_sha256", ""), canonical_project_digest(plan)
        )
    return valid


def consume_approval(approval: dict, token: str) -> bool:
    """Consume an approval once after validating its token and exact payload."""
    plan = {"tool": approval.get("tool"), "arguments": approval.get("arguments", {})}
    if isinstance(approval.get("project_payload"), dict):
        plan["project_payload"] = approval["project_payload"]
    if not validate_approval(
        plan,
        approval,
        token,
    ):
        return False
    approval["status"] = "consumed"
    approval["consumed_at"] = datetime.now(timezone.utc).isoformat()
    return True


def validate_execution(plan: dict, approval: dict) -> bool:
    """Require a consumed approval matching the persisted plan exactly."""
    tool, arguments = _bound_tool_arguments(plan)
    valid = approval.get("status") == "consumed" and _approval_is_unexpired(approval)
    valid = valid and secrets.compare_digest(
        approval.get("arguments_sha256", ""), arguments_digest(tool, arguments)
    )
    if str(tool or "").startswith("project."):
        valid = valid and secrets.compare_digest(
            approval.get("project_sha256", ""), canonical_project_digest(plan)
        )
    return valid


def _approval_is_unexpired(approval: dict) -> bool:
    try:
        expires_at = datetime.fromisoformat(approval.get("expires_at", ""))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return False
    return datetime.now(timezone.utc) < expires_at
