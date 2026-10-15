"""Role-selected assistant agents (S9): the tecnico role talks to TecnicoLumat.

The registry keeps the single `assistant:` block as the default and adds a
`role_agents:` map (Opción B): a role with a binding resolves to its own agent
(persona/prompts/skills/tools/memoria_scope); every other role resolves to the
default assistant, exactly as before.
"""

from __future__ import annotations


def test_registry_binds_the_tecnico_role_to_tecnico_lumat(repo_root):
    from app.agent_registry import load_registry

    registry = load_registry(repo_root / "agent" / "registry.yaml")

    assert set(registry.role_agents) == {"tecnico"}
    tecnico = registry.role_agents["tecnico"]
    assert tecnico.name == "TecnicoLumat"
    assert tecnico.persona == "personas/tecnico_lumat.md"
    assert tuple(skill.name for skill in tecnico.skills) == ("kb", "tools")


def test_load_assistant_config_selects_the_agent_by_role(repo_root):
    from app.services.prompts import load_assistant_config

    tecnico = load_assistant_config(role="tecnico")
    assert tecnico.name == "TecnicoLumat"
    assert "TecnicoLumat" in tecnico.persona

    # Every other role (and an unknown one) keeps the default assistant.
    for role in ("admin", "operador", "ghost"):
        config = load_assistant_config(role=role)
        assert config.name == "assistant"
        assert "Lumat internal executive operator" in config.persona


def test_tecnico_lumat_narrows_the_technician_tool_set(repo_root):
    from app.services.prompts import load_assistant_config

    tools = set(load_assistant_config(role="tecnico").tools_whitelist)

    # The KB is the point of the agent; project-namespace administration is not.
    assert "kb.retrieve" in tools
    assert "appointments.upcoming" in tools
    assert tools.isdisjoint({"project.create", "project.rename", "project.archive", "project.merge"})
    assert tools.isdisjoint({"skill.propose", "planning.open"})


def test_kb_retrieve_is_allowed_for_the_tecnico_role():
    from app.chat.assistant.tools.registry import is_tool_allowed_for_role

    assert is_tool_allowed_for_role("kb.retrieve", "tecnico") is True


def test_kb_retrieve_audience_follows_the_actor_role(monkeypatch):
    from app.chat.assistant.tools import registry as tools
    from app.models import KbVisibility

    captured = {}

    def fake_retrieve(session, query, *, top_k, audience, project_id, global_only):
        captured["audience"] = audience
        return []

    monkeypatch.setattr(tools.kb, "retrieve", fake_retrieve)

    tools._retrieve_kb(None, tools.KbArgs(query="politicas de garantia"), project_id=None, role="tecnico")
    assert captured["audience"] is KbVisibility.CUSTOMER

    tools._retrieve_kb(None, tools.KbArgs(query="politicas de garantia"), project_id=None, role="admin")
    assert captured["audience"] is None
