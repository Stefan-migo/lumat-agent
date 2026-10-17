"""WU-E/T1 — SMTP configuration + credential storage (S1, S2).

Runs against the migrated pgvector test DB (conftest DATABASE_URL).
"""

import base64

from sqlalchemy import select

from app.config import get_settings
from app.db import session_scope
from app.models import AuditLog, PanelSecret
from app.services import settings as settings_service
from app.services import smtp


ENCRYPTION_KEY = base64.urlsafe_b64encode(b"0" * 32).decode()


def _enable_encryption(monkeypatch) -> None:
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", ENCRYPTION_KEY)
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# S1 — settings keys
# ---------------------------------------------------------------------------


def test_new_smtp_keys_are_registered_with_safe_defaults():
    assert settings_service.SETTINGS_DEFAULTS["notify.smtp_port"] == 25
    assert settings_service.SETTINGS_DEFAULTS["notify.smtp_user"] == ""
    assert settings_service.SETTINGS_DEFAULTS["notify.smtp_tls"] == "none"
    # The pre-existing keys keep their values (no behavior change).
    assert settings_service.SETTINGS_DEFAULTS["notify.smtp_host"] == "localhost"
    assert settings_service.SETTINGS_DEFAULTS["notify.smtp_from"] == "notificaciones@lumat.cl"


def test_config_defaults_match_todays_behavior():
    """No configured values => exactly what the hardcoded localhost path did."""
    with session_scope() as session:
        config = smtp.load_smtp_config(session)

    assert config.host == "localhost"
    assert config.port == 25
    assert config.from_address == "notificaciones@lumat.cl"
    assert config.user == ""
    assert config.password is None
    assert config.tls == "none"


def test_config_reads_stored_values(monkeypatch):
    _enable_encryption(monkeypatch)
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_host", "mail.lumat.cl")
        settings_service.set_setting(session, "notify.smtp_port", 587)
        settings_service.set_setting(session, "notify.smtp_from", "sistema@lumat.cl")
        settings_service.set_setting(session, "notify.smtp_user", "sistema@lumat.cl")
        settings_service.set_setting(session, "notify.smtp_tls", "starttls")
        smtp.set_smtp_password(session, "hunter2-secret", actor="test-admin")

    with session_scope() as session:
        config = smtp.load_smtp_config(session)

    assert config.host == "mail.lumat.cl"
    assert config.port == 587
    assert config.from_address == "sistema@lumat.cl"
    assert config.user == "sistema@lumat.cl"
    assert config.password == "hunter2-secret"
    assert config.tls == "starttls"


def test_invalid_port_and_tls_fall_back_to_defaults():
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_port", 70000)
        settings_service.set_setting(session, "notify.smtp_tls", "ssl2")
    with session_scope() as session:
        config = smtp.load_smtp_config(session)
    assert config.port == 25
    assert config.tls == "none"

    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_port", 0)
    with session_scope() as session:
        assert smtp.load_smtp_config(session).port == 25

    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_port", "not-a-number")
    with session_scope() as session:
        assert smtp.load_smtp_config(session).port == 25


# ---------------------------------------------------------------------------
# S2 — encrypted password secret
# ---------------------------------------------------------------------------


def test_password_is_stored_encrypted_masked_and_audited(monkeypatch):
    _enable_encryption(monkeypatch)
    secret = "smtp-pass-9876"

    with session_scope() as session:
        smtp.set_smtp_password(session, secret, actor="test-admin", updated_by=None)

    with session_scope() as session:
        row = session.scalar(select(PanelSecret).where(PanelSecret.key == smtp.SMTP_PASSWORD_KEY))
        assert row is not None
        assert secret not in repr((row.ciphertext, row.nonce))
        status = smtp.smtp_password_status(session)
        assert status == {"configured": True, "masked": "…9876"}
        assert secret not in repr(status)
        assert smtp.get_smtp_password(session) == secret

    with session_scope() as session:
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "smtp_password.set"))
        assert audit is not None
        assert secret not in repr((audit.before, audit.after, audit.entity_id))
        assert audit.entity_id == smtp.SMTP_PASSWORD_KEY


def test_password_clear_removes_the_secret_and_audits(monkeypatch):
    _enable_encryption(monkeypatch)
    with session_scope() as session:
        smtp.set_smtp_password(session, "smtp-pass-9876", actor="test-admin")

    with session_scope() as session:
        smtp.clear_smtp_password(session, actor="test-admin")

    with session_scope() as session:
        assert smtp.get_smtp_password(session) is None
        assert smtp.smtp_password_status(session) == {"configured": False, "masked": ""}
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "smtp_password.clear"))
        assert audit is not None


def test_short_password_masks_without_leaking(monkeypatch):
    _enable_encryption(monkeypatch)
    with session_scope() as session:
        smtp.set_smtp_password(session, "ab", actor="test-admin")
    with session_scope() as session:
        assert smtp.smtp_password_status(session) == {"configured": True, "masked": "…"}
