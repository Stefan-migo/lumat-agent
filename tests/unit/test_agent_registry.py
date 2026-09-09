"""Registry reader + multi-agent roster coverage (h2-router-langgraph, PR 1).

AO-1 (registry declares the multi-agent roster), AO-2 (read-only startup
reader, no enforcement outside dispatch, not wired into prompts/respond), and
AC-4 (data-only registry; exactly one orchestrator; `agent:` block unchanged).

RED-first: `app.agent_registry` (load_registry / Agent / SubAgent) does not
exist until task 1.3 implements it, and `agent/registry.yaml` has no
`sub_agents:` sibling until task 1.1, so importing the module and asserting the
full roster fail before the production reader + data land.
"""

from __future__ import annotations

import pytest


# The known-tools set for slice 1 (design D5): the only tool the research
# triage sub-agent uses. The reader fails fast on any whitelist entry outside
# this set; the set grows in later slices.
KNOWN_TOOLS = ["kb.retrieve"]


def _load(repo_root):
    from app.agent_registry import load_registry

    return load_registry(repo_root / "agent" / "registry.yaml")


# --- AO-1: full multi-agent roster ------------------------------------------

def test_loads_full_roster_with_seven_fields_each(repo_root):
    # Full roster: orchestrator + five sub-agents, each sub-agent carrying all
    # seven fields (name/persona/tools_whitelist/kb_scope/memoria_scope/model/
    # temperature). The orchestrator entry resolves exactly as before (AC-4).
    reg = _load(repo_root)
    assert reg.orchestrator.name == "orchestrator"
    assert reg.orchestrator.persona == "personas/orchestrator.md"

    expected_subagents = {
        "research_triage",
        "retrieval",
        "customer_records",
        "human_handoff",
        "escalation",
    }
    assert set(reg.sub_agents) == expected_subagents

    for key, sub in reg.sub_agents.items():
        assert isinstance(sub.name, str) and sub.name
        assert isinstance(sub.persona, str) and sub.persona
        assert isinstance(sub.tools_whitelist, tuple) or isinstance(sub.tools_whitelist, list)
        assert isinstance(sub.kb_scope, (tuple, list, type(None)))
        assert isinstance(sub.memoria_scope, str)
        assert isinstance(sub.model, str) and sub.model
        assert isinstance(sub.temperature, float)

    assert reg.sub_agents["research_triage"].name == "kb-research-triage"
    assert tuple(reg.sub_agents["research_triage"].tools_whitelist) == ("kb.retrieve",)
    assert tuple(reg.sub_agents["research_triage"].kb_scope) == ("valores", "postventa")
    assert reg.sub_agents["research_triage"].memoria_scope == "customer"
    assert reg.sub_agents["research_triage"].model == "deepseek-chat"
    assert reg.sub_agents["research_triage"].temperature == 0


def test_all_whitelists_are_within_known_tools_slice(repo_root):
    # D5 / AO-6: every declared whitelist entry must be in the slice-1 known
    # set, else the reader fails fast (the set grows in later slices).
    reg = _load(repo_root)
    for sub in reg.sub_agents.values():
        for tool in sub.tools_whitelist:
            assert tool in KNOWN_TOOLS, f"unknown tool {tool} in {sub.name}"


def test_registry_data_only_no_runtime_consumer(repo_root):
    # AO-2 / AC-4: the reader is read-only data; prompts/respond never read the
    # registry. Mirrors the existing AC-4 guard for this new reader file.
    import app.agent_registry as reg_module

    assert getattr(reg_module, "load_registry", None) is not None
    for prog in ("app/services/prompts.py", "app/chat/nodes/respond.py"):
        path = repo_root / prog
        assert "registry.yaml" not in path.read_text(encoding="utf-8"), (
            f"{prog} must not read the registry"
        )


# --- AO-2: fail-fast validation ---------------------------------------------

def test_missing_required_field_rejected(repo_root, tmp_path):
    # A sub-agent missing `temperature` must fail startup (AO-2 scenario
    # "Invalid registry rejected"): no graph builds.
    import yaml

    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "agent": {
                    "name": "orchestrator",
                    "persona": "personas/orchestrator.md",
                    "skills": ["sdb"],
                    "tools_whitelist": [],
                    "kb_scope": None,
                    "memoria_scope": None,
                    "model": "deepseek-chat",
                },
                "sub_agents": {
                    "research_triage": {
                        "name": "kb-research-triage",
                        "persona": "personas/research_triage.md",
                        "tools_whitelist": ["kb.retrieve"],
                        "kb_scope": ["valores", "postventa"],
                        "memoria_scope": "customer",
                        "model": "deepseek-chat",
                        # "temperature" deliberately omitted
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    from app.agent_registry import RegistryError

    with __import__("pytest").raises(RegistryError):
        _load(registry_path)


def test_unknown_tools_whitelist_rejected(repo_root, tmp_path):
    # A whitelist entry outside the slice-1 known set fails fast (D5).
    import yaml

    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "agent": {
                    "name": "orchestrator",
                    "persona": "personas/orchestrator.md",
                    "skills": ["sdb"],
                    "tools_whitelist": [],
                    "kb_scope": None,
                    "memoria_scope": None,
                    "model": "deepseek-chat",
                },
                "sub_agents": {
                    "research_triage": {
                        "name": "kb-research-triage",
                        "persona": "personas/research_triage.md",
                        "tools_whitelist": ["kb.some_future_tool"],
                        "kb_scope": ["valores"],
                        "memoria_scope": "customer",
                        "model": "deepseek-chat",
                        "temperature": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    from app.agent_registry import RegistryError

    with __import__("pytest").raises(RegistryError):
        _load(registry_path)


def test_invalid_temperature_rejected(repo_root, tmp_path):
    # Non-numeric temperature fails fast.
    import yaml

    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "agent": {
                    "name": "orchestrator",
                    "persona": "personas/orchestrator.md",
                    "skills": ["sdb"],
                    "tools_whitelist": [],
                    "kb_scope": None,
                    "memoria_scope": None,
                    "model": "deepseek-chat",
                },
                "sub_agents": {
                    "research_triage": {
                        "name": "kb-research-triage",
                        "persona": "personas/research_triage.md",
                        "tools_whitelist": ["kb.retrieve"],
                        "kb_scope": ["valores"],
                        "memoria_scope": "customer",
                        "model": "deepseek-chat",
                        "temperature": "hot",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    from app.agent_registry import RegistryError

    with __import__("pytest").raises(RegistryError):
        _load(registry_path)


def test_not_exactly_one_orchestrator_rejected(repo_root, tmp_path):
    # The reader requires exactly one `agent:` key with name == orchestrator
    # (design D1 / AO-1). Missing orchestrator → error.
    import yaml

    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        yaml.safe_dump({"sub_agents": {"research_triage": {}}}),
        encoding="utf-8",
    )

    from app.agent_registry import RegistryError

    with __import__("pytest").raises(RegistryError):
        _load(registry_path)


def test_reader_returns_frozen_dataclasses(repo_root):
    from dataclasses import FrozenInstanceError

    reg = _load(repo_root)
    with __import__("pytest").raises(FrozenInstanceError):
        reg.sub_agents["research_triage"].name = "mutated"
    with __import__("pytest").raises(FrozenInstanceError):
        reg.orchestrator.name = "mutated"


def test_orchestrator_sub_agents_fields_frozen(repo_root):
    # Fresh objects each load (no shared mutable state across calls).
    reg_a = _load(repo_root)
    reg_b = _load(repo_root)
    assert reg_a is not reg_b
    assert reg_a.sub_agents is not reg_b.sub_agents


# --- AO-2 / design line 43: registry loaded ONCE (cached at graph construction)

def test_get_registry_caches_single_load(monkeypatch, repo_root):
    # design.md line 43: ``load_registry()`` runs ONCE at graph construction
    # (module scope, cached). ``get_registry`` is the cached getter the runtime
    # dispatch uses; it must not re-read ``registry.yaml`` on every call. The
    # pure ``load_registry`` still returns fresh objects (frozen test above).
    import app.agent_registry as reg_module

    calls = {"n": 0}
    original = reg_module.load_registry

    def counting(path=None):
        calls["n"] += 1
        return original(path)

    monkeypatch.setattr(reg_module, "load_registry", counting)
    monkeypatch.setattr(reg_module, "_registry_cache", None)

    first = reg_module.get_registry(repo_root / "agent" / "registry.yaml")
    second = reg_module.get_registry(repo_root / "agent" / "registry.yaml")

    assert calls["n"] == 1, "the registry loader must run exactly once"
    assert first is second, "the cached getter must return the SAME object"
    assert first.sub_agents["research_triage"].name == "kb-research-triage"


def test_valid_registry_resolves_assistant_runtime_configuration(repo_root):
    reg = _load(repo_root)

    assert reg.assistant.name == "assistant"
    assert reg.assistant.persona == "personas/assistant.md"
    assert reg.assistant.prompts == {
        "plan": "prompts/assistant_plan.md",
        "respond": "prompts/assistant_respond.md",
        "classify": "prompts/assistant_classify.md",
    }
    assert len(reg.assistant.tools_whitelist) == 13
    assert "automation.create_rule" in reg.assistant.tools_whitelist


@pytest.mark.parametrize("field", ["persona", "prompt"])
def test_missing_assistant_runtime_reference_rejected(repo_root, tmp_path, field):
    import yaml

    source = yaml.safe_load((repo_root / "agent" / "registry.yaml").read_text(encoding="utf-8"))
    if field == "persona":
        source["assistant"]["persona"] = "personas/missing.md"
    else:
        source["assistant"]["prompts"]["plan"] = "prompts/missing.md"
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(yaml.safe_dump(source), encoding="utf-8")

    from app.agent_registry import RegistryError

    with pytest.raises(RegistryError, match="does not exist"):
        from app.agent_registry import load_registry

        load_registry(registry_path)
