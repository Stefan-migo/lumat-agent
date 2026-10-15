"""Read-only startup registry reader for the multi-agent roster (H2 router).

AO-2 / D2: the registry is data-only; this module loads `agent/registry.yaml`
at boot and validates it, but does NOT enforce tools or memory scope
beyond data declaration. It is deliberately NOT wired into
`app/services/prompts.py` or `app/chat/nodes/respond.py` (AC-4 / D2) so the
no-runtime-consumer invariant stays intact.

Fail-fast contract (design D5 / AO-2):
- exactly one top-level `agent:` key with ``name == "orchestrator"`` (AC-4)
- a `sub_agents:` sibling mapping agent keys -> sub-agent declarations
- every sub-agent carries all six required fields
- every `tools_whitelist` entry is within the slice-1 known-tools set, which
  grows in later slices (currently ``["kb.retrieve"]``)
- `temperature` is numeric

Any violation raises ``RegistryError`` at load time so no graph builds on a
bad registry (AO-2 "Invalid registry rejected").
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.chat.assistant.tools.registry import TOOL_REGISTRY

# The assistant tool registry is the source of truth for declared capabilities.
KNOWN_TOOLS = tuple(TOOL_REGISTRY)

# All six fields every sub-agent must declare (AO-1).
SUBAGENT_REQUIRED_FIELDS = (
    "name",
    "persona",
    "tools_whitelist",
    "memoria_scope",
    "model",
    "temperature",
)


class RegistryError(ValueError):
    """Raised when ``agent/registry.yaml`` violates the schema."""


@dataclass(frozen=True)
class SubAgent:
    name: str
    persona: str
    tools_whitelist: tuple[str, ...]
    memoria_scope: str
    model: str
    temperature: float


@dataclass(frozen=True)
class Agent:
    name: str
    persona: str
    skills: tuple[str, ...]
    tools_whitelist: tuple[str, ...]
    memoria_scope: str | None
    model: str


@dataclass(frozen=True)
class AssistantSkill:
    name: str
    description: str
    path: str


@dataclass(frozen=True)
class Assistant:
    name: str
    persona: str
    prompts: dict[str, str]
    tools_whitelist: tuple[str, ...]
    memoria_scope: str | None
    model: str
    skills: tuple[AssistantSkill, ...]


@dataclass(frozen=True)
class Registry:
    orchestrator: Agent
    sub_agents: dict[str, SubAgent]
    assistant: Assistant
    role_agents: dict[str, Assistant]


def _coerce_str_list(value, *, what: str) -> tuple[str, ...]:
    if isinstance(value, str):
        raise RegistryError(f"{what} must be a list, got a string: {value!r}")
    if not isinstance(value, list):
        raise RegistryError(f"{what} must be a list, got {type(value).__name__}")
    for item in value:
        if not isinstance(item, str) or not item:
            raise RegistryError(f"{what} contains a non-string entry: {item!r}")
    return tuple(value)


def _coerce_optional_str_list(value, *, what: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    return _coerce_str_list(value, what=what)


def _coerce_assistant_skills(value) -> tuple[AssistantSkill, ...]:
    if not isinstance(value, list):
        raise RegistryError(f"assistant.skills must be a list, got {type(value).__name__}")
    skills = []
    for index, entry in enumerate(value):
        where = f"assistant.skills[{index}]"
        if not isinstance(entry, dict):
            raise RegistryError(f"{where} must be a mapping, got {type(entry).__name__}")
        fields = {}
        for field in ("name", "description", "path"):
            field_value = entry.get(field)
            if not isinstance(field_value, str) or not field_value.strip():
                raise RegistryError(f"{where}.{field} must be a non-empty string")
            fields[field] = field_value
        skills.append(AssistantSkill(**fields))
    return tuple(skills)


def _build_agent(root: dict, where: str) -> Agent:
    missing = [f for f in ("name", "persona", "skills", "tools_whitelist", "model") if f not in root]
    if missing:
        raise RegistryError(f"{where}: missing required field(s): {', '.join(sorted(missing))}")
    return Agent(
        name=root["name"],
        persona=root["persona"],
        skills=_coerce_str_list(root["skills"], what=f"{where}.skills"),
        tools_whitelist=_coerce_str_list(root["tools_whitelist"], what=f"{where}.tools_whitelist"),
        memoria_scope=root.get("memoria_scope"),
        model=root["model"],
    )


def _runtime_path(agent_dir: Path, value, *, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise RegistryError(f"{what} must be a non-empty path")
    if not (agent_dir / value).is_file():
        raise RegistryError(f"{what} does not exist: {agent_dir / value}")
    return value


def _build_assistant(root: dict, agent_dir: Path, where: str = "assistant") -> Assistant:
    if not isinstance(root, dict):
        raise RegistryError(f"{where} must be a mapping, got {type(root).__name__}")
    required = ("name", "persona", "prompts", "tools_whitelist", "model")
    missing = [field for field in required if field not in root]
    if missing:
        raise RegistryError(f"{where}: missing required field(s): {', '.join(sorted(missing))}")
    persona = _runtime_path(agent_dir, root["persona"], what=f"{where}.persona")
    prompts = root["prompts"]
    if not isinstance(prompts, dict) or not prompts:
        raise RegistryError(f"{where}.prompts must be a non-empty mapping")
    resolved_prompts = {
        str(name): _runtime_path(agent_dir, path, what=f"{where}.prompts.{name}")
        for name, path in prompts.items()
    }
    tools = _coerce_str_list(root["tools_whitelist"], what=f"{where}.tools_whitelist")
    for tool in tools:
        if tool not in KNOWN_TOOLS:
            raise RegistryError(f"{where}: unknown tool {tool!r}")
    return Assistant(
        name=root["name"],
        persona=persona,
        prompts=resolved_prompts,
        tools_whitelist=tools,
        memoria_scope=root.get("memoria_scope"),
        model=root["model"],
        skills=_coerce_assistant_skills(root.get("skills", [])),
    )


def _build_subagent(key: str, root: dict) -> SubAgent:
    where = f"sub_agents.{key}"
    if not isinstance(root, dict):
        raise RegistryError(f"{where}: sub-agent must be a mapping, got {type(root).__name__}")
    missing = [f for f in SUBAGENT_REQUIRED_FIELDS if f not in root]
    if missing:
        raise RegistryError(f"{where}: missing required field(s): {', '.join(sorted(missing))}")

    tools = _coerce_str_list(root["tools_whitelist"], what=f"{where}.tools_whitelist")
    for tool in tools:
        if tool not in KNOWN_TOOLS:
            raise RegistryError(
                f"{where}: tools_whitelist entry {tool!r} not in known-tools set {list(KNOWN_TOOLS)}"
            )

    temperature = root["temperature"]
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise RegistryError(f"{where}.temperature must be numeric, got {temperature!r}")

    return SubAgent(
        name=root["name"],
        persona=root["persona"],
        tools_whitelist=tools,
        memoria_scope=root["memoria_scope"],
        model=root["model"],
        temperature=float(temperature),
    )


def load_registry(path: str | Path | None = None) -> Registry:
    """Load and validate ``agent/registry.yaml`` into a frozen ``Registry``.

    Fail-fast on a malformed registry (AO-2): exactly one ``agent:`` block
    declaring ``name == orchestrator``, a ``sub_agents:`` sibling, and every
    sub-agent valid per the slice-1 schema.

    Raises ``RegistryError`` on any violation.
    """
    if path is None:
        path = Path(__file__).resolve().parents[1] / "agent" / "registry.yaml"
    path = Path(path)
    if not path.is_file():
        raise RegistryError(f"registry file not found: {path}")

    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise RegistryError(f"registry must be a YAML mapping, got {type(raw).__name__}")

    root_agent = raw.get("agent")
    if not isinstance(root_agent, dict):
        raise RegistryError("registry must declare exactly one `agent:` block")
    if root_agent.get("name") != "orchestrator":
        raise RegistryError(
            f"exactly one orchestrator is required; agent.name must be 'orchestrator', got {root_agent.get('name')!r}"
        )

    sub_agents_map = raw.get("sub_agents")
    if sub_agents_map is None:
        raise RegistryError("registry must declare a `sub_agents:` sibling")
    if not isinstance(sub_agents_map, dict):
        raise RegistryError(f"`sub_agents:` must be a mapping, got {type(sub_agents_map).__name__}")
    if not sub_agents_map:
        raise RegistryError("`sub_agents:` must not be empty")

    orchestrator = _build_agent(root_agent, "agent")
    _runtime_path(path.parent, orchestrator.persona, what="agent.persona")
    sub_agents = {
        key: _build_subagent(str(key), decl)
        for key, decl in sub_agents_map.items()
    }
    for key, sub_agent in sub_agents.items():
        _runtime_path(path.parent, sub_agent.persona, what=f"sub_agents.{key}.persona")
    if "assistant" not in raw:
        raise RegistryError("registry must declare an `assistant:` configuration")
    assistant = _build_assistant(raw["assistant"], path.parent)
    role_agents = _build_role_agents(raw.get("role_agents"), path.parent)
    return Registry(
        orchestrator=orchestrator,
        sub_agents=sub_agents,
        assistant=assistant,
        role_agents=role_agents,
    )


def _build_role_agents(value, agent_dir: Path) -> dict[str, Assistant]:
    """Build the optional ``role_agents:`` map (role key -> assistant override).

    A role with a binding talks to its own agent; every other role resolves to
    the default ``assistant:`` block. Keys must be known user roles so a typo
    cannot silently give the wrong role the default assistant.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RegistryError(f"role_agents must be a mapping, got {type(value).__name__}")
    from app.models import UserRole

    valid_roles = {role.value for role in UserRole}
    agents: dict[str, Assistant] = {}
    for role, decl in value.items():
        if not isinstance(role, str) or role not in valid_roles:
            raise RegistryError(
                f"role_agents: unknown role {role!r}; expected one of {sorted(valid_roles)}"
            )
        agents[role] = _build_assistant(decl, agent_dir, where=f"role_agents.{role}")
    return agents


def select_assistant(registry: Registry, role: str | None) -> Assistant:
    """Return the agent bound to ``role`` in ``role_agents:``, else the default."""
    if role:
        bound = registry.role_agents.get(role)
        if bound is not None:
            return bound
    return registry.assistant


# Cached runtime getter (design line 43): ``load_registry`` reads + validates
# ``registry.yaml`` ONCE at graph construction (module scope, cached) and the
# dispatch path reuses that single load instead of re-reading the file every
# turn. ``get_registry`` is the cached reader the runtime (graph/sub-graph)
# calls; ``load_registry`` stays the pure, always-fresh reader used by the
# fail-fast unit tests and any path-specific validation (e.g. registry tests).
_registry_cache: Registry | None = None


def get_registry(path: str | Path | None = None) -> Registry:
    """Return the loaded registry, cached so it is read from disk at most once.

    Designed for the runtime default path (design line 43): the first call at
    graph construction loads and validates ``agent/registry.yaml``; every
    subsequent call returns the cached ``Registry`` without re-reading the
    file. Passing an explicit ``path`` is intended for tests/callers that only
    need the default read cached once; path-qualified validation should use
    ``load_registry(path)`` directly.
    """
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = load_registry(path)
    return _registry_cache
