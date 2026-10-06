"""Project-scoped assistant configuration (Slice 1)."""

from pydantic import BaseModel, field_validator

from app.chat.assistant.tools.registry import TOOL_REGISTRY


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
