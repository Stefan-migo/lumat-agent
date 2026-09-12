"""OpenSpec contract tests for the WU-1 project registry foundation."""

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import Memory, Project, ProjectAlias, ProjectAudit
from app.services import projects

pytestmark = pytest.mark.spec("PROJECTS-WU1")


@pytest.fixture(autouse=True)
def clean_projects(migrated_db):
    with SessionLocal() as session:
        session.query(ProjectAlias).delete()
        session.query(ProjectAudit).delete()
        session.query(Project).filter(Project.slug != "default").delete()
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
        unique = next(c for c in Memory.__table__.constraints if c.name is None)
        assert {column.name for column in unique.columns} == {
            "proyecto", "scope", "entity_id", "topic_key"
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
            session, "new-project", "New Project", "shared purpose", allow_ambiguous=False
        )
        assert result.project is None
        assert result.requires_approval is True
        assert result.candidates[0].slug == "existing"
