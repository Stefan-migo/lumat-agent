from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.chat.assistant.tools.registry import TOOL_REGISTRY
from app.models import UserRole
from app.services.prompts import load_assistant_config
from app.services.project_config import resolve_effective_config
from app.services.skills import global_skill_index


DEFAULT_TOOLS = {
    "assistant.capabilities",
    "customers.search",
    "customers.list",
    "conversations.search",
    "conversations.list",
    "appointments.upcoming",
    "customers.operational_history",
    "cases.list",
    "kb.retrieve",
    "memory.read",
    "memory.search",
    "memory.write",
    "memory.update",
    "memory.delete",
    "dashboard.summary",
    "project.list",
    "project.find",
}


def resolve(*, proyecto="default", config=None, role=UserRole.ADMIN, assistant_state=None):
    session = MagicMock()
    session.scalar.return_value = SimpleNamespace(config=config) if config is not None else None
    thread = SimpleNamespace(
        proyecto=proyecto,
        user_id=1,
        assistant_state=assistant_state or {},
    )
    return resolve_effective_config(session, thread, role)


def test_global_only_enables_default_tier_for_admin():
    effective = resolve()

    assert set(effective.tools_whitelist) == DEFAULT_TOOLS
    assert effective.instructions == ""
    assert effective.skills_index == global_skill_index(load_assistant_config())


def test_project_skill_is_appended_to_effective_index():
    effective = resolve(
        proyecto="workspace",
        config={"skills": [{"name": "local", "description": "Local skill", "body": "Inline body"}]},
    )

    skill = effective.skills_index[-1]
    assert (skill.name, skill.description, skill.scope, skill.path, skill.body) == (
        "local", "Local skill", "project", None, "Inline body"
    )


def test_project_skill_overrides_global_skill_in_place():
    global_index = global_skill_index(load_assistant_config())
    global_skill = next(skill for skill in global_index if skill.name == "memoria-tukulpan")
    effective = resolve(
        proyecto="workspace",
        config={"skills": [{"name": global_skill.name, "description": "Project description", "body": "Project body"}]},
    )

    assert len([skill for skill in effective.skills_index if skill.name == global_skill.name]) == 1
    overridden = next(skill for skill in effective.skills_index if skill.name == global_skill.name)
    assert effective.skills_index.index(overridden) == global_index.index(global_skill)
    assert overridden.description == "Project description"
    assert overridden.scope == "project"
    assert overridden.path is None
    assert overridden.body == "Project body"


def test_empty_project_config_enables_default_tier_only():
    effective = resolve(proyecto="workspace", config={})

    assert set(effective.tools_whitelist) == DEFAULT_TOOLS


def test_project_can_enable_selected_opt_in_tool():
    effective = resolve(
        proyecto="workspace",
        config={"tool_policy": {"opt_in_enabled": ["web.search"]}},
    )

    assert DEFAULT_TOOLS <= set(effective.tools_whitelist)
    assert "web.search" in effective.tools_whitelist
    assert "web.fetch" not in effective.tools_whitelist


@pytest.mark.parametrize("role", [UserRole.OPERADOR])
def test_project_cannot_add_opt_in_tool_outside_role_allowlist(role):
    effective = resolve(
        proyecto="workspace",
        config={"tool_policy": {"opt_in_enabled": ["automation.create_rule"]}},
        role=role,
    )

    assert "automation.create_rule" not in effective.tools_whitelist


def test_thread_override_replaces_only_project_opt_in_policy():
    effective = resolve(
        proyecto="workspace",
        config={"tool_policy": {"opt_in_enabled": ["web.search"]}},
        assistant_state={"tool_policy": {"opt_in_enabled": ["web.fetch"]}},
    )

    assert DEFAULT_TOOLS <= set(effective.tools_whitelist)
    assert "web.fetch" in effective.tools_whitelist
    assert "web.search" not in effective.tools_whitelist


def test_role_filter_applies_to_default_tier():
    effective = resolve(proyecto="default", role=UserRole.TECNICO)

    assert "customers.search" not in effective.tools_whitelist
    assert "memory.read" in effective.tools_whitelist


def test_tool_order_follows_global_whitelist():
    effective = resolve(
        proyecto="workspace",
        config={"tool_policy": {"opt_in_enabled": ["web.search"]}},
    )
    expected = tuple(
        name
        for name in load_assistant_config().tools_whitelist
        if name in set(effective.tools_whitelist)
    )

    assert effective.tools_whitelist == expected
