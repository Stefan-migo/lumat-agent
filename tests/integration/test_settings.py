"""T4.1.1 integration tests — settings KV service (D5 storage; SS-1..5; SH-5).

Scenarios mapped from tasks.md T4.1.1 + specs settings-scope-limits:

- read: stored value wins; known-but-unset key -> built-in default
  (`meta_pricing`, SS-4 reference cost); unknown key -> None (or caller default)
- write: `set_setting` UPSERTs a row and records an audit entry on every change
  (SH-5: who/what/when) — first write audits before=None
- update: a second write updates in place (still one row) and appends a new
  audit entry with before/after
- `updated_by` persists the acting panel user id (FK -> users)

Runs against the migrated pgvector test DB (conftest DATABASE_URL).
"""

import psycopg
import pytest
from sqlalchemy import func, select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, Settings  # noqa: E402
from app.services import settings  # noqa: E402

ADMIN_DB_URL = "postgresql://lumat:lumat@localhost:5432/lumat"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset settings, audit_log and users before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE audit_log, settings, users RESTART IDENTITY CASCADE"
        )
    yield


def _count_settings() -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count(Settings.key)))


def _count_audit() -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count(AuditLog.id)))


def _insert_user(username: str = "admin1") -> int:
    """Create a panel user via admin connection; returns its id."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        return conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
            (username, "bcrypt-placeholder"),
        ).fetchone()[0]


# ---------------------------------------------------------------------------
# Read behavior
# ---------------------------------------------------------------------------


def test_read_returns_stored_value():
    with SessionLocal() as session:
        settings.set_setting(session, "custom_key", {"enabled": True}, actor="admin1")
        session.commit()
    with SessionLocal() as session:
        assert settings.get_setting(session, "custom_key") == {"enabled": True}


def test_read_default_fallback_for_known_key():
    """meta_pricing is a known key: unset rows fall back to the built-in default."""
    with SessionLocal() as session:
        assert settings.get_setting(session, "meta_pricing") == {
            "service_message_cost": 0.01
        }
    assert _count_settings() == 0  # default never materializes a row


def test_read_unknown_key_returns_none():
    with SessionLocal() as session:
        assert settings.get_setting(session, "no_such_key") is None


def test_read_unknown_key_uses_caller_default():
    with SessionLocal() as session:
        assert settings.get_setting(session, "no_such_key", default={"x": 1}) == {
            "x": 1
        }


# ---------------------------------------------------------------------------
# Write behavior
# ---------------------------------------------------------------------------


def test_set_creates_row_and_audits_change():
    with SessionLocal() as session:
        row = settings.set_setting(
            session, "emergency_contacts", {"phone": "+56900000000"}, actor="admin1"
        )
        session.commit()
        assert row.key == "emergency_contacts"
        assert row.updated_by is None  # system/panel write without user id
    assert _count_settings() == 1
    with SessionLocal() as session:
        entry = session.scalar(select(AuditLog).order_by(AuditLog.id.desc()))
        assert entry is not None
        assert entry.actor == "admin1"
        assert entry.action == "settings.change"
        assert entry.entity == "settings"
        assert entry.entity_id == "emergency_contacts"
        assert entry.before is None  # first write has no prior value
        assert entry.after == {"value": {"phone": "+56900000000"}}


def test_set_update_upserts_in_place():
    with SessionLocal() as session:
        settings.set_setting(session, "tone", {"greeting": "Hola"}, actor="admin1")
        settings.set_setting(session, "tone", {"greeting": "Hola!"}, actor="admin1")
        session.commit()
    assert _count_settings() == 1  # update, not a second row
    assert _count_audit() == 2  # one audit entry per write
    with SessionLocal() as session:
        row = session.get(Settings, "tone")
        assert row.value == {"greeting": "Hola!"}
        entries = list(
            session.scalars(select(AuditLog).order_by(AuditLog.id))
        )
        assert entries[0].before is None
        assert entries[0].after == {"value": {"greeting": "Hola"}}
        assert entries[1].before == {"value": {"greeting": "Hola"}}
        assert entries[1].after == {"value": {"greeting": "Hola!"}}


def test_set_records_updated_by_user():
    user_id = _insert_user("operador1")
    with SessionLocal() as session:
        settings.set_setting(
            session, "tone", {"greeting": "Hola"}, actor="operador1",
            updated_by=user_id,
        )
        session.commit()
    with SessionLocal() as session:
        row = session.get(Settings, "tone")
        assert row.updated_by == user_id
