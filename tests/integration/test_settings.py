"""T4.1 integration tests — settings KV service + semantic accessors.

Scenarios mapped from tasks.md T4.1.1/T4.1.2 + specs settings-scope-limits:

- read: stored value wins; known-but-unset key -> built-in default
  (`meta_pricing`, SS-4 reference cost); unknown key -> None (or caller default)
- write: `set_setting` UPSERTs a row and records an audit entry on every change
  (SH-5: who/what/when) — first write audits before=None
- update: a second write updates in place (still one row) and appends a new
  audit entry with before/after
- `updated_by` persists the acting panel user id (FK -> users)
- scope rules (SS-1): `get_scope_mode` -> bot_resolve by default, per-category
  `always_escalate` override, invalid stored mode falls back to default
- emergency keywords (SS-2): `get_emergency_keywords` -> EM-1 defaults until
  overridden; list round-trips through the KV store
- tone/messages (SS-5): validated tone default; `get_message` resolves built-in
  defaults and overrides for `messages.<key>`
- defaults never materialize rows; every write is audited

Runs against the migrated pgvector test DB (conftest DATABASE_URL).
"""

import psycopg
import pytest
from sqlalchemy import func, select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, Settings  # noqa: E402
from app.services import settings  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()


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


# ---------------------------------------------------------------------------
# T4.1.2 — Scope rules per category (SS-1)
# ---------------------------------------------------------------------------


def test_scope_mode_default_is_bot_resolve():
    """Unset categories resolve as bot_resolve; reading never creates a row."""
    with SessionLocal() as session:
        assert settings.get_scope_mode(session, "valores") == "bot_resolve"
        assert settings.get_scope_mode(session, "calefont") == "bot_resolve"
    assert _count_settings() == 0


def test_scope_mode_per_category_override():
    """One category set to always_escalate; other categories keep the default."""
    with SessionLocal() as session:
        settings.set_setting(
            session, "scope_rules", {"valores": "always_escalate"}, actor="admin1"
        )
        session.commit()
    with SessionLocal() as session:
        assert settings.get_scope_mode(session, "valores") == "always_escalate"
        assert settings.get_scope_mode(session, "calefont") == "bot_resolve"


def test_scope_mode_invalid_stored_mode_falls_back_to_default():
    """A stored value outside the two literals behaves as unset (SS-1)."""
    with SessionLocal() as session:
        settings.set_setting(session, "scope_rules", {"valores": "maybe"}, actor="admin1")
        session.commit()
    with SessionLocal() as session:
        assert settings.get_scope_mode(session, "valores") == "bot_resolve"


# ---------------------------------------------------------------------------
# T4.1.2 — Emergency keywords (SS-2)
# ---------------------------------------------------------------------------


def test_emergency_keywords_default_contains_em1_core():
    """EM-1 expressions present by default; no row materialized until set."""
    with SessionLocal() as session:
        keywords = settings.get_emergency_keywords(session)
    for core in (
        "olor a gas", "fuga", "humo", "incendio", "chispa", "explosión",
        "monóxido", "intoxicación", "riesgo eléctrico", "filtración severa",
    ):
        assert core in keywords
    assert _count_settings() == 0


def test_emergency_keywords_override_round_trip():
    """Owner list replaces defaults and reads back unchanged (list round-trip)."""
    with SessionLocal() as session:
        settings.set_setting(
            session, "emergency.keywords", ["fuga de gas", "chispa"], actor="admin1"
        )
        session.commit()
    with SessionLocal() as session:
        assert settings.get_emergency_keywords(session) == ["fuga de gas", "chispa"]


# ---------------------------------------------------------------------------
# T4.1.2 — Tone and standard messages (SS-5)
# ---------------------------------------------------------------------------


def test_tone_default_when_unset():
    with SessionLocal() as session:
        assert settings.get_tone(session) == "cercano"
    assert _count_settings() == 0


def test_tone_override():
    with SessionLocal() as session:
        settings.set_setting(session, "tone.style", "formal", actor="admin1")
        session.commit()
    with SessionLocal() as session:
        assert settings.get_tone(session) == "formal"


def test_invalid_tone_falls_back_to_default():
    with SessionLocal() as session:
        settings.set_setting(session, "tone.style", "warm-professional", actor="admin1")
        session.commit()
    with SessionLocal() as session:
        assert settings.get_tone(session) == settings.DEFAULT_TONE_STYLE


def test_tone_directives_are_exact_and_complete():
    assert settings.TONE_STYLES == ("cercano", "formal", "directo")
    assert settings.TONE_DIRECTIVES == {
        "cercano": "Responde con un tono cercano, amable y claro.",
        "formal": "Responde con un tono formal, profesional y preciso.",
        "directo": "Responde de forma directa, breve y clara.",
    }


def test_message_uses_builtin_default_when_unset():
    with SessionLocal() as session:
        assert settings.get_message(session, "greeting") == settings.MESSAGE_DEFAULTS["greeting"]
        assert settings.get_message(session, "cannot_answer") == settings.MESSAGE_DEFAULTS["cannot_answer"]
    assert _count_settings() == 0


def test_message_override_wins_over_caller_default():
    with SessionLocal() as session:
        settings.set_setting(
            session, "messages.greeting", "¡Hola!", actor="admin1"
        )
        settings.set_setting(
            session, "messages.cannot_answer", "Un asesor te contactará.", actor="admin1"
        )
        session.commit()
    with SessionLocal() as session:
        assert settings.get_message(session, "greeting", "Hola") == "¡Hola!"
        assert (
            settings.get_message(session, "cannot_answer", "No puedo")
            == "Un asesor te contactará."
        )
        # unset message key still falls back to the caller default
        assert settings.get_message(session, "farewell", "Chao") == "Chao"


# ---------------------------------------------------------------------------
# T4.1.2 — Audit on semantic writes (SH-5)
# ---------------------------------------------------------------------------


def test_semantic_writes_are_audited():
    """scope_rules and emergency.keywords writes each record an audit entry."""
    with SessionLocal() as session:
        settings.set_setting(
            session, "scope_rules", {"valores": "always_escalate"}, actor="admin1"
        )
        settings.set_setting(
            session, "emergency.keywords", ["chispa"], actor="admin1"
        )
        session.commit()
    assert _count_audit() == 2
    with SessionLocal() as session:
        entries = {
            e.entity_id: e for e in session.scalars(select(AuditLog))
        }
        assert entries["scope_rules"].actor == "admin1"
        assert entries["scope_rules"].action == "settings.change"
        assert entries["scope_rules"].after == {"value": {"valores": "always_escalate"}}
        assert entries["emergency.keywords"].after == {"value": ["chispa"]}
