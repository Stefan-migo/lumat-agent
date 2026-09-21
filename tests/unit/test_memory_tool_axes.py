import json
from unittest.mock import MagicMock, Mock

import pytest

import app.chat.assistant.tools.registry as registry
from app.chat.assistant.nodes import _planner_tool_catalog
from app.services import tukulpan


def test_memory_tool_declares_visibility_without_a_write_target():
    args = registry.MemoryWriteArgs.model_validate(
        {
            "titulo": "Project fact",
            "contenido": "A reusable fact",
            "topic_key": "agent:fact",
            "visibility": "project",
        }
    )
    assert args.visibility == "project"
    with pytest.raises(ValueError):
        registry.MemoryWriteArgs.model_validate(
            {
                "titulo": "Project fact",
                "contenido": "A reusable fact",
                "topic_key": "agent:fact",
                "scope": "agent",
            }
        )


def test_memory_write_topic_key_contract_is_advertised_in_the_schema():
    topic_key_schema = registry.MemoryWriteArgs.model_json_schema()["properties"]["topic_key"]

    assert topic_key_schema.get("pattern") == r"^agent:"


def test_planner_catalog_advertises_the_topic_key_contract():
    catalog = json.loads(_planner_tool_catalog(["memory.write"]))
    memory_write = next(entry for entry in catalog if entry["name"] == "memory.write")

    assert memory_write["arguments"]["properties"]["topic_key"].get("pattern") == r"^agent:"


def test_memory_write_topic_key_still_requires_the_agent_namespace():
    with pytest.raises(ValueError):
        registry.MemoryWriteArgs.model_validate(
            {
                "titulo": "A fact",
                "contenido": "A fact",
                "topic_key": "test",
            }
        )

    assert registry.MemoryWriteArgs.model_validate(
        {
            "titulo": "A fact",
            "contenido": "A fact",
            "topic_key": "agent:fact",
        }
    )


def test_agent_scope_requires_canonical_entity():
    assert registry.MemoryArgs.model_validate(
        {"scope": "agent", "entity_id": tukulpan.agent_memory_entity(tukulpan.WRITABLE_PROYECTO)}
    )
    with pytest.raises(ValueError, match="canonical agent"):
        registry.MemoryArgs.model_validate({"scope": "agent", "entity_id": "agent:other"})


def test_project_write_maps_axis_and_stamps_agent_provenance(monkeypatch):
    captured = {}

    def fake_upsert(_session, **kwargs):
        captured.update(kwargs)
        return Mock(id=7)

    monkeypatch.setattr(registry.memory, "upsert", fake_upsert)
    session = MagicMock()
    args = registry.MemoryWriteArgs(
        titulo="Project fact",
        contenido="A reusable fact",
        topic_key="agent:fact",
        visibility="project",
    )

    result = registry._write_memory(session, args, trusted_thread_id=42)

    assert result == {"written": True, "id": 7, "topic_key": "agent:fact"}
    assert captured["scope"] == "agent"
    assert captured["entity_id"] == tukulpan.agent_memory_entity(tukulpan.WRITABLE_PROYECTO)
    assert captured["proyecto"] == tukulpan.WRITABLE_PROYECTO
    assert captured["producer"] == tukulpan.MemoryProducer.AGENT
    assert captured["origin_thread_id"] == "42"
    assert captured["visibility"] == "project"
