"""Production-turn coverage for the panel assistant harness."""

import json

import httpx
import respx

from app.db import SessionLocal
from app.models import InternalChatMessage, User
from app.services.users import hash_password


def _admin(client, username: str) -> int:
    with SessionLocal() as session:
        user = User(username=username, password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
        user_id = user.id
        session.commit()
    assert client.post("/panel/api/login", json={"username": username, "password": "pass"}).status_code == 200
    return user_id


def _provider(planner: dict, captured: list[dict]):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured.append(body)
        if body.get("stream"):
            payload = json.dumps({"choices": [{"delta": {"content": "Registry response"}}]})
            return httpx.Response(200, content=f"data: {payload}\n\ndata: [DONE]\n\n")
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(planner)}, "finish_reason": "stop"}],
        })

    return handler


def test_valid_read_runs_through_production_graph_with_history_and_registry_prompt(client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    from app.config import get_settings
    get_settings.cache_clear()
    _admin(client, "production-read")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    with SessionLocal() as session:
        session.add(InternalChatMessage(thread_id=thread_id, author="admin", content="older context", status="processed"))
        session.add(InternalChatMessage(thread_id=thread_id, author="agent", content="newer context", status="processed"))
        session.commit()

    planner = {"kind": "tool", "tool": "customers.search", "arguments": {"query": "Ana"}, "summary": "Find Ana", "requires_approval": False}
    captured: list[dict] = []
    with respx.mock(base_url="https://openrouter.ai/api/v1") as router:
        router.post("/chat/completions").mock(side_effect=_provider(planner, captured))
        response = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Find Ana"})

    assert response.status_code == 201
    settled = client.get(f"/panel/api/chat/threads/{thread_id}").json()
    assert settled["messages"][0]["status"] == "processed"
    assert len(captured) == 3
    assert "older context" in captured[0]["messages"][-1]["content"]
    assert captured[0]["messages"][0]["content"].startswith("You are the Lumat internal executive operator")
    assert any("already run" in call["messages"][-1]["content"] for call in captured)
    with SessionLocal() as session:
        thread = session.get(__import__("app.models", fromlist=["InternalChatThread"]).InternalChatThread, thread_id)
        assert thread.assistant_state["planner"]["kind"] == "tool"
        assert thread.assistant_state["guardrails"]["whitelisted"] is True


def test_malformed_or_unwhitelisted_production_plan_falls_back_without_execution(client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    from app.config import get_settings
    get_settings.cache_clear()
    _admin(client, "production-invalid")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]
    planner = {"kind": "tool", "tool": "not.allowed", "arguments": {}, "summary": "Unsafe", "requires_approval": False}
    captured: list[dict] = []
    with respx.mock(base_url="https://openrouter.ai/api/v1") as router:
        router.post("/chat/completions").mock(side_effect=_provider(planner, captured))
        response = client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "Do something"})

    assert response.status_code == 201
    settled = client.get(f"/panel/api/chat/threads/{thread_id}").json()
    assert settled["messages"][0]["status"] == "processed"
    with SessionLocal() as session:
        from app.models import InternalChatThread
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["planner"]["valid"] is False
        assert thread.assistant_state["guardrails"]["decision"] == "fallback"
        assert thread.assistant_state["execution_status"] == "completed"
    # The plan is rejected, so the turn ends on the bounded summary: the planner call and the thread
    # title, and no responder call dressing the failure as an answer.
    assert len(captured) == 2
    assert captured[0]["messages"][0]["content"].startswith("You are the Lumat internal executive operator")
    assert "You are Lumat's internal operations assistant." not in captured[0]["messages"][0]["content"]
    assert settled["messages"][-1]["content"] == "No pude planificar esa solicitud de forma segura. Inténtalo nuevamente."
