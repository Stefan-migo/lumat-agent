"""T4.3 integration tests — emergency owner/technician notification (EM-4).

Scenarios mapped 1:1 from
openspec/changes/hito-1-setup-whatsapp/specs/emergency-detection/spec.md:

- EM-4 "Notification sent": a strong emergency hit sends the WhatsApp
  utility template `emergency_alert` to the configured owner/technician
  number (customer phone, location when known, context) — Meta mocked via
  respx; the case is flagged + notification audited (SH-5)
- EM-4 email fallback: when WhatsApp fails (Meta error / template not
  approved) a plain-text email goes to `notify.owner_email` via stdlib
  smtplib — smtplib.SMTP is patched, never a real SMTP server
- The notification NEVER blocks the safety reply (EM-3): total failure
  audits `notification.failed` and the chat reply still lands
- Settings defaults (notify.owner_email / notify.owner_whatsapp /
  notify.smtp_host / notify.smtp_from) registered per SETTINGS_DEFAULTS

Part 1 (service): direct calls against the migrated pgvector test DB.
Part 2 (graph): full-graph strong hit fires the notification automatically.
"""

import json
from datetime import datetime, timedelta, timezone
from email import message_from_string
from typing import Callable

import httpx
import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation  # noqa: E402
from app.chat.state import get_or_create_conversation  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AuditLog,
    Case,
    Conversation,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services import notify  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from app.services.settings import (  # noqa: E402
    DEFAULT_OWNER_EMAIL,
    DEFAULT_OWNER_WHATSAPP,
    DEFAULT_SMTP_FROM,
    DEFAULT_SMTP_HOST,
    SETTINGS_DEFAULTS,
)
from app.webhook import ingest  # noqa: E402

ADMIN_DB_URL = "postgresql://lumat:lumat@localhost:5432/lumat"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat + settings tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


# ---------------------------------------------------------------------------
# SMTP fakes — tests MUST never reach a real SMTP server (stdlib smtplib).
# ---------------------------------------------------------------------------


def _capturing_smtp(sent_emails: list) -> Callable:
    """Return an smtplib.SMTP replacement recording (from, tos, msg) tuples."""

    def factory(*args, **kwargs):
        class _Fake:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def sendmail(self, from_addr, to_addrs, msg):
                sent_emails.append((from_addr, to_addrs, msg))

        return _Fake()

    return factory


def _failing_smtp(*args, **kwargs):
    raise OSError("SMTP connection refused")


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_case(**overrides) -> tuple[int, int, int]:
    """Seed customer + conversation + emergency case; returns (case, customer, conv)."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        case = Case(
            conversation_id=conv.id,
            customer_id=customer.id,
            status="escalado",
            emergency=True,
            **overrides,
        )
        session.add(case)
        session.commit()
        return case.id, customer.id, conv.id


def _audit_rows() -> list[AuditLog]:
    with SessionLocal() as session:
        return list(session.scalars(select(AuditLog).order_by(AuditLog.id)))


def _template_body(request: httpx.Request) -> dict:
    return json.loads(request.content)


def _start_conversation() -> int:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        return conv.id


def _turn(conv_id: int, text: str, wamid: str) -> list[str]:
    """Append an inbound message and run the graph (replies persisted)."""
    with SessionLocal() as session:
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        message = session.scalars(
            select(Message).where(Message.conversation_id == conv_id, Message.wamid == wamid)
        ).one()
        replies = run_conversation(session, message)
        session.commit()
        return replies


# ---------------------------------------------------------------------------
# Part 1 — settings defaults (SETTINGS_DEFAULTS pattern, T4.1)
# ---------------------------------------------------------------------------


def test_notify_settings_defaults_registered():
    # unconfigured keys must behave out of the box (SS "works first run")
    assert SETTINGS_DEFAULTS["notify.owner_email"] == DEFAULT_OWNER_EMAIL
    assert SETTINGS_DEFAULTS["notify.owner_whatsapp"] == DEFAULT_OWNER_WHATSAPP
    assert SETTINGS_DEFAULTS["notify.smtp_host"] == DEFAULT_SMTP_HOST
    assert SETTINGS_DEFAULTS["notify.smtp_from"] == DEFAULT_SMTP_FROM


# ---------------------------------------------------------------------------
# Part 1 — send_emergency_notification (EM-4 primary channel: WhatsApp template)
# ---------------------------------------------------------------------------


def _call_notification(case_id: int, context: str, **conv_data) -> dict:
    """Run send_emergency_notification against the seeded case; returns result."""
    with SessionLocal() as session:
        from app.models import Customer

        case = session.get(Case, case_id)
        customer = session.get(Customer, case.customer_id)
        conv = session.get(Conversation, case.conversation_id)
        if conv_data:
            conv.captured_data = conv_data
        result = notify.send_emergency_notification(
            session, case, customer, conv, context=context
        )
        session.commit()
        return result


def test_template_goes_to_owner_with_phone_and_context(mock_meta_send):
    case_id, _, _ = _seed_case()
    result = _call_notification(case_id, "hay una fuga de gas en el calefont")

    assert result["channel"] == "whatsapp"
    assert result["wamid"] == "wamid.out123"

    body = _template_body(mock_meta_send.calls.last.request)
    assert body["to"] == DEFAULT_OWNER_WHATSAPP
    assert body["type"] == "template"
    assert body["template"]["name"] == "emergency_alert"
    assert body["template"]["language"]["code"] == "es"
    params = [p["text"] for p in body["template"]["components"][0]["parameters"]]
    assert params[0] == "+56912345678"  # customer phone
    assert params[2] == "hay una fuga de gas en el calefont"  # context

    # EM-4: case notified + SH-5 audit with channel/recipient/cost
    with SessionLocal() as session:
        case = session.get(Case, case_id)
        assert case.notified_at is not None
    sent = [a for a in _audit_rows() if a.action == "notification.sent"]
    assert len(sent) == 1
    assert sent[0].entity == "case"
    assert sent[0].after["channel"] == "whatsapp"
    assert sent[0].after["recipient"] == DEFAULT_OWNER_WHATSAPP
    assert sent[0].after["wamid"] == "wamid.out123"
    assert sent[0].after["cost_meta"] == pytest.approx(0.01)


def test_template_includes_location_from_captured_data(mock_meta_send):
    case_id, _, _ = _seed_case()
    _call_notification(case_id, "hay olor a gas", address="Av. Siempre Viva 123, Providencia")

    body = _template_body(mock_meta_send.calls.last.request)
    params = [p["text"] for p in body["template"]["components"][0]["parameters"]]
    assert params[1] == "Av. Siempre Viva 123, Providencia"


# ---------------------------------------------------------------------------
# Part 1 — email fallback (EM-4; stdlib smtplib, no new dependency)
# ---------------------------------------------------------------------------


def test_email_fallback_on_whatsapp_failure(mock_meta_send, monkeypatch):
    """Meta error / missing template approval -> email to notify.owner_email."""
    mock_meta_send.routes[0].mock(
        return_value=httpx.Response(400, json={"error": {"code": 100, "message": "invalid"}})
    )
    sent_emails: list = []
    monkeypatch.setattr("app.services.notify.smtplib.SMTP", _capturing_smtp(sent_emails))

    case_id, _, _ = _seed_case()
    result = _call_notification(case_id, "hay una fuga de gas en el calefont")

    assert result["channel"] == "email"
    assert result["wamid"] is None
    assert len(sent_emails) == 1
    assert sent_emails[0][1] == [DEFAULT_OWNER_EMAIL]
    # EmailMessage base64-encodes non-ASCII payloads — decode before asserting
    body_text = message_from_string(sent_emails[0][2]).get_payload(decode=True).decode()
    assert "fuga de gas" in body_text
    assert DEFAULT_OWNER_WHATSAPP in body_text  # customer phone in the body

    with SessionLocal() as session:
        assert session.get(Case, case_id).notified_at is not None
    actions = {a.action for a in _audit_rows()}
    assert "notification.failed" in actions  # whatsapp attempt
    assert "notification.sent" in actions  # email fallback delivered
    email_audit = next(a for a in _audit_rows() if a.action == "notification.sent")
    assert email_audit.after["channel"] == "email"
    assert email_audit.after["recipient"] == DEFAULT_OWNER_EMAIL


def test_both_channels_fail_audits_and_never_raises(mock_meta_send, monkeypatch):
    """Total failure: audited (SH-5), notified_at stays None, no exception."""
    mock_meta_send.routes[0].mock(
        return_value=httpx.Response(400, json={"error": {"code": 100, "message": "invalid"}})
    )
    monkeypatch.setattr("app.services.notify.smtplib.SMTP", _failing_smtp)

    case_id, _, _ = _seed_case()
    result = _call_notification(case_id, "hay un incendio en la casa")

    assert result["channel"] == "none"
    with SessionLocal() as session:
        assert session.get(Case, case_id).notified_at is None
    failed = [a for a in _audit_rows() if a.action == "notification.failed"]
    assert len(failed) == 2  # whatsapp attempt + email attempt
    assert {a.after["channel"] for a in failed} == {"whatsapp", "email"}


# ---------------------------------------------------------------------------
# Part 2 — graph: the emergency node fires the notification on a strong hit
# ---------------------------------------------------------------------------


def test_emergency_node_fires_notification_on_strong_hit(mock_openai_chat, mock_meta_send):
    conv_id = _start_conversation()
    replies = _turn(conv_id, "hay una fuga de gas en el calefont", "wamid.nfy1")

    # EM-3: the safety protocol is still the chat reply
    assert any("INSTRUCCIONES DE SEGURIDAD" in r for r in replies)
    # EM-4: the owner/technician got the WhatsApp template (separate channel)
    template_calls = [
        c for c in mock_meta_send.calls if _template_body(c.request)["type"] == "template"
    ]
    assert len(template_calls) == 1
    assert _template_body(template_calls[0].request)["to"] == DEFAULT_OWNER_WHATSAPP

    with SessionLocal() as session:
        case = session.scalar(select(Case).where(Case.conversation_id == conv_id))
        assert case.notified_at is not None
    sent = [a for a in _audit_rows() if a.action == "notification.sent"]
    assert len(sent) == 1
    assert sent[0].after["channel"] == "whatsapp"


def test_notification_failure_never_blocks_safety_reply(mock_openai_chat, mock_meta_send, monkeypatch):
    """EM-3: reply regardless — notification failures are logged, never blocking."""
    mock_meta_send.routes[0].mock(
        return_value=httpx.Response(400, json={"error": {"code": 100, "message": "invalid"}})
    )
    monkeypatch.setattr("app.services.notify.smtplib.SMTP", _failing_smtp)

    conv_id = _start_conversation()
    replies = _turn(conv_id, "hay una fuga de gas en el calefont", "wamid.nfy2")

    assert any("INSTRUCCIONES DE SEGURIDAD" in r for r in replies)
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        assert conv.state.value == "human"
        case = session.scalar(select(Case).where(Case.conversation_id == conv_id))
        assert case.emergency is True
        assert case.notified_at is None  # nothing delivered -> retry allowed
    failed = [a for a in _audit_rows() if a.action == "notification.failed"]
    assert len(failed) == 2


# ---------------------------------------------------------------------------
# Part 3 — ack via reply keyword (T4.3.2; EM-4 "Notification acknowledged")
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["ok", "listo", "recibido", "gracias", "OK", "Ok, gracias", "gracias!", "recibido, ok"],
)
def test_is_ack_message_true(text):
    assert notify.is_ack_message(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "ok pero no funciona",
        "no gracias",
        "gracias por tu ayuda",
        "hola",
        "sí",
        "",
        "revisa mi calefont",
    ],
)
def test_is_ack_message_false(text):
    assert notify.is_ack_message(text) is False


def test_acknowledge_records_ack_on_case():
    case_id, _, conv_id = _seed_case()
    with SessionLocal() as session:
        acked = notify.acknowledge_emergency_if_ack(session, conv_id, "ok gracias")
        session.commit()
        assert acked is True
        case = session.get(Case, case_id)
        assert case.acknowledged_at is not None
        assert case.ack_by == "customer_reply"

    ack_audit = [a for a in _audit_rows() if a.action == "case.acknowledged"]
    assert len(ack_audit) == 1
    assert ack_audit[0].entity == "case"
    assert ack_audit[0].after["ack_by"] == "customer_reply"
    assert ack_audit[0].after["keyword"] == "ok gracias"


def test_ack_ignored_when_already_acknowledged():
    case_id, _, conv_id = _seed_case(
        acknowledged_at=datetime.now(timezone.utc), ack_by="panel"
    )
    with SessionLocal() as session:
        assert notify.acknowledge_emergency_if_ack(session, conv_id, "ok") is False
        session.commit()
    assert len([a for a in _audit_rows() if a.action == "case.acknowledged"]) == 0


def test_ack_ignored_without_emergency_case():
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        conv_id = conv.id
    with SessionLocal() as session:
        assert notify.acknowledge_emergency_if_ack(session, conv_id, "ok") is False
        session.commit()
    assert len([a for a in _audit_rows() if a.action == "case.acknowledged"]) == 0


def test_ack_hooked_in_ingest_process_message(mock_meta_send):
    """The ack check lives in the webhook ingest flow (process_message)."""
    case_id, _, conv_id = _seed_case()
    with SessionLocal() as session:
        session.get(Conversation, conv_id).captured_data = {"_pending": "name"}
        session.commit()
    with SessionLocal() as session:
        session.add(
            Message(
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="ok",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        message = session.scalars(
            select(Message)
            .where(Message.conversation_id == conv_id, Message.direction == MessageDirection.INBOUND)
        ).one()
        ingest.process_message(session, message)
        session.commit()
        case = session.get(Case, case_id)
        assert case.acknowledged_at is not None
        assert case.ack_by == "customer_reply"
    assert len([a for a in _audit_rows() if a.action == "case.acknowledged"]) == 1


# ---------------------------------------------------------------------------
# Part 4 — reminder escalation: unacked > 15 min, reminder email max 2 (T4.3.2)
# ---------------------------------------------------------------------------


def test_reminder_sent_after_15min_and_capped(monkeypatch):
    sent_emails: list = []
    monkeypatch.setattr("app.services.notify.smtplib.SMTP", _capturing_smtp(sent_emails))

    old = datetime.now(timezone.utc) - timedelta(minutes=20)
    case_id, _, _ = _seed_case(notified_at=old)

    with SessionLocal() as session:
        assert notify.send_pending_emergency_reminders(session) == 1
        session.commit()
        assert session.get(Case, case_id).reminder_count == 1
    assert len(sent_emails) == 1
    assert sent_emails[0][1] == [DEFAULT_OWNER_EMAIL]

    with SessionLocal() as session:
        assert notify.send_pending_emergency_reminders(session) == 1
        session.commit()
    with SessionLocal() as session:
        # capped at MAX_REMINDERS — the third pass sends nothing
        assert notify.send_pending_emergency_reminders(session) == 0
        session.commit()
        assert session.get(Case, case_id).reminder_count == 2

    reminders = [a for a in _audit_rows() if a.action == "notification.reminder_sent"]
    assert len(reminders) == 2
    assert {r.after["recipient"] for r in reminders} == {DEFAULT_OWNER_EMAIL}


def test_reminder_skips_fresh_acked_and_capped_cases(monkeypatch):
    sent_emails: list = []
    monkeypatch.setattr("app.services.notify.smtplib.SMTP", _capturing_smtp(sent_emails))

    now = datetime.now(timezone.utc)
    _seed_case(notified_at=now - timedelta(minutes=5))  # too fresh
    _seed_case(
        notified_at=now - timedelta(minutes=20),
        acknowledged_at=now,
        ack_by="customer_reply",
    )  # already acked
    _seed_case(notified_at=now - timedelta(minutes=20), reminder_count=2)  # capped

    with SessionLocal() as session:
        assert notify.send_pending_emergency_reminders(session) == 0
        session.commit()
    assert sent_emails == []


def test_sweep_received_triggers_reminders(monkeypatch):
    """Reminder sweep runs inside the existing webhook sweep (no scheduler)."""
    sent_emails: list = []
    monkeypatch.setattr("app.services.notify.smtplib.SMTP", _capturing_smtp(sent_emails))

    case_id, _, _ = _seed_case(
        notified_at=datetime.now(timezone.utc) - timedelta(minutes=20)
    )
    ingest.sweep_received()  # no received messages; the reminder pass still runs

    with SessionLocal() as session:
        assert session.get(Case, case_id).reminder_count == 1
    assert len(sent_emails) == 1
