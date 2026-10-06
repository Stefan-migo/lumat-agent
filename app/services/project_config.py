"""Project-scoped assistant configuration (Slice 1)."""

from dataclasses import dataclass

from pydantic import BaseModel, field_validator
from sqlalchemy import select

from app.chat.assistant.tools.registry import TOOL_REGISTRY, is_tool_allowed_for_role
from app.models import Project, UserRole
from app.services.prompts import load_assistant_config
from app.services.skills import SkillDefinition, global_skill_index


class ToolPolicy(BaseModel):
    opt_in_enabled: list[str] = []

    @field_validator("opt_in_enabled")
    @classmethod
    def validate_tool_names(cls, names: list[str]) -> list[str]:
        unknown = sorted(set(names) - TOOL_REGISTRY.keys())
        if unknown:
            raise ValueError(f"Unknown tool name(s): {', '.join(unknown)}")
        return names


class ProjectSkill(BaseModel):
    name: str
    description: str
    body: str

    @field_validator("name", "description", "body")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Project skill fields must not be empty")
        return value


class ProjectConfig(BaseModel):
    instructions: str = ""
    tool_policy: ToolPolicy = ToolPolicy()
    skills: list[ProjectSkill] = []

    @field_validator("skills")
    @classmethod
    def validate_unique_skill_names(cls, skills: list[ProjectSkill]) -> list[ProjectSkill]:
        names = [skill.name for skill in skills]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate project skill name")
        return skills


@dataclass(frozen=True)
class EffectiveConfig:
    instructions: str
    tools_whitelist: tuple[str, ...]
    skills_index: tuple[SkillDefinition, ...]


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

    global_skills = global_skill_index(load_assistant_config())
    project_skills = {
        skill.name: SkillDefinition(
            name=skill.name,
            description=skill.description,
            scope="project",
            path=None,
            body=skill.body,
        )
        for skill in project_cfg.skills
    }
    skills_index = tuple(
        project_skills.pop(skill.name, skill) for skill in global_skills
    ) + tuple(project_skills.values())

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
    return EffectiveConfig(
        instructions=project_cfg.instructions,
        tools_whitelist=tools,
        skills_index=skills_index,
    )
