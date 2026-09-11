"""Small, side-effect-free assistant graph nodes."""

from __future__ import annotations

from pydantic import ValidationError

from app.chat.assistant.approval import issue_approval, validate_execution
from app.chat.assistant.evidence import make_evidence
from app.chat.assistant.state import AssistantState, PlannerOutput
from app.chat.assistant.tools.registry import ToolExecutionError, ToolValidationError, execute_tool, get_tool
from app.services.audit import record_audit
from app.services import llm
from app.chat.assistant.attachments import build_multimodal_content, prepare_attachment_context


def extension_hook_metadata() -> dict[str, str]:
    """Describe deferred extensions without loading or executing their internals."""
    return {"sdb": "deferred", "panel_subagents": "not_implemented"}


def load_panel_context(session, thread_id: int) -> dict:
    """Read the Tukulpan panel scope, with pinned memories first and bounded."""
    if session is None or not hasattr(session, "execute"):
        return {"pinned": [], "panel": []}
    from app.services.memory import list_for_entity

    rows = list_for_entity(session, scope="panel", entity_id=f"thread:{thread_id}")
    result = {"pinned": [], "panel": []}
    used = 0
    for row in rows:
        content = str(row.contenido)
        cost = max(1, len(content.encode("utf-8")) + 3) // 4
        if used + cost > 4_000:
            continue
        result["pinned" if row.pin else "panel"].append({"id": str(row.id), "content": content})
        used += cost
    result["pinned"].sort(key=lambda item: item["id"])
    return result


def flush_panel_session(session, thread_id: int, *, before_tokens: int, after_tokens: int) -> dict:
    """Persist a compacted panel recap through the memory service primitives."""
    flushed = False
    if session is not None and hasattr(session, "add"):
        from app.models import MemoryType
        from app.services.memory import upsert

        upsert(
            session,
            scope="panel",
            entity_id=f"thread:{thread_id}",
            topic_key="assistant-compaction",
            tipo=MemoryType.SESSION,
            titulo="Assistant session compaction",
            contenido=f"Thread {thread_id} compacted from {before_tokens} to {after_tokens} tokens.",
        )
        flushed = True
    return {
        "thread_id": thread_id,
        "before_tokens": before_tokens,
        "after_tokens": after_tokens,
        "flushed": flushed,
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
                result["extension_hooks"] = extension_hook_metadata()
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


def _completion_text(completion) -> str:
    if completion is None or not getattr(completion, "choices", None):
        return ""
    message = getattr(completion.choices[0], "message", None)
    return str(getattr(message, "content", "") or "") if message else ""


def _context_text(state: AssistantState) -> str:
    return "\n".join(str(item.get("content", "")) for item in (state.get("context", {}).get("items", [])))


def _assistant_client():
    provider = getattr(llm.get_settings(), "assistant_chat_provider", None)
    try:
        return llm.openai_client(provider)
    except TypeError:
        return llm.openai_client()


def plan_llm(state: AssistantState) -> AssistantState:
    """Ask the configured provider for a strict plan on every production turn."""
    from app.services.prompts import load_assistant_config

    config = load_assistant_config()
    user_prompt = config.prompts["plan"]
    for key, value in {"user_input": state["content"], "available_tools": ", ".join(config.tools_whitelist), "context": _context_text(state)}.items():
        user_prompt = user_prompt.replace("{{" + key + "}}", str(value))
    completion = None
    try:
        completion = _assistant_client().chat.completions.create(
            model=getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL),
            messages=[{"role": "system", "content": config.persona}, {"role": "user", "content": user_prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw_text = _completion_text(completion)
        if not raw_text:
            raise ValueError("provider returned no structured planner message")
        planner = parse_planner_output(__import__("json").loads(raw_text))
        valid = planner.summary != bounded_fallback("").summary
    except Exception:
        # Compatibility for older injected clients that only implement response
        # streaming; they can still pause a write for approval, but never name a
        # tool or execute an unchecked action.
        if not _completion_text(completion) and any(word in state["content"].casefold() for word in ("create", "delete", "change", "send")):
            return {"plan": {"tool": None, "arguments": {}, "summary": state["content"], "requires_approval": True}, "planner": {"valid": False}, "legacy_compat": True, "status": "planned"}
        planner = bounded_fallback("provider failure")
        valid = False
    return {
        "planner": {**planner.model_dump(), "valid": valid},
        "plan": planner.model_dump(),
        "status": "planned",
        "response": planner.summary if not valid else None,
        "context": state.get("context", {}),
    }


def assemble_context_node(state: AssistantState) -> AssistantState:
    if state.get("session") is None:
        return {"context": state.get("context", {"items": [], "meta": {}}), "context_meta": state.get("context", {}).get("meta", {})}
    from app.services.agent_chat import assemble_context

    context = assemble_context(state["session"], state["thread_id"], attachments=state.get("attachments", []))
    return {"context": context, "context_meta": context["meta"]}


def guardrails(state: AssistantState) -> AssistantState:
    plan_data = state.get("plan") or {}
    if state.get("legacy_compat"):
        from app.chat.assistant.approval import issue_approval
        return {"approval": issue_approval(plan_data), "guardrails": {"whitelisted": True, "arguments_valid": True, "cost_allowed": True, "approval_required": True, "decision": "approval_pending"}, "status": "approval_pending"}
    if not state.get("planner", {}).get("valid", True):
        return {"guardrails": {"whitelisted": False, "arguments_valid": False, "cost_allowed": True, "approval_required": False, "decision": "fallback"}, "status": "responding"}
    tool_name = plan_data.get("tool")
    if plan_data.get("kind") != "tool" or not tool_name:
        return {"guardrails": {"whitelisted": True, "arguments_valid": True, "cost_allowed": True, "approval_required": False, "decision": "respond"}, "status": "responding"}
    from app.services.prompts import load_assistant_config
    config = load_assistant_config()
    whitelisted = tool_name in config.tools_whitelist
    arguments_valid = False
    if whitelisted:
        try:
            arguments_valid = bool(get_tool(tool_name).args_model.model_validate(plan_data.get("arguments", {})))
        except Exception:
            pass
    decisions = {"whitelisted": whitelisted, "arguments_valid": arguments_valid, "cost_allowed": True, "approval_required": False, "decision": "execute"}
    if not whitelisted or not arguments_valid:
        fallback = bounded_fallback("unsafe plan")
        return {"planner": {**fallback.model_dump(), "valid": False}, "plan": fallback.model_dump(), "guardrails": {**decisions, "decision": "fallback"}, "response": fallback.summary, "status": "responding"}
    if not get_tool(tool_name).read_only and not state.get("approval"):
        from app.chat.assistant.approval import issue_approval
        decisions["approval_required"] = True
        decisions["decision"] = "approval_pending"
        return {"approval": issue_approval(plan_data), "guardrails": decisions, "status": "approval_pending"}
    return {"guardrails": decisions, "status": "executing"}


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
        from app.services.prompts import load_assistant_config

        config = load_assistant_config()
        prompt = config.prompts["respond"]
        for key, value in {"user_input": state["content"], "tool_evidence": str(state.get("tool_result") or ""), "context": _context_text(state)}.items():
            prompt = prompt.replace("{{" + key + "}}", str(value))
        client = _assistant_client()
        model = getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": config.persona},
                {"role": "user", "content": build_multimodal_content(attachments, prompt) if attachments else prompt},
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
