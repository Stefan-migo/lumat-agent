"""Metadata-only assistant extension hooks and terminology migration contracts."""

from pathlib import Path
from dataclasses import replace

from app.chat.assistant.nodes import extension_hook_metadata
from app.chat.assistant.nodes import plan


SDB_TERMINOLOGY_CONSUMERS = (
    Path("agent/skills/sdb.md"),
    Path("agent/README.md"),
    Path("openspec/specs/agent-config/spec.md"),
)


def test_extension_hooks_expose_status_metadata_without_executable_hooks():
    metadata = extension_hook_metadata()

    assert metadata == {
        "sdb": "deferred",
        "panel_subagents": "implemented",
    }
    assert all(not callable(value) for value in metadata.values())

    state = plan(
        {
            "content": "complex request",
            "planner_output": {
                "kind": "complex",
                "arguments": {"steps": ["research"]},
                "summary": "A future extension is required.",
                "requires_approval": False,
            },
        }
    )
    assert state["extension_hooks"] == metadata


def test_declared_but_inert_customer_worker_is_not_reported_as_implemented(monkeypatch):
    from app.agent_registry import get_registry
    from app.chat.assistant import delegation

    registry = get_registry()
    inert = replace(registry.sub_agents["customer_records"], tools_whitelist=())
    monkeypatch.setattr(
        delegation,
        "get_registry",
        lambda: replace(registry, sub_agents={**registry.sub_agents, "customer_records": inert}),
    )

    assert extension_hook_metadata()["panel_subagents"] == "not_implemented"


def test_all_inventoried_lumat_sdb_consumers_use_guardrails_terminology(repo_root):
    old_terms = ("SDB", "Deterministic Behavior Database")

    for relative_path in SDB_TERMINOLOGY_CONSUMERS:
        content = (repo_root / relative_path).read_text(encoding="utf-8")
        assert not any(term in content for term in old_terms), relative_path
        assert "Gates deterministas / Guardrails" in content, relative_path


def test_spec_driven_behavior_scope_remains_outside_terminology_migration(repo_root):
    spec = (
        repo_root / "openspec/changes/archive/2026-09-10-harness-lumat/specs/harness-lumat/spec.md"
    ).read_text(
        encoding="utf-8"
    )

    assert "SDB subgraph" in spec
