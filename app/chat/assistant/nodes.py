"""Small, side-effect-free assistant graph nodes."""

from __future__ import annotations

import json
import logging
import re
from contextlib import nullcontext
from datetime import datetime, timezone
from pydantic import ValidationError

from app.chat.assistant.approval import validate_execution
from app.chat.assistant.evidence import make_evidence
from app.chat.assistant.markup import ToolCallMarkupSanitizer
from app.chat.assistant.state import AssistantState, PlannerOutput, estimate_tokens, validate_cortex_session
from app.chat.assistant.tools.registry import AUTONOMOUS_WRITE_ALLOWLIST, TOOL_REGISTRY, ToolExecutionError, ToolValidationError, execute_tool, get_tool
from app.services.audit import record_audit
from app.db import session_scope
from app.services import kb
from app.services import llm
from app.services import project_files
from app.services.costs import (
    combined_cost_mode,
    daily_cost_state,
    daily_spend,
    internal_thread_cost_state,
    internal_thread_spend,
    maybe_alert_owner,
    record_llm_cost,
)
from app.services.skills import SkillDefinition
from app.chat.assistant.attachments import build_multimodal_content, image_url_part, prepare_attachment_context
from app.models import AssistantAttachment, InternalChatMessage
from app.chat.assistant.verification import EFFECT_TOOLS, run_verification, verification_required


logger = logging.getLogger(__name__)

_TOOL_EVIDENCE_LIMIT = 4_000
_KB_EVIDENCE_LIMIT = 4_000
_PLANNER_FAILURE_EXCERPT_LIMIT = 1_000
MAX_ASSISTANT_TOOL_STEPS = 2
DELEGATION_SPAN_MAX_STEPS = 2
DELEGATION_WRITE_REFUSED = "delegation_write_refused"
DELEGATION_TOOL_REFUSED = "delegation_tool_refused"
DELEGATION_MEMORY_SCOPE_REFUSED = "delegation_memory_scope_refused"
# Bodies loaded for the responder every turn, even when the planner does not
# declare them. Scoped to the responder: the planner keeps seeing only the
# skill index ({name, description}), never these bodies (D8).
ALWAYS_ON_RESPONDER_SKILLS = ("memoria-tukulpan",)
PANEL_GROUNDING_REFUSAL = (
    "No encontré evidencia suficiente en la base de conocimiento para responder con seguridad. "
    "Reformula la consulta o aporta más contexto."
)
PANEL_KB_UNAVAILABLE = (
    "La base de conocimiento no está disponible para esta consulta. "
    "No pude consultarla; un operador deberá revisarla."
)
PANEL_LOOP_WRITE_REFUSAL = (
    "No puedo ejecutar esa acción dentro de una consulta de varios pasos. "
    "Pídemela directamente y te pediré confirmación antes de ejecutarla."
)
PANEL_DELEGATION_REFUSAL = "I cannot safely delegate that request."
_SOCIAL_WORDS = frozenset({
    "adios", "buenas", "buenos", "bye", "chau", "como", "de", "dia", "días", "día",
    "dias", "estas", "esta", "excelente", "gracias", "hello", "hi", "hola", "hasta",
    "entendido", "genial", "listo", "luego", "muchas", "mucho", "nada", "noches", "nos",
    "ok", "okay", "okey", "perfecto", "por", "pronto", "que", "tal", "tardes", "thanks",
    "todo", "va", "vemos", "ya", "bien", "favor", "dale", "bueno",
})


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
    from app.chat.assistant.delegation import DelegationScopeError, resolve_delegation_scope

    try:
        resolve_delegation_scope("customer_records")
    except DelegationScopeError:
        wired = False
    else:
        wired = True
    return {"panel_subagents": "implemented" if wired else "not_implemented"}


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
        summary="No pude planificar esa solicitud de forma segura. Inténtalo nuevamente.",
        requires_approval=False,
    )


def _planner_failure(reason: str, stage: str, error: Exception, raw: object = "") -> dict[str, str]:
    """Build the bounded, persisted diagnosis for one planner failure."""
    raw_text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False, default=str)
    return {
        "reason": reason,
        "stage": stage,
        "exception_type": type(error).__name__,
        "exception": str(error)[:_PLANNER_FAILURE_EXCERPT_LIMIT],
        "raw_excerpt": raw_text[:_PLANNER_FAILURE_EXCERPT_LIMIT],
    }


def _log_planner_failure(diagnosis: dict[str, str]) -> None:
    logger.error(
        "planner failure reason=%s stage=%s exception_type=%s",
        diagnosis["reason"],
        diagnosis["stage"],
        diagnosis["exception_type"],
        extra={"diagnosis": diagnosis},
    )


def parse_planner_output(
    raw: object,
    *,
    raw_text: str | None = None,
) -> tuple[PlannerOutput, bool, dict[str, str] | None]:
    """Validate planner data and convert invalid data to a bounded response."""
    try:
        return PlannerOutput.model_validate(raw), True, None
    except (TypeError, ValidationError) as exc:
        diagnosis = _planner_failure(
            "planner_output_validation_failed", "validation", exc, raw if raw_text is None else raw_text
        )
        return bounded_fallback(diagnosis["reason"]), False, diagnosis


def plan(state: AssistantState) -> AssistantState:
    content = state["content"].strip()
    raw = state.get("planner_output")
    if raw is not None:
        planner, valid, diagnosis = parse_planner_output(raw)
        if valid:
            planner_data = {**planner.model_dump(), "valid": True}
            result: AssistantState = {
                "planner": planner_data,
                "plan": planner.model_dump(),
                "status": "planned",
            }
            if planner.kind == "complex":
                result["extension_hooks"] = extension_hook_metadata()
            return result
        _log_planner_failure(diagnosis)
        return {
            "planner": {**planner.model_dump(), "valid": False, "failure": diagnosis},
            "plan": planner.model_dump(),
            "status": "planned",
            "response": planner.summary,
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
    """Render the context items, the conversation identity, and any compaction rotation cue."""
    context = state.get("context", {})
    text = [str(item.get("content", "")) for item in context.get("items", [])]
    meta = context.get("meta") or {}
    if meta.get("scope") and meta.get("entity_id"):
        text.append(
            f"Conversation identity: scope={meta['scope']} "
            "(the panel memory read target is derived server-side)"
        )
    compaction = state.get("compaction") or {}
    if compaction.get("failed"):
        text.append(
            "History recap unavailable: this thread was compacted but no recap could be saved, so "
            "no memory row holds the earlier messages. Do not claim to remember them."
        )
    elif compaction.get("rotated"):
        text.append(
            "History recap saved: earlier messages in this thread were compacted into a recap "
            "stored as thread memory. Pull it with memory.read with scope=own and no entity_id "
            "before claiming to remember earlier turns."
        )
    return "\n".join(text)


def _planner_context_text(state: AssistantState) -> str:
    context = _context_text(state)
    prior_results = _render_tool_evidence(state)
    return f"{context}\nPrior tool evidence:\n{prior_results}" if prior_results else context


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

def _cost_snapshot(session: object, thread_id: int) -> dict[str, float | str]:
    """Read the current cost state without emitting alerts or changing state."""
    if session is None:
        return {
            "thread_percent": 0.0,
            "thread_mode": "normal",
            "daily_percent": 0.0,
            "daily_mode": "normal",
            "mode": "normal",
        }
    thread_percent, thread_mode = internal_thread_cost_state(session, thread_id)
    day_percent, day_mode = daily_cost_state(session)
    return {
        "thread_percent": thread_percent,
        "thread_mode": thread_mode,
        "daily_percent": day_percent,
        "daily_mode": day_mode,
        "mode": combined_cost_mode(thread_mode, day_mode),
    }


def panel_cost_gate(state: AssistantState) -> AssistantState:
    """Choose the worst internal-thread/UTC-day mode before any paid LLM call."""
    session = state.get("session")
    snapshot = _cost_snapshot(session, state["thread_id"])
    if session is None:
        return {"cost_mode": "normal", "cost_directive": ""}

    today = datetime.now(timezone.utc).date().isoformat()
    maybe_alert_owner(
        session, scope="conversation", entity_id=str(state["thread_id"]),
        percent=snapshot["thread_percent"],
        spend=internal_thread_spend(session, state["thread_id"]),
    )
    maybe_alert_owner(
        session, scope="daily", entity_id=today, percent=snapshot["daily_percent"],
        spend=daily_spend(session),
    )
    mode = snapshot["mode"]
    return {
        "cost_mode": mode,
        "cost_directive": COST_DIRECTIVE if mode == "conservative" else "",
        "response": COST_BLOCKED_REPLY if mode == "blocked" else None,
        "status": "completed" if mode == "blocked" else state.get("status"),
        "guardrails": {
            "cost_allowed": mode != "blocked",
            "cost_mode": mode,
            "thread_percent": snapshot["thread_percent"],
            "daily_percent": snapshot["daily_percent"],
        },
    }


def _planner_tool_catalog(whitelist: list[str]) -> str:
    def without_titles(value):
        if isinstance(value, dict):
            return {
                key: without_titles(nested)
                for key, nested in value.items()
                if key != "title"
            }
        if isinstance(value, list):
            return [without_titles(nested) for nested in value]
        return value

    return json.dumps(
        [
            {
                "name": name,
                "description": definition.description,
                "arguments": without_titles(definition.schema()),
            }
            for name in whitelist
            if (definition := TOOL_REGISTRY.get(name)) is not None
        ],
        separators=(",", ":"),
    )


def _delegation_plan(state: AssistantState, scope) -> PlannerOutput:
    """Plan one delegated read against only the resolved sub-agent catalog."""
    from app.chat.assistant.delegation import DelegationScope

    if not isinstance(scope, DelegationScope):
        raise TypeError("delegation requires a resolved DelegationScope")
    prompt = (
        f"{scope.persona}\n\nReturn one JSON tool plan or a respond plan. "
        f"Available tools: {_planner_tool_catalog(list(scope.tools_whitelist))}\n"
        f"Request: {state['content']}\nContext: {_context_text(state)}\n"
        f"Prior delegated results: {_render_tool_evidence(state)}"
    )
    completion = _assistant_client().chat.completions.create(
        model=getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL),
        messages=[{"role": "system", "content": "Return evidence-gathering tool plans only."},
                  {"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    _record_usage(state, f"delegation:{scope.key}", completion)
    raw = json.loads(_completion_text(completion))
    planner, valid, _ = parse_planner_output(raw)
    return planner if valid else bounded_fallback("delegation planner output invalid")


def delegation_span(state: AssistantState, scope) -> AssistantState:
    """Run a bounded read-only evidence span; it never creates a user-facing answer."""
    results = list(state.get("tool_results") or [])
    evidence = list(state.get("evidence") or [])
    decisions: list[str] = []
    steps = 0
    while steps < DELEGATION_SPAN_MAX_STEPS:
        planner = _delegation_plan({**state, "tool_results": results}, scope)
        if isinstance(planner, dict):
            planner, _, _ = parse_planner_output(planner)
        if planner.kind != "tool" or not planner.tool:
            break
        steps += 1
        tool_name = planner.tool
        try:
            definition = get_tool(tool_name)
        except ToolValidationError:
            decisions.append(DELEGATION_TOOL_REFUSED)
            continue
        if not definition.read_only:
            decisions.append(DELEGATION_WRITE_REFUSED)
            continue
        if tool_name not in scope.tools_whitelist:
            decisions.append(DELEGATION_TOOL_REFUSED)
            continue
        arguments = planner.arguments
        if tool_name in {"memory.read", "memory.search"} and scope.memoria_scope == "customer" and arguments.get("scope") != "customer":
            decisions.append(DELEGATION_MEMORY_SCOPE_REFUSED)
            continue
        try:
            result = execute_tool(
                state.get("session"), tool_name, arguments,
                whitelist=set(scope.tools_whitelist),
                cost_allowed=True,
                role=state.get("actor_role"),
                trusted_thread_id=state.get("thread_id"),
                owner_id=state.get("user_id"),
                proyecto=_project_slug(state),
                project_id=(state.get("effective") or {}).get("project_id"),
            )
        except (ToolExecutionError, ToolValidationError) as exc:
            result = {"tool": tool_name, "status": "error", "error": str(exc), "result": {"unavailable": True}}
        provenance = {"sub_agent": scope.key, "step": steps, "tool": tool_name}
        results.append({**result, "provenance": provenance})
        evidence.append(
            make_evidence(
                tool=tool_name,
                status=result.get("status", "completed"),
                detail="Delegated tool result",
            )
            | {"provenance": provenance}
        )
    return {
        "tool_results": results,
        "evidence": evidence,
        "delegation": {
            "sub_agent": scope.key,
            "steps": steps,
            "cap": DELEGATION_SPAN_MAX_STEPS,
            "cap_reached": steps >= DELEGATION_SPAN_MAX_STEPS,
            "decisions": decisions,
        },
    }


def delegation_node(state: AssistantState) -> AssistantState:
    """Run the delegated span on the read-only scope guardrails already validated.

    Guardrails resolves the scope and carries it in ``state["delegation"]``; resolving it
    again here would reopen a window where a registry or persona change between the two
    nodes lets ``DelegationScopeError`` escape the turn instead of ending it. The graph
    reaches this node only through the ``delegate`` decision, which is set in the same
    branch that writes the carried scope, so it is always present.
    """
    from app.chat.assistant.delegation import DelegationScope

    scope = DelegationScope(**state["delegation"])
    result = delegation_span(state, scope)
    return {**result, "tool_steps": state.get("tool_steps", 0) + 1, "status": "completed"}


def plan_llm(state: AssistantState) -> AssistantState:
    """Ask the configured provider for a strict plan on every production turn."""
    from app.services.prompts import load_assistant_config

    config = load_assistant_config()
    user_prompt = config.prompts["plan"]
    available_tools = _planner_tool_catalog(list(_effective_tools(state)))
    available_skills = json.dumps(
        [{"name": skill.name, "description": skill.description} for skill in _effective_skill_index(state)],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    for key, value in {"user_input": state["content"], "available_tools": available_tools,
                       "available_skills": available_skills, "context": _planner_context_text(state)}.items():
        user_prompt = user_prompt.replace("{{" + key + "}}", str(value))
    if state.get("cost_directive"):
        user_prompt += "\n\n" + state["cost_directive"]
    tool_images = _tool_image_parts(state)
    user_content: object = [{"type": "text", "text": user_prompt}, *tool_images] if tool_images else user_prompt
    completion = None
    raw_text = ""
    diagnosis = None
    try:
        completion = _assistant_client().chat.completions.create(
            model=getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL),
            messages=[{"role": "system", "content": _effective_persona(state, config)}, {"role": "user", "content": user_content}],
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        diagnosis = _planner_failure("provider_call_failed", "provider", exc)

    if diagnosis is None:
        try:
            _record_usage(state, "planner", completion)
        except Exception as exc:
            diagnosis = _planner_failure("usage_recording_failed", "instrumentation", exc)

    if diagnosis is None:
        try:
            raw_text = _completion_text(completion)
        except Exception as exc:
            diagnosis = _planner_failure("completion_extraction_failed", "extraction", exc)

    if diagnosis is None:
        if not raw_text.strip():
            diagnosis = _planner_failure(
                "empty_completion", "completion", ValueError("provider returned no structured planner message")
            )
        else:
            try:
                raw = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                diagnosis = _planner_failure("invalid_json", "parse", exc, raw_text)
            else:
                planner, valid, diagnosis = parse_planner_output(raw, raw_text=raw_text)
    if diagnosis is not None:
        _log_planner_failure(diagnosis)
        # Compatibility for older injected clients that only implement response
        # streaming; they can still pause a write for approval, but never name a
        # tool or execute an unchecked action.
        if not raw_text and any(word in state["content"].casefold() for word in ("create", "delete", "change", "send")):
            return {"plan": {"tool": None, "arguments": {}, "summary": state["content"], "requires_approval": True}, "planner": {"valid": False, "failure": diagnosis}, "legacy_compat": True, "status": "planned"}
        planner = bounded_fallback(diagnosis["reason"])
        valid = False
    result = {
        "planner": {**planner.model_dump(), "valid": valid},
        "plan": planner.model_dump(),
        "status": "planned",
        "response": planner.summary if not valid else None,
        "context": state.get("context", {}),
    }
    if diagnosis is not None:
        result["planner"]["failure"] = diagnosis
    return result


def assemble_context_node(state: AssistantState) -> AssistantState:
    if state.get("session") is None:
        meta = state.get("context", {}).get("meta", {})
        return {"context": state.get("context", {"items": [], "meta": {}}), "context_meta": meta, "projection_evidence": meta, "effective": None}
    from app.models import InternalChatThread
    from app.services.project_config import resolve_effective_config
    from app.services.agent_chat import assemble_context

    thread = state["session"].get(InternalChatThread, state["thread_id"])
    effective = None
    if thread is not None:
        config = resolve_effective_config(state["session"], thread, state.get("actor_role") or "")
        effective = {
            "project_id": config.project_id,
            "instructions": config.instructions,
            "tools_whitelist": list(config.tools_whitelist),
            "skills_index": [
                {"name": skill.name, "description": skill.description, "scope": skill.scope,
                 "path": skill.path, "body": skill.body}
                for skill in config.skills_index
            ],
        }
    context = assemble_context(state["session"], state["thread_id"], attachments=state.get("attachments", []))
    if thread is not None:
        from app.services.thread_resources import pinned_context

        reference, pinned_skills = pinned_context(state["session"], thread)
        if reference:
            context["items"].append({"source": "pinned_resources", "content": reference})
        if effective is not None:
            effective["pinned_skills"] = pinned_skills
    return {"context": context, "context_meta": context["meta"], "projection_evidence": context["meta"], "effective": effective}


def memory_bootstrap(state: AssistantState) -> AssistantState:
    """Add bounded own-memory rows as code-initiated prior tool evidence."""
    if state.get("session") is None or type(state.get("thread_id")) is not int or state["thread_id"] <= 0:
        return {}
    try:
        result = execute_tool(
            state["session"], "memory.read", {"scope": "own", "limit": 3},
            whitelist=set(_effective_tools(state)),
            cost_allowed=(state.get("guardrails") or {}).get("cost_allowed", True),
            role=state.get("actor_role"), trusted_thread_id=state.get("thread_id"),
            owner_id=state.get("user_id"), proyecto=_project_slug(state),
            project_id=(state.get("effective") or {}).get("project_id"),
        )
    except (ToolValidationError, ToolExecutionError):
        return {}
    rows = result.get("result") if isinstance(result, dict) else None
    if not rows:
        return {}
    entry = {**result, "arguments": {"scope": "own", "limit": 3}, "code_initiated": True}
    return {"tool_results": [*(state.get("tool_results") or []), entry]}


def _effective_tools(state) -> tuple[str, ...]:
    effective = state.get("effective")
    if effective:
        tools = tuple(effective["tools_whitelist"])
    else:
        from app.services.prompts import load_assistant_config

        tools = load_assistant_config().tools_whitelist

    if not validate_cortex_session(state) or state["cortex_session"]["status"] != "active":
        return tools
    from app.chat.assistant.tools.registry import get_tool

    allowed = []
    for name in tools:
        if name == "memory.write" or name.startswith("planning."):
            allowed.append(name)
            continue
        try:
            definition = get_tool(name)
        except ValueError:
            continue
        if not definition.write:
            allowed.append(name)
    return tuple(allowed)


def _effective_skill_index(state) -> tuple[SkillDefinition, ...]:
    from app.services.prompts import load_assistant_config
    from app.services.skills import global_skill_index

    effective = state.get("effective")
    if effective:
        return tuple(SkillDefinition(**skill) for skill in effective["skills_index"])
    return global_skill_index(load_assistant_config())


def _validated_skills(state) -> list[str]:
    declared = (state.get("plan") or {}).get("skills") or []
    pinned = (state.get("effective") or {}).get("pinned_skills") or []
    allowed = {skill.name for skill in _effective_skill_index(state)}
    valid = []
    for name in [*declared, *pinned]:
        if isinstance(name, str) and name in allowed and name not in valid:
            valid.append(name)
    return valid


def _planning_overlay(state) -> str:
    """The facilitator overlay, injected only while a planning session is active (S2)."""
    if not validate_cortex_session(state) or state["cortex_session"]["status"] != "active":
        return ""
    from app.services.prompts import load as load_prompt

    return load_prompt("prompts/planning_facilitator.md").strip()


def _effective_persona(state, config) -> str:
    effective = state.get("effective") or {}
    instructions = (effective.get("instructions") or "").strip()
    parts = [config.persona]
    if instructions:
        parts.append(instructions)
    overlay = _planning_overlay(state)
    if overlay:
        parts.append(overlay)
    return "\n\n".join(parts)


def _skill_context(state) -> str:
    from app.services.skills import SkillError, load_skill_body

    definitions = {skill.name: skill for skill in _effective_skill_index(state)}
    declared = state.get("guardrails", {}).get("skills") or []
    names = list(dict.fromkeys([*declared, *ALWAYS_ON_RESPONDER_SKILLS]))
    bodies = []
    for name in names:
        definition = definitions.get(name)
        if definition is None:
            continue
        try:
            body = load_skill_body(definition)
        except SkillError as exc:
            logger.warning("Skipping unavailable assistant skill %r: %s", name, exc)
            continue
        bodies.append(f"### Skill: {name}\n{body}")
    return "\n\n".join(bodies)


def _responder_system_prompt(state, config) -> str:
    persona = _effective_persona(state, config)
    skills = _skill_context(state)
    return f"{persona}\n\n{skills}" if skills else persona


def _is_autonomous_write(tool_name: str | None, thread_id: object) -> bool:
    return tool_name in AUTONOMOUS_WRITE_ALLOWLIST and type(thread_id) is int and thread_id > 0


def _is_conversational_turn(content: str) -> bool:
    """Allow only short, purely social turns to bypass knowledge grounding."""
    text = content.strip().casefold()
    if not text or len(text) > 40 or "?" in text:
        return False
    words = re.findall(r"[\wáéíóúüñ]+", text)
    return bool(words) and all(word in _SOCIAL_WORDS for word in words)


def guardrails(state: AssistantState) -> AssistantState:
    plan_data = state.get("plan") or {}
    if state.get("legacy_compat"):
        from app.chat.assistant.approval import issue_approval
        return {"approval": issue_approval(plan_data), "guardrails": {"whitelisted": True, "arguments_valid": True, "cost_allowed": True, "approval_required": True, "decision": "approval_pending"}, "status": "approval_pending"}
    if not state.get("planner", {}).get("valid", True):
        return {"guardrails": {"whitelisted": False, "arguments_valid": False, "cost_allowed": True, "approval_required": False, "decision": "fallback"}, "status": "responding"}
    validated_skills = _validated_skills(state)
    if plan_data.get("kind") == "delegate":
        from app.chat.assistant.delegation import DelegationScopeError, resolve_delegation_scope

        try:
            scope = resolve_delegation_scope(plan_data.get("sub_agent", ""))
        except DelegationScopeError as exc:
            return {
                "guardrails": {
                    "whitelisted": False,
                    "arguments_valid": False,
                    "scope_valid": False,
                    "cost_allowed": True,
                    "approval_required": False,
                    "decision": "delegate_refused",
                    "reason": str(exc),
                },
                "response": PANEL_DELEGATION_REFUSAL,
                "status": "completed",
            }
        return {
            # The delegation node consumes this scope before delegation_span overwrites
            # `delegation` with its run summary, so it must carry every field the span
            # enforces -- including the worker's memoria_scope.
            "delegation": {
                "key": scope.key,
                "persona": scope.persona,
                "tools_whitelist": scope.tools_whitelist,
                "memoria_scope": scope.memoria_scope,
            },
            "guardrails": {
                "whitelisted": True,
                "arguments_valid": True,
                "scope_valid": True,
                "cost_allowed": True,
                "approval_required": False,
                "decision": "delegate",
                "skills": validated_skills,
            },
        }
    tool_name = plan_data.get("tool")
    if plan_data.get("kind") != "tool" or not tool_name:
        decision = "respond" if _is_conversational_turn(state.get("content", "")) else "retrieve_kb"
        return {"guardrails": {"whitelisted": True, "arguments_valid": True, "cost_allowed": True, "approval_required": False, "decision": decision, "skills": validated_skills}, "status": "responding"}
    whitelisted = tool_name in _effective_tools(state)
    arguments_valid = False
    if whitelisted:
        try:
            arguments_valid = bool(get_tool(tool_name).args_model.model_validate(plan_data.get("arguments", {})))
        except Exception:
            pass
    decisions = {"whitelisted": whitelisted, "arguments_valid": arguments_valid, "cost_allowed": True, "approval_required": False, "decision": "execute", "skills": validated_skills}
    if not whitelisted or not arguments_valid:
        diagnosis = _planner_failure(
            "unsafe_plan", "guardrails", ValueError("planner plan failed guardrails"), plan_data
        )
        _log_planner_failure(diagnosis)
        fallback = bounded_fallback(diagnosis["reason"])
        return {"planner": {**fallback.model_dump(), "valid": False, "failure": diagnosis}, "plan": fallback.model_dump(), "guardrails": {**decisions, "decision": "fallback"}, "response": fallback.summary, "status": "responding"}
    if tool_name == "skill.propose":
        from app.services.prompts import load_assistant_config
        from app.services.skills import global_skill_index

        proposed_name = plan_data.get("arguments", {}).get("name")
        if proposed_name in {skill.name for skill in global_skill_index(load_assistant_config())}:
            reason = "A project skill cannot use the name of a global skill."
            if state.get("session") is not None:
                record_audit(
                    state["session"], actor=state.get("actor") or "assistant",
                    action="skill.propose.rejected", entity="internal_chat_thread",
                    entity_id=str(state.get("thread_id")),
                    after={"run_id": state.get("run_id"), "name": proposed_name, "reason": "global_skill_collision"},
                )
            return {
                "approval": None,
                "guardrails": {**decisions, "whitelisted": False, "approval_required": False, "decision": "skill_shadow_refused"},
                "response": reason,
                "status": "completed",
            }
    autonomous_write = _is_autonomous_write(tool_name, state.get("thread_id"))
    if not get_tool(tool_name).read_only and state.get("tool_steps", 0) >= 1:
        decisions["decision"] = "loop_write_refused"
        decisions["approval_required"] = False
        return {
            "approval": None,
            "guardrails": decisions,
            "response": PANEL_LOOP_WRITE_REFUSAL,
            "status": "completed",
        }
    if not get_tool(tool_name).read_only and not autonomous_write and not state.get("approval"):
        from app.chat.assistant.approval import issue_approval
        decisions["approval_required"] = True
        decisions["decision"] = "approval_pending"
        return {"approval": issue_approval(plan_data), "guardrails": decisions, "status": "approval_pending"}
    return {"guardrails": decisions, "status": "executing"}


def _omission_marker(omitted: int) -> str:
    return f"[{omitted} earlier tool result(s) omitted]\n"


def _render_tool_evidence(state: AssistantState) -> str:
    results = state.get("tool_results") or ([state["tool_result"]] if state.get("tool_result") else [])
    rendered_results = []
    for result in results:
        payload = result.get("result") if isinstance(result, dict) else None
        if payload is not None:
            rendered_results.append(json.dumps(payload, ensure_ascii=False))
    if not rendered_results:
        return ""
    # Newest first, and the omission marker is budgeted *with* the results. The newest result
    # is what the planner decides from, so it must never be the part a final cut removes --
    # prepending the marker after budgeting is exactly how it used to disappear.
    newest_first = list(reversed(rendered_results))
    kept: list[str] = []
    used = 0
    for index, item in enumerate(newest_first):
        older = len(newest_first) - index - 1
        reserve = len(_omission_marker(older)) if older else 0
        if kept and used + len(item) + 1 + reserve > _TOOL_EVIDENCE_LIMIT:
            break
        kept.append(item)
        used += len(item) + 1
    omitted = len(newest_first) - len(kept)
    body = "\n".join(reversed(kept))
    # Dropping older results must not be silent: the planner decides "I have enough" from this
    # rendering, so it has to know when evidence was left out of it.
    prefix = _omission_marker(omitted) if omitted else ""
    if len(prefix) + len(body) <= _TOOL_EVIDENCE_LIMIT:
        return prefix + body
    # A single result larger than the whole budget: truncate it, never the marker.
    return prefix + body[: _TOOL_EVIDENCE_LIMIT - len(prefix) - 1] + "…"


def _resolve_tool_image(state: AssistantState, handle: dict) -> dict | None:
    """Turn a `view_image` handle into a vision part, re-validating scope at call time."""
    session = state.get("session")
    image_id = handle.get("id")
    if session is None or type(image_id) is not int:
        return None
    if handle.get("source") == "project":
        project_id = (state.get("effective") or {}).get("project_id")
        if not isinstance(project_id, int):
            return None
        source = project_files.get_project_file(session, project_id, image_id)
    elif handle.get("source") == "thread":
        row = session.get(AssistantAttachment, image_id)
        source = row if row is not None and row.thread_id == state.get("thread_id") and row.deleted_at is None else None
    else:
        return None
    if source is None:
        return None
    try:
        return image_url_part(source.stored_path, mime=source.content_type, filename=source.filename)
    except (OSError, ValueError):
        return None


def _tool_image_parts(state: AssistantState) -> list[dict]:
    """Vision parts for images a tool returned this turn; empty otherwise (on-demand, S5)."""
    parts: list[dict] = []
    for result in state.get("tool_results") or []:
        payload = result.get("result") if isinstance(result, dict) else None
        handle = payload.get("image") if isinstance(payload, dict) else None
        if isinstance(handle, dict):
            part = _resolve_tool_image(state, handle)
            if part is not None:
                parts.append(part)
    return parts


def tool_loop_head(state: AssistantState) -> AssistantState:
    """Finish or request an explicitly opted-in, bounded read-only follow-up."""
    plan = state.get("plan") or {}
    steps = state.get("tool_steps", 0)
    cost = _cost_snapshot(state.get("session"), state["thread_id"])
    if cost["mode"] != "normal":
        return {
            "cost_mode": cost["mode"],
            "cost_directive": COST_DIRECTIVE if cost["mode"] == "conservative" else "",
            "guardrails": {
                **state.get("guardrails", {}),
                "cost_allowed": cost["mode"] != "blocked",
                "cost_mode": cost["mode"],
                "decision": "loop_cost_stopped",
            },
            "status": "completed",
        }
    if plan.get("kind") != "tool" or not plan.get("tool"):
        return {"status": "completed"}
    # Chaining is read-only end to end (D3): a write is an action, not evidence, so it always
    # ends the turn -- including an autonomous write that opted into a follow-up step.
    if not get_tool(plan["tool"]).read_only:
        return {"status": "completed"}
    if not plan.get("follow_up"):
        return {"status": "completed"}
    # Record the cap only when another step was requested and the budget ended the turn.
    if steps >= MAX_ASSISTANT_TOOL_STEPS:
        return {"cap_reached": True, "status": "completed"}
    return {"status": "planned"}


def _tool_accumulation(state: AssistantState, result: dict) -> dict:
    # ponytail: preserve the exact dispatched arguments alongside the result for verification.
    return {
        "tool_results": [*(state.get("tool_results") or []), result],
        "tool_steps": state.get("tool_steps", 0) + 1,
    }


def verify_effects(state: AssistantState) -> AssistantState:
    """Verify dispatched effects against the plan and evidence, never dispatching writes."""
    steps = state.get("tool_results") or []
    required, gate_reason = verification_required(
        dispatched_tools=(item.get("tool") for item in steps),
        explicit=bool(state.get("verify_requested")), handoff=bool(state.get("sdb_requested")),
    )
    if not required:
        return {}

    def tool_executor(name, arguments):
        definition = get_tool(name)
        whitelist = {tool for tool in _effective_tools(state) if get_tool(tool).read_only}
        if not definition.read_only or name not in whitelist:
            raise ToolValidationError("verification is read-only")
        return execute_tool(
            state.get("session"), name, arguments, whitelist=whitelist,
            role=state.get("actor_role"), trusted_thread_id=state.get("thread_id"),
            owner_id=state.get("user_id"), proyecto=_project_slug(state),
            project_id=(state.get("effective") or {}).get("project_id"),
        )

    criterion = (state.get("plan") or {}).get("success_criterion") or (state.get("planner_output") or {}).get("success_criterion")
    result = run_verification(
        criterion=criterion, steps=steps, evidence=state.get("evidence") or [], tool_executor=tool_executor,
    )
    verification = {
        "required": True, "gate_reason": gate_reason,
        "status": result.status, "detail": result.reason,
    }
    return {
        "verification": verification,
        "evidence": [make_evidence(tool="verification", status=result.status, detail=result.reason)],
    }


def _render_kb_evidence(state: AssistantState) -> str:
    rendered = "\n".join(
        f"{index}. {chunk['content'].strip()}"
        for index, chunk in enumerate(state.get("kb_chunks") or [], 1)
        if isinstance(chunk, dict) and chunk.get("content", "").strip()
    )
    if len(rendered) <= _KB_EVIDENCE_LIMIT:
        return rendered
    return rendered[:_KB_EVIDENCE_LIMIT - 1] + "…"


def retrieve_kb(state: AssistantState) -> AssistantState:
    """Retrieve bounded evidence before answering a non-social panel turn."""
    session = state.get("session")
    # Hoisted out of the try: only the retrieval itself may degrade. A missing
    # `content` is a caller error, not a knowledge-base outage, and must not be
    # disguised as one.
    query = state["content"].strip()
    project_id = (state.get("effective") or {}).get("project_id")
    with session_scope() if session is None else nullcontext(session) as session:
        try:
            chunks = kb.retrieve(
                session,
                query,
                top_k=kb.DEFAULT_TOP_K,
                min_sim=kb.DEFAULT_MIN_SIM,
                audience=None,
                **({"project_id": project_id} if project_id is not None else {"global_only": True}),
            )
        except Exception as error:
            detail = f"Knowledge-base retrieval failed: {error}"
            logger.warning("Read-only tool kb.retrieve failed: %s", detail)
            return {
                "guardrails": {**state.get("guardrails", {}), "decision": "kb_unavailable"},
                "evidence": [make_evidence(tool="kb.retrieve", status="degraded", detail=detail)],
                "response": PANEL_KB_UNAVAILABLE,
                "status": "degraded",
            }
        chunks = [
            chunk
            for chunk in chunks
            if isinstance(chunk, dict)
            and isinstance(chunk.get("content"), str)
            and chunk["content"].strip()
        ]
    if not chunks:
        return {
            "guardrails": {**state.get("guardrails", {}), "decision": "grounding_refusal"},
            "evidence": [make_evidence(
                tool="kb.retrieve",
                status="completed",
                detail="No grounded knowledge-base evidence found",
            )],
            "response": PANEL_GROUNDING_REFUSAL,
            "status": "completed",
        }
    return {
        "kb_chunks": chunks,
        "guardrails": {**state.get("guardrails", {}), "decision": "respond"},
        "status": "responding",
    }


def execute(state: AssistantState) -> AssistantState:
    plan_data = state["plan"]
    tool_already_ran = state.get("status") in {"completed", "degraded", "error", "approval_pending"}
    autonomous_write = _is_autonomous_write(plan_data.get("tool"), state.get("thread_id"))
    if not tool_already_ran and plan_data["requires_approval"] and not autonomous_write and not validate_execution(plan_data, state.get("approval") or {}):
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
    if tool_name and not tool_already_ran:
        try:
            result = execute_tool(
                state.get("session"),
                tool_name,
                plan_data.get("arguments", {}),
                approval=state.get("approval"),
                whitelist=set(_effective_tools(state)),
                cost_allowed=state.get("guardrails", {}).get("cost_allowed", True),
                role=state.get("actor_role"),
                trusted_thread_id=state.get("thread_id"),
                owner_id=state.get("user_id"),
                proyecto=_project_slug(state),
                project_id=(state.get("effective") or {}).get("project_id"),
            )
        except (ToolExecutionError, ToolValidationError) as exc:
            detail = str(exc)
            failed_result = {"tool": tool_name, "status": "error", "error": detail}
            if state.get("session") is not None:
                record_audit(
                    state["session"], actor=state.get("actor") or "assistant",
                    action="internal_chat.execution", entity="internal_chat_thread",
                    entity_id=str(state.get("thread_id")),
                    after={"run_id": state.get("run_id"), "tool": tool_name, "status": "error"},
                )
            return {
                "tool_result": failed_result,
                **_tool_accumulation(state, {**failed_result, "arguments": plan_data.get("arguments", {})}),
                "evidence": [make_evidence(tool=tool_name, status="error", detail=detail)],
                "error": detail,
                "response": f"Tool execution failed: {detail}",
                "status": "error",
            }
        if result.get("status") == "error":
            detail = result.get("error", "tool failed")
            if get_tool(tool_name).read_only:
                logger.warning("Read-only tool %s failed: %s", tool_name, detail)
                bounded_result = {
                    "unavailable": True,
                    "tool": tool_name,
                    "degraded_reason": "Read-only tool unavailable",
                }
                degraded_reason = bounded_result["degraded_reason"]
                bounded_result = {**result, "result": bounded_result}
                return {
                    "tool_result": bounded_result,
                    **_tool_accumulation(state, {**bounded_result, "arguments": plan_data.get("arguments", {})}),
                    "evidence": [make_evidence(tool=tool_name, status="degraded", detail=degraded_reason)],
                    "response": f"Tool {tool_name} unavailable.",
                    "status": "degraded",
                }
            return {
                "tool_result": result,
                **_tool_accumulation(state, {**result, "arguments": plan_data.get("arguments", {})}),
                "evidence": [make_evidence(tool=tool_name, status="error", detail=detail)],
                "error": detail,
                "response": f"Tool execution failed: {detail}",
                "status": "error",
            }
        if result.get("status") == "approval_pending":
            return {
                "tool_result": result,
                **_tool_accumulation(state, {**result, "arguments": plan_data.get("arguments", {})}),
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
            **_tool_accumulation(state, {**result, "arguments": plan_data.get("arguments", {})}),
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
        tool_statement = (
            "A panel tool has already run for this request. Use its evidence to answer with text only; "
            "you must not emit tool-call markup."
            if state.get("tool_result") is not None
            else "The listed tools are panel capabilities only. This reply cannot invoke them. "
            "Answer with text only; you must not emit tool-call markup."
        )
        for key, value in {
            "user_input": state["content"],
            "available_tools": ", ".join(_effective_tools(state)),
            "tool_statement": tool_statement,
            "tool_evidence": _render_tool_evidence(state),
            "kb_evidence": _render_kb_evidence(state),
            "context": _context_text(state),
        }.items():
            prompt = prompt.replace("{{" + key + "}}", str(value))
        if state.get("cost_directive"):
            prompt += "\n\n" + state["cost_directive"]
        client = _assistant_client()
        model = getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL)
        tool_images = _tool_image_parts(state)
        if attachments or tool_images:
            base = build_multimodal_content(attachments, prompt) if attachments else [{"type": "text", "text": prompt}]
            user_content: object = [*base, *tool_images]
        else:
            user_content = prompt
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _responder_system_prompt(state, config)},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            stream=True,
            stream_options={"include_usage": True},
        )
        chunks: list[str] = []
        markup_sanitizer = ToolCallMarkupSanitizer()
        usage_seen = False
        for chunk in completion:
            if getattr(chunk, "usage", None) is not None:
                _record_usage(state, "response", chunk)
                usage_seen = True
            token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
            if token:
                clean_token = markup_sanitizer.feed(token)
                if clean_token:
                    chunks.append(clean_token)
                    on_token(clean_token)
        clean_tail = markup_sanitizer.flush()
        if clean_tail:
            chunks.append(clean_tail)
            on_token(clean_tail)
        if not usage_seen:
            _record_usage(state, "response", None)
        response = "".join(chunks) or response
    verification = state.get("verification") or {}
    if verification.get("status") in {"failed", "unverifiable"}:
        effect_ran = EFFECT_TOOLS.intersection(item.get("tool") for item in state.get("tool_results", []))
        prefix = "The effect ran. " if effect_ran else ""
        qualification = f"\n\n{prefix}verification: {verification['status']} — {verification.get('detail', '')}"
        response += qualification
        if on_token is not None:
            on_token(qualification)
    session = state.get("session")
    if session is not None and not tool_already_ran:
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
