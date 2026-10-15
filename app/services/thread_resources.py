"""Per-thread pinned project resources (project files, planning sessions, skills).

A thread may pin project-level resources to its own context. The selection is
stored in ``thread.assistant_state["resources"]`` and only references resources
that already belong to the thread's project (files/skills) or to the thread owner
(planning sessions); the content itself is read on demand with tools, never
injected in full every turn.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.chat.assistant.state import merge_assistant_state
from app.models import InternalChatThread, Project
from app.services import project_files
from app.services.projects import normalize_slug


class ThreadResources(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_files: list[int] = []
    planning_sessions: list[str] = []
    skills: list[str] = []


def _thread_project(session, thread) -> Project | None:
    proyecto = thread.proyecto
    if not proyecto or normalize_slug(proyecto) == "default":
        return None
    owner_filter = Project.owner_id.is_(None) if thread.user_id is None else Project.owner_id == thread.user_id
    return session.scalar(select(Project).where(Project.slug == normalize_slug(proyecto), owner_filter))


def _available_planning_sessions(session, thread) -> list[dict]:
    rows = session.scalars(
        select(InternalChatThread).where(InternalChatThread.user_id == thread.user_id)
    ).all()
    sessions = []
    for row in rows:
        cortex = (row.assistant_state or {}).get("cortex_session") or {}
        if not cortex.get("slug") or row.proyecto != thread.proyecto:
            continue
        sessions.append({"slug": cortex["slug"], "topic": cortex.get("topic"), "status": cortex.get("status")})
    return sessions


def _available_skills(session, thread) -> list[dict]:
    from app.services.project_config import ProjectConfig

    project = _thread_project(session, thread)
    if project is None:
        return []
    config = ProjectConfig.model_validate(project.config or {})
    return [{"name": skill.name, "description": skill.description} for skill in config.skills]


def available_resources(session, thread) -> dict:
    """The resources this thread may pin, scoped to its project and owner."""
    project = _thread_project(session, thread)
    files = [] if project is None else [
        {"id": row.id, "filename": row.filename, "content_type": row.content_type, "size": row.size}
        for row in project_files.list_project_files(session, project.id)
    ]
    return {
        "project_files": files,
        "planning_sessions": _available_planning_sessions(session, thread),
        "skills": _available_skills(session, thread),
    }


def read_thread_resources(session, thread) -> dict:
    stored = (thread.assistant_state or {}).get("resources")
    resources = ThreadResources.model_validate(stored) if stored else ThreadResources()
    return {
        "resources": resources.model_dump(),
        "available": available_resources(session, thread),
        "inherited": stored is None,
    }


def _pinned_selection(session, thread) -> dict:
    stored = (thread.assistant_state or {}).get("resources")
    if not stored:
        return {"project_files": [], "planning_sessions": [], "skills": []}
    resources = ThreadResources.model_validate(stored)
    available = available_resources(session, thread)
    files = {row["id"]: row for row in available["project_files"]}
    sessions = {row["slug"]: row for row in available["planning_sessions"]}
    skills = {row["name"]: row for row in available["skills"]}
    return {
        "project_files": [
            {"id": value, "filename": files[value]["filename"]}
            for value in resources.project_files
            if value in files
        ],
        "planning_sessions": [
            {"slug": value, "topic": sessions[value].get("topic")}
            for value in resources.planning_sessions
            if value in sessions
        ],
        "skills": [
            {"name": value, "description": skills[value].get("description")}
            for value in resources.skills
            if value in skills
        ],
    }


def pinned_context(session, thread) -> tuple[str, list[str]]:
    """The compact ``<pinned_resources>`` reference and the pinned skill names.

    The reference carries only names/ids/slugs for the planner; the content stays
    read-on-demand (read_project_file / planning.read_report / declared skills).
    Returns ``("", [])`` when nothing is pinned.
    """
    selection = _pinned_selection(session, thread)
    lines: list[str] = []
    for row in selection["project_files"]:
        lines.append(f'- project file #{row["id"]} "{row["filename"]}" — read it with read_project_file')
    for row in selection["planning_sessions"]:
        topic = f' ({row["topic"]})' if row["topic"] else ""
        lines.append(f'- planning session "{row["slug"]}"{topic} — read it with planning.read_report')
    for row in selection["skills"]:
        lines.append(f'- skill "{row["name"]}" — active for this turn')
    reference = "<pinned_resources>\n" + "\n".join(lines) + "\n</pinned_resources>" if lines else ""
    return reference, [row["name"] for row in selection["skills"]]


def set_thread_resources(session, thread, resources: ThreadResources) -> None:
    available = available_resources(session, thread)
    file_ids = {row["id"] for row in available["project_files"]}
    slugs = {row["slug"] for row in available["planning_sessions"]}
    names = {row["name"] for row in available["skills"]}
    unknown = [
        *(f"project_file:{value}" for value in resources.project_files if value not in file_ids),
        *(f"planning_session:{value}" for value in resources.planning_sessions if value not in slugs),
        *(f"skill:{value}" for value in resources.skills if value not in names),
    ]
    if unknown:
        raise ValueError(f"Unknown resource(s): {', '.join(sorted(unknown))}")
    deduped = ThreadResources(
        project_files=list(dict.fromkeys(resources.project_files)),
        planning_sessions=list(dict.fromkeys(resources.planning_sessions)),
        skills=list(dict.fromkeys(resources.skills)),
    )
    thread.assistant_state = merge_assistant_state(
        thread.assistant_state or {}, {"resources": deduped.model_dump()}
    )


def reset_thread_resources(thread) -> None:
    state = dict(thread.assistant_state or {})
    state.pop("resources", None)
    thread.assistant_state = state
