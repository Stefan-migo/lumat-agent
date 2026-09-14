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


def _sdb_bindings(payload: dict) -> list[dict]:
    bindings = []
    for order, task in enumerate(payload.get("tasks") or []):
        if not isinstance(task, dict):
            continue
        tool = task.get("tool")
        arguments = task.get("arguments") or {}
        binding = {
            "order": order,
            "task_id": task.get("id"),
            "tool": tool,
            "arguments": arguments,
            "arguments_sha256": arguments_digest(
                tool, arguments, order=order, task_id=task.get("id")
            ),
        }
        if isinstance(tool, str) and tool.startswith("project."):
            project_payload = canonical_project_payload({
                "tool": tool,
                "arguments": arguments,
                "project_payload": task.get("project_payload") or (
                    {"operation": tool.removeprefix("project."), "arguments": arguments, "decision": task["decision"]}
                    if "decision" in task else None
                ),
            })
            binding["project_payload"] = project_payload
            binding["project_sha256"] = canonical_project_digest({"project_payload": project_payload})
        bindings.append(binding)
    return bindings


def canonical_sdb_payload(payload: dict) -> dict:
    """Select the phase/spec/tasks fields that an SDB approval covers."""
    return {
        "phase": payload.get("phase"),
        "spec": payload.get("spec") or {},
        "tasks": payload.get("tasks") or [],
        "sdb_bindings": _sdb_bindings(payload),
    }


def canonical_sdb_digest(payload: dict) -> str:
    """Return a fixed-size digest for the complete canonical SDB payload."""
    encoded = json.dumps(
        canonical_sdb_payload(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def _bound_tool_arguments(plan: dict) -> tuple[str | None, dict]:
    sdb = plan.get("sdb")
    task = (sdb or {}).get("tasks", [])[0] if isinstance(sdb, dict) else {}
    return plan.get("tool") or task.get("tool"), plan.get("arguments") or task.get("arguments", {})


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
    sdb = plan.get("sdb")
    task = (sdb or {}).get("tasks", [])[0] if isinstance(sdb, dict) else {}
    tool = plan.get("tool") or task.get("tool")
    arguments = plan.get("arguments") or task.get("arguments", {})
    bindings = _sdb_bindings(sdb) if isinstance(sdb, dict) else []
    approval = {
        "token": token,
        "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
        "tool": tool,
        "arguments": arguments,
        "arguments_sha256": bindings[0]["arguments_sha256"] if bindings else arguments_digest(tool, arguments),
        "expires_at": expiry.isoformat(),
        "status": "pending",
    }
    if isinstance(sdb, dict):
        approval["sdb_bindings"] = bindings
        approval["sdb_payload"] = {**canonical_sdb_payload(sdb), "sdb_bindings": bindings}
        approval["sdb_sha256"] = canonical_sdb_digest({**sdb, "sdb_bindings": bindings})
        approval["spec_sha256"] = sdb.get("spec", {}).get("sha256", "")
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
    sdb = plan.get("sdb")
    if isinstance(sdb, dict):
        valid = valid and approval.get("sdb_bindings") == _sdb_bindings(sdb)
        valid = valid and secrets.compare_digest(
            approval.get("sdb_sha256", ""), canonical_sdb_digest(sdb)
        )
        valid = valid and secrets.compare_digest(
            str(approval.get("spec_sha256", "")), str(sdb.get("spec", {}).get("sha256", ""))
        )
    else:
        valid = valid and secrets.compare_digest(
            approval.get("arguments_sha256", ""), arguments_digest(tool, arguments)
        )
    if str(plan.get("tool", "")).startswith("project.") and not isinstance(sdb, dict):
        valid = valid and secrets.compare_digest(
            approval.get("project_sha256", ""), canonical_project_digest(plan)
        )
    return valid


def consume_approval(approval: dict, token: str) -> bool:
    """Consume an approval once after validating its token and exact payload."""
    plan = {"tool": approval.get("tool"), "arguments": approval.get("arguments", {})}
    if isinstance(approval.get("sdb_payload"), dict):
        plan["sdb"] = approval["sdb_payload"]
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
    sdb = plan.get("sdb")
    if isinstance(sdb, dict):
        expected_bindings = _sdb_bindings(sdb)
        valid = valid and approval.get("sdb_bindings") == expected_bindings
        binding = plan.get("task_binding")
        if not isinstance(binding, dict):
            binding = next(
                (item for item in expected_bindings if item["tool"] == tool and item["arguments"] == arguments),
                None,
            )
        valid = valid and isinstance(binding, dict) and binding in approval.get("sdb_bindings", [])
        if isinstance(binding, dict):
            valid = valid and binding.get("tool") == tool and binding.get("arguments") == arguments
            valid = valid and binding.get("arguments_sha256") == arguments_digest(
                tool, arguments, order=binding.get("order"), task_id=binding.get("task_id")
            )
            if str(tool or "").startswith("project."):
                project_payload = binding.get("project_payload")
                valid = valid and isinstance(project_payload, dict)
                valid = valid and secrets.compare_digest(
                    binding.get("project_sha256", ""),
                    canonical_project_digest({"project_payload": project_payload})
                    if isinstance(project_payload, dict) else "0",
                )
        valid = valid and secrets.compare_digest(
            approval.get("sdb_sha256", ""), canonical_sdb_digest(sdb)
        )
        valid = valid and secrets.compare_digest(
            str(approval.get("spec_sha256", "")), str(sdb.get("spec", {}).get("sha256", ""))
        )
    else:
        valid = valid and secrets.compare_digest(
            approval.get("arguments_sha256", ""), arguments_digest(tool, arguments)
        )
    if str(tool or "").startswith("project.") and not isinstance(sdb, dict):
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
