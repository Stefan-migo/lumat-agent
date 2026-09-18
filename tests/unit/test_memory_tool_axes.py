from unittest.mock import MagicMock, Mock

import pytest

import app.chat.assistant.tools.registry as registry
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


def test_agent_scope_requires_canonical_entity():
    assert registry.MemoryArgs.model_validate(
        {"scope": "agent", "entity_id": tukulpan.AGENT_MEMORY_ENTITY}
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
    assert captured["entity_id"] == tukulpan.AGENT_MEMORY_ENTITY
    assert captured["producer"] == tukulpan.MemoryProducer.AGENT
    assert captured["origin_thread_id"] == "42"
    assert captured["visibility"] == "project"
