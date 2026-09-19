"""Read-only assistant capability contract (AC-10)."""

from __future__ import annotations


def _login(client, username: str, password: str) -> None:
    response = client.post("/panel/api/login", json={"username": username, "password": password})
    assert response.status_code == 200


def test_capabilities_requires_admin_json(client):
    response = client.get("/panel/api/assistant/capabilities")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_capabilities_denies_operator_without_configuration(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")

    response = client.get("/panel/api/assistant/capabilities")

    assert response.status_code == 403
    assert response.json() == {"detail": "admin role required"}
    assert "automation.create_rule" not in response.text


def test_admin_capabilities_reflect_real_tools_and_runtime_config(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client, "adm", "adm-pass")

    response = client.get("/panel/api/assistant/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["tools"]) == 19
    assert {tool["name"] for tool in payload["tools"]} >= {
        "kb.retrieve", "memory.read", "memory.search", "memory.write", "automation.create_rule"
    }
    assert next(tool for tool in payload["tools"] if tool["name"] == "kb.retrieve")["read_only"] is True
    assert next(tool for tool in payload["tools"] if tool["name"] == "automation.create_rule")["write"] is True
    assert payload["personas"] == ["personas/assistant.md"]
    assert set(payload["prompts"]) == {
        "prompts/assistant_plan.md", "prompts/assistant_respond.md", "prompts/assistant_classify.md"
    }
    assert payload["kb_available"] is True
    assert payload["memory_available"] is True


def test_capabilities_has_no_mutation_route(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client, "adm", "adm-pass")

    response = client.post("/panel/api/assistant/capabilities", json={})

    assert response.status_code == 405
