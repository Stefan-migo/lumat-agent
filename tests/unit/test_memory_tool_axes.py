import json
from unittest.mock import MagicMock, Mock

import pytest

import app.chat.assistant.tools.registry as registry
from app.chat.assistant.nodes import _planner_tool_catalog
from app.services import tukulpan
from app.services.prompts import load_assistant_config


def test_memory_tool_declares_visibility_without_a_write_target():
    args = registry.MemoryWriteArgs.model_validate(
        {
            "titulo": "Project fact",
            "contenido": "A reusable fact",
            "topic_key": "agent:fact",
            "tipo": "decision",
            "visibility": "global",
        }
    )
    assert args.visibility == "global"
    with pytest.raises(ValueError):
        registry.MemoryWriteArgs.model_validate(
            {
                "titulo": "Project fact",
                "contenido": "A reusable fact",
                "topic_key": "agent:fact",
                "scope": "agent",
            }
        )


def test_memory_write_rejects_the_retired_project_label():
    """The renamed vocabulary must not keep accepting the old word."""
    with pytest.raises(ValueError):
        registry.MemoryWriteArgs.model_validate(
            {
                "titulo": "Project fact",
                "contenido": "A reusable fact",
                "topic_key": "agent:fact",
                "tipo": "decision",
                "visibility": "project",
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
                "tipo": "decision",
            }
        )

    assert registry.MemoryWriteArgs.model_validate(
        {
            "titulo": "A fact",
            "contenido": "A fact",
            "topic_key": "agent:fact",
            "tipo": "decision",
        }
    )


def test_memory_write_requires_type_and_defaults_visibility_to_global():
    payload = {
        "titulo": "A fact",
        "contenido": "A fact",
        "topic_key": "agent:fact",
    }

    with pytest.raises(ValueError):
        registry.MemoryWriteArgs.model_validate(payload)

    args = registry.MemoryWriteArgs.model_validate({**payload, "tipo": "discovery"})
    assert args.visibility == "global"


def test_memory_own_scope_defaults_and_rejects_internal_axes():
    assert registry.MemoryArgs.model_validate({}).root.scope == "own"
    assert registry.MemorySearchArgs.model_validate({"query": "fact"}).root.scope == "own"
    for scope in ("panel", "agent"):
        with pytest.raises(ValueError):
            registry.MemoryArgs.model_validate({"scope": scope})


def _advertised_scope_variants(schema: dict) -> dict:
    """Map each announced scope to the schema variant that declares it."""
    assert "$defs" in schema, "the arguments schema announces no per-scope variant"
    return {variant["properties"]["scope"]["const"]: variant for variant in schema["$defs"].values()}


def test_memory_read_schema_advertises_each_scope_entity_contract():
    variants = _advertised_scope_variants(registry.MemoryArgs.model_json_schema())

    assert set(variants) == {"own", "customer"}
    assert variants["own"]["properties"]["entity_id"]["type"] == "null"
    assert variants["customer"]["properties"]["entity_id"]["pattern"] == r"^(?:customer:\d+|\d+)$"


def test_planner_catalog_advertises_the_memory_read_scope_contract():
    catalog = json.loads(_planner_tool_catalog(["memory.read", "memory.search"]))

    for entry in catalog:
        variants = _advertised_scope_variants(entry["arguments"])
        assert set(variants) == {"own", "customer"}


def test_planner_prompt_does_not_order_a_rejected_memory_read_shape():
    template = load_assistant_config().prompts["plan"]

    assert 'entity_id="thread:' not in template


def test_own_memory_read_and_search_union_thread_and_agent_axes(monkeypatch):
    thread_row = Mock(scope="panel", entity_id="thread:42", topic_key="thread-note")
    agent_row = Mock(scope="agent", entity_id="agent:default", topic_key="project-note")
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id: [thread_row] if entity_id == "thread:42" else [agent_row],
    )
    assert registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42
    ) == [thread_row, agent_row]

    monkeypatch.setattr(
        registry.memory,
        "hybrid_search",
        lambda _session, _query, *, scope, entity_id, top_k: [
            {"entity_id": entity_id, "score": 0.8 if scope == "panel" else 0.9}
        ],
    )
    results = registry._search_memory(
        MagicMock(), registry.MemorySearchArgs.model_validate({"query": "fact"}), trusted_thread_id=42
    )
    assert [row["entity_id"] for row in results] == ["agent:default", "thread:42"]


def test_own_memory_never_returns_another_threads_panel_row(monkeypatch):
    other_thread = Mock(scope="panel", entity_id="thread:7", topic_key="other")
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id: [other_thread] if entity_id == "thread:7" else [],
    )
    assert registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42
    ) == []


def test_own_memory_read_interleaves_both_axes_before_truncating(monkeypatch):
    thread_rows = [
        Mock(scope="panel", entity_id="thread:42", topic_key=f"thread-{index}") for index in range(3)
    ]
    agent_rows = [
        Mock(scope="agent", entity_id="agent:default", topic_key=f"project-{index}") for index in range(2)
    ]
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id: thread_rows if scope == "panel" else agent_rows,
    )

    assert registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42
    ) == [thread_rows[0], agent_rows[0], thread_rows[1], agent_rows[1], thread_rows[2]]


def test_own_memory_read_never_starves_the_project_axis(monkeypatch):
    thread_rows = [
        Mock(scope="panel", entity_id="thread:42", topic_key=f"thread-{index}") for index in range(10)
    ]
    agent_row = Mock(scope="agent", entity_id="agent:default", topic_key="project-note")
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id: thread_rows if scope == "panel" else [agent_row],
    )

    result = registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42
    )

    assert len(result) == 10
    assert agent_row in result


def test_own_memory_read_topic_filter_still_matches_both_axes(monkeypatch):
    thread_rows = [
        Mock(scope="panel", entity_id="thread:42", topic_key="keep"),
        Mock(scope="panel", entity_id="thread:42", topic_key="drop"),
    ]
    agent_rows = [
        Mock(scope="agent", entity_id="agent:default", topic_key="keep"),
        Mock(scope="agent", entity_id="agent:default", topic_key="drop"),
    ]
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id: thread_rows if scope == "panel" else agent_rows,
    )

    result = registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({"topic": "keep"}), trusted_thread_id=42
    )

    assert [row.topic_key for row in result] == ["keep", "keep"]


def test_global_write_maps_axis_and_stamps_agent_provenance(monkeypatch):
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
        tipo="decision",
        visibility="global",
    )

    result = registry._write_memory(session, args, trusted_thread_id=42)

    assert result == {"written": True, "id": 7, "topic_key": "agent:fact"}
    assert captured["scope"] == "agent"
    assert captured["entity_id"] == tukulpan.agent_memory_entity(tukulpan.WRITABLE_PROYECTO)
    assert captured["proyecto"] == tukulpan.WRITABLE_PROYECTO
    assert captured["producer"] == tukulpan.MemoryProducer.AGENT
    assert captured["origin_thread_id"] == "42"
    assert captured["visibility"] == "global"
