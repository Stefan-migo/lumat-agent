"""Small, side-effect-free assistant graph nodes."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import re
from pydantic import ValidationError

from app.chat.assistant.approval import validate_execution
from app.chat.assistant.evidence import make_evidence
from app.chat.assistant.state import AssistantState, PlannerOutput, estimate_tokens, validate_cortex_session
from app.chat.assistant.tools.registry import ToolExecutionError, ToolValidationError, execute_tool, get_tool
from app.services.audit import record_audit
from app.services import llm
from app.services.costs import (
    combined_cost_mode,
    daily_cost_state,
    daily_spend,
    internal_thread_cost_state,
    internal_thread_spend,
    maybe_alert_owner,
    record_llm_cost,
)
from app.chat.assistant.attachments import build_multimodal_content, prepare_attachment_context
from app.models import InternalChatMessage


def _project_slug(state: AssistantState) -> str:
    """Read the namespace only from the service-issued project capability."""
    authorization = state.get("project_authorization")
    if authorization is None:
        return "default"
    from app.services.projects import _ProjectAuthorization

    if not isinstance(authorization, _ProjectAuthorization):
        raise ValueError("SDB project selection requires an authorized project capability")
    return authorization.slug


def extension_hook_metadata() -> dict[str, str]:
    """Describe deferred extensions without loading or executing their internals."""
    return {"sdb": "deferred", "panel_subagents": "not_implemented"}


_PLANNING_COMMAND = re.compile(r"^/planning(?: ([^\s].*?))?$")


def parse_planning_command(content: str) -> dict[str, str | None] | None:
    """Parse only the exact planning command forms; ordinary text is inert."""
    if not isinstance(content, str):
        return None
    match = _PLANNING_COMMAND.fullmatch(content)
    if not match or not match.group(1):
        return None
    topic = match.group(1)
    if topic == "close":
        return {"action": "close", "topic": None}
    return {"action": "open", "topic": topic}


def cortex_session_gate(state: AssistantState) -> AssistantState:
    """Route only a valid active thread flag; missing state fails closed."""
    if not validate_cortex_session(state):
        return {"cortex_route": "normal", "cortex_rejection": "invalid-session"}
    if state["cortex_session"]["status"] != "active":
        return {"cortex_route": "normal", "cortex_rejection": "inactive-session"}
    return {"cortex_route": "cortex", "cortex_rejection": None}


def classify_cortex_turn(content: str) -> str:
    """Classify the bounded Cortex loop without inferring lifecycle changes."""
    text = content.strip()
    if text == "/planning close":
        return "close"
    lowered = text.casefold()
    if "?" in text or lowered.startswith(("what ", "why ", "how ")):
        return "question"
    if lowered.startswith(("research ", "investigate ", "look up ")):
        return "research"
    if lowered.startswith(("decide ", "we will ", "let's use ", "use ")):
        return "decision"
    return "continue"


def cortex_session_turn(state: AssistantState) -> AssistantState:
    """Advance an active Cortex session; questions/research need no decision."""
    current = dict(state["cortex_session"])
    turn_class = (state.get("planner") or {}).get("cortex_class") or classify_cortex_turn(state.get("content", ""))
    index = current.get("turn_index", 0) + 1
    current.update({"turn_index": index, "last_class": turn_class})
    result: AssistantState = {
        "cortex_session": current,
        "response": "Cortex session closed." if turn_class == "close" else state.get("content", ""),
        "status": "completed",
    }
    if turn_class == "close":
        current.update({"status": "closed", "closed_at": datetime.now(timezone.utc).isoformat()})
    elif turn_class == "decision":
        key = f"cortex-session/{current['slug']}:decision:{index}"
        current["decision_keys"] = [*current.get("decision_keys", []), key]
        session = state.get("session")
        if session is not None and hasattr(session, "add"):
            from app.services.tukulpan import record_decision
            record_decision(session, thread_id=state["thread_id"], topic_key=key,
                            title=current["topic"], content=state.get("content", ""))
    result["cortex_session"] = current
    return result


def load_panel_context(session, thread_id: int) -> dict:
    """Read the Tukulpan panel scope, with pinned memories first and bounded."""
    if session is None or not hasattr(session, "execute"):
        return {"pinned": [], "panel": []}
    from app.services.prompts import load_assistant_config
    from app.services.tukulpan import list_for_entity

    scope = load_assistant_config().memoria_scope or "panel"
    rows = list_for_entity(session, scope=scope, entity_id=f"thread:{thread_id}")
    result = {"pinned": [], "panel": []}
    for row in rows:
        content = str(row.contenido)
        result["pinned" if row.pin else "panel"].append({"id": str(row.id), "content": content})
    return result


def flush_panel_session(session, thread_id: int, *, source_message_ids: list[int], recap: str,
                        source_tokens: int, truncated: bool) -> dict:
    """Persist meaningful pre-rotation content through the canonical write seam."""
    if session is None or not hasattr(session, "add"):
        return {"written": False, "degraded_reason": "session persistence unavailable"}
    if not source_message_ids:
        return {"written": False, "degraded_reason": "no source messages for recap"}
    from app.services.tukulpan import write_recap

    return write_recap(
        session,
        thread_id=thread_id,
        source_message_ids=source_message_ids,
        recap=recap,
        source_tokens=source_tokens,
        truncated=truncated,
    )


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


def _record_usage(state: AssistantState, call_key: str, completion) -> None:
    session = state.get("session")
    request_id = state.get("request_message_id")
    if session is None or request_id is None:
        return
    usage = getattr(completion, "usage", None)
    record_llm_cost(
        session,
        message_id=request_id,
        target=session.get(InternalChatMessage, request_id),
        call_key=f"{state['run_id']}:{call_key}",
        model=getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL),
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
    )


COST_DIRECTIVE = "Answer concisely; use the minimum necessary context and avoid optional tool calls."
COST_BLOCKED_REPLY = (
    "The assistant is temporarily unavailable because the configured usage limit was reached. "
    "Please review cost settings."
)

SDB_SPEC_LIMIT = 8_192
SDB_RESULT_LIMIT = 4_096
SDB_TEXT_LIMIT = 500


def sdb_clarify(state: AssistantState) -> AssistantState:
    """Accept one bounded scope for the native run."""
    content = state.get("content", "").strip()[:SDB_TEXT_LIMIT]
    scope = {"entities": ["service history"], "request": content, "proyecto": _project_slug(state)}
    return {
        "sdb_phase": "CLARIFY",
        "sdb_scope": scope,
        "status": "sdb_clarified",
    }


def sdb_spec(state: AssistantState) -> AssistantState:
    """Freeze the clarified scope before any task planning."""
    scope = state.get("sdb_scope") or {"entities": [], "request": ""}
    spec = {"scope": scope, "scope_frozen": True}
    encoded = str(spec).encode("utf-8")[:SDB_SPEC_LIMIT]
    spec["sha256"] = sha256(encoded).hexdigest()
    return {"sdb_phase": "SPEC", "sdb_spec": spec, "status": "sdb_specified"}


def sdb_plan(state: AssistantState) -> AssistantState:
    """Create bounded tasks, each with exactly one verifiable output."""
    spec = state["sdb_spec"]
    scope = spec["scope"]
    task = {
        "id": "task-1",
        "scope": scope,
        "summary": "Review the requested service history",
        "verifiable_output": "A bounded service-history summary",
    }
    return {"sdb_phase": "PLAN", "sdb_tasks": [task], "status": "sdb_planned"}


def sdb_approve(state: AssistantState) -> AssistantState:
    """Pause until a future approval flow supplies an explicit decision."""
    return {"sdb_phase": "APPROVE", "approval": {"status": "pending"}, "status": "approval_pending"}


def sdb_execute(state: AssistantState) -> AssistantState:
    """Expose the deferred retrieval boundary without claiming work was done."""
    results = [
        {"task_id": task["id"], "status": "not-implemented"}
        for task in state.get("sdb_tasks", [])
    ]
    result = {"results": results}
    return {"sdb_phase": "EXECUTE", "sdb_result": result, "status": "sdb_executed"}


def sdb_verify(state: AssistantState) -> AssistantState:
    """Reject verification until real task results exist."""
    tasks = state.get("sdb_tasks", [])
    results = state.get("sdb_result", {}).get("results", [])
    verified = len(tasks) == len(results) and all(item.get("status") == "completed" for item in results)
    verification = {"status": "passed" if verified else "failed", "task_ids": [task["id"] for task in tasks], "artifact_refs": []}
    return {"sdb_phase": "VERIFY", "verification": verification, "status": "sdb_verified" if verified else "error"}


def sdb_deliver(state: AssistantState) -> AssistantState:
    """Return honest terminal evidence without expanding the frozen scope."""
    verification = state.get("verification", {})
    status = "completed" if verification.get("status") == "passed" else "degraded"
    evidence = [{"route": "sdb", "phase": "DELIVER", "status": status,
                 "task_ids": verification.get("task_ids", []),
                 **({} if status == "completed" else {"reason": "verification did not pass on real work"})}]
    return {"sdb_phase": "DELIVER", "evidence": evidence, "status": status}


def resolve_sdb_item(spec: dict, requested: str) -> dict:
    """Resolve only entities in the frozen scope, with distinct absence errors."""
    entities = spec.get("scope", {}).get("entities", [])
    if requested not in entities:
        return {"status": "error", "error": "scope-not-found"}
    return {"status": "error", "error": "not-exist"}


def panel_cost_gate(state: AssistantState) -> AssistantState:
    """Choose the worst internal-thread/UTC-day mode before any paid LLM call."""
    session = state.get("session")
    if session is None:
        return {"cost_mode": "normal", "cost_directive": ""}

    thread_percent, thread_mode = internal_thread_cost_state(session, state["thread_id"])
    day_percent, day_mode = daily_cost_state(session)
    today = datetime.now(timezone.utc).date().isoformat()
    maybe_alert_owner(
        session, scope="conversation", entity_id=str(state["thread_id"]),
        percent=thread_percent,
        spend=internal_thread_spend(session, state["thread_id"]),
    )
    maybe_alert_owner(
        session, scope="daily", entity_id=today, percent=day_percent,
        spend=daily_spend(session),
    )
    mode = combined_cost_mode(thread_mode, day_mode)
    return {
        "cost_mode": mode,
        "cost_directive": COST_DIRECTIVE if mode == "conservative" else "",
        "response": COST_BLOCKED_REPLY if mode == "blocked" else None,
        "status": "completed" if mode == "blocked" else state.get("status"),
        "guardrails": {
            "cost_allowed": mode != "blocked",
            "cost_mode": mode,
            "thread_percent": thread_percent,
            "daily_percent": day_percent,
        },
    }


def plan_llm(state: AssistantState) -> AssistantState:
    """Ask the configured provider for a strict plan on every production turn."""
    from app.services.prompts import load_assistant_config

    config = load_assistant_config()
    user_prompt = config.prompts["plan"]
    for key, value in {"user_input": state["content"], "available_tools": ", ".join(config.tools_whitelist), "context": _context_text(state)}.items():
        user_prompt = user_prompt.replace("{{" + key + "}}", str(value))
    if state.get("cost_directive"):
        user_prompt += "\n\n" + state["cost_directive"]
    completion = None
    try:
        completion = _assistant_client().chat.completions.create(
            model=getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL),
            messages=[{"role": "system", "content": config.persona}, {"role": "user", "content": user_prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        _record_usage(state, "planner", completion)
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
        meta = state.get("context", {}).get("meta", {})
        return {"context": state.get("context", {"items": [], "meta": {}}), "context_meta": meta, "projection_evidence": meta}
    from app.services.agent_chat import assemble_context

    context = assemble_context(state["session"], state["thread_id"], attachments=state.get("attachments", []))
    return {"context": context, "context_meta": context["meta"], "projection_evidence": context["meta"]}


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
        if result.get("status") == "approval_pending":
            return {
                "tool_result": result,
                "approval": result.get("approval"),
                "guardrails": {**state.get("guardrails", {}), "approval_required": True,
                                "decision": "approval_pending"},
                "response": "This project selection requires approval before execution.",
                "status": "approval_pending",
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
        if state.get("cost_directive"):
            prompt += "\n\n" + state["cost_directive"]
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
            stream_options={"include_usage": True},
        )
        chunks: list[str] = []
        usage_seen = False
        for chunk in completion:
            if getattr(chunk, "usage", None) is not None:
                _record_usage(state, "response", chunk)
                usage_seen = True
            token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
            if token:
                chunks.append(token)
                on_token(token)
        if not usage_seen:
            _record_usage(state, "response", None)
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
        evidence = [*state["evidence"]]
    else:
        evidence = [make_evidence(tool=None, status="completed", detail="Assistant response generated")]
    context_meta = state.get("context_meta") or state.get("context", {}).get("meta", {})
    if context_meta:
        evidence[-1] = {**evidence[-1], "context_meta": context_meta}
    compaction = state.get("compaction") or {}
    if compaction.get("failed"):
        evidence.append({
            "tool": None,
            "status": "degraded",
            "detail": compaction.get("write", {}).get("degraded_reason", "compaction write failed"),
            "compaction": compaction,
        })
    return {
        "evidence": evidence,
        "status": "degraded" if compaction.get("failed") else state.get("status", "completed"),
    }
