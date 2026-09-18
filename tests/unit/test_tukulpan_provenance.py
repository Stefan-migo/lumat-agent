from pathlib import Path
import re

import pytest

import app.services.tukulpan as tukulpan


def test_agent_memory_entity_matches_registry_name():
    registry = Path(__file__).parents[2] / "agent" / "registry.yaml"
    content = registry.read_text()
    assistant_name = re.search(r"^assistant:\n(?:.*\n)*?  name: (.+)$", content, re.MULTILINE).group(1)
    assert hasattr(tukulpan, "AGENT_MEMORY_ENTITY")
    assert tukulpan.AGENT_MEMORY_ENTITY == f"agent:{assistant_name}"


def test_visibility_target_maps_declared_visibility():
    assert tukulpan.visibility_target("thread", thread_id=42) == ("panel", "thread:42")
    assert tukulpan.visibility_target("project", thread_id=42) == (
        tukulpan.AGENT_SCOPE,
        tukulpan.AGENT_MEMORY_ENTITY,
    )


def test_visibility_target_rejects_unknown_visibility():
    with pytest.raises(ValueError, match="visibility"):
        tukulpan.visibility_target("customer", thread_id=42)
