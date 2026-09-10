"""Small, side-effect-free assistant graph nodes."""

from __future__ import annotations

from pydantic import ValidationError

from app.chat.assistant.approval import issue_approval, validate_execution
from app.chat.assistant.evidence import make_evidence
from app.chat.assistant.state import AssistantState, PlannerOutput
from app.chat.assistant.tools.registry import ToolExecutionError, ToolValidationError, execute_tool
from app.services.audit import record_audit
from app.services import llm
from app.chat.assistant.attachments import build_multimodal_content, prepare_attachment_context


def load_panel_context(session, thread_id: int) -> dict:
    """Tukulpan seam: expose only panel-scoped and pinned context."""
    return {"pinned": [], "panel": []}


def flush_panel_session(session, thread_id: int, *, before_tokens: int, after_tokens: int) -> dict:
    """Tukulpan seam for future memory flushing; it never executes hooks."""
    return {
        "thread_id": thread_id,
        "before_tokens": before_tokens,
        "after_tokens": after_tokens,
        "flushed": False,
    }


def bounded_fallback(reason: str) -> PlannerOutput:
    """Return a safe, short response plan for malformed planner output."""
    return PlannerOutput(
        kind="respond",
        arguments={},
        summary="I could not safely plan that request. Please try again.",
        requires_approval=False,
    )


def parse_planner_output(raw: object) -> PlannerOutput:
    """Validate planner data and convert invalid data to a bounded response."""
    try:
        return PlannerOutput.model_validate(raw)
    except (TypeError, ValidationError):
        return bounded_fallback("invalid planner output")


def plan(state: AssistantState) -> AssistantState:
    content = state["content"].strip()
    raw = state.get("planner_output")
    if raw is not None:
        try:
            planner = PlannerOutput.model_validate(raw)
            planner_data = {**planner.model_dump(), "valid": True}
            result: AssistantState = {
                "planner": planner_data,
                "plan": planner.model_dump(),
                "status": "planned",
            }
            if planner.kind == "complex":
                result["extension_hooks"] = {"sdb": "deferred", "panel_subagents": "not_implemented"}
            return result
        except (TypeError, ValidationError):
            fallback = bounded_fallback("invalid planner output")
            return {
                "planner": {**fallback.model_dump(), "valid": False},
                "plan": fallback.model_dump(),
                "status": "planned",
                "response": fallback.summary,
                "error": "Invalid planner output.",
            }
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
        detail = "approval is missing, expired, tampered, or already consumed"
        evidence = make_evidence(tool=plan_data.get("tool"), status="error", detail=detail)
        state.setdefault("evidence", []).append(evidence)
        session = state.get("session")
        if session is not None:
            record_audit(
                session,
                actor=state.get("actor") or "assistant",
                action="internal_chat.execution_rejected",
                entity="internal_chat_thread",
                entity_id=str(state.get("thread_id")),
                after={"run_id": state.get("run_id"), "tool": plan_data.get("tool"), "reason": detail},
            )
        error = PermissionError(detail)
        error.evidence = [evidence]
        raise error
    tool_name = plan_data.get("tool")
    if tool_name:
        try:
            from app.services.prompts import load_assistant_config

            config = load_assistant_config()
            result = execute_tool(
                state.get("session"),
                tool_name,
                plan_data.get("arguments", {}),
                approval=state.get("approval"),
                whitelist=set(config.tools_whitelist),
                cost_allowed=state.get("guardrails", {}).get("cost_allowed", True),
            )
        except (ToolExecutionError, ToolValidationError) as exc:
            detail = str(exc)
            if state.get("session") is not None:
                record_audit(
                    state["session"], actor=state.get("actor") or "assistant",
                    action="internal_chat.execution", entity="internal_chat_thread",
                    entity_id=str(state.get("thread_id")),
                    after={"run_id": state.get("run_id"), "tool": tool_name, "status": "error"},
                )
            return {
                "tool_result": {"tool": tool_name, "status": "error", "error": detail},
                "evidence": [make_evidence(tool=tool_name, status="error", detail=detail)],
                "error": detail,
                "response": f"Tool execution failed: {detail}",
                "status": "error",
            }
        if result.get("status") == "error":
            detail = result.get("error", "tool failed")
            return {
                "tool_result": result,
                "evidence": [make_evidence(tool=tool_name, status="error", detail=detail)],
                "error": detail,
                "response": f"Tool execution failed: {detail}",
                "status": "error",
            }
        if state.get("session") is not None:
            record_audit(
                state["session"], actor=state.get("actor") or "assistant",
                action="internal_chat.execution", entity="internal_chat_thread",
                entity_id=str(state.get("thread_id")),
                after={"run_id": state.get("run_id"), "tool": tool_name, "status": "completed"},
            )
        return {
            "tool_result": result,
            "evidence": [make_evidence(tool=tool_name, status="completed", detail="Tool execution completed")],
            "response": f"Tool {tool_name} completed.",
            "status": "completed",
        }
    attachments = state.get("attachments") or []
    documents = prepare_attachment_context(attachments)
    content = state["content"].strip()
    if documents:
        content += "\n\n<attachments>\n" + "\n".join(
            f'[attachment filename="{d["filename"]}" id="{d["attachment_id"]}" type="{d["kind"]}"]\n{d["text"]}\n[/attachment]'
            for d in documents
        ) + "\n</attachments>"
    session = state.get("session")
    if attachments and session is not None:
        record_audit(session, actor=state.get("actor") or "assistant", action="internal_chat.attachments_used",
                     entity="internal_chat_thread", entity_id=str(state["thread_id"]),
                     after={"run_id": state.get("run_id"), "attachment_ids": [getattr(row, "id", None) for row in attachments]})
    response = f"I received your request: {content}"
    on_token = state.get("on_token")
    if on_token is not None:
        client = llm.openai_client(getattr(llm.get_settings(), "assistant_chat_provider", None)) if attachments else llm.openai_client()
        model = getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL) if attachments else llm.CHAT_MODEL
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are Lumat's internal operations assistant."},
                {"role": "user", "content": build_multimodal_content(attachments, content) if attachments else content},
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
    if state.get("evidence"):
        return {"evidence": state["evidence"], "status": state.get("status", "completed")}
    return {
        "evidence": [make_evidence(tool=None, status="completed", detail="Assistant response generated")],
        "status": state.get("status", "completed"),
    }
