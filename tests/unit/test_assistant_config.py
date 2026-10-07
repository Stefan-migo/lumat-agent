"""Read-only assistant runtime configuration contracts."""

import pytest

from app.services.prompts import load_assistant_config
from app.agent_registry import RegistryError
from app.chat.assistant.tools.registry import AUTONOMOUS_WRITE_ALLOWLIST


def test_complete_assistant_configuration_loads_declared_skill_index(repo_root):
    config = load_assistant_config(repo_root / "agent" / "registry.yaml")

    assert config.name == "assistant"
    assert "Lumat internal executive operator" in config.persona
    assert set(config.prompts) == {"plan", "respond", "classify"}
    assert "<available_tools>" in config.prompts["plan"]
    assert "<available_skills>{{available_skills}}</available_skills>" in config.prompts["plan"]
    assert [(skill.name, skill.description, skill.path) for skill in config.skills] == [
        (
            "memoria-tukulpan",
            "Tukulpan memory: own vs customer axis, when to read/write, and correct memory.* argument shapes.",
            "skills/assistant/memoria-tukulpan.md",
        )
    ]
    assert "SECRET SKILL BODY" not in config.prompts["plan"]
    assert config.memoria_scope == "panel"


def test_assistant_persona_authorizes_the_autonomous_write(repo_root):
    config = load_assistant_config(repo_root / "agent" / "registry.yaml")

    for tool_name in AUTONOMOUS_WRITE_ALLOWLIST:
        assert tool_name in config.persona
    assert "except" in config.persona
    assert "already authorized and runs without asking" in config.persona


def test_assistant_persona_keeps_approval_for_every_other_write(repo_root):
    config = load_assistant_config(repo_root / "agent" / "registry.yaml")

    assert "ask for approval before any write operation" in config.persona
    assert "Every other write still needs approval" in config.persona


def test_assistant_extends_the_web_allowance_to_fetched_page_text(repo_root):
    """The reader's evidence is citable, but only as narrowly as the search allowance.

    Both artifacts must carry the tool and the citation duty: the persona is the standing rule and
    the responder prompt is the per-turn reminder, so one carrying the allowance without the other
    is a silent gap between what the runtime declares and what the model is told.
    """
    config = load_assistant_config(repo_root / "agent" / "registry.yaml")

    assert "web.fetch" in config.persona
    assert "the URL that evidence reports after redirects" in config.persona
    assert "web.fetch" in config.prompts["respond"]
    assert "the URL that evidence reports after redirects" in config.prompts["respond"]


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
