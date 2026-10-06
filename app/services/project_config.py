"""Project-scoped assistant configuration (Slice 1)."""

from dataclasses import dataclass

from pydantic import BaseModel, field_validator
from sqlalchemy import select

from app.chat.assistant.tools.registry import TOOL_REGISTRY, is_tool_allowed_for_role
from app.models import Project, UserRole
from app.services.prompts import load_assistant_config


class ToolPolicy(BaseModel):
    opt_in_enabled: list[str] = []

    @field_validator("opt_in_enabled")
    @classmethod
    def validate_tool_names(cls, names: list[str]) -> list[str]:
        unknown = sorted(set(names) - TOOL_REGISTRY.keys())
        if unknown:
            raise ValueError(f"Unknown tool name(s): {', '.join(unknown)}")
        return names


class ProjectConfig(BaseModel):
    instructions: str = ""
    tool_policy: ToolPolicy = ToolPolicy()


@dataclass(frozen=True)
class EffectiveConfig:
    instructions: str
    tools_whitelist: tuple[str, ...]


def resolve_effective_config(session, thread, role: UserRole | str) -> EffectiveConfig:
    """Resolve project and thread policy against the global catalog and role."""
    from app.services.projects import normalize_slug

    project_cfg = ProjectConfig()
    proyecto = thread.proyecto
    if proyecto and normalize_slug(proyecto) != "default":
        slug = normalize_slug(proyecto)
        owner_filter = Project.owner_id.is_(None) if thread.user_id is None else Project.owner_id == thread.user_id
        project = session.scalar(select(Project).where(Project.slug == slug, owner_filter))
        if project is not None:
            project_cfg = ProjectConfig.model_validate(project.config or {})

    enabled_opt_in = project_cfg.tool_policy.opt_in_enabled
    assistant_state = thread.assistant_state or {}
    if "tool_policy" in assistant_state:
        enabled_opt_in = ToolPolicy.model_validate(assistant_state["tool_policy"]).opt_in_enabled

    role_value = role.value if isinstance(role, UserRole) else role
    global_whitelist = load_assistant_config().tools_whitelist
    enabled = set(enabled_opt_in)
    tools = tuple(
        name
        for name in global_whitelist
        if is_tool_allowed_for_role(name, role_value)
        and (TOOL_REGISTRY[name].tier == "default" or name in enabled)
    )
    return EffectiveConfig(instructions=project_cfg.instructions, tools_whitelist=tools)
