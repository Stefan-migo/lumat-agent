import pytest

import app.services.tukulpan as tukulpan


def test_agent_memory_entity_is_derived_from_project():
    assert tukulpan.agent_memory_entity("acme") == "agent:acme"
    assert tukulpan.agent_memory_entity("acme") != tukulpan.agent_memory_entity("default")


def test_thread_memory_entity_is_derived_from_thread():
    assert tukulpan.thread_memory_entity(42) == "thread:42"


def test_visibility_target_maps_declared_visibility():
    assert tukulpan.visibility_target("thread", thread_id=42, proyecto="acme") == ("panel", "thread:42")
    assert tukulpan.visibility_target("global", thread_id=42, proyecto="acme") == (
        tukulpan.AGENT_SCOPE,
        "agent:acme",
    )


def test_visibility_target_rejects_unknown_visibility():
    # "project" was the retired label: it must not be reachable any more.
    for unknown in ("customer", "project"):
        with pytest.raises(ValueError, match="visibility"):
            tukulpan.visibility_target(unknown, thread_id=42, proyecto="acme")
