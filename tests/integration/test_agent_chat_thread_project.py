"""Real-database coverage for chat-thread project binding by authenticated owner.

This test needs the migrated, truncated test database. It lives in the
integration suite on purpose: `tests/unit/conftest.py` makes `migrated_db` and
`clean_db` no-ops because that suite is DB-free, so a DB-backed test placed
under `tests/unit/` only passed when another suite happened to migrate first.
"""

from uuid import uuid4

import pytest

from app.db import SessionLocal
from app.models import InternalChatThread, Project, User
from app.services import agent_chat


def test_same_slug_projects_bind_and_resolve_by_authenticated_owner(fake_embedder, migrated_db):
    with SessionLocal() as session:
        users = [User(username=f"chat-owner-{uuid4().hex}", password_hash="test") for _ in range(2)]
        session.add_all(users)
        session.flush()
        slug = f"shared-{uuid4().hex[:8]}"
        projects = [Project(
            slug=slug, name=f"Project {index}", purpose=f"Purpose {index}",
            purpose_embedding=[0.0] * 384, owner_id=user.id,
        ) for index, user in enumerate(users)]
        foreign_only = Project(
            slug=f"foreign-{uuid4().hex[:8]}", name="Foreign project", purpose="Foreign purpose",
            purpose_embedding=[0.0] * 384, owner_id=users[1].id,
        )
        session.add_all([*projects, foreign_only])
        session.flush()

        with pytest.raises(ValueError):
            agent_chat.create_thread(session, users[0], proyecto=foreign_only.slug)
        threads = [agent_chat.create_thread(session, user, proyecto=slug) for user in users]
        assert [agent_chat._thread_project_authorization(session, thread).owner_id for thread in threads] == [
            user.id for user in users
        ]
        with pytest.raises(ValueError):
            agent_chat._thread_project_authorization(
                session, InternalChatThread(user_id=users[0].id, proyecto=slug + "-missing")
            )
