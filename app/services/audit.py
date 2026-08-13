"""Append-only audit service (SH-5).

Every auditable action is recorded via `record_audit` (actor, action, entity,
before/after snapshots) into the `audit_log` table. Append-only is enforced at
two levels: the service only exposes INSERT + read (no update/delete), and the
DB grants give the `app` role INSERT+SELECT only on `audit_log` (see
db/migrations/001_init.sql). Admin reads use `list_audit_entries`.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog


def record_audit(
    session: Session,
    *,
    actor: str,
    action: str,
    entity: str,
    entity_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    """Insert one append-only audit entry and return it (caller commits)."""
    entry = AuditLog(
        actor=actor,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before=before,
        after=after,
    )
    session.add(entry)
    return entry


def list_audit_entries(session: Session, limit: int = 100) -> Sequence[AuditLog]:
    """Admin read: newest entries first (SH-5 — admin-only at the app layer)."""
    return list(
        session.scalars(
            select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
        )
    )
