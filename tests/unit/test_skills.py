from __future__ import annotations

import shutil

import pytest
import yaml

from app.agent_registry import RegistryError
from app.services.prompts import load_assistant_config


def _registry_with_skills(repo_root, tmp_path, skills):
    agent_dir = tmp_path / "agent"
    shutil.copytree(repo_root / "agent", agent_dir)
    registry_path = agent_dir / "registry.yaml"
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    raw["assistant"]["skills"] = skills
    registry_path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return registry_path


def test_global_skill_index_preserves_order_without_reading_bodies(repo_root, tmp_path, monkeypatch):
    from app.services import skills as skills_module

    declarations = [
        {"name": "second", "description": "Second description", "path": "skills/assistant/second.md"},
        {"name": "first", "description": "First description", "path": "skills/assistant/first.md"},
    ]
    registry_path = _registry_with_skills(repo_root, tmp_path, declarations)
    config = load_assistant_config(registry_path)
    monkeypatch.setattr(skills_module.Path, "read_text", lambda *args, **kwargs: pytest.fail("body read during indexing"))

    index = skills_module.global_skill_index(config)

    assert [(item.name, item.description, item.scope, item.path, item.body) for item in index] == [
        ("second", "Second description", "global", "skills/assistant/second.md", None),
        ("first", "First description", "global", "skills/assistant/first.md", None),
    ]


def test_load_skill_body_reads_global_file_on_demand(repo_root, tmp_path, monkeypatch):
    from app.services import skills as skills_module

    registry_path = _registry_with_skills(
        repo_root, tmp_path,
        [{"name": "guide", "description": "Guide", "path": "skills/assistant/guide.md"}],
    )
    body_path = tmp_path / "agent" / "skills" / "assistant" / "guide.md"
    body_path.parent.mkdir(parents=True, exist_ok=True)
    body_path.write_text("Skill body\n", encoding="utf-8")
    monkeypatch.setattr(skills_module, "_AGENT_DIR", tmp_path / "agent")
    definition = skills_module.global_skill_index(load_assistant_config(registry_path))[0]

    assert skills_module.load_skill_body(definition) == "Skill body\n"


def test_missing_global_skill_body_fails_closed(repo_root, tmp_path, monkeypatch):
    from app.services import skills as skills_module

    registry_path = _registry_with_skills(
        repo_root, tmp_path,
        [{"name": "guide", "description": "Guide", "path": "skills/assistant/missing.md"}],
    )
    monkeypatch.setattr(skills_module, "_AGENT_DIR", tmp_path / "agent")
    definition = skills_module.global_skill_index(load_assistant_config(registry_path))[0]

    with pytest.raises(skills_module.SkillError, match="missing.md"):
        skills_module.load_skill_body(definition)


def test_whatsapp_roster_stubs_are_not_in_assistant_index(repo_root):
    from app.services.skills import global_skill_index

    names = {item.name for item in global_skill_index(load_assistant_config(repo_root / "agent" / "registry.yaml"))}

    assert not names.intersection({"sdb", "emergency", "handoff", "capture"})


def test_real_registry_indexes_and_lazily_loads_memoria_tukulpan(repo_root):
    from app.services.skills import global_skill_index, load_skill_body

    index = global_skill_index(load_assistant_config(repo_root / "agent" / "registry.yaml"))
    skill = next(item for item in index if item.name == "memoria-tukulpan")

    assert skill.description == "Tukulpan memory: own vs customer axis, when to read/write, and correct memory.* argument shapes."
    assert skill.path == "skills/assistant/memoria-tukulpan.md"
    assert skill.scope == "global"
    assert load_skill_body(skill) == (repo_root / "agent" / skill.path).read_text(encoding="utf-8")
    assert not {item.name for item in index}.intersection({"sdb", "emergency", "handoff", "capture"})


def test_malformed_assistant_skill_entry_is_rejected(repo_root, tmp_path):
    registry_path = _registry_with_skills(
        repo_root, tmp_path,
        [{"name": "guide", "path": "skills/assistant/guide.md"}],
    )

    with pytest.raises(RegistryError, match="description"):
        load_assistant_config(registry_path)
