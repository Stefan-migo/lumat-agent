"""OpenSpec contract tests for the WU-1 project registry foundation."""

import inspect as stdlib_inspect

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import (
    InternalChatThread,
    Memory,
    MemoryObservation,
    MemoryType,
    ObservationType,
    Project,
    ProjectAlias,
    ProjectAudit,
    User,
)
from app.services import projects

pytestmark = pytest.mark.spec("PROJECTS-WU1")


@pytest.fixture(autouse=True)
def clean_projects(migrated_db):
    with SessionLocal() as session:
        session.query(ProjectAlias).delete()
        session.query(ProjectAudit).delete()
        session.query(Project).filter(Project.slug != "default").delete()
        if session.scalar(select(Project).where(Project.slug == "default")) is None:
            session.add(Project(
                slug="default",
                name="Default",
                purpose="Default project namespace",
                purpose_embedding=[0.0] * 384,
            ))
        session.commit()
    yield


def test_project_registry_migration_and_models(migrated_db, admin_conn):
    tables = {
        row[0]
        for row in admin_conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ).fetchall()
    }
    assert {"projects", "project_aliases", "project_audit"} <= tables

    for table in ("projects", "project_aliases", "memories"):
        columns = {
            row[0]
            for row in admin_conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = %s",
                (table,),
            ).fetchall()
        }
        assert "owner_id" in columns

    constraints = {
        row[0]
        for row in admin_conn.execute(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'memories'::regclass"
        ).fetchall()
    }
    assert "uq_memories_owner_project_scope_entity_topic" in constraints

    column = admin_conn.execute(
        """
        SELECT format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        WHERE c.relname = 'projects' AND a.attname = 'purpose_embedding'
        """
    ).fetchone()
    assert column == ("vector(384)",)

    default = admin_conn.execute(
        "SELECT slug, status FROM projects WHERE slug = 'default'"
    ).fetchone()
    assert default == ("default", "active")

    with SessionLocal() as session:
        assert {Project.__tablename__, ProjectAlias.__tablename__, ProjectAudit.__tablename__} <= set(
            inspect(session.bind).get_table_names()
        )
        assert Memory.__table__.constraints
        unique = next(
            c
            for c in Memory.__table__.constraints
            if {column.name for column in c.columns}
            == {"owner_id", "proyecto", "scope", "entity_id", "topic_key"}
        )
        assert {column.name for column in unique.columns} == {
            "owner_id", "proyecto", "scope", "entity_id", "topic_key"
        }


def test_project_slug_is_normalized_and_unique(migrated_db):
    with SessionLocal() as session:
        projects.create(session, "  Field Ops  ", "Field Ops", "Coordinate field operations")
        session.commit()
        with pytest.raises(IntegrityError):
            projects.create(session, "field-ops", "Other", "A different purpose")
            session.commit()
        session.rollback()


def test_find_prefers_exact_slug_without_embedding(migrated_db, monkeypatch):
    with SessionLocal() as session:
        project = projects.create(session, "billing", "Billing", "Invoices and payments")
        session.commit()
        monkeypatch.setattr(projects.kb, "embed_texts", lambda _: pytest.fail("must not embed"))
        result = projects.find(session, "BILLING")
        assert result.project.id == project.id
        assert result.candidates == []
        assert result.requires_approval is False


def test_projects_with_same_slug_are_scoped_by_owner(migrated_db, monkeypatch):
    with SessionLocal() as session:
        first = User(username="first-owner", password_hash="test")
        second = User(username="second-owner", password_hash="test")
        session.add_all([first, second])
        session.flush()
        monkeypatch.setattr(projects.kb, "embed_texts", lambda _: ([[1.0] + [0.0] * 383], 0))
        a = projects.create(session, "shared-name", "First", "first distinct purpose", owner_id=first.id)
        b = projects.create(session, "shared-name", "Second", "second distinct purpose", owner_id=second.id)
        session.flush()

        assert a.owner_id == first.id
        assert b.owner_id == second.id
        assert projects.find(session, "shared-name", owner_id=first.id).project.id == a.id
        assert projects.find(session, "shared-name", owner_id=second.id).project.id == b.id
        assert projects.find(session, "shared-name").project is None


def test_aliases_allow_same_name_for_different_owners(migrated_db, monkeypatch):
    with SessionLocal() as session:
        owners = [
            User(username="alias-owner-a", password_hash="test"),
            User(username="alias-owner-b", password_hash="test"),
        ]
        session.add_all(owners)
        session.flush()
        monkeypatch.setattr(projects.kb, "embed_texts", lambda _: ([[1.0] + [0.0] * 383], 0))
        for owner, slug in zip(owners, ("alias-a", "alias-b")):
            project = projects.create(session, slug, slug, f"purpose {slug}", owner_id=owner.id)
            session.flush()
            session.add(ProjectAlias(project_id=project.id, owner_id=owner.id, alias="shared alias"))
        session.flush()
        assert session.query(ProjectAlias).filter_by(alias="shared alias").count() == 2


def test_agent_context_and_merge_require_project_owner(migrated_db, monkeypatch):
    with SessionLocal() as session:
        owner = User(username="merge-owner", password_hash="test")
        other_owner = User(username="other-merge-owner", password_hash="test")
        session.add_all([owner, other_owner])
        session.flush()
        monkeypatch.setattr(projects.kb, "embed_texts", lambda _: ([[1.0] + [0.0] * 383], 0))
        source = projects.create(session, "owned-source", "Source", "source purpose", owner_id=owner.id)
        target = projects.create(session, "owned-target", "Target", "target purpose", owner_id=owner.id)
        stranger_project = projects.create(session, "stranger", "Stranger", "stranger purpose", owner_id=other_owner.id)
        session.flush()

        assert projects.agent_context(session, "owned-source", owner.id).owner_id == owner.id
        with pytest.raises(ValueError, match="not an active project"):
            projects.agent_context(session, "owned-source", other_owner.id)
        with pytest.raises(ValueError):
            projects.merge(session, source, stranger_project, owner_id=owner.id)
        projects.merge(session, source, target, owner_id=owner.id)
        assert target.status.value == "active"


def test_find_returns_at_most_three_close_candidates_and_requires_approval(
    migrated_db, monkeypatch
):
    with SessionLocal() as session:
        monkeypatch.setattr(
            projects.kb,
            "embed_texts",
            lambda _: ([[1.0] + [0.0] * 383], 0),
        )
        for slug in ("alpha", "beta", "gamma", "delta"):
            projects.create(session, slug, slug.title(), "shared operations purpose")
        session.commit()
        result = projects.find(session, "shared purpose")
        assert len(result.candidates) == 3
        assert result.project is None
        assert result.requires_approval is True
        assert all(candidate.similarity >= 0.85 for candidate in result.candidates)


def test_create_deduplicates_normalized_purpose_as_ambiguous(migrated_db, monkeypatch):
    with SessionLocal() as session:
        projects.create(session, "existing", "Existing", "  Shared Purpose ")
        session.commit()
        monkeypatch.setattr(
            projects.kb,
            "embed_texts",
            lambda _: ([[1.0] + [0.0] * 383], 0),
        )
        result = projects.create(
            session, "new-project", "New Project", "shared purpose"
        )
        assert result.project is None
        assert result.requires_approval is True
        assert result.candidates[0].slug == "existing"


def test_create_deduplicates_semantically_similar_purpose_as_ambiguous(
    migrated_db, monkeypatch
):
    with SessionLocal() as session:
        monkeypatch.setattr(
            projects.kb,
            "embed_texts",
            lambda _: ([[1.0] + [0.0] * 383], 0),
        )
        projects.create(session, "existing", "Existing", "Coordinate field operations")
        session.commit()

        result = projects.create(
            session, "new-project", "New Project", "Organize field operations"
        )

        assert result.project is None
        assert result.requires_approval is True
        assert [candidate.slug for candidate in result.candidates] == ["existing"]
        assert session.scalar(select(Project).where(Project.slug == "new-project")) is None


def test_create_has_no_ambiguity_bypass_parameter():
    assert "allow_ambiguous" not in stdlib_inspect.signature(projects.create).parameters


def _project(session, slug: str) -> Project:
    row = projects.create(session, slug, slug.title(), f"Purpose for {slug}")
    session.flush()
    return row


def test_rename_records_name_alias_and_audit_without_changing_slug(migrated_db):
    with SessionLocal() as session:
        project = _project(session, "field-ops")
        session.commit()
        project = session.get(Project, project.id)
        renamed = projects.rename(session, project, "Field Operations", actor="agent")
        session.commit()

        assert renamed.slug == "field-ops"
        alias = session.query(ProjectAlias).filter_by(project_id=project.id).one()
        assert alias.alias == "field operations"
        audit = session.query(ProjectAudit).filter_by(project_id=project.id).one()
        assert audit.action == "rename"
        assert audit.after["name"] == "Field Operations"


def test_rename_validation_failure_leaves_registry_and_artifacts_unchanged(migrated_db, monkeypatch):
    with SessionLocal() as session:
        project = _project(session, "field-ops")
        project_id = project.id
        session.commit()
        project = session.get(Project, project_id)
        monkeypatch.setattr(projects, "_validate_namespace", lambda *args: (_ for _ in ()).throw(ValueError("migration failed")))
        with pytest.raises(ValueError, match="migration failed"):
            projects.rename(session, project, "Broken", actor="agent")
        session.rollback()
        assert session.get(Project, project_id).name == "Field-Ops"
        assert session.query(ProjectAlias).count() == 0


def test_rename_and_merge_reject_active_runs_before_changes(migrated_db):
    with SessionLocal() as session:
        user = User(username="lifecycle", password_hash="test")
        session.add(user)
        session.flush()
        source = _project(session, "source")
        target = _project(session, "target")
        thread = InternalChatThread(user_id=user.id, active_run_id="run-1", assistant_state={"sdb": {"proyecto": "source"}})
        session.add(thread)
        session.flush()
        with pytest.raises(ValueError, match="active SDB run"):
            projects.rename(session, source, "Source Renamed", actor="agent")
        with pytest.raises(ValueError, match="active SDB run"):
            projects.merge(session, source, target, actor="agent")
        assert session.get(Project, source.id).name == "Source"
        assert session.get(Project, target.id).status.value == "active"


def test_merge_is_atomic_on_byte_different_composite_key(migrated_db, fake_embedder):
    with SessionLocal() as session:
        source, target = _project(session, "source"), _project(session, "target")
        for project, content in ((source, "source bytes"), (target, "target bytes")):
            from app.services import tukulpan
            tukulpan.upsert(session, proyecto=project.slug, scope="panel", entity_id="thread:1", topic_key="same", tipo=MemoryType.DECISION, titulo="same", contenido=content, authorization=projects.agent_context(session, project.slug))
        with pytest.raises(ValueError, match="conflict"):
            projects.merge(session, source, target, actor="agent")
        assert session.query(Memory).filter_by(proyecto="source").count() == 1
        assert session.get(Project, source.id).status.value == "active"


def test_merge_preserves_target_and_records_source_alias(migrated_db, fake_embedder):
    with SessionLocal() as session:
        source, target = _project(session, "source"), _project(session, "target")
        from app.services import tukulpan
        tukulpan.upsert(session, proyecto="source", scope="panel", entity_id="thread:1", topic_key="one", tipo=MemoryType.DECISION, titulo="one", contenido="one", authorization=projects.agent_context(session, "source"))
        projects.merge(session, source, target, actor="agent")
        session.commit()
        assert session.get(Project, target.id).status.value == "active"
        assert session.get(Project, source.id).status.value == "archived"
        assert session.query(ProjectAlias).filter_by(project_id=target.id, alias="source").count() == 1
        assert session.query(Memory).filter_by(proyecto="target", topic_key="one").count() == 1


def test_merge_deduplicates_hash_collisions_and_repoints_observations(migrated_db, fake_embedder):
    with SessionLocal() as session:
        source, target = _project(session, "source"), _project(session, "target")
        from app.services import tukulpan

        source_memory = tukulpan.upsert(
            session,
            proyecto="source",
            scope="panel",
            entity_id="thread:1",
            topic_key="source-topic",
            tipo=MemoryType.DECISION,
            titulo="Shared fact",
            contenido="The customer prefers afternoon visits.",
            authorization=projects.agent_context(session, "source"),
        )
        target_memory = tukulpan.upsert(
            session,
            proyecto="target",
            scope="panel",
            entity_id="thread:1",
            topic_key="target-topic",
            tipo=MemoryType.DECISION,
            titulo="Shared fact",
            contenido="  THE customer   prefers afternoon visits. ",
            authorization=projects.agent_context(session, "target"),
        )
        observation = MemoryObservation(
            memory_id=source_memory.id,
            scope="panel",
            entity_id="thread:1",
            tipo=ObservationType.OPORTUNIDAD,
            detalle={"source": "merge"},
        )
        session.add(observation)
        session.flush()

        projects.merge(session, source, target, actor="agent")
        session.commit()

        assert session.query(Memory).filter(Memory.proyecto.in_(("source", "target"))).count() == 1
        surviving = session.query(Memory).one()
        assert surviving.id == target_memory.id
        assert surviving.duplicate_count == 2
        assert session.query(MemoryObservation).one().memory_id == surviving.id


def test_default_project_cannot_be_merged_away(migrated_db):
    with SessionLocal() as session:
        default = session.scalar(select(Project).where(Project.slug == "default"))
        other = _project(session, "other")
        with pytest.raises(ValueError, match="default"):
            projects.merge(session, default, other, actor="agent")


def test_archive_records_lifecycle_audit(migrated_db):
    with SessionLocal() as session:
        project = _project(session, "retired")
        projects.archive(session, project, actor="agent")
        session.commit()
        assert session.get(Project, project.id).status.value == "archived"
        audit = session.query(ProjectAudit).filter_by(project_id=project.id).one()
        assert audit.action == "archive"
