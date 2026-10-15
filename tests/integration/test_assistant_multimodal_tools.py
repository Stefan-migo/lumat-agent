"""The harness injects tool-returned images into the model calls (S5, decision B)."""

from types import SimpleNamespace

from app.db import SessionLocal
from app.models import AssistantAttachment, User
from app.services.agent_chat import create_thread
from app.services.users import hash_password

_PLANNER_RESPONSE = (
    '{"kind":"respond","arguments":{},"summary":"Done.","requires_approval":false}'
)


def _user(username: str, role: str = "admin") -> int:
    with SessionLocal() as session:
        user = User(username=username, password_hash=hash_password("pass"), role=role)
        session.add(user)
        session.flush()
        user_id = user.id
        session.commit()
    return user_id


def _thread_with_image(owner_id: int, tmp_path) -> tuple[int, int]:
    source = tmp_path / "shot.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\n-image-bytes")
    with SessionLocal() as session:
        user = session.get(User, owner_id)
        thread = create_thread(session, user)
        row = AssistantAttachment(
            thread_id=thread.id, filename="shot.png", kind="image", content_type="image/png",
            size=source.stat().st_size, sha256="e" * 64, stored_path=str(source),
        )
        session.add(row)
        session.flush()
        thread_id, attachment_id = thread.id, row.id
        session.commit()
    return thread_id, attachment_id


def _state(session, thread_id: int, tool_results) -> dict:
    return {
        "content": "What is in this image?",
        "context": {"items": []},
        "session": session,
        "thread_id": thread_id,
        "tool_results": tool_results,
    }


def _planner_client(captured):
    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=_PLANNER_RESPONSE))])

    return lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def _monkeypatch_planner(monkeypatch):
    monkeypatch.setattr(
        "app.services.prompts.load_assistant_config",
        lambda **_kwargs: SimpleNamespace(prompts={"plan": "{{user_input}}"}, tools_whitelist=[], skills=(), persona="persona"),
    )


def test_planner_message_includes_a_tool_image_part(monkeypatch, tmp_path):
    from app.chat.assistant.nodes import plan_llm

    thread_id, attachment_id = _thread_with_image(_user("mm-planner"), tmp_path)
    captured = {}
    _monkeypatch_planner(monkeypatch)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", _planner_client(captured))

    with SessionLocal() as session:
        plan_llm(_state(session, thread_id, [
            {"tool": "view_image", "status": "completed", "result": {"image": {"source": "thread", "id": attachment_id}}},
        ]))

    content = captured["messages"][1]["content"]
    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "What is in this image?"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_planner_message_stays_text_only_without_a_tool_image(monkeypatch, tmp_path):
    from app.chat.assistant.nodes import plan_llm

    thread_id, _ = _thread_with_image(_user("mm-planner-plain"), tmp_path)
    captured = {}
    _monkeypatch_planner(monkeypatch)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", _planner_client(captured))

    with SessionLocal() as session:
        plan_llm(_state(session, thread_id, [
            {"tool": "memory.read", "status": "completed", "result": {"rows": []}},
        ]))

    assert isinstance(captured["messages"][1]["content"], str)


def test_responder_message_includes_a_tool_image_part(monkeypatch, tmp_path):
    import httpx
    import respx

    from app.chat.assistant.nodes import execute
    from app.config import get_settings

    thread_id, attachment_id = _thread_with_image(_user("mm-responder"), tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    get_settings.cache_clear()
    try:
        with respx.mock(base_url="https://openrouter.ai/api/v1") as router:
            route = router.post("/chat/completions").mock(return_value=httpx.Response(
                200, headers={"content-type": "text/event-stream"},
                content='data: {"choices":[{"delta":{"content":"Seen"}}]}\n\ndata: [DONE]\n\n',
            ))
            with SessionLocal() as session:
                state = _state(session, thread_id, [
                    {"tool": "view_image", "status": "completed",
                     "result": {"image": {"source": "thread", "id": attachment_id}}},
                ])
                state.update({
                    "run_id": "run-view-image",
                    "on_token": lambda token: None,
                    "plan": {"tool": None, "arguments": {}, "requires_approval": False},
                })
                execute(state)
                session.flush()
                session.rollback()

            assert route.called
            body = __import__("json").loads(route.calls[0].request.content)
            content = body["messages"][1]["content"]
            assert content[0]["type"] == "text"
            assert content[1]["type"] == "image_url"
            assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    finally:
        get_settings.cache_clear()
