"""Small, side-effect-free assistant graph nodes."""

from __future__ import annotations

import json
import logging
import re
from contextlib import nullcontext
from datetime import datetime, timezone
from hashlib import sha256
from pydantic import ValidationError

from app.chat.assistant.approval import validate_execution
from app.chat.assistant.evidence import make_evidence
from app.chat.assistant.markup import ToolCallMarkupSanitizer
from app.chat.assistant.state import AssistantState, PlannerOutput, SDBTask, estimate_tokens, validate_cortex_session
from app.chat.assistant.tools.registry import AUTONOMOUS_WRITE_ALLOWLIST, TOOL_REGISTRY, ToolExecutionError, ToolValidationError, execute_tool, get_tool
from app.services.audit import record_audit
from app.db import session_scope
from app.services import kb
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


logger = logging.getLogger(__name__)

_TOOL_EVIDENCE_LIMIT = 4_000
_KB_EVIDENCE_LIMIT = 4_000
_PLANNER_FAILURE_EXCERPT_LIMIT = 1_000
MAX_ASSISTANT_TOOL_STEPS = 2
DELEGATION_SPAN_MAX_STEPS = 2
DELEGATION_WRITE_REFUSED = "delegation_write_refused"
DELEGATION_TOOL_REFUSED = "delegation_tool_refused"
DELEGATION_MEMORY_SCOPE_REFUSED = "delegation_memory_scope_refused"
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
    return {"sdb": "deferred", "panel_subagents": "implemented" if wired else "not_implemented"}


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
    task = SDBTask(
        id="task-1",
        scope=scope,
        summary="Review the requested service history",
        verifiable_output="A bounded service-history summary",
        tool="conversations.search",
        arguments={"query": scope["request"], "limit": 10},
    )
    return {"sdb_phase": "PLAN", "sdb_tasks": [task.model_dump()], "status": "sdb_planned"}


def sdb_approve(state: AssistantState) -> AssistantState:
    """Pause until a future approval flow supplies an explicit decision."""
    return {"sdb_phase": "APPROVE", "approval": {"status": "pending"}, "status": "approval_pending"}


def sdb_execute(state: AssistantState) -> AssistantState:
    """Project canonical durable results without executing a second runner."""
    result = state.get("sdb_result") or {"results": []}
    return {"sdb_phase": "EXECUTE", "sdb_result": result, "status": "sdb_executed"}


def sdb_verify(state: AssistantState) -> AssistantState:
    """Compare frozen task identity and bounded evidence in deterministic order."""
    tasks = state.get("sdb_tasks", [])
    current = state.get("sdb_result") or {}
    persisted = state.get("sdb_persisted_results") or []
    incoming = current.get("results", []) if isinstance(current, dict) else []
    by_task = {item.get("task_id"): item for item in persisted + incoming if item.get("task_id")}
    ordered = []
    mismatches = []
    for order, task in enumerate(tasks):
        task_id = task.get("id")
        item = by_task.get(task_id)
        if item is None:
            mismatches.append({"field": "task_id", "order": order, "expected": task_id, "actual": None})
            continue
        expected = {"task_id": task_id, "order": order, "tool": task.get("tool"), "status": "completed"}
        actual = {key: item.get(key) for key in expected}
        for field, expected_value in expected.items():
            if actual[field] != expected_value:
                mismatches.append({"field": field, "order": order, "expected": expected_value, "actual": actual[field]})
        from app.chat.assistant.tools.registry import get_tool

        if not get_tool(task.get("tool")).read_only and not item.get("result") and not item.get("evidence"):
            mismatches.append({"field": "mutation_evidence", "order": order, "expected": "bounded evidence", "actual": None})
        ordered.append(item)
    extra = sorted(set(by_task) - {task.get("id") for task in tasks})
    mismatches.extend({"field": "task_id", "expected": "frozen task", "actual": task_id} for task_id in extra)
    verified = not mismatches and len(ordered) == len(tasks)
    verification = {
        "status": "passed" if verified else "failed", "task_ids": [task.get("id") for task in tasks],
        "results": ordered, "mismatches": mismatches, "artifact_refs": [],
    }
    return {"sdb_phase": "VERIFY", "verification": verification, "status": "sdb_verified" if verified else "error"}


def sdb_deliver(state: AssistantState) -> AssistantState:
    """Deliver only verified evidence whose caller transaction is durable."""
    verification = state.get("verification", {})
    result = state.get("sdb_result") or {}
    committed = result.get("durable_commit", True) if isinstance(result, dict) else False
    status = "completed" if verification.get("status") == "passed" and committed else "failed"
    evidence = [{"route": "sdb", "phase": "DELIVER", "status": status,
                 "task_ids": verification.get("task_ids", []),
                   **({} if status == "completed" else {"reason": "durable commit not confirmed" if not committed else "verification did not pass on real work"})}]
    return {"sdb_phase": "DELIVER", "evidence": evidence, "status": status}


def resolve_sdb_item(spec: dict, requested: str) -> dict:
    """Resolve only entities in the frozen scope, with distinct absence errors."""
    entities = spec.get("scope", {}).get("entities", [])
    if requested not in entities:
        return {"status": "error", "error": "scope-not-found"}
    return {"status": "error", "error": "not-exist"}


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
    available_tools = _planner_tool_catalog(config.tools_whitelist)
    for key, value in {"user_input": state["content"], "available_tools": available_tools, "context": _planner_context_text(state)}.items():
        user_prompt = user_prompt.replace("{{" + key + "}}", str(value))
    if state.get("cost_directive"):
        user_prompt += "\n\n" + state["cost_directive"]
    completion = None
    raw_text = ""
    diagnosis = None
    try:
        completion = _assistant_client().chat.completions.create(
            model=getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL),
            messages=[{"role": "system", "content": config.persona}, {"role": "user", "content": user_prompt}],
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
        return {"context": state.get("context", {"items": [], "meta": {}}), "context_meta": meta, "projection_evidence": meta}
    from app.services.agent_chat import assemble_context

    context = assemble_context(state["session"], state["thread_id"], attachments=state.get("attachments", []))
    return {"context": context, "context_meta": context["meta"], "projection_evidence": context["meta"]}


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
            },
        }
    tool_name = plan_data.get("tool")
    if plan_data.get("kind") != "tool" or not tool_name:
        decision = "respond" if _is_conversational_turn(state.get("content", "")) else "retrieve_kb"
        return {"guardrails": {"whitelisted": True, "arguments_valid": True, "cost_allowed": True, "approval_required": False, "decision": decision}, "status": "responding"}
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
        diagnosis = _planner_failure(
            "unsafe_plan", "guardrails", ValueError("planner plan failed guardrails"), plan_data
        )
        _log_planner_failure(diagnosis)
        fallback = bounded_fallback(diagnosis["reason"])
        return {"planner": {**fallback.model_dump(), "valid": False, "failure": diagnosis}, "plan": fallback.model_dump(), "guardrails": {**decisions, "decision": "fallback"}, "response": fallback.summary, "status": "responding"}
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
    return {
        "tool_results": [*(state.get("tool_results") or []), result],
        "tool_steps": state.get("tool_steps", 0) + 1,
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
    with session_scope() if session is None else nullcontext(session) as session:
        try:
            chunks = kb.retrieve(
                session,
                query,
                top_k=kb.DEFAULT_TOP_K,
                min_sim=kb.DEFAULT_MIN_SIM,
                audience=None,
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
            from app.services.prompts import load_assistant_config

            config = load_assistant_config()
            result = execute_tool(
                state.get("session"),
                tool_name,
                plan_data.get("arguments", {}),
                approval=state.get("approval"),
                whitelist=set(config.tools_whitelist),
                cost_allowed=state.get("guardrails", {}).get("cost_allowed", True),
                role=state.get("actor_role"),
                trusted_thread_id=state.get("thread_id"),
                owner_id=state.get("user_id"),
                proyecto=_project_slug(state),
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
                **_tool_accumulation(state, failed_result),
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
                    **_tool_accumulation(state, bounded_result),
                    "evidence": [make_evidence(tool=tool_name, status="degraded", detail=degraded_reason)],
                    "response": f"Tool {tool_name} unavailable.",
                    "status": "degraded",
                }
            return {
                "tool_result": result,
                **_tool_accumulation(state, result),
                "evidence": [make_evidence(tool=tool_name, status="error", detail=detail)],
                "error": detail,
                "response": f"Tool execution failed: {detail}",
                "status": "error",
            }
        if result.get("status") == "approval_pending":
            return {
                "tool_result": result,
                **_tool_accumulation(state, result),
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
            **_tool_accumulation(state, result),
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
            "available_tools": ", ".join(config.tools_whitelist),
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
