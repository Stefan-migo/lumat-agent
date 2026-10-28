"""Removed planning operations cannot be authorized through any role mapping."""

from app.chat.assistant.tools.registry import ROLE_TOOL_ALLOWLIST, is_tool_allowed_for_role


REMOVED_PLANNING_TOOLS = (
    "planning.open", "planning.close", "planning.record_decision",
    "planning.record_note", "planning.read_report",
)


def test_removed_planning_tools_fail_closed_for_all_roles():
    assert all(name not in ROLE_TOOL_ALLOWLIST for name in REMOVED_PLANNING_TOOLS)
    for name in REMOVED_PLANNING_TOOLS:
        for role in ("admin", "operador", "tecnico"):
            assert is_tool_allowed_for_role(name, role) is False
