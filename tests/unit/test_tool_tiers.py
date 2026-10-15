from app.chat.assistant.tools.registry import TOOL_REGISTRY


DEFAULT_TOOLS = {
    "assistant.capabilities",
    "customers.search",
    "customers.list",
    "customers.operational_history",
    "conversations.search",
    "conversations.list",
    "appointments.upcoming",
    "cases.list",
    "kb.retrieve",
    "memory.read",
    "memory.search",
    "memory.write",
    "memory.update",
    "memory.delete",
    "dashboard.summary",
    "analytics.chatbot_metrics",
    "analytics.chatbot_conversations",
    "conversations.transcript",
    "settings.update",
    "project.list",
    "project.find",
    "list_project_files",
    "read_project_file",
    "view_image",
    "artifact.save",
    "skill.propose",
    "planning.open",
    "planning.close",
    "planning.record_decision",
    "planning.record_note",
    "planning.read_report",
}

OPT_IN_TOOLS = {
    "web.search",
    "web.fetch",
    "automation.create_rule",
    "project.create",
    "project.rename",
    "project.archive",
    "project.merge",
}


def test_tool_registry_declares_exact_default_and_opt_in_tiers():
    default_tools = {name for name, tool in TOOL_REGISTRY.items() if tool.tier == "default"}
    opt_in_tools = {name for name, tool in TOOL_REGISTRY.items() if tool.tier == "opt_in"}

    assert all(tool.tier in {"default", "opt_in"} for tool in TOOL_REGISTRY.values())
    assert default_tools == DEFAULT_TOOLS
    assert opt_in_tools == OPT_IN_TOOLS
    assert default_tools.isdisjoint(opt_in_tools)
    assert default_tools | opt_in_tools == set(TOOL_REGISTRY)
