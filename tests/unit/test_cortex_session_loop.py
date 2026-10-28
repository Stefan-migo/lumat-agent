"""Assistant loop keeps legacy Cortex state out and preserves the SDB handoff."""

from app.chat.assistant.graph import run_assistant
from app.chat.assistant.nodes import _effective_tools


def test_effective_tools_are_not_filtered_by_legacy_cortex_state():
    tools = ("memory.delete", "project.create", "kb.retrieve")
    effective = {"tools_whitelist": tools}
    legacy_state = {"effective": effective, "cortex_session": {"status": "active"}}

    assert _effective_tools(legacy_state) == tools


def test_sdb_requested_remains_a_turn_state_field():
    # The graph's public entry point continues accepting the SDB handoff signal.
    assert "sdb_requested" in run_assistant.__annotations__ or "sdb_requested" in run_assistant.__code__.co_varnames
