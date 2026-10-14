"""Planning (Cortex) session lifecycle shared by the HTTP routes and the agent tools."""

from __future__ import annotations

from datetime import datetime, timezone


class PlanningSessionError(ValueError):
    """A planning-session operation was rejected; `status_code` maps it to HTTP."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def normalized_topic(topic: str) -> str:
    """Trim a planning topic, rejecting a blank one before any thread is created."""
    value = (topic or "").strip()
    if not value:
        raise PlanningSessionError("topic must not be blank", 400)
    return value


def build_slug(topic: str, thread_id: int) -> str:
    return f"{topic.lower().replace(' ', '-')}-{thread_id}"


def open_session(session, thread, topic: str) -> dict:
    """Activate a planning session on `thread`; reject an already-active one."""
    topic = normalized_topic(topic)
    cortex = (thread.assistant_state or {}).get("cortex_session") or {}
    if cortex.get("status") == "active":
        raise PlanningSessionError("planning session is already active", 409)
    thread.assistant_state = {
        **(thread.assistant_state or {}),
        "cortex_session": {
            "slug": build_slug(topic, thread.id),
            "topic": topic,
            "status": "active",
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "closed_at": None,
            "report_key": None,
        },
    }
    session.flush()
    return dict(thread.assistant_state["cortex_session"])


def open_in_new_thread(session, *, owner_id: int, proyecto: str, topic: str):
    """Create a dedicated thread and open the planning session on it."""
    topic = normalized_topic(topic)
    from app.models import User

    user = session.get(User, owner_id)
    if user is None:
        raise PlanningSessionError("owner not found", 404)
    from app.services.agent_chat import create_thread

    try:
        thread = create_thread(session, user, proyecto=proyecto or "default")
    except ValueError as exc:
        raise PlanningSessionError(str(exc), 400) from exc
    state = open_session(session, thread, topic)
    return thread, state


def build_report(cortex: dict) -> str:
    """Assemble the substantive markdown report from the captured session items (S8)."""
    notes = cortex.get("notes") or []
    by_kind: dict[str, list[str]] = {kind: [] for kind in NOTE_KINDS}
    for note in notes:
        content = (note.get("content") or "").strip()
        if content:
            by_kind.setdefault(note.get("kind"), []).append(content)

    def bullets(lines: list[str]) -> str:
        return "\n".join(f"- {line}" for line in lines) if lines else NOT_CAPTURED

    decisions = [
        f"**{decision.get('title', '')}** — {decision.get('content', '')}"
        for decision in (cortex.get("decisions") or [])
        if decision.get("title") or decision.get("content")
    ]
    sections = [
        f"# Planning session report: {cortex.get('topic', '')}".rstrip(),
        "",
        "## Objective",
        bullets(by_kind.get("objective", [])),
        "",
        "## Decisions",
        bullets(decisions),
        "",
        "## Risks",
        bullets(by_kind.get("risk", [])),
        "",
        "## Next steps",
        bullets(by_kind.get("next_step", [])),
        "",
        "## Notes",
        bullets(by_kind.get("general", [])),
    ]
    return "\n".join(sections).strip() + "\n"


NOTE_KINDS = frozenset({"objective", "risk", "next_step", "general"})
NOT_CAPTURED = "_Not captured._"


def _active_cortex(thread) -> dict:
    cortex = dict((thread.assistant_state or {}).get("cortex_session") or {})
    if cortex.get("status") != "active":
        raise PlanningSessionError("planning session is not active", 409)
    return cortex


def _require_text(value: str, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise PlanningSessionError(f"{field} must not be blank", 400)
    return text


def _append_capture(session, thread, field: str, entry: dict) -> list:
    cortex = _active_cortex(thread)
    entries = [*cortex.get(field, []), entry]
    cortex[field] = entries
    thread.assistant_state = {**(thread.assistant_state or {}), "cortex_session": cortex}
    session.flush()
    return entries


def record_decision(session, thread, *, title: str, content: str) -> dict:
    """Append a structured decision to the active session; reject a blank one."""
    entry = {"title": _require_text(title, "title"), "content": _require_text(content, "content")}
    return {"decision": entry, "decisions": _append_capture(session, thread, "decisions", entry)}


def record_note(session, thread, *, kind: str, content: str) -> dict:
    """Append a structured note to the active session; reject a bad kind or blank content."""
    if kind not in NOTE_KINDS:
        raise PlanningSessionError(f"kind must be one of {sorted(NOTE_KINDS)}", 400)
    entry = {"kind": kind, "content": _require_text(content, "content")}
    return {"note": entry, "notes": _append_capture(session, thread, "notes", entry)}


def close_session(session, thread) -> dict:
    """Close the active planning session and persist its report."""
    _active_cortex(thread)
    cortex = dict((thread.assistant_state or {}).get("cortex_session") or {})
    from app.services.agent_chat import close_cortex_session

    return close_cortex_session(session, thread, report=build_report(cortex))
