"""WU-E/T2 — the generic email sender uses the configured transport (S3).

`notifications.send_email` must stop hardcoding `smtplib.SMTP("localhost")` and
delegate to `notify.send_email`; this pins that seam so the two implementations
cannot diverge again.
"""

import email
import email.policy

from app.db import session_scope
from app.services import notifications, notify, settings as settings_service


def _recording_smtp(record: dict):
    class _Fake:
        def __init__(self, host, port):
            record["host"] = host
            record["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def sendmail(self, from_addr, to_addrs, msg):
            record["from"] = from_addr
            record["to"] = to_addrs
            record["msg"] = msg

    return _Fake


def test_notifications_send_email_uses_the_configured_transport(monkeypatch):
    """The generic operation sender must no longer hardcode localhost (S3)."""
    record: dict = {}
    monkeypatch.setattr(notify.smtplib, "SMTP", _recording_smtp(record))
    with session_scope() as session:
        settings_service.set_setting(session, "notify.smtp_host", "mail.lumat.cl")
        settings_service.set_setting(session, "notify.smtp_port", 2525)

    with session_scope() as session:
        notifications.send_email(session, "dest@example.test", "Cuerpo")

    assert record["host"] == "mail.lumat.cl"
    assert record["port"] == 2525
    assert record["from"] == settings_service.DEFAULT_SMTP_FROM
    parsed = email.message_from_string(record["msg"], policy=email.policy.default)
    assert parsed["Subject"] == "Notificación Lumat"
    assert parsed["To"] == "dest@example.test"
    # Pre-WU-E this path sent a bare From; unifying the transport must not
    # change the header a recipient sees (verifier blocker, WU-E/T6).
    assert parsed["From"] == settings_service.DEFAULT_SMTP_FROM
