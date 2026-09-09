"""Small, side-effect-free assistant graph nodes."""

from __future__ import annotations

from app.chat.assistant.approval import issue_approval
from app.chat.assistant.evidence import make_evidence
from app.chat.assistant.state import AssistantState


def plan(state: AssistantState) -> AssistantState:
    content = state["content"].strip()
    requires_approval = any(word in content.casefold() for word in ("create", "delete", "change", "send"))
    proposed = {
        "tool": None,
        "arguments": {},
        "summary": content,
        "requires_approval": requires_approval,
    }
    return {"plan": proposed, "status": "approval_pending" if requires_approval else "planned"}


def approval_gate(state: AssistantState) -> AssistantState:
    plan_data = state["plan"]
    if plan_data["requires_approval"] and not state.get("approval"):
        return {"approval": issue_approval(plan_data), "status": "approval_pending"}
    return {"status": "approved" if plan_data["requires_approval"] else "executing"}


def execute(state: AssistantState) -> AssistantState:
    content = state["content"].strip()
    return {
        "tool_result": {"status": "completed", "tool": None},
        "response": f"I received your request: {content}",
        "status": "completed",
    }


def collect_evidence(state: AssistantState) -> AssistantState:
    return {
        "evidence": [make_evidence(tool=None, status="completed", detail="Assistant response generated")],
        "status": state.get("status", "completed"),
    }
