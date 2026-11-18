"""The real chat path: an answered project approval creates the project it approved.

The reported production failure was `project create approval is missing an explicit decision` after
the operator clicked approve. The click was never the problem: the approval was consumed and the
resume refused it. These tests walk the same path -- issue, answer, consume, execute -- and pin the
outcome at both ends of it.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.chat.assistant import nodes as assistant_nodes
from app.chat.assistant.approval import ApprovalDecisionError, issue_approval
from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, Project, User
from app.services import projects
from app.services.agent_chat import approve_plan
from app.services.users import hash_password

PURPOSE = "gasfitería de emergencia"


class _Completions:
    """Only the responder may run: a resumed approval carries its own plan."""

    def __init__(self, text="Listo."):
        self.text = text
        self.stream_calls = 0

    def create(self, **kwargs):
        if not kwargs.get("stream"):
            raise AssertionError("a resumed approval must never re-plan")
        self.stream_calls += 1
        return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=self.text))])]


def _mount_client(monkeypatch):
    completions = _Completions()
    monkeypatch.setattr(
        assistant_nodes,
        "_assistant_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=completions)),
    )
    return completions


def _fixed_embedding(monkeypatch):
    monkeypatch.setattr(projects.kb, "embed_texts", lambda _texts: ([[1.0] + [0.0] * 383], 0))


def _owner(session):
    """The single owner that seeded projects and the thread both belong to."""
    user = User(username=f"decision-{uuid4().hex[:10]}", password_hash=hash_password("pass"), role="admin")
    session.add(user)
    session.flush()
    return user


def _seed(session, *, plan, approval, user=None, proyecto="default"):
    suffix = uuid4().hex[:10]
    user = user or _owner(session)
    run_id = f"decision-{suffix}"
    thread = InternalChatThread(
        user_id=user.id,
        proyecto=proyecto,
        active_run_id=run_id,
        current_plan=plan,
        assistant_state={
            "stage": "approval_pending",
            "execution_status": "pending",
            "approval": approval,
            "actor_role": "admin",
            "tool_results": [],
            "tool_steps": 0,
            "live": {"run_id": run_id, "stage": "approval_pending", "status": "approval_pending"},
        },
    )
    session.add(thread)
    session.flush()
    session.add(
        InternalChatMessage(
            thread_id=thread.id,
            author="admin",
            content="creá el proyecto E2E temporal",
            status="approval_pending",
            assistant_metadata={"run_id": run_id, "approval": approval},
        )
    )
    session.commit()
    return user, thread


def _create_plan(slug="e2e-temporal", purpose=PURPOSE):
    return {
        "kind": "tool",
        "tool": "project.create",
        "arguments": {"slug": slug, "name": "E2E temporal", "purpose": purpose},
        "summary": "Crear el proyecto E2E temporal",
        "requires_approval": True,
        "follow_up": False,
    }


def _approve(thread_id, token, **kwargs):
    """Approve and commit in its own session, exactly as the panel endpoint does.

    The endpoint's `get_db` dependency commits the request, so a test that only flushed would
    assert against a rolled-back transaction. The returned status is read before the commit
    expires the ORM instance.
    """
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        user = session.get(User, thread.user_id)
        message = approve_plan(session, thread, user, thread.active_run_id, token, **kwargs)
        status = None if message is None else message.status
        session.commit()
        return status


def _reply_message(session, thread_id, run_id):
    return session.scalar(
        select(InternalChatMessage)
        .where(
            InternalChatMessage.thread_id == thread_id,
            InternalChatMessage.author == "agent",
            InternalChatMessage.assistant_metadata["run_id"].as_string() == run_id,
        )
        .order_by(InternalChatMessage.id.desc())
    )


def test_answered_create_approval_creates_the_project(migrated_db, monkeypatch):
    """S1: the exact chain that failed in production now creates the project."""
    _mount_client(monkeypatch)
    _fixed_embedding(monkeypatch)
    plan = _create_plan()
    approval = issue_approval(plan)
    with SessionLocal() as session:
        user, thread = _seed(session, plan=plan, approval=approval)
        thread_id, token, run_id = thread.id, approval["token"], thread.active_run_id

    assert _approve(thread_id, token, decision={"create_distinct": True}) == "processed"
    with SessionLocal() as session:
        project = session.scalar(
            select(Project).where(Project.slug == "e2e-temporal", Project.owner_id == user.id)
        )
        assert project is not None
        assert project.purpose == PURPOSE
        stored = session.get(InternalChatThread, thread_id).assistant_state
        assert stored["approval"]["status"] == "consumed"
        assert stored["approval"]["project_payload"]["decision"] == {"create_distinct": True}
        reply = _reply_message(session, thread_id, run_id)
        assert reply is not None and reply.content


def test_unanswered_create_approval_consumes_nothing(migrated_db, monkeypatch):
    """S2: no decision means no consumption, no execution, and no project."""
    _mount_client(monkeypatch)
    _fixed_embedding(monkeypatch)
    plan = _create_plan()
    approval = issue_approval(plan)
    with SessionLocal() as session:
        user, thread = _seed(session, plan=plan, approval=approval)
        thread_id, token = thread.id, approval["token"]

    with pytest.raises(ApprovalDecisionError, match="project decision required"):
        _approve(thread_id, token)

    with SessionLocal() as session:
        stored = session.get(InternalChatThread, thread_id).assistant_state
        assert stored["approval"]["status"] == "pending"
        assert stored["execution_status"] == "pending"
        assert session.scalar(
            select(Project).where(Project.slug == "e2e-temporal", Project.owner_id == user.id)
        ) is None
        # The unanswered approval is still answerable: nothing was burned.
        assert stored["approval"]["project_decision"]["options"] == ["create_distinct"]


def test_created_project_is_not_duplicated_by_a_second_approval(migrated_db, monkeypatch):
    """S1, S2: a replayed token cannot create the project twice."""
    _mount_client(monkeypatch)
    _fixed_embedding(monkeypatch)
    plan = _create_plan()
    approval = issue_approval(plan)
    with SessionLocal() as session:
        user, thread = _seed(session, plan=plan, approval=approval)
        thread_id, token = thread.id, approval["token"]

    assert _approve(thread_id, token, decision={"create_distinct": True}) is not None
    assert _approve(thread_id, token, decision={"create_distinct": True}) is None

    with SessionLocal() as session:
        assert len(
            session.scalars(
                select(Project).where(Project.slug == "e2e-temporal", Project.owner_id == user.id)
            ).all()
        ) == 1


def test_duplicate_purpose_raises_the_informed_gate(migrated_db, monkeypatch):
    """S4: consent is not consent to duplicate -- the owner sees the conflict first."""
    _mount_client(monkeypatch)
    _fixed_embedding(monkeypatch)
    with SessionLocal() as session:
        owner = _owner(session)
        session.add(
            Project(slug="gasfiteria", name="Gasfitería", purpose=PURPOSE, purpose_embedding=[1.0] + [0.0] * 383, owner_id=owner.id)
        )
        session.commit()
        user_id = owner.id

    plan = _create_plan(purpose=f"  {PURPOSE} ")
    approval = issue_approval(plan)
    with SessionLocal() as session:
        user, thread = _seed(session, plan=plan, approval=approval, user=session.get(User, user_id))
        thread_id, token = thread.id, approval["token"]

    assert _approve(thread_id, token, decision={"create_distinct": True}) == "approval_pending"
    with SessionLocal() as session:
        stored = session.get(InternalChatThread, thread_id).assistant_state
        # No duplicate was created, and the owner now has an answerable question.
        assert session.scalar(
            select(Project).where(Project.slug == "e2e-temporal", Project.owner_id == user_id)
        ) is None
        envelope = stored["approval"]["project_decision"]
        assert envelope["operation"] == "create"
        assert envelope["options"] == ["selected_slug", "create_anyway"]
        assert [candidate["slug"] for candidate in envelope["candidates"]] == ["gasfiteria"]


def test_informed_gate_can_choose_the_existing_project(migrated_db, monkeypatch):
    """S4: the second answer either reuses the conflicting project or creates deliberately."""
    _mount_client(monkeypatch)
    _fixed_embedding(monkeypatch)
    with SessionLocal() as session:
        owner = _owner(session)
        session.add(
            Project(slug="gasfiteria", name="Gasfitería", purpose=PURPOSE, purpose_embedding=[1.0] + [0.0] * 383, owner_id=owner.id)
        )
        session.commit()
        user_id = owner.id

    plan = _create_plan(purpose=PURPOSE)
    first = issue_approval(plan)
    with SessionLocal() as session:
        user, thread = _seed(session, plan=plan, approval=first, user=session.get(User, user_id))
        thread_id, token = thread.id, first["token"]

    assert _approve(thread_id, token, decision={"create_distinct": True}) is not None

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        second = thread.assistant_state["approval"]
        second_token = second["token"]
        assert second["project_decision"]["options"] == ["selected_slug", "create_anyway"]

    assert _approve(thread_id, second_token, decision={"selected_slug": "gasfiteria"}) is not None

    with SessionLocal() as session:
        assert session.scalar(
            select(Project).where(Project.slug == "e2e-temporal", Project.owner_id == user_id)
        ) is None
        stored = session.get(InternalChatThread, thread_id).assistant_state
        assert stored["approval"]["status"] == "consumed"
        assert stored["approval"]["project_payload"]["decision"] == {"selected_slug": "gasfiteria"}


def test_informed_gate_can_create_a_deliberate_duplicate(migrated_db, monkeypatch):
    """S4: `create_anyway` is the owner saying, with the conflict on screen, create it."""
    _mount_client(monkeypatch)
    _fixed_embedding(monkeypatch)
    with SessionLocal() as session:
        owner = _owner(session)
        session.add(
            Project(slug="gasfiteria", name="Gasfitería", purpose=PURPOSE, purpose_embedding=[1.0] + [0.0] * 383, owner_id=owner.id)
        )
        session.commit()
        user_id = owner.id

    plan = _create_plan(purpose=PURPOSE)
    first = issue_approval(plan)
    with SessionLocal() as session:
        user, thread = _seed(session, plan=plan, approval=first, user=session.get(User, user_id))
        thread_id, token = thread.id, first["token"]

    assert _approve(thread_id, token, decision={"create_distinct": True}) is not None
    with SessionLocal() as session:
        second_token = session.get(InternalChatThread, thread_id).assistant_state["approval"]["token"]

    assert _approve(thread_id, second_token, decision={"create_anyway": True}) is not None

    with SessionLocal() as session:
        created = session.scalar(
            select(Project).where(Project.slug == "e2e-temporal", Project.owner_id == user_id)
        )
        assert created is not None
        assert created.purpose == PURPOSE


def test_a_decision_the_approval_did_not_offer_cannot_be_forced(migrated_db, monkeypatch):
    """S2: `create_anyway` skips the informed gate, so it must be unanswerable at gate one."""
    _mount_client(monkeypatch)
    _fixed_embedding(monkeypatch)
    plan = _create_plan()
    approval = issue_approval(plan)
    with SessionLocal() as session:
        user, thread = _seed(session, plan=plan, approval=approval)
        thread_id, token = thread.id, approval["token"]

    with pytest.raises(ApprovalDecisionError, match="not offered"):
        _approve(thread_id, token, decision={"create_anyway": True})

    with SessionLocal() as session:
        stored = session.get(InternalChatThread, thread_id).assistant_state
        assert stored["approval"]["status"] == "pending"
        assert session.scalar(
            select(Project).where(Project.slug == "e2e-temporal", Project.owner_id == user.id)
        ) is None
