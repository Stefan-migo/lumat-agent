"""Persistence boundary for the panel assistant graph."""

from datetime import datetime, timezone
import json
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.chat.assistant.graph import run_assistant
from app.chat.assistant.approval import arguments_digest, canonical_sdb_digest, issue_approval, validate_approval
from app.chat.assistant.nodes import execute, sdb_deliver, sdb_verify
from app.chat.assistant.tools.registry import ToolExecutionError, ToolValidationError, execute_tool, get_tool
from app.chat.assistant import nodes as assistant_nodes
from app.chat.assistant.attachments import prepare_attachment_context
from app.chat.assistant.state import COMPACTION_RETENTION_TOKENS, COMPACTION_THRESHOLD_TOKENS, INJECTION_TOKEN_BUDGET, estimate_tokens, merge_assistant_state
from app.chat.assistant.recovery import claim_execution, recover_events, revalidate_sdb_resume, resumable_sdb_tasks
from app.models import AssistantAttachment, InternalChatMessage, InternalChatThread, User
from app.services.audit import record_audit
from app.services.realtime import stage_event
from app.services import tukulpan
from app.services import projects


SDB_EVENT_LIMIT = 4 * 1024
SDB_EVENT_HISTORY_LIMIT = 64


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
    proyecto = ((thread.assistant_state or {}).get("sdb") or {}).get("proyecto", "default")
    return None if proyecto == "default" else projects.agent_context(session, proyecto)


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
                    authorization = projects.agent_context(session, created_slug)
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


def load_panel_context(session, thread_id: int) -> dict:
    """Delegate the read-only Tukulpan panel context seam."""
    return assistant_nodes.load_panel_context(session, thread_id)


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
    if authorization is not None and projects.agent_context(session, authorization.slug) != authorization:
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


def compact_session(session, thread_id: int, messages: list, *, before_tokens: int) -> dict:
    """Flush and retain the newest bounded history when the session threshold is met."""
    retention = COMPACTION_RETENTION_TOKENS
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
    if before_tokens < COMPACTION_THRESHOLD_TOKENS:
        return {
            "window_tokens": 8_000,
            "threshold_tokens": COMPACTION_THRESHOLD_TOKENS,
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
            "window_tokens": 8_000, "threshold_tokens": COMPACTION_THRESHOLD_TOKENS,
            "before_tokens": before_tokens, "after_tokens": used,
            "flushed": False, "rotated": False, "failed": True,
            "retained_message_ids": [message.id for message in retained], "write": write,
        }
    rotated_at = datetime.now(timezone.utc).isoformat()
    return {
        "window_tokens": 8_000,
        "threshold_tokens": COMPACTION_THRESHOLD_TOKENS,
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


def assemble_context(session, thread_id: int, *, messages=None, attachments=None, budget: int = INJECTION_TOKEN_BUDGET) -> dict:
    """Build bounded panel context in stable source order.

    The default is the fixed 4,000-token harness budget; callers may pass a
    smaller ceiling for focused tests and bounded adapters.
    """
    if messages is None:
        messages = list(session.scalars(
            select(InternalChatMessage)
            .where(InternalChatMessage.thread_id == thread_id)
            .order_by(InternalChatMessage.created_at, InternalChatMessage.id)
        ))
    attachments = attachments or []
    tukulpan = load_panel_context(session, thread_id)
    items: list[dict] = []
    message_ids: list[int] = []
    attachment_ids: list[int] = []
    tukulpan_ids: list[str] = []
    used = 0
    truncated = False

    for source in (tukulpan.get("pinned", []), tukulpan.get("panel", [])):
        for entry in source:
            content = str(entry.get("content", ""))
            cost = estimate_tokens(content)
            if used + cost > budget:
                truncated = True
                continue
            items.append({"source": "tukulpan", "content": content, "id": entry.get("id")})
            tukulpan_ids.append(str(entry.get("id")))
            used += cost

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
            "tukulpan_ids": tukulpan_ids,
            "estimated_tokens": used,
            "truncated": truncated,
        },
    }


def create_thread(session: Session, user: User) -> InternalChatThread:
    thread = InternalChatThread(user_id=user.id)
    session.add(thread)
    session.flush()
    record_audit(session, actor=user.username, action="internal_chat.thread_created",
                 entity="internal_chat_thread", entity_id=str(thread.id))
    return thread


def submit_message(
    session: Session,
    thread: InternalChatThread,
    user: User,
    content: str,
    attachment_ids: list[int] | None = None,
    *,
    sdb_requested: bool | None = None,
    project_authorization: projects._ProjectAuthorization | None = None,
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
    try:
        def publish_token(token: str) -> None:
            stage_event(session, type="token", conversation_id=thread.id, data={"token": token})

        attachments = list(session.scalars(select(AssistantAttachment).where(AssistantAttachment.thread_id == thread.id, AssistantAttachment.id.in_(attachment_ids or []), AssistantAttachment.deleted_at.is_(None)))) if attachment_ids else []
        context_attachments = prepare_attachment_context(attachments) if attachments else []
        context = assemble_context(session, thread.id, attachments=context_attachments)
        compaction = compact_session(
            session, thread.id, list(session.scalars(
                select(InternalChatMessage)
                .where(InternalChatMessage.thread_id == thread.id)
                .order_by(InternalChatMessage.created_at, InternalChatMessage.id)
            )), before_tokens=context["meta"]["estimated_tokens"]
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
        )
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
            "events": _events_for(result, thread.id, run_id),
            "context_meta": context["meta"],
            "planner": result.get("planner", {}),
            "guardrails": result.get("guardrails", {}),
            "cost_mode": result.get("cost_mode", "normal"),
            "cost_directive": result.get("cost_directive", ""),
            "compaction": compaction,
            **({"cortex_session": result["cortex_session"]} if result.get("cortex_session") else {}),
        })
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
    record_audit(session, actor=user.username, action="internal_chat.message_sent",
                 entity="internal_chat_message", entity_id=str(message.id),
                 after={"status": message.status})
    session.flush()
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


def stream_events(session: Session, thread: InternalChatThread, run_id: str | None = None) -> list[dict]:
    return recover_events(thread, run_id)


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
    thread.assistant_state = {
        **thread.assistant_state,
        "stage": "executing",
        "execution_status": "pending",
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
