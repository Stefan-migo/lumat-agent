"""WU-E/T2 — unified SMTP transport honors host/port/TLS/auth (S3, S4).

Runs against the migrated pgvector test DB (conftest DATABASE_URL). The SMTP
fakes never reach a real server: `smtplib` lives in `app.services.notify`.
"""

import base64
import email
import email.policy

from app.config import get_settings
from app.db import session_scope
from app.services import notify, settings as settings_service, smtp


ENCRYPTION_KEY = base64.urlsafe_b64encode(b"0" * 32).decode()


def _enable_encryption(monkeypatch) -> None:
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", ENCRYPTION_KEY)
    get_settings.cache_clear()


def _recording_smtp(record: dict):
    """Return an smtplib.SMTP replacement recording the whole handshake."""

    class _Fake:
        def __init__(self, host, port):
            record["host"] = host
            record["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            record["starttls"] = True

        def login(self, user, password):
            record["login"] = (user, password)

        def sendmail(self, from_addr, to_addrs, msg):
            record["from"] = from_addr
            record["to"] = to_addrs
            record["msg"] = msg

    return _Fake


def test_default_config_opens_a_plain_connection_on_host_and_port(monkeypatch):
    """Defaults (localhost:25, no user, tls=none) keep today's observable behavior."""
    record: dict = {}
    monkeypatch.setattr(notify.smtplib, "SMTP", _recording_smtp(record))

    with session_scope() as session:
        notify.send_email(session, "dest@example.test", "Asunto", "Cuerpo")

    assert record["host"] == "localhost"
    assert record["port"] == 25
    assert "starttls" not in record
    assert "login" not in record
    assert record["to"] == ["dest@example.test"]
    assert record["from"] == settings_service.DEFAULT_SMTP_FROM
    assert "Cuerpo" in record["msg"]
    # This path always showed a display name; keep it (verifier blocker, WU-E/T6).
    parsed = email.message_from_string(record["msg"], policy=email.policy.default)
    assert parsed["From"] == f"Lumat Emergencias <{settings_service.DEFAULT_SMTP_FROM}>"


def test_configured_starttls_and_login_are_used(monkeypatch):
    _enable_encryption(monkeypatch)
    record: dict = {}
    monkeypatch.setattr(notify.smtplib, "SMTP", _recording_smtp(record))
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_host", "mail.lumat.cl")
        settings_service.set_setting(session, "notify.smtp_port", 587)
        settings_service.set_setting(session, "notify.smtp_user", "sistema@lumat.cl")
        settings_service.set_setting(session, "notify.smtp_tls", "starttls")
        settings_service.set_setting(session, "notify.smtp_from", "sistema@lumat.cl")
        smtp.set_smtp_password(session, "smtp-secret", actor="test-admin")

    with session_scope() as session:
        notify.send_email(session, "dest@example.test", "Asunto", "Cuerpo")

    assert record["host"] == "mail.lumat.cl"
    assert record["port"] == 587
    assert record["starttls"] is True
    assert record["login"] == ("sistema@lumat.cl", "smtp-secret")
    assert record["from"] == "sistema@lumat.cl"


def test_ssl_mode_uses_smtp_ssl(monkeypatch):
    record: dict = {}
    monkeypatch.setattr(notify.smtplib, "SMTP", _recording_smtp({}))
    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", _recording_smtp(record))
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_tls", "ssl")

    with session_scope() as session:
        notify.send_email(session, "dest@example.test", "Asunto", "Cuerpo")

    assert record["host"] == "localhost"
    assert record["port"] == 25
    assert "starttls" not in record


def test_user_without_password_does_not_attempt_login(monkeypatch):
    record: dict = {}
    monkeypatch.setattr(notify.smtplib, "SMTP", _recording_smtp(record))
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_user", "sistema@lumat.cl")

    with session_scope() as session:
        notify.send_email(session, "dest@example.test", "Asunto", "Cuerpo")

    assert "login" not in record
