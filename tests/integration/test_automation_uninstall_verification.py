"""Verifier regression probes for the automation-uninstall work unit."""
import psycopg
import pytest
from sqlalchemy import select
from _testdb import admin_database_url

from app.db import SessionLocal
from app.models import AuditLog, AutomationExecution, AutomationInstallation, AutomationRule
from app.services.automation_installations import RecipeAlreadyInstalled, install, uninstall
from app.services.events import publish_event

A = "appointment_confirmation"
B = "appointment_no_show"
PARAMS = {"channel": "whatsapp"}


def _install(session, recipe_id, enabled=False):
    return install(session, recipe_id, dict(PARAMS), actor="admin", enabled=enabled)


def test_isolation_and_dependency_order(migrated_db):
    with SessionLocal() as session:
        a, b = _install(session, A), _install(session, B)
        rule_a = session.scalar(select(AutomationRule).where(AutomationRule.installation_id == a.id))
        rule_b = session.scalar(select(AutomationRule).where(AutomationRule.installation_id == b.id))
        event = publish_event(session, event_type="case.created", entity_type="case", entity_id="1", payload={}, dedupe_key="probe:evt")
        session.add_all([
            AutomationExecution(rule_id=rule_a.id, event_id=event.id, execution_key="probe:a", outcome="enqueued"),
            AutomationExecution(rule_id=rule_b.id, event_id=event.id, execution_key="probe:b", outcome="enqueued"),
        ])
        session.flush()
        a_id, b_id, rule_a_id, rule_b_id = a.id, b.id, rule_a.id, rule_b.id
        uninstall(session, a, actor="admin")
        session.flush()
        assert session.get(AutomationInstallation, a_id) is None
        assert session.scalar(select(AutomationRule).where(AutomationRule.id == rule_a_id)) is None
        assert session.scalars(select(AutomationExecution).where(AutomationExecution.rule_id == rule_a_id)).all() == []
        assert session.get(AutomationInstallation, b_id) is not None
        assert session.scalar(select(AutomationRule).where(AutomationRule.id == rule_b_id)) is not None
        survivors = session.scalars(select(AutomationExecution).where(AutomationExecution.rule_id == rule_b_id)).all()
        assert len(survivors) == 1 and survivors[0].execution_key == "probe:b"
        assert len(session.scalars(select(AuditLog).where(AuditLog.action == "automation.installation.delete")).all()) == 1
        session.commit()


def test_disabled_blocks_reinstall_until_uninstalled(migrated_db):
    with SessionLocal() as session:
        inst = _install(session, A, enabled=False)
        assert inst.enabled is False
        session.commit()
        inst_id = inst.id
    with SessionLocal() as session:
        with pytest.raises(RecipeAlreadyInstalled):
            _install(session, A)
        session.rollback()
    with SessionLocal() as session:
        inst = session.get(AutomationInstallation, inst_id)
        assert inst is not None and inst.enabled is False
        uninstall(session, inst, actor="admin")
        session.commit()
    with SessionLocal() as session:
        assert _install(session, A).id != inst_id
        session.commit()


def test_migration_057_grants_delete_to_app(migrated_db):
    with psycopg.connect(admin_database_url(), autocommit=True) as conn:
        assert conn.execute("SELECT 1 FROM schema_migrations WHERE version='057_grant_automation_installation_delete'").fetchone() == (1,)
        assert conn.execute("SELECT has_table_privilege('app','automation_installations','DELETE')").fetchone() == (True,)
        privs = {r[0] for r in conn.execute(
            "SELECT privilege_type FROM information_schema.role_table_grants WHERE grantee='app' AND table_name='automation_installations'"
        ).fetchall()}
    assert {"SELECT", "INSERT", "UPDATE", "DELETE"} <= privs, privs


def test_atomic_rollback_restores_everything(migrated_db, monkeypatch):
    import app.services.automation_installations as ai
    with SessionLocal() as session:
        a = _install(session, A)
        rule = session.scalar(select(AutomationRule).where(AutomationRule.installation_id == a.id))
        event = publish_event(session, event_type="case.created", entity_type="case", entity_id="9", payload={}, dedupe_key="probe:rollback")
        session.add(AutomationExecution(rule_id=rule.id, event_id=event.id, execution_key="probe:rb", outcome="enqueued"))
        session.flush()
        a_id, rule_id = a.id, rule.id
        session.commit()
    with SessionLocal() as session:
        inst = session.get(AutomationInstallation, a_id)
        monkeypatch.setattr(ai, "record_audit", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("audit sink down")))
        with pytest.raises(RuntimeError):
            uninstall(session, inst, actor="admin")
        session.rollback()
    with SessionLocal() as session:
        assert session.get(AutomationInstallation, a_id) is not None
        assert session.scalar(select(AutomationRule).where(AutomationRule.id == rule_id)) is not None
        assert len(session.scalars(select(AutomationExecution).where(AutomationExecution.rule_id == rule_id)).all()) == 1
