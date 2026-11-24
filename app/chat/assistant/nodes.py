"""Small, side-effect-free assistant graph nodes."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from contextlib import nullcontext
from datetime import datetime, timezone
from pydantic import ValidationError

from app.chat.assistant.approval import validate_execution
from app.chat.assistant.evidence import make_evidence
from app.chat.assistant.markup import ToolCallMarkupSanitizer
from app.chat.assistant.planner_json import load_planner_payload
from app.chat.assistant.state import AssistantState, PlannerOutput, estimate_tokens
from app.chat.assistant.tools.registry import AUTONOMOUS_WRITE_ALLOWLIST, TOOL_REGISTRY, ToolExecutionError, ToolValidationError, execute_tool, get_tool
from app.services.audit import record_audit
from app.db import release_transaction, session_scope
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

# Shared evidence budgets and their rationale live in budgets.py.
from app.config import get_settings
from app.chat.assistant.budgets import (
    _DETAIL_EVIDENCE_SHARE,
    _KB_EVIDENCE_LIMIT,
    _LISTING_EVIDENCE_SHARE,
    _TOOL_EVIDENCE_LIMIT,
)
_PLANNER_FAILURE_EXCERPT_LIMIT = 1_000
# The validation message travels into the repair prompt and the persisted guardrails snapshot, so it
# is one bounded line: enough to name the bound, never the whole pydantic traceback.
_ARGUMENTS_ERROR_LIMIT = 200
_ARTIFACT_INVENTORY_LIMIT = 10
# Default when settings cannot be read (tests and tooling that build a state without a session).
MAX_ASSISTANT_TOOL_STEPS = 8


def _release_before_provider_call(state: AssistantState) -> None:
    """Commit the turn's staged work before the model provider is waited on.

    A node that reads or writes and then calls the provider holds a pooled connection
    `idle in transaction`, and the database's idle guard terminates it at 180 s. The
    release is skipped on the approved-write resume, which keeps one transaction on
    purpose (pool-safety S2).
    """
    session = state.get("session")
    if state.get("resume") or not callable(getattr(session, "in_transaction", None)):
        return
    release_transaction(session)


def _tool_step_limit() -> int:
    """Steps allowed in one turn, from settings so it can be tuned without a release."""
    try:
        return get_settings().assistant_tool_step_limit
    except Exception:
        return MAX_ASSISTANT_TOOL_STEPS
# Bodies loaded for the responder every turn, even when the planner does not
# declare them. Scoped to the responder: the planner keeps seeing only the
# skill index ({name, description}), never these bodies (D8).
ALWAYS_ON_RESPONDER_SKILLS = ("memoria-tukulpan",)
PANEL_KB_UNAVAILABLE = (
    "La base de conocimiento no está disponible para esta consulta. "
    "No pude consultarla; un operador deberá revisarla."
)
# The responder is never replaced by a fixed sentence: an unsupported turn has to say what it looked
# for, what it is missing and what the operator can do. The prohibition is what preserves the
# grounding guarantee; the explanation is what removes the dead end.
NO_EVIDENCE_DIRECTIVE = (
    "<no_evidence>\n"
    "This turn has no tool result and no retrieved knowledge-base chunk. Do not answer from general "
    "knowledge and do not deny the request with a boilerplate sentence. Instead: state what you "
    "understood the request to be; say which source you checked or which one you would need "
    "(knowledge base, a project file, or a tool the operator can name); say plainly that you have no "
    "evidence for it; and give the operator the concrete next step (name the exact client, case, date "
    "or document, or ask for the tool that reads it). Never state prices, policies, schedules or any "
    "other business fact without evidence behind it, and never claim an action you did not run in "
    "this turn.\n"
    "</no_evidence>"
)
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
    return {"panel_subagents": "retired"}


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


def _arguments_error_text(exc: Exception) -> str:
    """Name the bound a plan missed, in one bounded line, from the boundary's own words.

    `str(ValidationError)` starts with a count line ("1 validation error for SearchArgs"), which tells
    a repairing model nothing. The field and its message are what a correction needs; anything else
    falls back to the exception text, flattened and bounded because it ends up in a prompt and in the
    persisted guardrails snapshot.
    """
    details = getattr(exc, "errors", None)
    errors = details() if callable(details) else None
    if isinstance(errors, list) and errors:
        first = errors[0] or {}
        location = ".".join(str(part) for part in first.get("loc") or ())
        message = str(first.get("msg") or "")
        text = f"{location}: {message}" if location else message
    else:
        text = str(exc)
    return text.strip().replace("\n", " ")[:_ARGUMENTS_ERROR_LIMIT] or type(exc).__name__



    """Build the bounded, persisted diagnosis for one planner failure."""
    raw_text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False, default=str)
    return {
        "reason": reason,
        "stage": stage,
        "exception_type": type(error).__name__,
        "exception": str(error)[:_PLANNER_FAILURE_EXCERPT_LIMIT],
        "raw_excerpt": raw_text[:_PLANNER_FAILURE_EXCERPT_LIMIT],
    }


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
    prior_results = _render_tool_evidence(state, surface="planner")
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


# Stages where the model's own output was unusable in a way a second answer can fix. A provider or
# instrumentation failure is not repaired by asking again: it only doubles the paid call.
_REPAIRABLE_PLAN_STAGES = frozenset({"parse", "validation"})

# The repair turn names the exact contract instead of repeating the long planning prompt: the model
# already answered, it just wrapped the answer badly. `extra="forbid"` stays strict, so an invented
# field has to be dropped by the model, not by the trust boundary.
PLANNER_REPAIR_DIRECTIVE = (
    "Your previous answer was not a usable plan. Reply with ONLY one JSON object, no prose, no code "
    "fence, and no keys other than these: kind, tool, arguments, summary, "
    "success_criterion, requires_approval, follow_up, skills. Escape every newline and tab inside a "
    "string as \\n and \\t."
)


def _attachment_inventory(state: AssistantState) -> str:
    """List this turn's thread attachments so a tool call can name one by id.

    `view_image(source="thread", id=...)` resolves against `assistant_attachments`, but the prompt is
    the only place an id can come from: without this block the planner could only guess one, and every
    attempt failed with `thread image not found` no matter how the image was uploaded.
    """
    lines = []
    for attachment in state.get("attachments") or []:
        if isinstance(attachment, dict):
            attachment_id = attachment.get("id")
            filename = attachment.get("filename")
            kind = attachment.get("kind")
        else:
            attachment_id = getattr(attachment, "id", None)
            filename = getattr(attachment, "filename", None)
            kind = getattr(attachment, "kind", None)
        if not attachment_id or not filename:
            continue
        kind = kind or "attachment"
        lines.append(f'[attachment id="{attachment_id}" filename="{filename}" kind="{kind}"]')
    return "\n".join(lines)


def _planner_messages(state: AssistantState) -> list[dict]:
    """Build the effective system/user planner prompt, shared by planning and repair."""
    from app.services.prompts import load_assistant_config

    config = load_assistant_config(role=state.get("actor_role"))
    user_prompt = config.prompts["plan"]
    available_tools = _planner_tool_catalog(list(_effective_tools(state)))
    available_skills = json.dumps(
        [{"name": skill.name, "description": skill.description} for skill in _effective_skill_index(state)],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    for key, value in {
        "user_input": state["content"],
        "available_tools": available_tools,
        "available_skills": available_skills,
        "context": _planner_context_text(state),
    }.items():
        user_prompt = user_prompt.replace("{{" + key + "}}", str(value))
    inventory = _attachment_inventory(state)
    if inventory:
        user_prompt += "\n\n<attachments>\n" + inventory + "\n</attachments>"
    if state.get("cost_directive"):
        user_prompt += "\n\n" + state["cost_directive"]
    tool_images = _tool_image_parts(state)
    user_content: object = [{"type": "text", "text": user_prompt}, *tool_images] if tool_images else user_prompt
    return [
        {"role": "system", "content": _effective_persona(state, config)},
        {"role": "user", "content": user_content},
    ]


def repair_plan(state: AssistantState) -> AssistantState:
    """Give one guardrails-rejected plan a single, explicitly bounded correction turn."""
    diagnosis = ((state.get("planner") or {}).get("failure") or {})
    guard = state.get("guardrails") or {}
    try:
        previous_plan = json.loads(diagnosis.get("raw_excerpt", "{}"))
    except (TypeError, json.JSONDecodeError):
        # A truncated excerpt is not the plan: the persisted excerpt is bounded, so a long plan arrives
        # cut. `state["plan"]` cannot stand in for it either -- guardrails already replaced it with the
        # bounded fallback by the time this node runs -- and showing the model a plan it never wrote is
        # worse than showing it none. The rejection below names the reason either way.
        previous_plan = None
    whitelisted = "true" if guard.get("whitelisted") else "false"
    arguments_valid = "true" if guard.get("arguments_valid") else "false"
    arguments_error = guard.get("arguments_error") or ""
    rejection = (
        f"Guardrails rejected the previous plan: whitelisted={whitelisted}; "
        f"arguments_valid={arguments_valid}. Return a corrected plan only.\n"
        + (f"Arguments error: {arguments_error}\n" if arguments_error else "")
        + (
            f"Previous plan: {json.dumps(previous_plan, ensure_ascii=False, separators=(',', ':'))}\n"
            if previous_plan is not None
            else ""
        )
        + f"{PLANNER_REPAIR_DIRECTIVE}"
    )
    messages = [*_planner_messages(state)]
    if previous_plan is not None:
        messages.append({"role": "assistant", "content": json.dumps(previous_plan, ensure_ascii=False)})
    messages.append({"role": "user", "content": rejection})
    raw_text, _completion, call_failure = _planner_call(messages, state, "planner_guardrails_repair")
    repaired = None
    valid = False
    if call_failure is None:
        try:
            raw = load_planner_payload(raw_text)
            repaired, valid, parse_failure = parse_planner_output(raw, raw_text=raw_text)
        except json.JSONDecodeError as exc:
            parse_failure = _planner_failure("invalid_json", "parse", exc, raw_text)
        if not valid:
            call_failure = parse_failure
    result: AssistantState = {"plan_repair_attempted": True}
    if valid and repaired is not None:
        result.update({
            "planner": {**repaired.model_dump(), "valid": True},
            "plan": repaired.model_dump(),
            "status": "planned",
            "response": None,
        })
        return result
    failure = call_failure or diagnosis or _planner_failure(
        "unsafe_plan", "guardrails", ValueError("planner plan failed guardrails")
    )
    _log_planner_failure(failure)
    fallback = bounded_fallback(failure["reason"])
    result.update({
        "plan_repair_terminal": True,
        "planner": {**fallback.model_dump(), "valid": False, "failure": failure},
        "plan": fallback.model_dump(),
        "guardrails": {**guard, "decision": "fallback"},
        "response": fallback.summary,
        "status": "responding",
    })
    return result


def _planner_call(messages: list[dict], state: AssistantState, call_key: str) -> tuple[str, object, dict[str, str] | None]:
    """Run one paid planner call and read its text, keeping today's bounded diagnoses."""
    try:
        _release_before_provider_call(state)
        completion = _assistant_client().chat.completions.create(
            model=getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL),
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        return "", None, _planner_failure("provider_call_failed", "provider", exc)
    try:
        _record_usage(state, call_key, completion)
    except Exception as exc:
        return "", completion, _planner_failure("usage_recording_failed", "instrumentation", exc)
    try:
        return _completion_text(completion), completion, None
    except Exception as exc:
        return "", completion, _planner_failure("completion_extraction_failed", "extraction", exc)


def _read_planner_plan(raw_text: str) -> tuple[PlannerOutput | None, bool, dict[str, str] | None]:
    """Read one plan out of a provider answer, tolerating the payload damage seen in production."""
    if not raw_text.strip():
        return None, False, _planner_failure(
            "empty_completion", "completion", ValueError("provider returned no structured planner message")
        )
    try:
        raw = load_planner_payload(raw_text)
    except json.JSONDecodeError as exc:
        return None, False, _planner_failure("invalid_json", "parse", exc, raw_text)
    return parse_planner_output(raw, raw_text=raw_text)


def plan_llm(state: AssistantState) -> AssistantState:
    """Ask the configured provider for a strict plan on every production turn."""
    messages = _planner_messages(state)
    raw_text, completion, diagnosis = _planner_call(messages, state, "planner")
    planner: PlannerOutput | None = None
    valid = False
    if diagnosis is None:
        planner, valid, diagnosis = _read_planner_plan(raw_text)
    if diagnosis is not None and diagnosis["stage"] in _REPAIRABLE_PLAN_STAGES:
        # One bounded repair turn: the model already answered, it only wrapped the answer badly.
        repair_text, _, repair_diagnosis = _planner_call(
            [*messages, {"role": "assistant", "content": raw_text}, {"role": "user", "content": PLANNER_REPAIR_DIRECTIVE}],
            state,
            "planner_repair",
        )
        if repair_diagnosis is None:
            repair_planner, repair_valid, repair_diagnosis = _read_planner_plan(repair_text)
            if repair_valid:
                planner, valid, diagnosis, raw_text = repair_planner, repair_valid, repair_diagnosis, repair_text
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
        try:
            from app.services.assistant_artifacts import list_artifacts

            artifacts = list_artifacts(state["session"], thread.id)[-_ARTIFACT_INVENTORY_LIMIT:][::-1]
            if artifacts:
                lines = [
                    "Artifacts of this thread — rewrite one with artifact.update(artifact_id=...), do not save a second file with the same name:",
                    *(f'- artifact #{row.id} "{row.filename}" v{row.version} ({row.size} B)' for row in artifacts),
                ]
                context["items"].append({"source": "thread_artifacts", "content": "\n".join(lines)})
        except Exception as exc:
            logger.warning("Skipping unavailable assistant artifact inventory: %s", exc)
        if effective is not None:
            effective["pinned_skills"] = pinned_skills
    return {"context": context, "context_meta": context["meta"], "projection_evidence": context["meta"], "effective": effective}


def memory_bootstrap(state: AssistantState) -> AssistantState:
    """Add bounded own-memory rows as labelled harness context, not tool evidence."""
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
    serialized = json.dumps(rows, ensure_ascii=False, default=str)
    if len(serialized) > _TOOL_EVIDENCE_LIMIT:
        serialized = serialized[:_TOOL_EVIDENCE_LIMIT - 1] + "…"
    context = state.get("context") or {"items": [], "meta": {}}
    items = list(context.get("items") or [])
    items.append({
        "source": "own_memory",
        "content": (
            "Project/thread memory read by the harness before this turn; "
            "not the result of any tool of this turn.\n" + serialized
        ),
    })
    return {"context": {**context, "items": items}}


def _effective_tools(state) -> tuple[str, ...]:
    effective = state.get("effective")
    if effective:
        return tuple(effective["tools_whitelist"])

    from app.services.prompts import load_assistant_config

    return load_assistant_config(role=state.get("actor_role")).tools_whitelist


def _effective_skill_index(state) -> tuple[SkillDefinition, ...]:
    from app.services.prompts import load_assistant_config
    from app.services.skills import global_skill_index

    effective = state.get("effective")
    if effective:
        return tuple(SkillDefinition(**skill) for skill in effective["skills_index"])
    return global_skill_index(load_assistant_config(role=state.get("actor_role")))


def _validated_skills(state) -> list[str]:
    declared = (state.get("plan") or {}).get("skills") or []
    pinned = (state.get("effective") or {}).get("pinned_skills") or []
    allowed = {skill.name for skill in _effective_skill_index(state)}
    valid = []
    for name in [*declared, *pinned]:
        if isinstance(name, str) and name in allowed and name not in valid:
            valid.append(name)
    return valid


def _effective_persona(state, config) -> str:
    effective = state.get("effective") or {}
    instructions = (effective.get("instructions") or "").strip()
    parts = [config.persona]
    if instructions:
        parts.append(instructions)
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


def _responder_prompt(state, config) -> str:
    """Render the responder template for this turn, including the no-evidence directive."""
    prompt = config.prompts["respond"]
    tool_statement = (
        "A panel tool has already run for this request. Use its evidence to answer with text only; "
        "you must not emit tool-call markup."
        if state.get("tool_result") is not None
        else "No panel tool ran for this request in this turn. The listed tools are available "
        "to this assistant; never state that you cannot use or execute them. Answer with text "
        "only; you must not emit tool-call markup."
    )
    for key, value in {
        "user_input": state["content"],
        "available_tools": ", ".join(_effective_tools(state)),
        "tool_statement": tool_statement,
        "tool_evidence": _render_tool_evidence(state, surface="responder"),
        "kb_evidence": _render_kb_evidence(state),
        "context": _context_text(state),
        "no_evidence": NO_EVIDENCE_DIRECTIVE if state.get("no_evidence") else "",
    }.items():
        prompt = prompt.replace("{{" + key + "}}", str(value))
    if state.get("cost_directive"):
        prompt += "\n\n" + state["cost_directive"]
    return prompt


def _is_autonomous_write(tool_name: str | None, thread_id: object) -> bool:
    return tool_name in AUTONOMOUS_WRITE_ALLOWLIST and type(thread_id) is int and thread_id > 0


# Verbs that name a write in the operator's own words. Used only to reserve the last step of a chain,
# never to authorize a write: the approval gate stays the only authority.
_WRITE_INTENT = (
    "escribe", "escribi", "escribí", "guarda", "guardá", "guardar", "actualiza", "actualizá",
    "crea", "creá", "crear", "edita", "editá", "agrega", "agregá", "agregar", "genera", "generá",
    "corrige", "corregí", "agrega", "anota", "anotá", "write", "save", "update", "create", "edit", "append",
)


def _asks_for_a_write(content: str) -> bool:
    text = (content or "").casefold()
    return any(re.search(rf"\b{re.escape(stem)}", text) for stem in _WRITE_INTENT)


def _chain_only_read(state: AssistantState) -> bool:
    """True when every step of this chain so far was a read-only tool."""
    results = state.get("tool_results") or []
    if not results:
        return False
    for result in results:
        if not isinstance(result, dict):
            return False
        try:
            if not get_tool(str(result.get("tool") or "")).read_only:
                return False
        except Exception:
            return False
    return True


def _file_read_counts(results) -> dict[int, int]:
    """How many times each project file was read in this chain, by file id."""
    counts: dict[int, int] = {}
    for result in results or []:
        if not isinstance(result, dict) or result.get("tool") != "read_project_file":
            continue
        arguments = result.get("arguments") or {}
        file_id = arguments.get("file_id") if isinstance(arguments, dict) else None
        if isinstance(file_id, int):
            counts[file_id] = counts.get(file_id, 0) + 1
    return counts


def _is_conversational_turn(content: str) -> bool:
    """Allow only short, purely social turns to bypass knowledge grounding."""
    text = content.strip().casefold()
    if not text or len(text) > 40 or "?" in text:
        return False
    words = re.findall(r"[\wáéíóúüñ]+", text)
    return bool(words) and all(word in _SOCIAL_WORDS for word in words)


def _has_turn_evidence(state: AssistantState) -> bool:
    """True when this turn already ran at least one tool step, successful or failed."""
    return bool(state.get("tool_steps")) and bool(state.get("tool_results"))


def guardrails(state: AssistantState) -> AssistantState:
    plan_data = state.get("plan") or {}
    if state.get("legacy_compat"):
        from app.chat.assistant.approval import issue_approval
        return {"approval": issue_approval(plan_data), "guardrails": {"whitelisted": True, "arguments_valid": True, "cost_allowed": True, "approval_required": True, "decision": "approval_pending"}, "status": "approval_pending"}
    if not state.get("planner", {}).get("valid", True):
        return {"guardrails": {"whitelisted": False, "arguments_valid": False, "cost_allowed": True, "approval_required": False, "decision": "fallback"}, "status": "responding"}
    validated_skills = _validated_skills(state)
    tool_name = plan_data.get("tool")
    prior_results = state.get("tool_results") or []
    previous = prior_results[-1] if prior_results and state.get("tool_steps", 0) else {}
    repeated_call = False
    if plan_data.get("kind") == "tool" and previous.get("tool") == tool_name and tool_name:
        try:
            definition = get_tool(tool_name)
            # A write has its own gate: its approval is bound to one exact plan and consumed when
            # it runs, so a repeated write is refused there. This guard exists to stop a read loop
            # from burning the step budget on the same page, and rewriting a write here detaches
            # the plan its approval belongs to.
            if definition.read_only:
                args_model = definition.args_model
                previous_arguments = args_model.model_validate(previous.get("arguments", {})).model_dump()
                planned_arguments = args_model.model_validate(plan_data.get("arguments", {})).model_dump()
                repeated_call = previous_arguments == planned_arguments
        except Exception:
            # Invalid calls are handled by the normal validation path below.
            pass
    # Pagination changes the offset, so an identical-call guard never fires on a re-read of the same
    # file. Two reads of one file are all a chain needs; a third is the loop production paid for with
    # six steps and no write.
    file_read_loop = False
    if plan_data.get("kind") == "tool" and tool_name == "read_project_file":
        planned_file_id = (plan_data.get("arguments") or {}).get("file_id")
        if isinstance(planned_file_id, int) and _file_read_counts(prior_results).get(planned_file_id, 0) >= 2:
            file_read_loop = True
    if file_read_loop:
        return {
            "plan": {**plan_data, "kind": "respond", "tool": None, "arguments": {}, "follow_up": False},
            "execution_stall": "repeated_file_read",
            "guardrails": {"whitelisted": True, "arguments_valid": True, "cost_allowed": True,
                           "approval_required": False, "decision": "respond", "skills": validated_skills,
                           "execution_stall": "repeated_file_read"},
            "status": "responding",
        }
    if repeated_call:
        return {
            "plan": {**plan_data, "kind": "respond", "tool": None, "arguments": {}, "follow_up": False},
            "execution_stall": "repeated_tool_call",
            "guardrails": {"whitelisted": True, "arguments_valid": True, "cost_allowed": True,
                           "approval_required": False, "decision": "respond", "skills": validated_skills,
                           "execution_stall": "repeated_tool_call"},
            "status": "responding",
        }
    if plan_data.get("kind") != "tool" or not tool_name:
        # A turn that already executed a tool keeps its own evidence. Routing it to the knowledge
        # base discards the result and, on an empty retrieval, replaces the answer with a refusal:
        # the measured case is a tool turn whose follow-up plan answered from nothing at all.
        conversational = _has_turn_evidence(state) or _is_conversational_turn(state.get("content", ""))
        decision = "respond" if conversational else "retrieve_kb"
        return {"guardrails": {"whitelisted": True, "arguments_valid": True, "cost_allowed": True, "approval_required": False, "decision": decision, "skills": validated_skills}, "status": "responding"}
    whitelisted = tool_name in _effective_tools(state)
    arguments_valid = False
    arguments_error = ""
    if whitelisted:
        try:
            arguments_valid = bool(get_tool(tool_name).args_model.model_validate(plan_data.get("arguments", {})))
        except Exception as exc:
            # Keep the boundary's own words. A repair turn that is told only "invalid" cannot know
            # which bound it missed.
            arguments_error = _arguments_error_text(exc)
    decisions = {"whitelisted": whitelisted, "arguments_valid": arguments_valid, "arguments_error": arguments_error, "cost_allowed": True, "approval_required": False, "decision": "execute", "skills": validated_skills}
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
    # Every class-A write needs its own consumed approval, at any step of a chain: the
    # step that just ran spent the previous token, and an approval is bound to the exact
    # plan it was granted for, so it can never authorize the next plan.
    if not get_tool(tool_name).read_only and not autonomous_write and not validate_execution(plan_data, state.get("approval") or {}):
        from app.chat.assistant.approval import issue_approval
        decisions["approval_required"] = True
        decisions["decision"] = "approval_pending"
        return {"approval": issue_approval(plan_data), "guardrails": decisions, "status": "approval_pending"}
    return {"guardrails": decisions, "status": "executing"}


def _omission_marker(omitted: int) -> str:
    return f"[{omitted} earlier tool result(s) omitted]\n"


def _cut_with_marker(text: str, available: int) -> tuple[str, int]:
    """Cut `text` to `available` characters, saying how many characters were dropped.

    The marker's own length depends on the number it carries, so the retained slice is recomputed
    with the marker in hand. Two passes settle it; the loop is bounded so a rounding surprise cannot
    turn a brake into a spin. The dropped count is returned with the text instead of being read back
    out of the marker: callers account for it, and re-parsing our own wording is a silent zero the
    day that wording changes.
    """
    retained = max(0, available)
    for _ in range(4):
        retained = max(0, available - len(f"[{len(text) - max(0, retained)} characters dropped]"))
    dropped = len(text) - retained
    return text[:retained] + f"[{dropped} characters dropped]", dropped


def _project_capability_evidence(payload):
    """Reduce the capability inventory to its count plus one name/access entry per tool.

    `assistant.capabilities` answers with one line per whitelisted tool, and at the current 38 tools
    that text is ~4,100 characters -- three quarters of the budget the entire responder turn shares
    across every executed step. The planner already receives name, description and argument schema
    for the same whitelist every turn (`_planner_tool_catalog`), so quoting the descriptions again
    here buys the responder nothing it cannot read there. What the evidence still owes it is which
    tools this turn could use, how many, and which of those write.

    The projection is built here, never returned from the tool: the tool's own result stays complete,
    and a returned list would be cut to `MAX_ITEMS` by `_plain` and lose tools in silence.
    """
    if not isinstance(payload, dict):
        return payload
    text = payload.get("capabilities")
    if not isinstance(text, str):
        return payload
    tools = []
    for line in text.splitlines():
        if " — " not in line:
            # The scope header ("Available in this turn's scope:") names no tool.
            continue
        name, _, tail = line.partition(" — ")
        access = tail[tail.rfind(" ("):].strip() if " (" in tail else ""
        tools.append(f"{name.strip()} {access}".strip())
    return {"tool_count": payload.get("tool_count", len(tools)), "tools": tools}


def _coalesce_file_reads(results: list) -> list:
    """Fold consecutive reads of one project file into a single evidence block.

    Two pages of one file used to compete for the same evidence budget, and the newest won: reading a
    5,899-byte file rendered 2,323 characters with the first half gone. The planner then re-read the half
    it had lost, which evicted the other, until the step budget ended the turn. One file read in N steps
    is one document, so it is rendered as one.
    """
    def _file_read(result) -> dict | None:
        if not isinstance(result, dict) or result.get("tool") != "read_project_file":
            return None
        payload = result.get("result")
        arguments = result.get("arguments")
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            return None
        if not isinstance(arguments, dict) or not isinstance(arguments.get("file_id"), int):
            return None
        return payload

    coalesced: list = []
    group: list = []
    group_file_id: int | None = None

    def _flush() -> None:
        nonlocal group, group_file_id
        if not group:
            return
        if len(group) == 1:
            coalesced.append(group[0])
        else:
            pages = [item.get("result") for item in group]
            first_result = group[-1]
            merged_text = "".join(str(page.get("text") or "") for page in pages)
            coalesced.append({
                "tool": "read_project_file",
                "status": first_result.get("status"),
                "arguments": {
                    "file_id": group_file_id,
                    "offsets": [page.get("offset") for page in pages],
                },
                "result": {
                    "file_id": group_file_id,
                    "filename": pages[0].get("filename"),
                    "text": merged_text,
                    "offset": pages[0].get("offset") or 0,
                    "next_offset": pages[-1].get("next_offset"),
                    "pages_joined": len(pages),
                    "chars": len(merged_text),
                },
            })
        group = []
        group_file_id = None

    for result in results or []:
        payload = _file_read(result)
        if payload is None:
            _flush()
            coalesced.append(result)
            continue
        if group and payload.get("file_id") != group_file_id:
            _flush()
        group_file_id = payload.get("file_id")
        group.append(result)
    _flush()
    return coalesced


# Cursor-shaped argument keys that are safe to keep verbatim: they identify *what* a step touched
# without carrying content or domain values. A digest of the whole argument map makes a repeat visible
# without storing the operator's data.
_AUDITABLE_ARGUMENT_KEYS = ("file_id", "artifact_id", "folder_id", "offset", "limit", "thread_id", "conversation_id", "customer_id", "case_id")


def _audit_arguments(arguments) -> dict:
    """Auditable trace of one step: a digest of the exact arguments plus safe cursor keys."""
    if not isinstance(arguments, dict):
        return {}
    serialized = json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str)
    trace = {"arguments_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest()}
    for key in _AUDITABLE_ARGUMENT_KEYS:
        value = arguments.get(key)
        if isinstance(value, (int, str)) and not isinstance(value, bool):
            trace[key] = value
    return trace


def _render_tool_evidence(state: AssistantState, *, surface: str = "responder") -> str:
    results = state.get("tool_results") or ([state["tool_result"]] if state.get("tool_result") else [])
    if not results:
        return ""
    results = _coalesce_file_reads(results)
    rendered_results: list[tuple[str, str]] = []
    rendered_tools: list[str] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        tool = str(result.get("tool") or "unknown")
        status = str(result.get("status") or "unknown")
        arguments = json.dumps(result.get("arguments") or {}, ensure_ascii=False, sort_keys=True, default=str)
        header = f"tool={tool} status={status} arguments={arguments}"
        payload = result.get("result")
        if tool == "assistant.capabilities":
            payload = _project_capability_evidence(payload)
        rendered = header
        if payload is not None:
            rendered += "\n" + json.dumps(payload, ensure_ascii=False, default=str)
            if tool in {"customers.list", "customers.search"} and isinstance(payload, list):
                try:
                    args = get_tool(tool).args_model.model_validate(result.get("arguments") or {})
                    limit, offset = args.limit, args.offset
                    page_cue = f"Customer page: limit={limit}, offset={offset}, returned={len(payload)}. "
                    if len(payload) == limit:
                        page_cue += (
                            f"There may be more; next offset={offset + limit}. "
                            "Repeating the same page advances nothing."
                        )
                    else:
                        page_cue += "This is a short page; no next offset is suggested."
                    rendered += "\n" + page_cue
                except (AttributeError, TypeError, ValueError):
                    pass
        # An identical tool + arguments + payload is the same information however many times the
        # model asked for it; quoting it twice only spends the responder's evidence budget.
        signature = f"{tool}\u0000{arguments}\u0000{json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)}"
        rendered_results.append((rendered, signature))
        rendered_tools.append(tool)
    if not rendered_results:
        return ""

    # Retain every executed step's identity/status even when its payload is omitted.
    inventory = ""
    stall = state.get("execution_stall")
    if stall:
        ran = ", ".join(str(item.get("tool") or "unknown") for item in results if isinstance(item, dict))
        inventory = f"Execution chain stopped ({stall}); tools already run: {ran}.\n"
    newest_first = list(reversed(rendered_results))
    kept: list[str] = []
    kept_indices: set[int] = set()
    quoted: set[str] = set()
    cut_dropped_chars = 0
    cut_result_index: int | None = None
    for reverse_index, (item, signature) in enumerate(newest_first):
        result_index = len(rendered_results) - reverse_index - 1
        if signature in quoted:
            # Counted by the omission marker below, and still named in the inventory.
            continue
        candidate = "\n".join(reversed([*kept, item]))
        omitted = len(rendered_results) - len(kept) - 1
        marker = _omission_marker(omitted) if omitted else ""
        inventory_lines = ""
        if omitted:
            inventory_lines = "Executed tools:\n" + "\n".join(
                f"- tool={result.get('tool') or 'unknown'} status={result.get('status') or 'unknown'}"
                for result in results if isinstance(result, dict)
            ) + "\n"
        if len(inventory) + len(inventory_lines) + len(marker) + len(candidate) <= _TOOL_EVIDENCE_LIMIT:
            kept.append(item)
            kept_indices.add(result_index)
            quoted.add(signature)
        elif not kept:
            # Preserve the newest result's provenance and label the payload tail lost to the brake.
            available = _TOOL_EVIDENCE_LIMIT - len(inventory) - len(inventory_lines) - len(marker)
            header, separator, payload_text = item.partition("\n")
            if separator:
                cut_text, cut_dropped_chars = _cut_with_marker(
                    payload_text, available - len(header) - len(separator)
                )
                cut_result_index = result_index
                kept.append(header + separator + cut_text)
            else:
                cut_text, cut_dropped_chars = _cut_with_marker(item, available)
                cut_result_index = result_index
                kept.append(cut_text)
            kept_indices.add(result_index)
            quoted.add(signature)
            break
        else:
            break
    omitted = len(rendered_results) - len(kept)
    body = "\n".join(reversed(kept))
    marker = _omission_marker(omitted) if omitted else ""
    inventory_lines = ""
    if omitted:
        inventory_lines = "Executed tools:\n" + "\n".join(
            f"- tool={result.get('tool') or 'unknown'} status={result.get('status') or 'unknown'}"
            for result in results if isinstance(result, dict)
        ) + "\n"
    prefix = inventory + inventory_lines + marker
    if len(prefix) + len(body) <= _TOOL_EVIDENCE_LIMIT:
        projection = prefix + body
    else:
        # If the newest payload alone exceeds the budget, retain its header and cut only payload text.
        projection = prefix + body[: max(0, _TOOL_EVIDENCE_LIMIT - len(prefix) - 1)] + "…"

    omitted_indices = set(range(len(rendered_results))) - kept_indices
    dropped_chars = cut_dropped_chars + sum(len(rendered_results[index][0]) for index in omitted_indices)
    if omitted_indices or cut_dropped_chars:
        tools = [rendered_tools[index] for index in sorted(omitted_indices)]
        if cut_dropped_chars and cut_result_index is not None:
            tools.append(rendered_tools[cut_result_index])
        session = state.get("session")
        if session is not None:
            try:
                with session.begin_nested():
                    record_audit(
                        session,
                        actor=state.get("actor") or "assistant",
                        action="assistant.evidence_truncated",
                        entity="internal_chat_thread",
                        entity_id=str(state.get("thread_id")),
                        after={
                            "run_id": state.get("run_id"),
                            "surface": surface,
                            "tools": tools,
                            "dropped_chars": dropped_chars,
                            "kept_results": len(kept_indices),
                            "omitted_results": len(omitted_indices),
                            "budget": _TOOL_EVIDENCE_LIMIT,
                        },
                    )
            except Exception:
                logger.warning("Assistant evidence truncation audit failed", exc_info=True)
    return projection


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
    """Finish the turn or continue to the next step of an opted-in, bounded chain."""
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
    if not plan.get("follow_up"):
        return {"status": "completed"}
    limit = _tool_step_limit()
    # A request that names a write must not spend its last step reading: the turn would close with the
    # promise to write "next turn", which is what production did five times over. Reserve the final step
    # for an action that is not another read of what this chain already consumed.
    if steps >= limit - 1 and _asks_for_a_write(state.get("content", "")) and _chain_only_read(state):
        return {"cap_reached": True, "execution_stall": "write_pending_after_reads", "status": "completed"}
    # Record the cap only when another step was requested and the budget ended the turn.
    if steps >= limit:
        return {"cap_reached": True, "status": "completed"}
    # The step that just ran spent its approval. Clearing it is what makes the next plan
    # earn its own: an approval is bound to one exact plan, so carrying it forward would
    # either re-authorize an identical write or break the binding of a different one.
    return {"status": "planned", "approval": None}


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
        try:
            return execute_tool(
                state.get("session"), name, arguments, whitelist=whitelist,
                role=state.get("actor_role"), trusted_thread_id=state.get("thread_id"),
                owner_id=state.get("user_id"), proyecto=_project_slug(state),
                project_id=(state.get("effective") or {}).get("project_id"),
            )
        finally:
            _release_before_provider_call(state)

    _release_before_provider_call(state)
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
        # No evidence is a turn without support, not a verdict: the responder explains it instead of
        # a fixed sentence cutting the turn before the model ever sees it.
        return {
            "guardrails": {**state.get("guardrails", {}), "decision": "respond"},
            "no_evidence": True,
            "evidence": [make_evidence(
                tool="kb.retrieve",
                status="completed",
                detail="No grounded knowledge-base evidence found",
            )],
            "status": "responding",
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
                    after={"run_id": state.get("run_id"), "tool": tool_name, "status": "error",
                           **_audit_arguments(plan_data.get("arguments"))},
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
                after={"run_id": state.get("run_id"), "tool": tool_name, "status": "completed",
                       **_audit_arguments(plan_data.get("arguments"))},
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
            f'[attachment filename="{d["filename"]}" id="{d["attachment_id"]}" type="{d["kind"]}"]\n{d.get("text", "")}\n[/attachment]'
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

        config = load_assistant_config(role=state.get("actor_role"))
        prompt = _responder_prompt({**state, "content": content}, config)
        try:
            client = _assistant_client()
            model = getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL)
            tool_images = _tool_image_parts(state)
            if attachments or tool_images:
                base = build_multimodal_content(attachments, prompt) if attachments else [{"type": "text", "text": prompt}]
                user_content: object = [*base, *tool_images]
            else:
                user_content = prompt
            _release_before_provider_call(state)
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
        except Exception as exc:
            if not state.get("resume"):
                raise
            # A resumed approval has already executed its write by the time narration runs:
            # a provider failure here must degrade the reply, never roll the write back.
            logger.warning("Responder failed after an approved write: %s", exc)
            state.setdefault("evidence", []).append(
                make_evidence(tool=None, status="degraded", detail="Assistant response generation failed")
            )
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
