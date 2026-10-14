"""Planning (Cortex) session lifecycle shared by the HTTP routes and the agent tools."""

from __future__ import annotations

import json
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


def build_report(cortex: dict) -> str:
    """Assemble the final report content for one session."""
    return json.dumps({"topic": cortex.get("topic", "")}, ensure_ascii=False)


def close_session(session, thread) -> dict:
    """Close the active planning session and persist its report."""
    cortex = dict((thread.assistant_state or {}).get("cortex_session") or {})
    if cortex.get("status") != "active":
        raise PlanningSessionError("planning session is not active", 409)
    from app.services.agent_chat import close_cortex_session

    return close_cortex_session(session, thread, report=build_report(cortex))
