"""Lazy loading for assistant skill documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.services.prompts import AssistantRuntimeConfig, _AGENT_DIR


class SkillError(Exception):
    """Raised when a declared skill body cannot be loaded."""


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    description: str
    scope: Literal["global", "project"]
    path: str | None = None
    body: str | None = None


def global_skill_index(config: AssistantRuntimeConfig) -> tuple[SkillDefinition, ...]:
    return tuple(
        SkillDefinition(name=skill.name, description=skill.description, scope="global", path=skill.path)
        for skill in config.skills
    )


def load_skill_body(defn: SkillDefinition) -> str:
    if defn.body is not None:
        return defn.body
    if defn.path is None:
        raise SkillError(f"Global skill {defn.name!r} has no declared body path")
    path = _AGENT_DIR / defn.path
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SkillError(f"Unable to load body for skill {defn.name!r} at {path}: {exc}") from exc
