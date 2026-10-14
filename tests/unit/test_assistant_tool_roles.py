import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.chat.assistant.tools import registry
from app.chat.assistant.tools.registry import ToolDefinition, ToolValidationError
from app.models import UserRole


ROLE_TOOL_EXPECTATIONS = {
    UserRole.ADMIN: set(registry.TOOL_REGISTRY),
    UserRole.OPERADOR: set(registry.TOOL_REGISTRY) - {"automation.create_rule"},
    UserRole.TECNICO: {
        "assistant.capabilities", "memory.read", "memory.search", "memory.write",
        "memory.update", "memory.delete", "project.list", "project.find",
        "project.create", "project.rename", "project.archive", "project.merge",
        "web.search", "web.fetch", "appointments.upcoming",
        "artifact.save",
    },
}


@pytest.mark.parametrize("role", list(UserRole))
@pytest.mark.parametrize("tool_name", list(registry.TOOL_REGISTRY))
def test_role_tool_matrix_is_enforced(role, tool_name, monkeypatch):
    expected_allowed = tool_name in ROLE_TOOL_EXPECTATIONS[role]
    monkeypatch.setitem(
        registry.TOOL_REGISTRY,
        tool_name,
        ToolDefinition(tool_name, registry.CapabilitiesArgs, True, lambda *_, **__: {"ok": True}, "test", tier="default"),
    )
    call = lambda: registry.execute_tool(
        SimpleNamespace(), tool_name, {}, role=role.value, owner_id=1, trusted_thread_id=1
    )

    if expected_allowed:
        result = call()
        assert result["result"] == {"ok": True}
        assert "error" not in result
    else:
        with pytest.raises(ToolValidationError, match="not authorized"):
            call()


def test_business_memory_roles_match_business_tool_permissions():
    assert registry.BUSINESS_MEMORY_ROLES == {"admin", "operador"}
    assert UserRole.TECNICO not in registry.ROLE_TOOL_ALLOWLIST["customers.search"]
    assert {UserRole.ADMIN, UserRole.OPERADOR} <= registry.ROLE_TOOL_ALLOWLIST["customers.search"]


def test_chatbot_metrics_is_allowed_to_admin_and_operator_only():
    assert registry.ROLE_TOOL_ALLOWLIST["analytics.chatbot_metrics"] == frozenset({
        UserRole.ADMIN, UserRole.OPERADOR,
    })


def test_conversation_inspection_tools_are_allowed_to_admin_and_operator_only():
    for name in ("analytics.chatbot_conversations", "conversations.transcript"):
        assert registry.ROLE_TOOL_ALLOWLIST[name] == frozenset({
            UserRole.ADMIN, UserRole.OPERADOR,
        })


def test_role_tool_map_is_complete_and_covers_every_role():
    assert set(registry.ROLE_TOOL_ALLOWLIST) == set(registry.TOOL_REGISTRY)
    assert set(ROLE_TOOL_EXPECTATIONS) == set(UserRole)
    for tool_name in registry.TOOL_REGISTRY:
        assert isinstance(registry.ROLE_TOOL_ALLOWLIST[tool_name], frozenset)
        for role in UserRole:
            assert (role in registry.ROLE_TOOL_ALLOWLIST[tool_name]) == (
                tool_name in ROLE_TOOL_EXPECTATIONS[role]
            )


@pytest.mark.parametrize("role", [None, 7, "unknown"])
def test_invalid_role_denies_every_tool(role):
    for tool_name in registry.TOOL_REGISTRY:
        with pytest.raises(ToolValidationError):
            registry.execute_tool(SimpleNamespace(), tool_name, {}, role=role, owner_id=1)


def test_missing_role_denies_every_tool():
    for tool_name in registry.TOOL_REGISTRY:
        with pytest.raises(ToolValidationError):
            registry.execute_tool(SimpleNamespace(), tool_name, {}, owner_id=1)


def test_all_execution_call_sites_pass_actor_role():
    expected = {
        "app/chat/assistant/nodes.py": {"delegation_span", "execute"},
    }
    root = Path(__file__).resolve().parents[2]
    for filename, function_names in expected.items():
        tree = ast.parse((root / filename).read_text())
        functions = {node.name: node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        calls = []
        for function_name in function_names:
            calls.extend(
                node for node in ast.walk(functions[function_name])
                if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "execute_tool"
            )
        assert calls
        assert all(any(keyword.arg == "role" for keyword in call.keywords) for call in calls)


def test_delegated_read_scope_executes_an_allowed_tool_and_passes_role(monkeypatch):
    from app.chat.assistant import nodes
    from app.chat.assistant.delegation import resolve_delegation_scope

    plans = iter([
        {"kind": "tool", "tool": "customers.search", "arguments": {"query": "Ana"},
         "summary": "Find customer", "requires_approval": False},
        {"kind": "respond", "summary": "Found no records."},
    ])
    monkeypatch.setattr(nodes, "_delegation_plan", lambda *_args, **_kwargs: next(plans))
    seen = []

    def execute(*args, **kwargs):
        seen.append(kwargs.get("role"))
        return {"tool": args[1], "status": "completed", "result": []}

    monkeypatch.setattr(nodes, "execute_tool", execute)
    result = nodes.delegation_span(
        {"content": "Find Ana", "thread_id": 1, "actor_role": "admin"},
        resolve_delegation_scope("customer_records"),
    )

    assert result["evidence"]
    assert seen == ["admin"]
