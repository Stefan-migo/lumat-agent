"""Exact-plan approval helpers for the assistant boundary."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone


class ApprovalDecisionError(ValueError):
    """The owner's project decision is missing or is not one this approval offers."""


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


def _offered_candidates(candidates) -> list[dict]:
    offered: list[dict] = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        slug = candidate.get("slug")
        if not isinstance(slug, str) or not slug:
            continue
        offered.append({
            "slug": slug,
            "name": str(candidate.get("name") or slug),
            "similarity": float(candidate.get("similarity") or 0.0),
        })
    return offered


def project_decision_envelope(tool: str | None, candidates=None) -> dict | None:
    """Describe the explicit decision a project approval needs, or None when it needs none.

    Only the two tools whose execution reads `decision` publish an envelope: nobody may be asked to
    answer a question the boundary will not look at. The candidates are the ones the server itself
    returned for this plan, so the client can echo a choice but never introduce one.

    `project.create` asks twice by design. Before the tool runs there is no conflict to inspect, so
    the first envelope offers only the consent to proceed (`create_distinct`); the service raises the
    informed gate when it actually finds a project with the same purpose, and that second envelope
    offers the candidate it found. Reusing a candidate or creating a deliberate duplicate
    (`create_anyway`) is therefore only answerable after the owner has seen what conflicts.
    """
    name = tool or ""
    if name not in {"project.find", "project.create"}:
        return None
    offered = _offered_candidates(candidates)
    if name == "project.find":
        # Without a candidate there is nothing to select, and an unanswerable approval is a trap.
        if not offered:
            return None
        return {"operation": "find", "options": ["selected_slug"], "candidates": offered}
    options = ["selected_slug", "create_anyway"] if offered else ["create_distinct"]
    return {"operation": "create", "options": options, "candidates": offered}


def validate_project_decision(envelope: dict | None, decision: object) -> dict:
    """Bind the owner's decision to the options this exact approval published.

    Returns the canonical decision the boundary accepts. Raises `ApprovalDecisionError` instead of
    guessing: an approval whose question went unanswered must not be consumed.
    """
    if not isinstance(envelope, dict):
        return {}
    options = [option for option in envelope.get("options") or [] if isinstance(option, str)]
    offered = {candidate["slug"] for candidate in _offered_candidates(envelope.get("candidates"))}
    if not isinstance(decision, dict) or not decision:
        raise ApprovalDecisionError("project decision required")
    if set(decision) == {"selected_slug"}:
        selected = decision["selected_slug"]
        if "selected_slug" not in options:
            raise ApprovalDecisionError("project decision is not offered by this approval")
        if not isinstance(selected, str) or selected not in offered:
            raise ApprovalDecisionError("project decision names a project this approval did not offer")
        return {"selected_slug": selected}
    if set(decision) == {"create_anyway"}:
        if "create_anyway" not in options or decision["create_anyway"] is not True:
            raise ApprovalDecisionError("project decision is not offered by this approval")
        return {"create_anyway": True}
    if set(decision) == {"create_distinct"}:
        if "create_distinct" not in options or decision["create_distinct"] is not True:
            raise ApprovalDecisionError("project decision is not offered by this approval")
        return {"create_distinct": True}
    raise ApprovalDecisionError("project decision is not offered by this approval")


def approved_project_binding(approval: dict, decision: dict) -> dict:
    """Bind an answered decision into the project payload the execution will validate.

    The plan's own arguments are already covered by `arguments_sha256`; this adds the decision the
    boundary requires and returns the digest that proves it, so the write that runs is exactly the
    one the owner answered -- never a decision reconstructed at execution time.
    """
    payload = approval.get("project_payload") if isinstance(approval.get("project_payload"), dict) else {}
    bound = {
        "operation": payload.get("operation"),
        "arguments": payload.get("arguments") or {},
        "decision": decision,
    }
    return {"payload": bound, "sha256": canonical_project_digest({"project_payload": bound})}


def issue_approval(plan: dict, *, expires_at: datetime | None = None, candidates=None) -> dict:
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
        envelope = project_decision_envelope(plan.get("tool"), candidates)
        if envelope is not None:
            # Outside `project_payload` on purpose: the decision is the answer to this envelope, not
            # part of the plan the owner sees approved, so it must not enter the plan's digest.
            approval["project_decision"] = envelope
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


def _execution_project_payload(plan: dict, approval: dict) -> dict:
    """The project payload this execution covers.

    `execute_tool` builds the payload from the plan and then, for project tools, uses the approval's
    own bound payload. A caller holding only the plan -- the graph's pre-execution check -- must
    resolve the same digest, or an answered decision would look like a tampered plan. The decision
    can never be forged here: it lives inside the approval, which only `approve_plan` mutates, and
    the operation and arguments still have to match the plan's.
    """
    if isinstance(plan.get("project_payload"), dict):
        return plan
    bound = approval.get("project_payload")
    if not isinstance(bound, dict):
        return plan
    tool, arguments = _bound_tool_arguments(plan)
    if bound.get("operation") != str(tool or "").removeprefix("project.") or bound.get("arguments") != arguments:
        return plan
    return {"project_payload": bound}


def validate_execution(plan: dict, approval: dict) -> bool:
    """Require a consumed approval matching the persisted plan exactly."""
    tool, arguments = _bound_tool_arguments(plan)
    valid = approval.get("status") == "consumed" and _approval_is_unexpired(approval)
    valid = valid and secrets.compare_digest(
        approval.get("arguments_sha256", ""), arguments_digest(tool, arguments)
    )
    if str(tool or "").startswith("project."):
        valid = valid and secrets.compare_digest(
            approval.get("project_sha256", ""), canonical_project_digest(_execution_project_payload(plan, approval))
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
