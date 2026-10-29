import json
from types import SimpleNamespace
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


def test_planner_catalog_description_matches_the_global_write_default():
    """The planner reads this description to decide how to use the tool.

    `visibility` defaults to `global`, so the advertised description must not
    claim the write is confined to the current thread (MEM-9 / AT-9).
    """
    catalog = json.loads(_planner_tool_catalog(["memory.write"]))
    description = next(entry for entry in catalog if entry["name"] == "memory.write")["description"]

    assert "global" in description
    assert "current panel thread" not in description


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


def test_planner_catalog_drops_titles_without_weakening_memory_read_schema():
    catalog = json.loads(_planner_tool_catalog(list(registry.TOOL_REGISTRY)))

    def assert_no_titles(value):
        if isinstance(value, dict):
            assert "title" not in value
            for nested in value.values():
                assert_no_titles(nested)
        elif isinstance(value, list):
            for nested in value:
                assert_no_titles(nested)

    assert_no_titles(catalog)

    memory_read = next(entry for entry in catalog if entry["name"] == "memory.read")
    variants = _advertised_scope_variants(memory_read["arguments"])

    assert set(variants) == {"own", "customer"}
    assert variants["customer"]["properties"]["entity_id"]["pattern"] == r"^(?:customer:\d+|\d+)$"
    assert variants["own"]["properties"]["entity_id"]["type"] == "null"
    assert {
        scope: variant["required"] for scope, variant in variants.items()
    } == {
        scope: variant["required"]
        for scope, variant in _advertised_scope_variants(registry.MemoryArgs.model_json_schema()).items()
    }


def test_planner_prompt_does_not_order_a_rejected_memory_read_shape():
    template = load_assistant_config().prompts["plan"]

    assert 'entity_id="thread:' not in template


def test_own_memory_read_and_search_union_thread_and_agent_axes(monkeypatch):
    thread_row = Mock(
        id=1, scope="panel", entity_id="thread:42", topic_key="thread-note", titulo="", tipo="decision",
        contenido="", created_at=None, updated_at=None,
    )
    agent_row = Mock(
        id=2, scope="agent", entity_id="agent:default", topic_key="project-note", titulo="", tipo="decision",
        contenido="", created_at=None, updated_at=None,
    )
    list_calls = []
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id, proyecto, owner_id: list_calls.append((scope, entity_id, proyecto)) or ([thread_row] if entity_id == "thread:42" else [agent_row]),
    )
    monkeypatch.setattr(registry.projects, "agent_context", lambda _session, slug, *, owner_id: SimpleNamespace(owner_id=owner_id))
    result = registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42, proyecto="acme"
    )
    assert [row["topic_key"] for row in result] == ["thread-note", "project-note"]
    assert list_calls == [("panel", "thread:42", "acme"), ("agent", "agent:acme", "acme")]

    monkeypatch.setattr(
        registry.memory,
        "hybrid_search",
        lambda _session, _query, *, scope, entity_id, proyecto, owner_id, top_k: [
            {"entity_id": entity_id, "score": 0.8 if scope == "panel" else 0.9}
        ],
    )
    results = registry._search_memory(
        MagicMock(), registry.MemorySearchArgs.model_validate({"query": "fact"}), trusted_thread_id=42, proyecto="acme"
    )
    assert [row["entity_id"] for row in results] == ["agent:acme", "thread:42"]


def test_own_memory_read_threads_derived_owner_into_both_axes(monkeypatch):
    seen = []
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id, proyecto, owner_id: seen.append((scope, owner_id)) or [],
    )
    monkeypatch.setattr(
        registry.projects,
        "agent_context",
        lambda _session, slug, *, owner_id: SimpleNamespace(owner_id=7),
    )

    assert registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42, proyecto="acme"
    ) == []
    assert seen == [("panel", 7), ("agent", 7)]


def test_own_memory_never_returns_another_threads_panel_row(monkeypatch):
    other_thread = Mock(scope="panel", entity_id="thread:7", topic_key="other")
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id, proyecto, owner_id: [other_thread] if entity_id == "thread:7" else [],
    )
    assert registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42
    ) == []


def test_own_memory_read_interleaves_both_axes_before_truncating(monkeypatch):
    thread_rows = [
        Mock(id=index, scope="panel", entity_id="thread:42", topic_key=f"thread-{index}", titulo="", tipo="decision", contenido="", created_at=None, updated_at=None)
        for index in range(3)
    ]
    agent_rows = [
        Mock(id=index, scope="agent", entity_id="agent:default", topic_key=f"project-{index}", titulo="", tipo="decision", contenido="", created_at=None, updated_at=None)
        for index in range(2)
    ]
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id, proyecto, owner_id: thread_rows if scope == "panel" else agent_rows,
    )

    result = registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42
    )
    assert [row["topic_key"] for row in result] == [
        "thread-0", "project-0", "thread-1", "project-1", "thread-2"
    ]


def test_own_memory_read_orders_each_axis_by_pin_handoff_then_recency(monkeypatch):
    def row(scope, entity_id, topic_key, *, pin=False, handoff=False, updated_at):
        return Mock(
            id=topic_key, scope=scope, entity_id=entity_id, topic_key=topic_key,
            titulo="", tipo="decision", contenido="", created_at=None,
            updated_at=updated_at, pin=pin, handoff=handoff,
        )

    thread_rows = [
        row("panel", "thread:42", "thread-recent", updated_at=3),
        row("panel", "thread:42", "thread-handoff", handoff=True, updated_at=1),
        row("panel", "thread:42", "thread-pin", pin=True, updated_at=0),
    ]
    agent_rows = [
        row("agent", "agent:acme", "agent-recent", updated_at=3),
        row("agent", "agent:acme", "agent-handoff", handoff=True, updated_at=1),
        row("agent", "agent:acme", "agent-pin", pin=True, updated_at=0),
    ]
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id, proyecto, owner_id: thread_rows if scope == "panel" else agent_rows,
    )
    monkeypatch.setattr(registry.projects, "agent_context", lambda _session, slug, *, owner_id: SimpleNamespace(owner_id=owner_id))

    result = registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42, proyecto="acme"
    )

    assert [item["topic_key"] for item in result] == [
        "thread-pin", "agent-pin", "thread-handoff", "agent-handoff", "thread-recent", "agent-recent"
    ]


def test_own_memory_read_returns_bounded_digest_with_stable_shape(monkeypatch):
    assert registry.MEMORY_READ_DIGEST_CONTENT_LIMIT == 500
    row = SimpleNamespace(
        id=7,
        scope="panel",
        entity_id="thread:42",
        topic_key="thread-note",
        titulo="Thread note",
        tipo="decision",
        contenido="x" * 501,
        handoff=True,
        last_seen_at=None,
        review_after=None,
        created_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, entity_id, **kwargs: [row] if entity_id == "thread:42" else [],
    )
    monkeypatch.setattr(registry.projects, "agent_context", lambda _session, slug, *, owner_id: SimpleNamespace(owner_id=owner_id))

    result = registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42, proyecto="acme"
    )

    assert result == [
        {
            "id": 7,
            "scope": "panel",
            "entity_id": "thread:42",
            "topic_key": "thread-note",
            "titulo": "Thread note",
            "tipo": "decision",
            "contenido": "x" * 500,
            "handoff": True,
            "last_seen_at": None,
            "review_after": None,
            "created_at": None,
            "updated_at": None,
        }
    ]


def test_own_memory_read_never_starves_the_project_axis(monkeypatch):
    thread_rows = [
        Mock(id=index, scope="panel", entity_id="thread:42", topic_key=f"thread-{index}", titulo="", tipo="decision", contenido="", created_at=None, updated_at=None)
        for index in range(10)
    ]
    agent_row = Mock(id=99, scope="agent", entity_id="agent:default", topic_key="project-note", titulo="", tipo="decision", contenido="", created_at=None, updated_at=None)
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id, proyecto, owner_id: thread_rows if scope == "panel" else [agent_row],
    )

    result = registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({}), trusted_thread_id=42
    )

    assert len(result) == 10
    assert any(row["topic_key"] == "project-note" for row in result)


def test_own_memory_read_topic_filter_still_matches_both_axes(monkeypatch):
    thread_rows = [
        Mock(id=1, scope="panel", entity_id="thread:42", topic_key="keep", titulo="", tipo="decision", contenido="", created_at=None, updated_at=None),
        Mock(id=2, scope="panel", entity_id="thread:42", topic_key="drop", titulo="", tipo="decision", contenido="", created_at=None, updated_at=None),
    ]
    agent_rows = [
        Mock(id=3, scope="agent", entity_id="agent:default", topic_key="keep", titulo="", tipo="decision", contenido="", created_at=None, updated_at=None),
        Mock(id=4, scope="agent", entity_id="agent:default", topic_key="drop", titulo="", tipo="decision", contenido="", created_at=None, updated_at=None),
    ]
    monkeypatch.setattr(
        registry.memory,
        "list_for_entity",
        lambda _session, *, scope, entity_id, proyecto, owner_id: thread_rows if scope == "panel" else agent_rows,
    )

    result = registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({"topic": "keep"}), trusted_thread_id=42
    )

    assert [row["topic_key"] for row in result] == ["keep", "keep"]


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
        handoff=True,
    )

    monkeypatch.setattr(registry.projects, "agent_context", lambda _session, slug, *, owner_id: Mock(slug=slug, owner_id=owner_id))
    result = registry._write_memory(session, args, trusted_thread_id=42, proyecto="acme")

    assert result == {"written": True, "id": 7, "topic_key": "agent:fact"}
    assert captured["scope"] == "agent"
    assert captured["entity_id"] == tukulpan.agent_memory_entity("acme")
    assert captured["proyecto"] == "acme"
    assert captured["authorization"].slug == "acme"
    assert captured["producer"] == tukulpan.MemoryProducer.AGENT
    assert captured["origin_thread_id"] == "42"
    assert captured["visibility"] == "global"
    assert captured["handoff"] is True


def test_memory_write_handoff_defaults_to_false():
    args = registry.MemoryWriteArgs(
        titulo="Project fact",
        contenido="A reusable fact",
        topic_key="agent:fact",
        tipo="decision",
    )

    assert args.handoff is False


def test_user_memory_write_uses_authenticated_user_axis_not_project_owner(monkeypatch):
    captured = {}
    monkeypatch.setattr(registry.projects, "agent_context", lambda *_args, **_kwargs: pytest.fail("user axis must not resolve project authorization"))
    monkeypatch.setattr(registry.memory, "upsert", lambda _session, **kwargs: captured.update(kwargs) or Mock(id=12))
    args = registry.MemoryWriteArgs(
        titulo="Person fact", contenido="Prefers concise updates", topic_key="agent:preference",
        tipo="preference", visibility="user",
    )

    result = registry._write_memory(MagicMock(), args, trusted_thread_id=3, proyecto="acme", owner_id=7)

    assert result == {"written": True, "id": 12, "topic_key": "agent:preference"}
    assert captured["scope"] == "user"
    assert captured["entity_id"] == "user:7"
    assert captured["proyecto"] == "default"
    assert captured["owner_id"] == 7
    assert captured["visibility"] == tukulpan.MemoryVisibility.GLOBAL
    assert captured["authorization"] is None


def test_user_memory_write_requires_positive_integer_owner_before_persistence(monkeypatch):
    writes = []
    monkeypatch.setattr(registry.memory, "upsert", lambda *_args, **_kwargs: writes.append(True))
    args = registry.MemoryWriteArgs(
        titulo="Person fact", contenido="Prefers concise updates", topic_key="agent:preference",
        tipo="preference", visibility="user",
    )

    for owner_id in (None, 0, -1, "7", True):
        with pytest.raises(registry.ToolValidationError, match="authenticated owner"):
            registry._write_memory(MagicMock(), args, trusted_thread_id=3, proyecto="default", owner_id=owner_id)
    assert writes == []


def test_user_memory_read_has_separate_budget_and_interleaves_three_axes(monkeypatch):
    calls = []
    def rows_for(scope, entity_id):
        return [Mock(
            id=f"{scope}-{i}", scope=scope, entity_id=entity_id, topic_key=f"{scope}-{i}",
            titulo="", tipo="decision", contenido="", created_at=None, updated_at=None,
        ) for i in range(5)]
    def list_axis(_session, *, scope, entity_id, proyecto, owner_id):
        calls.append((scope, entity_id, proyecto, owner_id))
        return rows_for(scope, entity_id)
    monkeypatch.setattr(registry.memory, "list_for_entity", list_axis)
    monkeypatch.setattr(registry.projects, "agent_context", lambda *_args, **kwargs: SimpleNamespace(owner_id=999))

    result = registry._read_memory(
        MagicMock(), registry.MemoryArgs.model_validate({"limit": 3}), trusted_thread_id=42,
        proyecto="acme", owner_id=7,
    )

    assert calls == [
        ("panel", "thread:42", "acme", 999),
        ("agent", "agent:acme", "acme", 999),
        ("user", "user:7", "default", 7),
    ]
    assert registry.USER_AXIS_LIMIT == 2
    assert len(result) == 3
    assert sum(row["scope"] == "user" for row in result) <= 2
    assert any(row["scope"] in {"panel", "agent"} for row in result)


def test_user_memory_search_has_separate_budget_and_interleaves_axes(monkeypatch):
    calls = []
    def search_axis(_session, query, *, scope, entity_id, proyecto, owner_id, top_k):
        calls.append((scope, entity_id, proyecto, owner_id, top_k))
        return [{"scope": scope, "entity_id": entity_id, "score": 1.0 - i / 10} for i in range(4)]
    monkeypatch.setattr(registry.memory, "hybrid_search", search_axis)
    monkeypatch.setattr(registry.projects, "agent_context", lambda *_args, **kwargs: SimpleNamespace(owner_id=999))

    result = registry._search_memory(
        MagicMock(), registry.MemorySearchArgs.model_validate({"query": "fact", "limit": 3}),
        trusted_thread_id=42, proyecto="acme", owner_id=7,
    )

    assert calls == [
        ("panel", "thread:42", "acme", 999, 3),
        ("agent", "agent:acme", "acme", 999, 3),
        ("user", "user:7", "default", 7, registry.USER_AXIS_LIMIT),
    ]
    assert len(result) == 3
    assert any(row["scope"] != "user" for row in result)
