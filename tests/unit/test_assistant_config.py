"""Read-only assistant runtime configuration contracts."""

import pytest

from app.services.prompts import load_assistant_config
from app.agent_registry import RegistryError


def test_complete_assistant_configuration_loads_without_skills(repo_root):
    config = load_assistant_config(repo_root / "agent" / "registry.yaml")

    assert config.name == "assistant"
    assert "Lumat internal executive operator" in config.persona
    assert set(config.prompts) == {"plan", "respond", "classify"}
    assert "<available_tools>" in config.prompts["plan"]
    assert config.skills == ()
    assert "skills" not in config.prompts["plan"]
    assert config.memoria_scope == "panel"


def test_missing_assistant_reference_fails_before_runtime_use(tmp_path, repo_root):
    registry = (repo_root / "agent" / "registry.yaml").read_text(encoding="utf-8")
    registry = registry.replace("personas/assistant.md", "personas/missing.md")
    path = tmp_path / "registry.yaml"
    path.write_text(registry, encoding="utf-8")
    for relative in (
        "personas/orchestrator.md",
        "personas/research_triage.md",
        "personas/retrieval.md",
        "personas/customer_records.md",
        "personas/human_handoff.md",
        "personas/escalation.md",
        "prompts/assistant_plan.md",
        "prompts/assistant_respond.md",
        "prompts/assistant_classify.md",
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text((repo_root / "agent" / relative).read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(RegistryError, match="assistant.persona does not exist"):
        load_assistant_config(path)
