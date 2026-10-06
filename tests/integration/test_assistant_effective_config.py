"""Effective project configuration is shared by planner and response prompts."""

import json
import re
from types import SimpleNamespace
from uuid import uuid4

from app.chat.assistant import nodes
from app.chat.assistant.graph import run_assistant
from app.chat.assistant.tools.registry import execute_tool
from app.db import SessionLocal
from app.models import DocumentFormat, InternalChatThread, Project, User
from app.services import kb
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


def test_assistant_kb_reads_global_and_current_project_only(fake_embedder):
    query = "assistant project knowledge isolation"
    with SessionLocal() as session:
        user = User(username=f"assistant-kb-{uuid4().hex[:10]}", password_hash="pass", role="admin")
        session.add(user)
        session.flush()
        projects = [
            Project(
                owner_id=user.id, slug=f"assistant-kb-{suffix}-{uuid4().hex[:6]}",
                name=suffix, purpose="Assistant KB test", purpose_embedding=[0.0] * 384,
            )
            for suffix in ("current", "other")
        ]
        session.add_all(projects)
        session.flush()
        thread = InternalChatThread(user_id=user.id, proyecto=projects[0].slug)
        session.add(thread)
        session.flush()
        doc_ids = [
            kb.ingest_document(session, title=title, fmt=DocumentFormat.MD, content=query.encode(), project_id=project_id).id
            for title, project_id in (("Global", None), ("Current", projects[0].id), ("Other", projects[1].id))
        ]
        session.flush()

        assembled = nodes.assemble_context_node({
            "session": session,
            "thread_id": thread.id,
            "actor_role": "admin",
        })
        preanswer = nodes.retrieve_kb({
            "session": session,
            "content": query,
            "effective": assembled["effective"],
        })
        tool_result = execute_tool(
            session, "kb.retrieve", {"query": query},
            project_id=assembled["effective"]["project_id"], role="admin",
        )

    expected = set(doc_ids[:2])
    assert assembled["effective"]["project_id"] == projects[0].id
    assert {chunk["document_id"] for chunk in preanswer["kb_chunks"]} == expected
    assert {chunk["document_id"] for chunk in tool_result["result"]} == expected
