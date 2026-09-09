"""Small, side-effect-free assistant graph nodes."""

from __future__ import annotations

from app.chat.assistant.approval import issue_approval, validate_execution
from app.chat.assistant.evidence import make_evidence
from app.chat.assistant.state import AssistantState
from app.services.audit import record_audit
from app.services import llm


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
    plan_data = state["plan"]
    if plan_data["requires_approval"] and not validate_execution(plan_data, state.get("approval") or {}):
        raise PermissionError("approval is missing, expired, tampered, or already consumed")
    content = state["content"].strip()
    response = f"I received your request: {content}"
    on_token = state.get("on_token")
    if on_token is not None:
        completion = llm.openai_client().chat.completions.create(
            model=llm.CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are Lumat's internal operations assistant."},
                {"role": "user", "content": content},
            ],
            temperature=0,
            stream=True,
        )
        chunks: list[str] = []
        for chunk in completion:
            token = chunk.choices[0].delta.content or ""
            if token:
                chunks.append(token)
                on_token(token)
        response = "".join(chunks) or response
    session = state.get("session")
    if session is not None:
        record_audit(
            session,
            actor=state.get("actor") or "assistant",
            action="internal_chat.execution",
            entity="internal_chat_thread",
            entity_id=str(state["thread_id"]),
            after={"run_id": state["run_id"], "tool": plan_data.get("tool"), "status": "completed"},
        )
    return {
        "tool_result": {"status": "completed", "tool": None},
        "response": response,
        "status": "completed",
    }


def collect_evidence(state: AssistantState) -> AssistantState:
    return {
        "evidence": [make_evidence(tool=None, status="completed", detail="Assistant response generated")],
        "status": state.get("status", "completed"),
    }
