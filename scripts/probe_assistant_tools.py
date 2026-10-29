#!/usr/bin/env python3
"""Probe registered assistant tools without exposing customer data or making writes."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Settings validates unrelated webhook/panel secrets at import time. Use
# non-secret placeholders only when absent; never replace DATABASE_URL/keys.
for _setting in ("APP_SECRET", "VERIFY_TOKEN", "META_ACCESS_TOKEN", "META_PHONE_NUMBER_ID", "PANEL_SESSION_SECRET"):
    os.environ.setdefault(_setting, f"tools-probe-{_setting.lower()}")

from sqlalchemy import select

from app.chat.assistant.tools.registry import TOOL_REGISTRY, execute_tool, is_tool_allowed_for_role
from app.config import get_settings
from app.db import SessionLocal
from app.models import AssistantAttachment, Conversation, Customer, InternalChatThread, Project, ProjectFile, User

# A fixture exists for each tool, including writes. Write fixtures are validated
# against their args models but never passed to execute_tool.
ARGUMENT_FIXTURES: dict[str, dict[str, Any]] = {
    "assistant.capabilities": {},
    "customers.search": {"query": "probe", "limit": 1},
    "customers.list": {"query": None, "limit": 1},
    "conversations.search": {"query": "probe", "limit": 1},
    "conversations.list": {"query": None, "limit": 1},
    "appointments.upcoming": {"limit": 1},
    "customers.operational_history": {"customer_id": 1, "limit": 1},
    "cases.list": {"limit": 1},
    "kb.retrieve": {"query": "probe", "top_k": 1},
    "memory.read": {"scope": "own", "limit": 1},
    "memory.search": {"scope": "own", "query": "probe", "limit": 1},
    "memory.write": {"titulo": "probe", "contenido": "probe", "topic_key": "agent:probe", "tipo": "discovery"},
    "memory.update": {"id": 1, "titulo": "probe"},
    "memory.delete": {"id": 1},
    "dashboard.summary": {"window_days": 1},
    "analytics.chatbot_metrics": {"window_days": 1},
    "analytics.chatbot_conversations": {"window_days": 1, "signal": "any", "limit": 1},
    "conversations.transcript": {"conversation_id": 1, "limit": 1},
    "settings.update": {"key": "probe", "value": "probe"},
    "web.search": {"query": "probe", "limit": 1},
    "web.fetch": {"url": "https://example.com/"},
    "automation.create_rule": {"recipe_id": "probe", "parameters": {}},
    "project.find": {"query": "probe"},
    "project.list": {"limit": 1},
    "list_project_files": {"limit": 1},
    "read_project_file": {"file_id": 1, "offset": 0, "limit": 100},
    "view_image": {"source": "project", "id": 1},
    "artifact.save": {"filename": "probe.txt", "content": "probe"},
    "project.create": {"slug": "probe", "name": "Probe", "purpose": "Probe"},
    "project.rename": {"project": "probe", "name": "Probe"},
    "project.archive": {"project": "probe"},
    "project.merge": {"source": "probe", "target": "probe-target"},
    "skill.propose": {"name": "probe", "description": "Probe", "body": "Probe"},
}
SKIP_REASONS: dict[str, str] = {
    # No tool is skipped for being expensive: probing a bounded read list is what this
    # instrument measures. Add an entry only when the environment, not the tool, makes a
    # call impossible, and name that condition.
}
UNBOUNDED_READ_NOTE = "handler materializes the list before slicing"


def _bounded_id(session, model, *conditions):
    return session.scalar(select(model.id).where(*conditions).order_by(model.id).limit(1))


def _summary(result: Any) -> str:
    """Summarize shape only; never stringify field values or returned rows."""
    if isinstance(result, list):
        keys = sorted({key for row in result[:20] if isinstance(row, dict) for key in row})
        return f"rows={len(result)} fields={','.join(keys) or '-'}"
    if isinstance(result, dict):
        if "capabilities" in result:
            return f"keys={','.join(sorted(result))} tool_count={result.get('tool_count', 0)}"
        if "files" in result and isinstance(result["files"], list):
            return f"keys={','.join(sorted(result))} files={len(result['files'])}"
        if "cases" in result or "appointments" in result:
            return f"keys={','.join(sorted(result))} cases={len(result.get('cases', []))} appointments={len(result.get('appointments', []))}"
        keys = sorted(result)
        return f"keys={','.join(keys[:20])}"
    if result is None:
        return "empty"
    # Avoid leaking scalar outputs; only describe the type.
    return f"type={type(result).__name__}"


def _tool_args(session, name: str, project_id: int | None, owner_id: int | None, thread_id: int | None) -> tuple[dict | None, str | None]:
    args = dict(ARGUMENT_FIXTURES[name])
    if name == "customers.operational_history":
        value = _bounded_id(session, Customer)
        if value is None:
            return None, "no customer rows"
        args["customer_id"] = value
    elif name == "conversations.transcript":
        value = _bounded_id(session, Conversation)
        if value is None:
            return None, "no conversation rows"
        args["conversation_id"] = value
    elif name == "read_project_file":
        if project_id is None or owner_id is None:
            return None, "no project files"
        value = _bounded_id(session, ProjectFile, ProjectFile.project_id == project_id)
        if value is None:
            return None, "no project files"
        args["file_id"] = value
    elif name == "view_image":
        if project_id is not None and owner_id is not None:
            value = _bounded_id(session, ProjectFile, ProjectFile.project_id == project_id, ProjectFile.content_type.like("image/%"))
            if value is not None:
                args.update(source="project", id=value)
            else:
                value = _bounded_id(session, AssistantAttachment, AssistantAttachment.thread_id == thread_id, AssistantAttachment.kind == "image", AssistantAttachment.deleted_at.is_(None)) if thread_id else None
                if value is None:
                    return None, "no project image or thread image"
                args.update(source="thread", id=value)
        else:
            value = _bounded_id(session, AssistantAttachment, AssistantAttachment.thread_id == thread_id, AssistantAttachment.kind == "image", AssistantAttachment.deleted_at.is_(None)) if thread_id else None
            if value is None:
                return None, "no image rows"
            args.update(source="thread", id=value)
    elif name in {"memory.read", "memory.search"}:
        if thread_id is None:
            return None, "no assistant thread rows"
    return args, None


def probe(role: str, proyecto: str, project_id: int | None, owner_id_override: int | None = None, thread_id_override: int | None = None, reveal_errors: bool = False) -> dict[str, Any]:
    settings = get_settings()
    # Ensure DATABASE_URL is the app's configured connection, not a probe-specific DSN.
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")
    report: list[dict[str, Any]] = []
    session = SessionLocal()
    try:
        user_id = owner_id_override or session.scalar(select(User.id).where(User.active.is_(True)).order_by(User.id).limit(1))
        owner_id = user_id
        if project_id is None and owner_id is not None and proyecto != "default":
            project_id = session.scalar(select(Project.id).where(Project.slug == proyecto, Project.owner_id == owner_id).order_by(Project.id).limit(1))
        if thread_id_override is not None:
            thread_id = thread_id_override
        elif owner_id is not None:
            thread_id = session.scalar(select(InternalChatThread.id).where(InternalChatThread.user_id == owner_id, InternalChatThread.proyecto == proyecto).order_by(InternalChatThread.id).limit(1))
            if thread_id is None:
                thread_id = session.scalar(select(InternalChatThread.id).where(InternalChatThread.user_id == owner_id).order_by(InternalChatThread.id).limit(1))
        else:
            thread_id = None
        # The catalog is the role's, not the single tool under test: passing {name} would make
        # assistant.capabilities describe a one-tool world and hide the very mismatch this probe
        # exists to catch. Project opt-in policy is a separate question from whether a tool works.
        catalog = {name for name in TOOL_REGISTRY if is_tool_allowed_for_role(name, role)}
        for name, definition in TOOL_REGISTRY.items():
            started = time.perf_counter()
            if name in SKIP_REASONS:
                report.append(_row(name, definition.tier, "skipped", started, SKIP_REASONS[name]))
                continue
            fixture = ARGUMENT_FIXTURES[name]
            definition.args_model.model_validate(fixture)
            if not definition.read_only:
                report.append(_row(name, definition.tier, "requires-approval", started, "write not executed"))
                continue
            if name == "web.search" and not settings.brave_search_api_key:
                report.append(_row(name, definition.tier, "skipped", started, "missing BRAVE_SEARCH_API_KEY"))
                continue
            if name == "project.find" and owner_id is None:
                report.append(_row(name, definition.tier, "skipped", started, "no active owner row for role"))
                continue
            args, reason = _tool_args(session, name, project_id, owner_id, thread_id)
            if reason:
                report.append(_row(name, definition.tier, "skipped", started, reason))
                continue
            try:
                result = execute_tool(
                    session, name, args, role=role, whitelist=catalog, proyecto=proyecto,
                    project_id=project_id, owner_id=owner_id,
                    trusted_thread_id=thread_id,
                )
                if result.get("status") == "error":
                    detail = str(result.get("error") or "")[:160] if reveal_errors else "details withheld"
                    report.append(_row(name, definition.tier, "error", started, f"tool returned an error; {detail}"))
                else:
                    summary = _summary(result.get("result"))
                    if name in {"project.list", "list_project_files"}:
                        summary += f" ({UNBOUNDED_READ_NOTE})"
                    report.append(_row(name, definition.tier, "ok", started, summary))
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"[:160] if reveal_errors else f"{type(exc).__name__}; details withheld"
                report.append(_row(name, definition.tier, "error", started, detail))
        session.rollback()
    finally:
        session.close()
    return {"tools": report, "exit_code": int(any(row["status"] == "error" for row in report))}


def _row(name: str, tier: str, status: str, started: float, summary: str) -> dict[str, Any]:
    return {"tool": name, "tier": tier, "status": status, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "summary": summary[:200]}


def _render(report: dict[str, Any]) -> str:
    headings = ("TOOL", "TIER", "STATUS", "MS", "SUMMARY")
    rows = [[str(row[key]) for key in ("tool", "tier", "status", "elapsed_ms", "summary")] for row in report["tools"]]
    widths = [max(len(headings[i]), *(len(row[i]) for row in rows)) for i in range(len(headings))]
    line = " | ".join(headings[i].ljust(widths[i]) for i in range(len(headings)))
    sep = "-+-".join("-" * width for width in widths)
    return "\n".join([line, sep, *(" | ".join(row[i].ljust(widths[i]) for i in range(len(headings))) for row in rows)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe read-only assistant tools without exposing customer data.")
    parser.add_argument("--role", default="admin")
    parser.add_argument("--proyecto", default="default")
    parser.add_argument("--project-id", type=int)
    parser.add_argument("--owner-id", type=int, help="owner whose data the probe reads; defaults to the first active user")
    parser.add_argument("--thread-id", type=int, help="assistant thread for thread-scoped tools such as memory.read")
    parser.add_argument("--reveal-errors", action="store_true", help="include exception messages (never row values) for diagnosis")
    parser.add_argument("--json", action="store_true", help="print a JSON report after the human table")
    args = parser.parse_args(argv)
    report = probe(args.role, args.proyecto, args.project_id, args.owner_id, args.thread_id, args.reveal_errors)
    print(_render(report))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
