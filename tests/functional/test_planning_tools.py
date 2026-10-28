"""Planning tool removal leaves ordinary memory tools available."""

from app.chat.assistant.tools.registry import ROLE_TOOL_ALLOWLIST, TOOL_REGISTRY


def test_planning_tools_are_absent_and_memory_tools_remain_authorized():
    removed = {
        "planning.open", "planning.close", "planning.record_decision",
        "planning.record_note", "planning.read_report",
    }
    assert removed.isdisjoint(TOOL_REGISTRY)
    assert removed.isdisjoint(ROLE_TOOL_ALLOWLIST)
    for name in ("memory.read", "memory.write", "memory.update"):
        assert name in TOOL_REGISTRY
        assert name in ROLE_TOOL_ALLOWLIST
