"""Independent verifier pins for the WU-E transport (S3, S4).

Committed from the verifier's probe set so the handshake contract it exercised
stays guarded (WU-E/T6).
"""

import base64
import email
import email.policy

import psycopg
import pytest

from _testdb import admin_database_url
from app.config import get_settings
from app.db import session_scope
from app.services import notifications, notify, settings as settings_service, smtp

_KEY = base64.urlsafe_b64encode(b"0" * 32).decode()


@pytest.fixture(autouse=True)
def _clean(migrated_db):
    with psycopg.connect(admin_database_url(), autocommit=True) as conn:
        conn.execute("TRUNCATE settings, panel_secrets, audit_log RESTART IDENTITY CASCADE")
    yield


def _key(monkeypatch):
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", _KEY)
    get_settings.cache_clear()


def _fake(record, ctor="SMTP"):
    class Fake:
        def __init__(self, host, port=None):
            record.setdefault("ctor", []).append(ctor)
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
            record["env_from"] = from_addr
            record["to"] = to_addrs
            record["msg"] = msg

    return Fake


def test_defaults_are_localhost_25_no_auth(monkeypatch):
    record = {}
    monkeypatch.setattr(notify.smtplib, "SMTP", _fake(record))
    with session_scope() as session:
        notify.send_email(session, "d@example.test", "Asunto", "Cuerpo")
    assert (record["host"], record["port"], record["ctor"], record["env_from"]) == (
        "localhost",
        25,
        ["SMTP"],
        settings_service.DEFAULT_SMTP_FROM,
    )
    assert "starttls" not in record and "login" not in record


def test_invalid_stored_tls_and_port_do_not_crash(monkeypatch):
    record = {}
    monkeypatch.setattr(notify.smtplib, "SMTP", _fake(record))
    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", _fake({}, "SMTP_SSL"))
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_tls", "bogus")
        settings_service.set_setting(session, "notify.smtp_port", "nope")
    with session_scope() as session:
        config = smtp.load_smtp_config(session)
        assert (config.tls, config.port) == ("none", 25)
        notify.send_email(session, "d@example.test", "S", "C")
    assert record["ctor"] == ["SMTP"] and "starttls" not in record


def test_user_without_password_no_login(monkeypatch):
    record = {}
    monkeypatch.setattr(notify.smtplib, "SMTP", _fake(record))
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_user", "u@example.test")
    with session_scope() as session:
        notify.send_email(session, "d@example.test", "S", "C")
    assert "login" not in record


def test_ssl_and_starttls_modes(monkeypatch):
    _key(monkeypatch)
    start, ssl_record = {}, {}
    monkeypatch.setattr(notify.smtplib, "SMTP", _fake(start))
    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", _fake(ssl_record, "SMTP_SSL"))
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_tls", "starttls")
    with session_scope() as session:
        notify.send_email(session, "d@example.test", "S", "C")
    assert start["starttls"] is True
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_tls", "ssl")
    with session_scope() as session:
        notify.send_email(session, "d@example.test", "S", "C")
    assert ssl_record["ctor"] == ["SMTP_SSL"] and "starttls" not in ssl_record


def test_generic_sender_delegates(monkeypatch):
    record = {}
    monkeypatch.setattr(notify.smtplib, "SMTP", _fake(record))
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_host", "mail.lumat.cl")
        settings_service.set_setting(session, "notify.smtp_port", 2526)
    with session_scope() as session:
        notifications.send_email(session, "dest@example.test", "Cuerpo")
    assert (record["host"], record["port"]) == ("mail.lumat.cl", 2526)
    parsed = email.message_from_string(record["msg"], policy=email.policy.default)
    assert parsed["Subject"] == "Notificación Lumat"
