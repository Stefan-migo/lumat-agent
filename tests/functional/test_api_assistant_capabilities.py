"""Read-only assistant capability contract (AC-10)."""

from __future__ import annotations

import pytest


def _login(client, username: str, password: str) -> None:
    response = client.post("/panel/api/login", json={"username": username, "password": password})
    assert response.status_code == 200


def test_capabilities_requires_admin_json(client):
    response = client.get("/panel/api/assistant/capabilities")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_capabilities_hides_tools_the_role_cannot_execute(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")

    response = client.get("/panel/api/assistant/capabilities")

    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["tools"]}
    # operador keeps every business read but no privileged write (D2/D7).
    assert "automation.create_rule" not in names
    assert {"customers.search", "kb.retrieve"} <= names


def test_technician_capabilities_exclude_every_business_read(client, make_user):
    make_user("tec", "tec-pass", role="tecnico")
    _login(client, "tec", "tec-pass")

    response = client.get("/panel/api/assistant/capabilities")

    assert response.status_code == 200
    payload = response.json()
    names = {tool["name"] for tool in payload["tools"]}
    assert names.isdisjoint(
        {
            "customers.search",
            "customers.list",
            "conversations.search",
            "conversations.list",
            "customers.operational_history",
            "cases.list",
            "dashboard.summary",
            "automation.create_rule",
        }
    )
    # S9: the technician talks to TecnicoLumat — it reads the (audience-scoped) KB
    # and its own memory, and no longer advertises project-namespace administration.
    assert payload["personas"] == ["personas/tecnico_lumat.md"]
    assert {
        "kb.retrieve",
        "memory.read",
        "memory.search",
        "memory.write",
        "project.list",
        "appointments.upcoming",
    } <= names
    assert "project.create" not in names
    # The derived flags must describe the same filtered catalog the count shows.
    assert payload["kb_available"] is True
    assert payload["memory_available"] is True


@pytest.mark.parametrize("role", ["admin", "operador", "tecnico"])
def test_capabilities_only_lists_tools_the_role_may_execute(client, make_user, role):
    """The catalog must never advertise a tool the role's map denies."""
    from app.chat.assistant.tools.registry import ROLE_TOOL_ALLOWLIST
    from app.models import UserRole

    make_user("who", "who-pass", role=role)
    _login(client, "who", "who-pass")

    response = client.get("/panel/api/assistant/capabilities")

    assert response.status_code == 200
    user_role = UserRole(role)
    for tool in response.json()["tools"]:
        assert user_role in ROLE_TOOL_ALLOWLIST.get(tool["name"], frozenset()), tool["name"]


def test_admin_capabilities_reflect_real_tools_and_runtime_config(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client, "adm", "adm-pass")

    response = client.get("/panel/api/assistant/capabilities")

    assert response.status_code == 200
    payload = response.json()
    # Derive the expected surface from the code registry so adding or removing a
    # tool does not break this contract test (WU#8 R3 follow-up).
    from app.chat.assistant.tools.registry import TOOL_REGISTRY

    # Compare as a multiset on purpose: a set would collapse a tool listed twice in
    # the response and still match the registry, so the duplicate would pass unnoticed
    # (R3-duplicate-tools). The payload follows the YAML whitelist order, not the
    # registry order, so sorting is what keeps the comparison order-independent.
    assert sorted(tool["name"] for tool in payload["tools"]) == sorted(TOOL_REGISTRY)
    assert {tool["name"] for tool in payload["tools"]} >= {
        "kb.retrieve", "memory.read", "memory.search", "memory.write", "automation.create_rule"
    }
    assert next(tool for tool in payload["tools"] if tool["name"] == "kb.retrieve")["read_only"] is True
    assert next(tool for tool in payload["tools"] if tool["name"] == "automation.create_rule")["write"] is True
    assert payload["personas"] == ["personas/assistant.md"]
    assert set(payload["prompts"]) == {
        "prompts/assistant_plan.md", "prompts/assistant_respond.md"
    }
    assert payload["kb_available"] is True
    assert payload["memory_available"] is True


def test_capabilities_has_no_mutation_route(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client, "adm", "adm-pass")

    response = client.post("/panel/api/assistant/capabilities", json={})

    assert response.status_code == 405
