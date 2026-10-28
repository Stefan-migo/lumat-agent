"""Per-thread pinned project resources (project files and skills).

A thread may pin project-level resources to its own context. The selection is
stored in ``thread.assistant_state["resources"]`` and only references resources
that already belong to the thread's project; content is read on demand, never
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
    skills: list[str] = []


def _thread_project(session, thread) -> Project | None:
    proyecto = thread.proyecto
    if not proyecto or normalize_slug(proyecto) == "default":
        return None
    owner_filter = Project.owner_id.is_(None) if thread.user_id is None else Project.owner_id == thread.user_id
    return session.scalar(select(Project).where(Project.slug == normalize_slug(proyecto), owner_filter))


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
        "skills": _available_skills(session, thread),
    }


def _stored_thread_resources(thread) -> dict | None:
    stored = (thread.assistant_state or {}).get("resources")
    if not stored:
        return None
    # Legacy pinned planning-session slugs remain stored but are no longer exposed
    # or resolved; ignore that obsolete field without rewriting persisted state.
    return {key: value for key, value in stored.items() if key != "planning_sessions"}


def read_thread_resources(session, thread) -> dict:
    stored = _stored_thread_resources(thread)
    resources = ThreadResources.model_validate(stored) if stored else ThreadResources()
    return {
        "resources": resources.model_dump(),
        "available": available_resources(session, thread),
        "inherited": stored is None,
    }


def _pinned_selection(session, thread) -> dict:
    stored = _stored_thread_resources(thread)
    if not stored:
        return {"project_files": [], "skills": []}
    resources = ThreadResources.model_validate(stored)
    available = available_resources(session, thread)
    files = {row["id"]: row for row in available["project_files"]}
    skills = {row["name"]: row for row in available["skills"]}
    return {
        "project_files": [
            {"id": value, "filename": files[value]["filename"]}
            for value in resources.project_files
            if value in files
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
    read-on-demand (read_project_file / declared skills).
    Returns ``("", [])`` when nothing is pinned.
    """
    selection = _pinned_selection(session, thread)
    lines: list[str] = []
    for row in selection["project_files"]:
        lines.append(f'- project file #{row["id"]} "{row["filename"]}" — read it with read_project_file')
    for row in selection["skills"]:
        lines.append(f'- skill "{row["name"]}" — active for this turn')
    reference = "<pinned_resources>\n" + "\n".join(lines) + "\n</pinned_resources>" if lines else ""
    return reference, [row["name"] for row in selection["skills"]]


def set_thread_resources(session, thread, resources: ThreadResources) -> None:
    available = available_resources(session, thread)
    file_ids = {row["id"] for row in available["project_files"]}
    names = {row["name"] for row in available["skills"]}
    unknown = [
        *(f"project_file:{value}" for value in resources.project_files if value not in file_ids),
        *(f"skill:{value}" for value in resources.skills if value not in names),
    ]
    if unknown:
        raise ValueError(f"Unknown resource(s): {', '.join(sorted(unknown))}")
    deduped = ThreadResources(
        project_files=list(dict.fromkeys(resources.project_files)),
        skills=list(dict.fromkeys(resources.skills)),
    )
    thread.assistant_state = merge_assistant_state(
        thread.assistant_state or {}, {"resources": deduped.model_dump()}
    )


def reset_thread_resources(thread) -> None:
    state = dict(thread.assistant_state or {})
    state.pop("resources", None)
    thread.assistant_state = state
