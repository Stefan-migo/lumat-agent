"""Persistence boundary for the panel assistant graph."""

from datetime import datetime, timezone
import asyncio
import json
import logging
import time
from typing import NamedTuple
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.chat.assistant.graph import run_assistant
from app.chat.assistant.approval import arguments_digest, canonical_sdb_digest, issue_approval, validate_approval
from app.chat.assistant.nodes import execute, sdb_deliver, sdb_verify
from app.chat.assistant.tools.registry import ToolExecutionError, ToolValidationError, execute_tool, get_tool
from app.chat.assistant import nodes as assistant_nodes
from app.chat.assistant.attachments import prepare_attachment_context
from app.chat.assistant.state import estimate_tokens, merge_assistant_state
from app.chat.assistant.recovery import claim_execution, recover_events, revalidate_sdb_resume, resumable_sdb_tasks
from app.config import get_settings
from app.models import AssistantAttachment, InternalChatMessage, InternalChatThread, User
from app.services.audit import record_audit
from app.services.realtime import stage_event
from app.services import tukulpan
from app.services import projects
from app.services import costs, llm

logger = logging.getLogger(__name__)


class HarnessLimits(NamedTuple):
    """Bounded harness limits, resolved from settings (single source of truth)."""

    injection_budget: int
    session_window: int
    compaction_threshold: int
    compaction_retention: int


def harness_limits() -> HarnessLimits:
    """Resolve the harness limits from settings.

    These were duplicated as module constants in `assistant.state` while the
    settings were never read, so the configuration did nothing. Settings are now
    the only source.
    """
    settings = get_settings()
    return HarnessLimits(
        injection_budget=settings.assistant_context_injection_budget,
        session_window=settings.assistant_session_window_tokens,
        compaction_threshold=settings.assistant_compaction_threshold_tokens,
        compaction_retention=settings.assistant_compaction_retention_tokens,
    )


SDB_EVENT_LIMIT = 4 * 1024
SDB_EVENT_HISTORY_LIMIT = 64
TITLE_MAX_BYTES = 120
TITLE_TIMEOUT_SECONDS = 5.0
# A panel run is orphaned once its `live` state stops advancing. The SSE poller
# already gives up after 300s, so a run silent for twice that window cannot
# still be executing; failing it closed is what turns an eternal spinner into a
# retryable failure.
STALE_RUN_SECONDS = 600


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sdb_plan(spec: dict, tasks: list[dict]) -> dict:
    return {"phase": "EXECUTE", "spec": spec, "tasks": tasks}


def cortex_approved_plan(spec: dict, tasks: list[dict]) -> dict:
    """Represent the closed report as an approved-plan-only SDB handoff."""
    return {
        "status": "approved-plan",
        "execution": "pending-approval",
        "sdb": _sdb_plan(spec, tasks),
        "tool": None,
        "arguments": {},
        "requires_approval": True,
    }


def close_cortex_session(session, thread: InternalChatThread, *, report: str) -> dict:
    """Persist and archive a Cortex report before exposing its SDB handoff."""
    cortex = dict((thread.assistant_state or {}).get("cortex_session") or {})
    slug = cortex["slug"]
    report_key = f"cortex-session/{slug}:report"
    tukulpan.archive_report(
        session, thread_id=thread.id, topic_key=report_key,
        title=cortex.get("topic", slug), content=report,
    )
    spec = {"scope": {"request": cortex.get("topic", ""), "report": report}, "report_key": report_key}
    plan = cortex_approved_plan(spec, [{
        "id": "cortex-report", "scope": {"entities": ["service history"], "request": cortex.get("topic", "")},
        "summary": "Read service history for the approved report",
        "verifiable_output": "A bounded service-history result",
        "tool": "conversations.search", "arguments": {"query": cortex.get("topic", ""), "limit": 10},
    }])
    run_id = uuid4().hex
    thread.assistant_state = merge_assistant_state(
        thread.assistant_state or {},
        {"stage": "approval_pending", "recoverable": True, "execution_status": "pending",
         "cortex_session": {"status": "closed", "closed_at": datetime.now(timezone.utc).isoformat(),
                             "report_key": report_key, "handoff": {"status": "pending", "sdb_phase": "SPEC"}},
         "approval": issue_approval(plan)},
    )
    thread.current_plan = plan
    thread.active_run_id = run_id
    return {"report_key": report_key, "report": report, "plan": plan, "run_id": run_id}


def _thread_project_authorization(session: Session, thread: InternalChatThread):
    proyecto = thread.proyecto
    return None if not proyecto or proyecto == "default" else projects.agent_context(
        session, proyecto, owner_id=thread.user_id
    )


def _run_sdb_tasks(session: Session, thread: InternalChatThread, run_id: str, authorization=None) -> dict:
    """Execute the frozen approved plan once, stopping at the first failure."""
    sdb = (thread.assistant_state or {}).get("sdb") or {}
    plan = thread.current_plan or {}
    frozen_tasks = plan.get("sdb", {}).get("tasks", [])
    persisted_results = {item.get("task_id"): item for item in sdb.get("results", []) if item.get("task_id")}
    pending = resumable_sdb_tasks(frozen_tasks, sdb.get("checkpoints", []))
    results = list(persisted_results.values())
    from app.services.prompts import load_assistant_config
    whitelist = set(load_assistant_config().tools_whitelist)
    cost_allowed = (thread.assistant_state or {}).get("guardrails", {}).get("cost_allowed", True)
    approval = (thread.assistant_state or {}).get("approval") or {}
    bindings = approval.get("sdb_bindings") or []
    for pending_index, task in enumerate(pending):
        binding = next((item for item in bindings if item.get("task_id") == task.get("id")), None)
        if binding is None and not bindings:
            order = next((index for index, item in enumerate(frozen_tasks) if item.get("id") == task.get("id")), None)
            if order is not None:
                binding = {
                    "order": order, "task_id": task.get("id"), "tool": task.get("tool"),
                    "arguments": task.get("arguments") or {},
                    "arguments_sha256": arguments_digest(
                        task.get("tool"), task.get("arguments") or {}, order=order, task_id=task.get("id")
                    ),
                }
        order = binding.get("order") if binding else None
        result = {
            "task_id": task.get("id"), "order": order, "tool": task.get("tool"),
            "status": "failed", "read_only": False, "result": None,
            "error": "SDB task rejected", "evidence": {},
        }
        try:
            if binding is None or order is None:
                raise ToolValidationError("SDB task is not present in consumed approval")
            if bindings and not revalidate_sdb_resume(thread, plan, approval, task, order):
                raise ToolValidationError("SDB task is not present in consumed approval")
            tool_name = task.get("tool")
            result["order"] = order
            if tool_name not in whitelist:
                raise ToolValidationError(f"tool is not whitelisted: {tool_name}")
            definition = get_tool(tool_name)
            result["read_only"] = definition.read_only
            arguments = definition.args_model.model_validate(task.get("arguments", {})).model_dump()
            from app.chat.assistant.state import SDBTask
            typed = SDBTask.model_validate({**task, "arguments": arguments})
            if not cost_allowed:
                raise ToolValidationError("assistant cost limit blocks tool execution")
            if not definition.read_only and approval.get("status") != "consumed":
                raise ToolValidationError("SDB tasks must use read-only tools")
            requested_project = typed.scope.get("proyecto", "default")
            if requested_project != "default":
                if authorization is None:
                    raise ToolValidationError("SDB project capability is unavailable")
                if authorization.slug != requested_project:
                    result["evidence"] = {"expected": authorization.slug, "requested": requested_project}
                    raise ToolValidationError("project-capability-scope-mismatch")
            if not definition.read_only and tool_name != "project.create":
                requested_slug = (
                    typed.arguments.get("project") if tool_name in {"project.rename", "project.archive"}
                    else typed.arguments.get("source") if tool_name == "project.merge" else requested_project
                )
                if authorization is None or requested_slug != authorization.slug:
                    result["evidence"] = {"expected": authorization.slug if authorization else None, "requested": requested_slug}
                    raise ToolValidationError("project-capability-scope-mismatch")
            tool_result = execute_tool(
                session, typed.tool, typed.arguments,
                approval=approval if not definition.read_only else None,
                task_binding=binding,
                whitelist=whitelist, cost_allowed=cost_allowed,
                role=(thread.assistant_state or {}).get("actor_role"),
                trusted_thread_id=thread.id,
                owner_id=thread.user_id,
                proyecto=authorization.slug if authorization is not None else "default",
            )
            result = {
                "task_id": typed.id, "order": order, "tool": typed.tool,
                "status": tool_result.get("status"), "read_only": definition.read_only,
                "result": tool_result.get("result"), "error": tool_result.get("error"),
                "evidence": tool_result.get("evidence") or {},
            }
            if result.get("status") != "completed":
                result["status"] = "failed"
            if result["status"] == "completed" and tool_name == "project.create":
                created = result.get("result") or {}
                created_slug = created.get("slug") if isinstance(created, dict) else None
                if created_slug:
                    authorization = projects.agent_context(session, created_slug, owner_id=thread.user_id)
            if result["status"] == "completed" and not definition.read_only:
                requested_project = authorization.slug if authorization else requested_project
        except (ToolValidationError, ToolExecutionError, TimeoutError, ValueError) as exc:
            result["error"] = str(exc)
        except Exception as exc:
            result["error"] = "SDB task failed"
        status = result["status"]
        audit_entry = None
        if hasattr(session, "add"):
            audit_entry = record_audit(
                session, actor="assistant", action="internal_chat.sdb_execution",
                entity="internal_chat_thread", entity_id=str(thread.id),
                after={"run_id": run_id, "task_id": result["task_id"], "status": status,
                       "order": result.get("order"), "tool": result.get("tool"),
                       "error": result.get("error"), "evidence": result.get("evidence")},
            )
            if hasattr(session, "flush"):
                session.flush()
        sequence = len(sdb.get("checkpoints", [])) + pending_index + 1
        checkpoint = {
            "run_id": run_id, "sequence": sequence, "order": result.get("order"),
            "task_id": result["task_id"], "tool": result.get("tool"), "status": status,
            "error": result.get("error"), "result_ref": f"sdb:{run_id}:result:{result['task_id']}",
        }
        audit_ref = getattr(audit_entry, "id", None)
        event = {
            "type": "task", "run_id": run_id, "sequence": sequence,
            "order": result.get("order"), "task_id": result["task_id"], "tool": result.get("tool"),
            "status": status, "error": result.get("error"), "evidence": result.get("evidence"),
            "checkpoint": checkpoint, "audit_ref": audit_ref,
            "proyecto": authorization.slug if authorization else "default",
        }
        persist_sdb_state(
            session, thread, run_id=run_id, phase="EXECUTE",
            checkpoint=checkpoint,
            events=[event],
            results=[result],
            authorization=authorization,
        )
        results.append(result)
        if status != "completed":
            break
    return {"results": results, "status": "completed" if results and all(item.get("status") == "completed" for item in results) and len(results) == len(frozen_tasks) else "failed"}


def _sdb_delivery(thread: InternalChatThread, result: dict) -> dict:
    tasks = (thread.current_plan or {}).get("sdb", {}).get("tasks", [])
    persisted = ((thread.assistant_state or {}).get("sdb") or {}).get("results", [])
    projection = sdb_verify({
        "sdb_tasks": tasks, "sdb_persisted_results": persisted, "sdb_result": result,
    })
    delivery = sdb_deliver({**projection, "sdb_result": result})
    mutation = any(not item.get("read_only", True) for item in projection["verification"].get("results", []))
    if delivery["status"] == "completed":
        response = "SDB mutation completed with verified durable evidence." if mutation else "SDB read completed with verified durable evidence."
    else:
        response = "SDB mutation failed; the run remains recoverable." if mutation else "SDB read failed; the run remains recoverable."
    return {
        "response": response,
        "evidence": delivery["evidence"],
        "verification": projection["verification"],
        "status": delivery["status"],
    }


def thread_dict(thread: InternalChatThread) -> dict:
    from app.panel.api.serializers import to_internal_chat_thread_dict

    return to_internal_chat_thread_dict(thread)


def message_dict(message: InternalChatMessage) -> dict:
    from app.panel.api.serializers import to_internal_chat_message_dict

    return to_internal_chat_message_dict(message)


def flush_panel_session(session, thread_id: int, *, source_message_ids: list[int], recap: str,
                        source_tokens: int, truncated: bool) -> dict:
    """Delegate the meaningful Tukulpan recap seam."""
    return assistant_nodes.flush_panel_session(
        session, thread_id, source_message_ids=source_message_ids, recap=recap,
        source_tokens=source_tokens, truncated=truncated,
    )


def persist_sdb_state(
    session: Session,
    thread: InternalChatThread,
    *,
    run_id: str,
    phase: str,
    checkpoint: dict,
    events: list[dict],
    spec: dict | None = None,
    results: list[dict] | None = None,
    authorization: projects._ProjectAuthorization | None = None,
) -> None:
    """Persist bounded SDB state in JSONB and the canonical Tukulpan seam."""
    if authorization is not None and not isinstance(authorization, projects._ProjectAuthorization):
        raise ValueError("SDB persistence requires an authorized project capability")
    if authorization is not None and projects.agent_context(
        session, authorization.slug, owner_id=thread.user_id
    ) != authorization:
        raise ValueError("SDB persistence requires an active authorized project capability")
    proyecto = authorization.slug if authorization is not None else "default"
    state = dict(thread.assistant_state or {})
    sdb = dict(state.get("sdb") or {})
    checkpoints = [*sdb.get("checkpoints", []), checkpoint]
    result_by_task = {item.get("task_id"): item for item in sdb.get("results", []) if item.get("task_id")}
    for result in results or []:
        if result.get("task_id"):
            result_by_task[result["task_id"]] = result
    existing_events = list(state.get("events") or [])
    ordered_events = []
    seen_events = set()
    for event in [*existing_events, *events]:
        identity = json.dumps(event, sort_keys=True, ensure_ascii=False)
        if identity in seen_events:
            continue
        seen_events.add(identity)
        event = dict(event)
        if ordered_events and event.get("sequence", 0) <= ordered_events[-1].get("sequence", 0):
            event["sequence"] = ordered_events[-1]["sequence"] + 1
        ordered_events.append(event)
    ordered_events = ordered_events[-SDB_EVENT_HISTORY_LIMIT:]
    bounded_events = [
        event if len(json.dumps(event, ensure_ascii=False).encode()) <= SDB_EVENT_LIMIT
        else {"type": event.get("type", "sdb"), "sequence": event.get("sequence", 0), "truncated": True}
        for event in ordered_events
    ]
    sdb.update({"run_id": run_id, "phase": phase, "checkpoints": checkpoints,
                "results": list(result_by_task.values()), "proyecto": proyecto})
    if spec is not None:
        sdb["spec_ref"] = {"sha256": spec.get("sha256"), "canonical_sha256": canonical_sdb_digest({"spec": spec, "tasks": [], "phase": phase})}
    thread.assistant_state = {**state, "sdb": sdb, "events": bounded_events}
    if spec is not None:
        tukulpan.persist_sdb_artifact(
            session, thread_id=thread.id, run_id=run_id, kind="spec", payload=spec,
            proyecto=proyecto, authorization=authorization,
        )
    sequence = checkpoint.get("sequence")
    tukulpan.persist_sdb_artifact(
        session, thread_id=thread.id, run_id=run_id, kind="state", sequence=sequence,
        payload=checkpoint, proyecto=proyecto, authorization=authorization,
    )
    for result in results or []:
        task_id = result.get("task_id")
        if task_id:
            tukulpan.persist_sdb_artifact(
                session, thread_id=thread.id, run_id=run_id, kind="result",
                task_id=task_id, payload=result, proyecto=proyecto, authorization=authorization,
            )


def compact_session(session, thread_id: int, messages: list) -> dict:
    """Flush and retain the newest bounded history when the session window fills.

    The trigger measures the thread's own window occupancy, computed from the
    DB-authoritative history. It must never be fed the injected context:
    `assemble_context` caps that at the injection budget, so a threshold of the
    same size could never be reached.
    """
    limits = harness_limits()
    retention = limits.compaction_retention
    retained = []
    used = 0
    for message in reversed(messages):
        cost = estimate_tokens(str(message.content))
        if used + cost > retention:
            continue
        retained.append(message)
        used += cost
    retained.reverse()
    truncated = len(retained) != len(messages)
    before_tokens = min(
        sum(estimate_tokens(str(message.content)) for message in messages),
        limits.session_window,
    )
    if before_tokens < limits.compaction_threshold:
        return {
            "window_tokens": limits.session_window,
            "threshold_tokens": limits.compaction_threshold,
            "before_tokens": before_tokens,
            "after_tokens": used,
            "flushed": False,
            "failed": False,
            "rotated": False,
            "retained_message_ids": [message.id for message in retained],
        }
    recap = "\n".join(f"{getattr(message, 'author', 'message')}: {message.content}" for message in retained)
    write = flush_panel_session(
        session, thread_id, source_message_ids=[message.id for message in retained],
        recap=recap, source_tokens=used, truncated=truncated,
    )
    written = bool(write.get("written"))
    if not written:
        return {
            "window_tokens": limits.session_window, "threshold_tokens": limits.compaction_threshold,
            "before_tokens": before_tokens, "after_tokens": used,
            "flushed": False, "rotated": False, "failed": True,
            "retained_message_ids": [message.id for message in retained], "write": write,
        }
    rotated_at = datetime.now(timezone.utc).isoformat()
    return {
        "window_tokens": limits.session_window,
        "threshold_tokens": limits.compaction_threshold,
        "before_tokens": before_tokens,
        "after_tokens": used,
        "flushed": True,
        "failed": False,
        "rotated": True,
        "retained_message_ids": [message.id for message in retained],
        "rotation": {
            "thread_id": thread_id,
            "retention_tokens": retention,
            "rotated_at": rotated_at,
        },
        "write": write,
    }


def assemble_context(session, thread_id: int, *, messages=None, attachments=None, budget: int | None = None) -> dict:
    """Build bounded panel context in stable source order.

    The default ceiling is the configured injection budget; callers may pass a
    smaller one for focused tests and bounded adapters.
    """
    if budget is None:
        budget = harness_limits().injection_budget
    if messages is None:
        messages = list(session.scalars(
            select(InternalChatMessage)
            .where(InternalChatMessage.thread_id == thread_id)
            .order_by(InternalChatMessage.created_at, InternalChatMessage.id)
        ))
    attachments = attachments or []
    items: list[dict] = []
    message_ids: list[int] = []
    attachment_ids: list[int] = []
    used = 0
    truncated = False

    messages = sorted(
        messages,
        key=lambda row: (
            getattr(row, "created_at", None).timestamp()
            if hasattr(getattr(row, "created_at", None), "timestamp")
            else 0,
            row.id,
        ),
    )
    retained_messages: list[dict] = []
    retained_ids: list[int] = []
    for message in reversed(messages):
        content = str(message.content)
        cost = estimate_tokens(content)
        if used + cost > budget:
            truncated = True
            continue
        retained_messages.append({"source": "history", "author": message.author, "content": content, "id": message.id})
        retained_ids.append(message.id)
        used += cost

    items.extend(reversed(retained_messages))
    message_ids.extend(reversed(retained_ids))

    for attachment in attachments:
        content = str(attachment.get("content", "") if isinstance(attachment, dict) else getattr(attachment, "content", ""))
        remaining = max(0, (budget - used) * 4)
        if not remaining:
            truncated = True
            continue
        encoded = content.encode("utf-8")
        if len(encoded) > remaining:
            content = encoded[:remaining].decode("utf-8", errors="ignore")
            truncated = True
        if content:
            attachment_id = attachment.get("id") if isinstance(attachment, dict) else getattr(attachment, "id", None)
            items.append({"source": "attachment", "content": content, "id": attachment_id})
            attachment_ids.append(attachment_id)
            used += estimate_tokens(content)

    return {
        "items": items,
        "meta": {
            "scope": "panel",
            "entity_id": f"thread:{thread_id}",
            "message_ids": message_ids,
            "attachment_ids": attachment_ids,
            "estimated_tokens": used,
            "truncated": truncated,
        },
    }


def create_thread(session: Session, user: User, *, proyecto: str = "default") -> InternalChatThread:
    if proyecto == "default":
        bound_project = "default"
    else:
        bound_project = projects.agent_context(session, proyecto, owner_id=user.id).slug
    thread = InternalChatThread(user_id=user.id, proyecto=bound_project)
    session.add(thread)
    session.flush()
    record_audit(session, actor=user.username, action="internal_chat.thread_created",
                 entity="internal_chat_thread", entity_id=str(thread.id),
                 after={"proyecto": bound_project})
    return thread


def _bounded_title(value: str) -> str:
    encoded = str(value or "").strip().encode("utf-8")[:TITLE_MAX_BYTES]
    return encoded.decode("utf-8", errors="ignore")


def _opening_message(session: Session, thread_id: int) -> InternalChatMessage | None:
    return session.scalar(
        select(InternalChatMessage)
        .where(InternalChatMessage.thread_id == thread_id, InternalChatMessage.author == "admin")
        .order_by(InternalChatMessage.created_at, InternalChatMessage.id)
    )


def _generate_thread_title(
    session: Session, thread: InternalChatThread, response_message: InternalChatMessage,
) -> None:
    """Set a one-time, bounded title without affecting the response path."""
    if thread.title is not None:
        return
    opening = _opening_message(session, thread.id)
    fallback = _bounded_title(opening.content if opening else "") or "Conversación con el asistente"
    try:
        _, mode = costs.internal_thread_cost_state(session, thread.id)
        if mode != "normal":
            thread.title = fallback
            return
        settings = llm.get_settings()
        provider = getattr(settings, "assistant_chat_provider", None)
        try:
            client = llm.openai_client(provider)
        except TypeError:
            client = llm.openai_client()
        completion = client.chat.completions.create(
            model=getattr(settings, "assistant_chat_model", llm.CHAT_MODEL),
            messages=[{
                "role": "user",
                "content": "Create a concise title for this opening assistant request. Return title text only.\n\n"
                           + (opening.content if opening else ""),
            }],
            temperature=0,
            max_tokens=24,
            timeout=TITLE_TIMEOUT_SECONDS,
        )
        choices = getattr(completion, "choices", [])
        message = getattr(choices[0], "message", None) if choices else None
        generated = _bounded_title(getattr(message, "content", "") if message else "")
        if not generated:
            thread.title = fallback
            return
        thread.title = generated
        usage = getattr(completion, "usage", None)
        costs.record_llm_cost(
            session,
            target=response_message,
            call_key=f"{response_message.assistant_metadata.get('run_id', '')}:title",
            model=getattr(settings, "assistant_chat_model", llm.CHAT_MODEL),
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
        )
    except Exception:
        thread.title = fallback


def create_run_message(
    session: Session,
    thread: InternalChatThread,
    user: User,
    content: str,
    attachment_ids: list[int] | None = None,
    *,
    sdb_requested: bool | None = None,
) -> InternalChatMessage:
    run_id = uuid4().hex
    message = InternalChatMessage(
        thread_id=thread.id,
        author="admin",
        content=content.strip(),
        status="processing",
        assistant_metadata={"run_id": run_id},
    )
    session.add(message)
    session.flush()
    thread.active_run_id = run_id
    thread.assistant_state = merge_assistant_state(thread.assistant_state or {}, {
        "execution_status": "pending",
        "live": {
            "run_id": run_id, "stage": "planning", "preview": "", "status": "running",
            "updated_at": _now_iso(),
        },
    })
    return message


def publish_live(session_factory, thread_id: int, run_id: str, *, stage=None, preview=None, status=None) -> None:
    """Best-effort short transaction for progress visible to SSE clients."""
    session = session_factory()
    try:
        thread = session.get(InternalChatThread, thread_id)
        if thread is None:
            return
        state = dict(thread.assistant_state or {})
        live = dict(state.get("live") or {})
        if live.get("run_id") != run_id:
            return
        live["run_id"] = run_id
        live["updated_at"] = _now_iso()
        for key, value in (("stage", stage), ("preview", preview), ("status", status)):
            if value is not None:
                live[key] = value
        thread.assistant_state = {**state, "live": live}
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Unable to publish assistant live progress")
    finally:
        session.close()


def _run_agent_turn_session(
    session: Session, thread: InternalChatThread, user: User, message: InternalChatMessage,
    attachment_ids: list[int], sdb_requested: bool | None,
) -> None:
    run_id = message.assistant_metadata["run_id"]
    try:
        project_authorization = _thread_project_authorization(session, thread)
        preview: list[str] = []
        token_count = 0
        last_flush = time.monotonic()

        def publish_token(token: str) -> None:
            nonlocal token_count, last_flush
            preview.append(token)
            token_count += 1
            now = time.monotonic()
            if token_count >= 40 or now - last_flush >= 0.25:
                publish_live(_session_factory(), thread.id, run_id, preview="".join(preview))
                token_count = 0
                last_flush = now

        attachments = list(session.scalars(select(AssistantAttachment).where(AssistantAttachment.thread_id == thread.id, AssistantAttachment.id.in_(attachment_ids), AssistantAttachment.deleted_at.is_(None)))) if attachment_ids else []
        context_attachments = prepare_attachment_context(attachments) if attachments else []
        context = assemble_context(session, thread.id, attachments=context_attachments)
        compaction = compact_session(
            session, thread.id, list(session.scalars(
                select(InternalChatMessage)
                .where(InternalChatMessage.thread_id == thread.id)
                .order_by(InternalChatMessage.created_at, InternalChatMessage.id)
            ))
        )
        result = run_assistant(
            thread_id=thread.id,
            user_id=user.id,
            content=message.content,
            run_id=run_id,
            request_message_id=message.id,
            on_token=publish_token,
            session=session,
            actor=user.username,
            actor_role=user.role.value,
            sdb_requested=sdb_requested,
            attachments=attachments,
            context=context,
            compaction=compaction,
            project_authorization=project_authorization,
            cortex_session=(thread.assistant_state or {}).get("cortex_session"),
            on_stage=lambda stage: publish_live(_session_factory(), thread.id, run_id, stage=stage),
        )
        publish_live(_session_factory(), thread.id, run_id, preview="".join(preview))
        thread.active_run_id = run_id
        thread.current_plan = result.get("plan")
        if result.get("sdb_phase"):
            thread.current_plan = _sdb_plan(result["sdb_spec"], result.get("sdb_tasks", []))
            thread.current_plan["sdb"] = dict(thread.current_plan)
            first_task = thread.current_plan["tasks"][0] if thread.current_plan["tasks"] else {}
            thread.current_plan.update({"tool": first_task.get("tool"), "arguments": first_task.get("arguments", {}), "requires_approval": True})
            result["approval"] = issue_approval(thread.current_plan)
        thread.assistant_state = merge_assistant_state(thread.assistant_state or {}, {
            "stage": result.get("status", "completed"),
            "recoverable": True,
            "approval": result.get("approval"),
            "execution_status": "pending" if result.get("status") == "approval_pending" else "completed",
            "live": {"run_id": run_id, "preview": "".join(preview), "status": "approval_pending" if result.get("status") == "approval_pending" else "completed"},
            "events": _events_for(result, thread.id, run_id),
            "context_meta": context["meta"],
            "guardrails": result.get("guardrails", {}),
            "cost_mode": result.get("cost_mode", "normal"),
            "cost_directive": result.get("cost_directive", ""),
            "tool_steps": result.get("tool_steps", 0),
            "cap_reached": result.get("cap_reached", False),
            "compaction": compaction,
            **({"cortex_session": result["cortex_session"]} if result.get("cortex_session") else {}),
        })
        # The planner snapshot belongs to this turn. Merging it kept an earlier turn's failure
        # diagnostic and arguments alive in a later successful turn, because `plan_llm` omits
        # `failure` on success and `arguments` is a nested dict the merge recursed into.
        thread.assistant_state["planner"] = result.get("planner", {})
        if result.get("sdb_phase"):
            persist_sdb_state(
                session,
                thread,
                run_id=run_id,
                phase=result["sdb_phase"],
                checkpoint={"sequence": 0, "phase": result["sdb_phase"]},
                events=_events_for(result, thread.id, run_id),
                spec=result.get("sdb_spec"),
                results=(result.get("sdb_result") or {}).get("results", []),
                authorization=project_authorization,
            )
        message.assistant_metadata = {
            **(message.assistant_metadata or {}),
            "run_id": run_id, "approval": result.get("approval"),
            "attachment_ids": [row.id for row in attachments],
            "cost_mode": result.get("cost_mode", "normal"),
        }
        if result.get("status") == "approval_pending":
            message.status = "approval_pending"
        else:
            message.status = "processed"
            message.completed_at = datetime.now(timezone.utc)
            response_message = InternalChatMessage(
                thread_id=thread.id,
                author="agent",
                content=result.get("response") or "No pude generar una respuesta. Inténtalo nuevamente.",
                status="processed",
                completed_at=datetime.now(timezone.utc),
                assistant_metadata={"run_id": run_id},
            )
            session.add(response_message)
            session.flush()
            _generate_thread_title(session, thread, response_message)
            stage_event(
                session,
                type="message",
                conversation_id=thread.id,
                data=message_dict(response_message),
            )
    except Exception as exc:
        message.status = "failed"
        message.error = "El agente no pudo procesar este mensaje. Reinténtalo."
        message.completed_at = datetime.now(timezone.utc)
        message.assistant_metadata = {**(message.assistant_metadata or {}), "run_id": run_id}
        thread.assistant_state = merge_assistant_state(thread.assistant_state or {}, {
            "stage": "failed",
            "execution_status": "failed",
            "live": {"run_id": run_id, "stage": "failed", "status": "failed"},
            "recoverable": True,
            "events": [{
                "type": "error",
                "thread_id": thread.id,
                "run_id": run_id,
                "sequence": 0,
                "error": str(exc),
                "evidence": getattr(exc, "evidence", []),
            }],
        })
        thread.active_run_id = run_id
        logger.exception("Assistant run failed", exc_info=exc)
    record_audit(session, actor=user.username, action="internal_chat.message_sent",
                 entity="internal_chat_message", entity_id=str(message.id),
                 after={"status": message.status})
    session.flush()


def _session_factory():
    from app.db import SessionLocal
    return SessionLocal


def run_agent_turn(*, thread_id: int, run_id: str, user_id: int,
                   attachment_ids: list[int], sdb_requested: bool | None) -> None:
    """Background entry point; owns and closes its database session."""
    session = _session_factory()()
    try:
        thread = session.get(InternalChatThread, thread_id)
        user = session.get(User, user_id)
        message = session.scalar(select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread_id,
            InternalChatMessage.assistant_metadata["run_id"].as_string() == run_id,
        ).order_by(InternalChatMessage.id.desc()))
        if thread is None or user is None or message is None:
            return
        # `_run_agent_turn_session` records `message_sent` itself, unconditionally
        # and with the final status — recording it again here duplicated the row.
        _run_agent_turn_session(session, thread, user, message, attachment_ids, sdb_requested)
        session.commit()
        publish_live(_session_factory(), thread_id, run_id,
                     status=(thread.assistant_state or {}).get("live", {}).get("status"),
                     preview=(thread.assistant_state or {}).get("live", {}).get("preview"))
    except Exception:
        session.rollback()
        logger.exception("Unable to complete background assistant run")
        if 'message' in locals() and message is not None and 'thread' in locals() and thread is not None:
            message.status = "failed"
            thread.assistant_state = merge_assistant_state(thread.assistant_state or {}, {
                "stage": "failed", "live": {"run_id": run_id, "stage": "failed", "status": "failed"},
            })
            session.commit()
    finally:
        session.close()


def submit_message(
    session: Session, thread: InternalChatThread, user: User, content: str,
    attachment_ids: list[int] | None = None, *, sdb_requested: bool | None = None,
) -> InternalChatMessage:
    """Compatibility wrapper retaining the historical synchronous service API."""
    message = create_run_message(session, thread, user, content, attachment_ids, sdb_requested=sdb_requested)
    _run_agent_turn_session(session, thread, user, message, attachment_ids or [], sdb_requested)
    return message


def _events_for(result: dict, thread_id: int, run_id: str) -> list[dict]:
    if result.get("sdb_phase"):
        phases = ["CLARIFY", "SPEC", "PLAN", "APPROVE"]
        return [
            {"type": "phase", "thread_id": thread_id, "run_id": run_id,
             "sequence": sequence, "phase": phase}
            for sequence, phase in enumerate(phases)
        ] + [{
            "type": "approval", "thread_id": thread_id, "run_id": run_id,
            "sequence": len(phases), "approval": result.get("approval"),
            "status": result.get("status"),
        }]
    events = [
        {"type": "plan", "thread_id": thread_id, "run_id": run_id, "sequence": 0, "plan": result.get("plan", {})},
        {"type": "approval", "thread_id": thread_id, "run_id": run_id, "sequence": 1, "approval": result.get("approval"), "status": result.get("status")},
    ]
    if result.get("status") != "approval_pending":
        events.extend(_execution_events(result, thread_id, run_id, len(events)))
    return events


def _execution_events(result: dict, thread_id: int, run_id: str, sequence: int) -> list[dict]:
    tool_result = result.get("tool_result") or {}
    return [
        {"type": "tool", "thread_id": thread_id, "run_id": run_id, "sequence": sequence, "tool": tool_result.get("tool"), "status": tool_result.get("status", result.get("status", "completed"))},
        {"type": "evidence", "thread_id": thread_id, "run_id": run_id, "sequence": sequence + 1, "evidence": result.get("evidence", [])},
        {"type": "status", "thread_id": thread_id, "run_id": run_id, "sequence": sequence + 2, "status": result.get("status", "completed")},
        {"type": "response", "thread_id": thread_id, "run_id": run_id, "sequence": sequence + 3, "content": result.get("response", "")},
    ]


_TERMINAL_RUN_STATUSES = {"completed", "failed", "approval_pending"}


class _EventCursor:
    """Turns successive polls into a single de-duplicated view of one run.

    Persisted events are authoritative and emitted once each; the live stage and
    preview are emitted only when they change. Keeping this state in one place is
    what stops the sync and async polls from drifting apart.
    """

    def __init__(self) -> None:
        self._seen: set[tuple] = set()
        self._stage: object = object()
        self._preview: object = object()
        self.sequence = 0

    def feed(self, events: list[dict], live: dict, thread_id: int, run_id: str) -> tuple[list[dict], bool]:
        """Return the events to emit now and whether the run reached a terminal status."""
        fresh: list[dict] = []
        for event in events:
            identity = (event.get("run_id"), event.get("sequence"), event.get("type"), event.get("task_id"), event.get("tool"))
            if identity not in self._seen:
                self._seen.add(identity)
                fresh.append(event)
                self.sequence = max(self.sequence, int(event.get("sequence", 0)) + 1)
        if live.get("run_id") != run_id:
            return fresh, False
        if live.get("stage") != self._stage:
            self._stage = live.get("stage")
            fresh.append({"type": "status", "thread_id": thread_id, "run_id": run_id, "sequence": self.sequence, "status": self._stage})
            self.sequence += 1
        if live.get("preview") != self._preview:
            self._preview = live.get("preview")
            fresh.append({"type": "response", "thread_id": thread_id, "run_id": run_id, "sequence": self.sequence, "content": self._preview})
            self.sequence += 1
        return fresh, live.get("status") in _TERMINAL_RUN_STATUSES


def _poll_once(session_factory, thread_id: int, run_id: str) -> tuple[list[dict], dict] | None:
    """Read one snapshot in a short transaction; None when the thread is gone."""
    session = session_factory()
    try:
        thread = session.get(InternalChatThread, thread_id)
        if thread is None:
            return None
        return recover_events(thread, run_id), dict((thread.assistant_state or {}).get("live") or {})
    finally:
        session.close()


def stream_events(session_factory, thread_id: int, run_id: str, *, timeout=300.0, interval=0.25):
    """Poll short transactions so persisted events and live progress are observable."""
    # Keep the pre-live service helper callable for older integrations; the SSE
    # endpoint uses `stream_events_async` instead (see `assistant-sse-resource-hold`).
    if not isinstance(thread_id, int):
        return recover_events(thread_id, run_id)
    if not run_id:
        return iter(())

    def poll():
        """Yield each event once while the run remains observable."""
        started = time.monotonic()
        cursor = _EventCursor()
        while time.monotonic() - started < timeout:
            snapshot = _poll_once(session_factory, thread_id, run_id)
            if snapshot is None:
                return
            fresh, done = cursor.feed(*snapshot, thread_id, run_id)
            yield from fresh
            if done:
                return
            time.sleep(interval)
        # Falling out of the loop means the deadline elapsed with the run still
        # unsettled: the stream is ending, the run is not. This transport-only
        # marker lets clients distinguish the deadline from a finished turn.
        yield {"type": "timeout", "thread_id": thread_id, "run_id": run_id}

    return poll()


async def stream_events_async(session_factory, thread_id: int, run_id: str, *, timeout=300.0, interval=0.25):
    """Poll without holding a worker thread while a stream waits.

    Only the database read hops to a thread; the wait between polls is an
    `asyncio.sleep` on the event loop. A sync generator here would be consumed
    through the process-wide AnyIO pool (40 workers), so an open stream would
    keep one of those workers busy for its whole 300 s life.
    """
    if not isinstance(thread_id, int):
        for event in recover_events(thread_id, run_id):
            yield event
        return
    if not run_id:
        return
    started = time.monotonic()
    cursor = _EventCursor()
    while time.monotonic() - started < timeout:
        snapshot = await asyncio.to_thread(_poll_once, session_factory, thread_id, run_id)
        if snapshot is None:
            return
        fresh, done = cursor.feed(*snapshot, thread_id, run_id)
        for event in fresh:
            yield event
        if done:
            return
        await asyncio.sleep(interval)
    # Falling out of the loop means the deadline elapsed with the run still
    # unsettled: the stream is ending, the run is not. This transport-only
    # marker lets clients distinguish the deadline from a finished turn.
    yield {"type": "timeout", "thread_id": thread_id, "run_id": run_id}


def approve_plan(session: Session, thread: InternalChatThread, user: User, run_id: str, token: str, *, reject: bool = False) -> InternalChatMessage | None:
    """Atomically consume or reject the approval stored on the thread."""
    plan = thread.current_plan or {}
    state = thread.assistant_state or {}
    approval = state.get("approval") or {}
    if thread.active_run_id != run_id or not validate_approval(plan, approval, token):
        return None
    status = "rejected" if reject else "consumed"
    updated = session.execute(
        text("""
            UPDATE internal_chat_threads
            SET assistant_state = jsonb_set(assistant_state, '{approval,status}', CAST(:status AS jsonb))
            WHERE id = :thread_id
              AND active_run_id = :run_id
              AND assistant_state #>> '{approval,status}' = 'pending'
            RETURNING id
        """),
        {"status": json.dumps(status), "thread_id": thread.id, "run_id": run_id},
    ).scalar_one_or_none()
    if updated is None:
        return None
    session.refresh(thread)
    message = session.scalar(
        select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread.id,
            InternalChatMessage.assistant_metadata["run_id"].as_string() == run_id,
        ).order_by(InternalChatMessage.id.desc())
    )
    if message is None:
        return None
    if reject:
        message.status = "rejected"
        return message
    actor_role = getattr(user.role, "value", user.role)
    thread.assistant_state = {
        **thread.assistant_state,
        "stage": "executing",
        "execution_status": "pending",
        "actor_role": actor_role,
    }
    session.flush()
    if not claim_execution(session, thread):
        return None
    if plan.get("sdb"):
        result = _run_sdb_tasks(session, thread, run_id, _thread_project_authorization(session, thread))
        result.update(_sdb_delivery(thread, result))
    else:
        result = execute({
        "thread_id": thread.id,
        "run_id": run_id,
        "content": message.content,
        "plan": plan,
        "approval": thread.assistant_state["approval"],
        "session": session,
        "actor": user.username,
        "actor_role": actor_role,
        "request_message_id": message.id,
        })
    message.status = "processed" if result.get("status") == "completed" else "failed"
    message.completed_at = datetime.now(timezone.utc)
    thread.assistant_state = {**thread.assistant_state, "stage": result.get("status"), "execution_status": result.get("status"), "verification": result.get("verification")}
    response_message = InternalChatMessage(
        thread_id=thread.id, author="agent", content=result["response"], status="processed",
        completed_at=datetime.now(timezone.utc), assistant_metadata={"run_id": run_id},
    )
    session.add(response_message)
    session.flush()
    thread.assistant_state = {
        **thread.assistant_state,
        "events": [
            *(thread.assistant_state.get("events") or []),
            *_execution_events(result, thread.id, run_id, len(thread.assistant_state.get("events") or [])),
        ],
    }
    session.flush()
    return message


def _fail_orphaned_run(session: Session, thread: InternalChatThread, *, now: datetime, run_id: str | None = None) -> bool:
    """Fail a run nothing can still be working on, which re-enables the Retry action.

    Callers own the evidence that the run is orphaned; this only writes the
    terminal state and the operator-facing copy a crashed run produces.
    """
    run_id = run_id or (thread.assistant_state or {}).get("live", {}).get("run_id") or thread.active_run_id
    message = session.scalar(
        select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread.id,
            InternalChatMessage.assistant_metadata["run_id"].as_string() == run_id,
            InternalChatMessage.status == "processing",
        ).order_by(InternalChatMessage.id.desc())
    )
    if message is not None:
        message.status = "failed"
        message.error = "El agente no pudo procesar este mensaje. Reinténtalo."
        message.completed_at = now
    thread.assistant_state = merge_assistant_state(thread.assistant_state or {}, {
        "stage": "failed",
        "execution_status": "failed",
        "recoverable": True,
        "live": {
            "run_id": run_id, "stage": "failed", "status": "failed", "updated_at": now.isoformat(),
        },
    })
    logger.warning("Reaped an orphaned assistant run for thread %s", thread.id)
    session.flush()
    return True


def reap_stale_run(session: Session, thread: InternalChatThread) -> bool:
    """Fail closed on a panel run whose background task never ran, or died.

    `create_run_message` commits the operator's message as `processing` and the
    HTTP handler hands the turn to an in-process FastAPI background task, so a
    crash or redeploy between those two points leaves the row spinning forever.
    Nothing can still be working on a run whose `live` state stopped advancing
    for `STALE_RUN_SECONDS`, so mark it failed with the same copy a crashed run
    produces — which is what re-enables the operator's Retry action.

    A run the durable `resume_thread` path can still reclaim is left alone:
    recovering a persisted execution beats failing it. Rows written before
    `live.updated_at` existed are reaped on sight, which is correct because the
    deploy that introduced this field is exactly what orphaned them.
    """
    state = thread.assistant_state or {}
    if state.get("stage") == "executing" and state.get("execution_status") == "pending":
        return False
    live = state.get("live") or {}
    if live.get("status") != "running":
        return False
    try:
        updated_at = datetime.fromisoformat(live.get("updated_at") or "")
    except (TypeError, ValueError):
        updated_at = None
    now = datetime.now(timezone.utc)
    if updated_at is not None and (now - updated_at).total_seconds() < STALE_RUN_SECONDS:
        return False
    return _fail_orphaned_run(session, thread, now=now, run_id=live.get("run_id") or thread.active_run_id)


def reap_orphaned_runs(session_factory, *, limit: int = 50) -> int:
    """Fail every assistant run this fresh process cannot own; called once at boot.

    A single process owns no background task before it serves a request, so a
    `running` live state at startup is proof the run was orphaned by a crash or a
    redeploy — no silence timer needed. Waiting for `STALE_RUN_SECONDS` instead
    leaves the operator with a live spinner and no Retry action for ten minutes
    after every deploy that lands mid-turn.

    Resumable executions are skipped: `resume_thread` can still reclaim those,
    and failing them would discard persisted work.
    """
    session = session_factory()
    reaped = 0
    try:
        threads = session.scalars(
            select(InternalChatThread)
            .where(InternalChatThread.assistant_state["live"]["status"].as_string() == "running")
            .order_by(InternalChatThread.id)
            .limit(limit)
        ).all()
        now = datetime.now(timezone.utc)
        for thread in threads:
            state = thread.assistant_state or {}
            if state.get("stage") == "executing" and state.get("execution_status") == "pending":
                continue
            _fail_orphaned_run(session, thread, now=now)
            reaped += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    if reaped:
        logger.warning("Reaped %s orphaned assistant runs at startup", reaped)
    return reaped


def resume_thread(session: Session, thread: InternalChatThread, user: User) -> bool:
    """Resume a persisted execution after interruption, with an atomic claim."""
    state = thread.assistant_state or {}
    if state.get("stage") != "executing" or not claim_execution(session, thread, active_run_id=thread.active_run_id):
        return False
    run_id = thread.active_run_id
    if not run_id:
        return False
    message = session.scalar(
        select(InternalChatMessage).where(
            InternalChatMessage.thread_id == thread.id,
            InternalChatMessage.assistant_metadata["run_id"].as_string() == run_id,
            InternalChatMessage.status == "processing",
        ).order_by(InternalChatMessage.id.desc())
    )
    if message is None:
        return False
    actor_role = getattr(user.role, "value", user.role)
    thread.assistant_state = {**(thread.assistant_state or {}), "actor_role": actor_role}
    if (thread.current_plan or {}).get("sdb"):
        result = _run_sdb_tasks(session, thread, run_id, _thread_project_authorization(session, thread))
        result.update(_sdb_delivery(thread, result))
    else:
        result = execute({
        "thread_id": thread.id,
        "run_id": run_id,
        "content": message.content,
        "plan": thread.current_plan or {},
        "approval": thread.assistant_state.get("approval"),
        "session": session,
        "actor": user.username,
        "actor_role": actor_role,
        "request_message_id": message.id,
        })
    message.status = "processed" if result.get("status") == "completed" else "failed"
    message.completed_at = datetime.now(timezone.utc)
    thread.assistant_state = {**thread.assistant_state, "stage": result.get("status"), "execution_status": result.get("status"), "verification": result.get("verification")}
    session.add(InternalChatMessage(
        thread_id=thread.id, author="agent", content=result["response"], status="processed",
        completed_at=datetime.now(timezone.utc), assistant_metadata={"run_id": run_id},
    ))
    thread.assistant_state = {
        **thread.assistant_state,
        "events": [
            *(thread.assistant_state.get("events") or []),
            *_execution_events(result, thread.id, run_id, len(thread.assistant_state.get("events") or [])),
        ],
    }
    session.flush()
    return True


def get_thread(session: Session, thread_id: int, user_id: int) -> tuple[InternalChatThread, list[InternalChatMessage]] | None:
    thread = session.scalar(select(InternalChatThread).where(InternalChatThread.id == thread_id, InternalChatThread.user_id == user_id))
    if thread is None:
        return None
    messages = list(session.scalars(select(InternalChatMessage).where(InternalChatMessage.thread_id == thread.id).order_by(InternalChatMessage.created_at, InternalChatMessage.id)))
    return thread, messages


def read_owned_thread_run(session_factory, thread_id: int, user_id: int) -> tuple[str | None] | None:
    """Ownership check and `active_run_id` for the assistant stream route.

    Callers run this through `asyncio.to_thread`, so it opens its own short
    session instead of receiving one: a `Session` is not thread-safe and must
    not cross threads — the same shape `_poll_once` gives the stream's polling.
    The one-tuple keeps "not this user's thread" (`None`) distinct from a thread
    that simply has no active run.
    """
    session = session_factory()
    try:
        thread = session.scalar(select(InternalChatThread).where(InternalChatThread.id == thread_id, InternalChatThread.user_id == user_id))
        return None if thread is None else (thread.active_run_id,)
    finally:
        session.close()
