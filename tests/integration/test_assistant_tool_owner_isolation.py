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

        cross = execute_tool(
            session, "memory.search", {"scope": "own", "query": "Owner A secret"},
            trusted_thread_id=thread_b.id, owner_id=user_b.id, proyecto="field-ops",
        )
        assert cross["result"] == []

        business_search = execute_tool(
            session, "memory.search", {"scope": "customer", "entity_id": "customer:9", "query": "Business memory"},
            trusted_thread_id=thread_b.id, owner_id=user_b.id,
        )
        assert business.id in {row["id"] for row in business_search["result"]}

        with pytest.raises(
            ToolValidationError, match="owner-scoped tool requires the authenticated owner"
        ):
            execute_tool(session, "project.list", {})


def test_two_users_with_same_slug_recall_only_their_private_memory_and_share_business_memory(fake_embedder):
    with SessionLocal() as session:
        user_a = User(username="same-slug-a", password_hash="test", role="admin")
        user_b = User(username="same-slug-b", password_hash="test", role="admin")
        stranger = User(username="same-slug-stranger", password_hash="test", role="admin")
        session.add_all((user_a, user_b, stranger))
        session.flush()
        threads = {
            user.id: InternalChatThread(user_id=user.id) for user in (user_a, user_b, stranger)
        }
        session.add_all(threads.values())
        session.flush()
        projects = [Project(
            slug="identical-slug", name="Identical", purpose="Private project",
            purpose_embedding=[0.0] * 384, owner_id=user.id,
        ) for user in (user_a, user_b, stranger)]
        session.add_all(projects)
        session.flush()
        assert {project.owner_id for project in session.scalars(
            select(Project).where(Project.slug == "identical-slug")
        )} == {user_a.id, user_b.id, stranger.id}

        private_rows = {}
        for user, content in ((user_a, "alpha private marker"), (user_b, "bravo private marker")):
            authorization = agent_chat.projects.agent_context(
                session, "identical-slug", owner_id=user.id
            )
            private_rows[user.id] = tukulpan.upsert(
                session, authorization=authorization, proyecto="identical-slug", scope="agent",
                entity_id="agent:identical-slug", topic_key="private", tipo=MemoryType.DISCOVERY,
                titulo=content, contenido=content, visibility=MemoryVisibility.GLOBAL,
            )
        business = tukulpan.upsert(
            session, proyecto="default", scope="customer", entity_id="customer:4242",
            topic_key="shared-business", tipo=MemoryType.DISCOVERY, titulo="Shared business",
            contenido="shared business marker", visibility=MemoryVisibility.THREAD,
        )
        session.flush()

        assert user_a.role == "admin" and user_b.role == "admin"
        # These cross-assertions ARE the admin non-override proof.
        for user, own_content, other_user, other_content in (
            (user_a, "alpha private marker", user_b, "bravo private marker"),
            (user_b, "bravo private marker", user_a, "alpha private marker"),
        ):
            own_read = execute_tool(
                session, "memory.read", {"scope": "own"}, trusted_thread_id=threads[user.id].id,
                owner_id=user.id, proyecto="identical-slug",
            )["result"]
            assert private_rows[user.id].id in {row["id"] for row in own_read}
            own_search = execute_tool(
                session, "memory.search", {"scope": "own", "query": own_content},
                trusted_thread_id=threads[user.id].id, owner_id=user.id, proyecto="identical-slug",
            )["result"]
            assert own_content in [row["contenido"] for row in own_search]
            cross = execute_tool(
                session, "memory.search", {"scope": "own", "query": other_content},
                trusted_thread_id=threads[user.id].id, owner_id=user.id, proyecto="identical-slug",
            )["result"]
            # Similarity search may return the caller's own nearest memory; the invariant is
            # that the other owner's row never appears.
            assert private_rows[other_user.id].id not in {row["id"] for row in cross}

            shared_read = execute_tool(
                session, "memory.read", {"scope": "customer", "entity_id": "customer:4242"},
                trusted_thread_id=threads[user.id].id, owner_id=user.id,
            )["result"]
            assert business.id in {row["id"] for row in shared_read}
            shared_search = execute_tool(
                session, "memory.search", {
                    "scope": "customer", "entity_id": "customer:4242",
                    "query": "shared business marker",
                }, trusted_thread_id=threads[user.id].id, owner_id=user.id,
            )["result"]
            assert business.id in {row["id"] for row in shared_search}

        admin_read = execute_tool(
            session, "memory.read", {"scope": "own"}, trusted_thread_id=threads[stranger.id].id,
            owner_id=stranger.id, proyecto="identical-slug",
        )["result"]
        assert admin_read == []
        for row in private_rows.values():
            admin_cross = execute_tool(
                session, "memory.search", {"scope": "own", "query": row.contenido},
                trusted_thread_id=threads[stranger.id].id, owner_id=stranger.id,
                proyecto="identical-slug",
            )["result"]
            assert row.id not in {item["id"] for item in admin_cross}
        no_project_read = execute_tool(
            session, "memory.read", {"scope": "customer", "entity_id": "customer:4242"},
            trusted_thread_id=threads[stranger.id].id, owner_id=stranger.id,
        )["result"]
        assert business.id in {row["id"] for row in no_project_read}
        no_project_search = execute_tool(
            session, "memory.search", {
                "scope": "customer", "entity_id": "customer:4242",
                "query": "shared business marker",
            }, trusted_thread_id=threads[stranger.id].id, owner_id=stranger.id,
        )["result"]
        assert business.id in {row["id"] for row in no_project_search}
