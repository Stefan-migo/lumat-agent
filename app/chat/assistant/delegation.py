"""Resolve the bounded read-only scope available to panel delegation."""

from dataclasses import dataclass
from pathlib import Path

from app.agent_registry import Registry, get_registry
from app.chat.assistant.tools.registry import TOOL_REGISTRY


class DelegationScopeError(ValueError):
    """A declared sub-agent cannot be safely delegated to."""


@dataclass(frozen=True)
class DelegationScope:
    key: str
    persona: str
    tools_whitelist: tuple[str, ...]


def resolve_delegation_scope(
    key: str,
    *,
    registry: Registry | None = None,
) -> DelegationScope:
    """Resolve a declared sub-agent, rejecting any scope that is not read-only."""
    registry = registry or get_registry()
    subagent = registry.sub_agents.get(key)
    if subagent is None:
        raise DelegationScopeError(f"unknown sub-agent: {key}")
    if not subagent.tools_whitelist:
        raise DelegationScopeError(f"sub-agent {key!r} has an empty delegation scope")

    for name in subagent.tools_whitelist:
        tool = TOOL_REGISTRY.get(name)
        if tool is None:
            raise DelegationScopeError(f"sub-agent {key!r} declares unknown tool: {name}")
        if not tool.read_only:
            raise DelegationScopeError(f"sub-agent {key!r} scope is not read-only: {name}")

    persona_path = Path(__file__).resolve().parents[3] / "agent" / subagent.persona
    try:
        persona = persona_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DelegationScopeError(f"sub-agent {key!r} persona is unavailable") from exc
    return DelegationScope(key, persona, subagent.tools_whitelist)
