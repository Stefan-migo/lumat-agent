"""Effective project configuration is shared by planner and response prompts."""

import json
import re
from types import SimpleNamespace
from uuid import uuid4

from app.chat.assistant import nodes
from app.chat.assistant.graph import run_assistant
from app.db import SessionLocal
from app.models import InternalChatThread, Project, User
from app.services.prompts import load_assistant_config
from app.services.users import hash_password


def test_run_assistant_uses_effective_project_config(monkeypatch):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"kind": "respond", "summary": "Hello", "requires_approval": False})))],
            usage=None,
        )

    monkeypatch.setattr(nodes, "_assistant_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    suffix = uuid4().hex[:10]
    with SessionLocal() as session:
        user = User(username=f"effective-config-{suffix}", password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
        project = Project(
            owner_id=user.id,
            slug=f"effective-{suffix}",
            name="Effective config test",
            purpose="Test assistant configuration",
            purpose_embedding=[0.0] * 384,
            config={"instructions": "Use the project-specific vocabulary."},
        )
        session.add(project)
        session.flush()
        threads = [
            InternalChatThread(user_id=user.id, proyecto=project.slug),
            InternalChatThread(
                user_id=user.id,
                proyecto=project.slug,
                assistant_state={"tool_policy": {"opt_in_enabled": ["web.search"]}},
            ),
        ]
        session.add_all(threads)
        session.flush()

        for thread in threads:
            run_assistant(
                thread_id=thread.id,
                user_id=user.id,
                content="hello",
                run_id=f"effective-{thread.id}",
                session=session,
                actor_role="admin",
            )

    planner_calls = calls
    assert len(planner_calls) == 2
    catalogs = [
        json.loads(re.search(r"<available_tools>(.*?)</available_tools>", call["messages"][-1]["content"], re.DOTALL).group(1))
        for call in planner_calls
    ]
    assert "web.search" not in {tool["name"] for tool in catalogs[0]}
    assert "web.search" in {tool["name"] for tool in catalogs[1]}
    system_message = planner_calls[0]["messages"][0]["content"]
    assert system_message.startswith(
        f"{load_assistant_config().persona}\n\nUse the project-specific vocabulary."
    )
