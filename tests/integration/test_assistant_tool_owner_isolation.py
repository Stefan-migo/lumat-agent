"""Real-database coverage for assistant project and memory ownership."""

from sqlalchemy import select
import pytest

from app.db import SessionLocal
from app.chat.assistant.approval import issue_approval
from app.models import InternalChatThread, Project, User
from app.services import agent_chat
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.models import MemoryType, MemoryVisibility
from app.services import tukulpan


def test_sdb_project_creation_is_bound_to_thread_owner():
    plan = {
        "phase": "EXECUTE",
        "spec": {"sha256": "owner-isolation"},
        "tasks": [{
            "id": "create-project",
            "scope": {"proyecto": "default"},
            "summary": "Create project",
            "verifiable_output": "Project exists",
            "tool": "project.create",
            "arguments": {
                "slug": "field-ops",
                "name": "Field Ops",
                "purpose": "Field operations management",
            },
            "decision": {"create_distinct": True},
        }, {
            "id": "list-projects",
            "scope": {"proyecto": "field-ops"},
            "summary": "Use the created project",
            "verifiable_output": "Project is listed",
            "tool": "project.list",
            "arguments": {},
        }],
    }
    approval = issue_approval({"sdb": plan})
    approval["status"] = "consumed"

    with SessionLocal() as session:
        user = User(username="owner-a", password_hash="test", role="admin")
        session.add(user)
        session.flush()
        thread = InternalChatThread(user_id=user.id, current_plan={"sdb": plan})
        thread.assistant_state = {"sdb": {"checkpoints": []}, "approval": approval}
        session.add(thread)
        session.flush()

        result = agent_chat._run_sdb_tasks(session, thread, "owner-run")
        project = session.scalar(select(Project).where(Project.slug == "field-ops"))

        assert project is not None and project.owner_id == thread.user_id
        assert result["status"] == "completed", result["results"]
        assert [item["status"] for item in result["results"]] == ["completed", "completed"], [(item["status"], item.get("error")) for item in result["results"]]


def test_registry_scopes_projects_and_memory_to_authenticated_owner(fake_embedder):
    with SessionLocal() as session:
        user_a, user_b = [
            User(username=f"owner-{suffix}", password_hash="test", role="admin")
            for suffix in ("a", "b")
        ]
        session.add_all((user_a, user_b))
        session.flush()
        thread_a = InternalChatThread(user_id=user_a.id)
        thread_b = InternalChatThread(user_id=user_b.id)
        session.add_all((thread_a, thread_b))
        session.flush()
        for user in (user_a, user_b):
            session.add(Project(
                slug="field-ops", name="Field Ops", purpose="Field operations",
                purpose_embedding=[0.0] * 384, owner_id=user.id,
            ))
        session.flush()
        authorization_a = agent_chat.projects.agent_context(session, "field-ops", owner_id=user_a.id)
        private = tukulpan.upsert(
            session, authorization=authorization_a, proyecto="field-ops", scope="agent",
            entity_id="agent:field-ops", topic_key="agent:private", tipo=MemoryType.DISCOVERY,
            titulo="Private", contenido="Owner A secret", visibility=MemoryVisibility.GLOBAL,
        )
        business = tukulpan.upsert(
            session, proyecto="default", scope="customer", entity_id="customer:9",
            topic_key="business:shared", tipo=MemoryType.DISCOVERY, titulo="Business",
            contenido="Business memory", visibility=MemoryVisibility.THREAD,
        )
        session.flush()

        listed = execute_tool(session, "project.list", {}, owner_id=user_b.id)
        assert {row["owner_id"] for row in listed["result"] if row["slug"] == "field-ops"} == {user_b.id}

        own = execute_tool(
            session, "memory.read", {"scope": "own"}, trusted_thread_id=thread_b.id,
            owner_id=user_b.id, proyecto="field-ops",
        )
        assert private.id not in {row["id"] for row in own["result"]}
        with pytest.raises(ToolValidationError, match="not owned by the assistant"):
            execute_tool(
                session, "memory.update", {"id": private.id, "titulo": "Changed"},
                trusted_thread_id=thread_b.id, owner_id=user_b.id, proyecto="field-ops",
            )
        with pytest.raises(ToolValidationError, match="not owned by the assistant"):
            execute_tool(
                session, "memory.delete", {"id": private.id}, trusted_thread_id=thread_b.id,
                owner_id=user_b.id, proyecto="field-ops",
            )

        shared = execute_tool(
            session, "memory.read", {"scope": "customer", "entity_id": "customer:9"},
            trusted_thread_id=thread_b.id, owner_id=user_b.id,
        )
        assert business.id in {row["id"] for row in shared["result"]}
