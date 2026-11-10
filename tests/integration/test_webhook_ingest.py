"""T2.2 integration tests — webhook ingest pipeline (WH-3..WH-7).

Scenarios mapped 1:1 from openspec/specs/whatsapp-webhook/spec.md:

- WH-2 "Valid signature": accepted, persisted, 200
- WH-2 "Invalid signature": 403, payload dropped (nothing persisted)
- WH-3 "Slow downstream processing": 200 returned before processing completes
- WH-4 "Crash after 200 but before processing": row persisted; sweep reprocesses
- WH-5 "Meta retries a delivery": same wamid twice -> one row, processed once
- WH-6 "Unsupported event type": non-messages event -> 200, nothing persisted
- WH-6 "Error 131051 message": skipped without processing
- WH-7 "Burst of retries": dedup keeps exactly one processing pass per wamid

Plus: E.164 phone normalization, media download + retry-via-sweep, per-phone
rate limit (15 msg/min), and the startup recovery sweep.

Runs against the migrated pgvector test DB (conftest DATABASE_URL).
"""

import hashlib
import hmac
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import httpx

import psycopg
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import (  # noqa: E402
    Conversation,
    ConversationEvent,
    ConversationState,
    DeliveryStatus,
    AuditLog,
    Customer,
    CustomerState,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.settings import MESSAGE_DEFAULTS, REPLY_TEXT_DEFAULTS  # noqa: E402
from app.webhook import ingest  # noqa: E402
from app.webhook import router as router_module  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

WEBHOOK_URL = "/webhook/whatsapp"
SECRET = "test-app-secret"
SENDER = "56912345678"  # Chilean mobile, as Meta's wa_id delivers it


def _signature(body: bytes) -> str:
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _post(client: TestClient, payload: dict) -> httpx.Response:
    body = json.dumps(payload).encode()
    return client.post(
        WEBHOOK_URL, content=body, headers={"X-Hub-Signature-256": _signature(body)}
    )


def _message(wamid: str, text: str | None = None, msg: dict | None = None) -> dict:
    base = {"from": SENDER, "id": wamid, "timestamp": "1723000000"}
    if msg is not None:
        base.update(msg)
    elif text is not None:
        base.update({"type": "text", "text": {"body": text}})
    return base


def _payload(messages: list[dict], field: str = "messages", value_extra: dict | None = None) -> dict:
    value = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "15551234567", "phone_number_id": "101010"},
        "contacts": [{"profile": {"name": "Test"}, "wa_id": SENDER}],
    }
    if messages:
        value["messages"] = messages
    if value_extra:
        value.update(value_extra)
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "111", "changes": [{"field": field, "value": value}]}],
    }


def _count_messages() -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count(Message.id)))


def _statuses_payload(statuses: list[dict]) -> dict:
    return _payload([], value_extra={"statuses": statuses})


def _count_inbound() -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count(Message.id)).where(
                Message.direction == MessageDirection.INBOUND
            )
        )


def _message_rows() -> list[Message]:
    with SessionLocal() as session:
        return list(session.scalars(select(Message).order_by(Message.id)))


ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset webhook-related tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE audit_log, conversation_events, cases, messages, conversations, customers "
            "RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The in-memory rate limiter is module state; reset it per test."""
    ingest.rate_limiter.reset()
    yield


# ---------------------------------------------------------------------------
# Normalization (pure functions)
# ---------------------------------------------------------------------------


@pytest.mark.spec("CR-2")
def test_normalize_phone_e164_full_number():
    assert ingest.normalize_phone_e164("56912345678") == "+56912345678"


@pytest.mark.spec("CR-2")
def test_normalize_phone_e164_local_mobile():
    # Chilean local mobile without country code: 9XXXXXXXX -> +56 9...
    assert ingest.normalize_phone_e164("912345678") == "+56912345678"


@pytest.mark.spec("CR-2")
def test_normalize_phone_e164_with_spaces_and_plus():
    assert ingest.normalize_phone_e164("+56 9 1234 5678") == "+56912345678"


def test_normalize_message_text():
    nm = ingest.normalize_message(
        _message("wamid.1", text="Hola, necesito un gasfiter"),
        {"contacts": [{"wa_id": SENDER}]},
    )
    assert nm is not None
    assert nm.wamid == "wamid.1"
    assert nm.phone_e164 == "+56912345678"
    assert nm.msg_type == MessageType.TEXT
    assert nm.text == "Hola, necesito un gasfiter"
    assert nm.media_url is None


def test_normalize_message_media_url():
    raw = _message(
        "wamid.2",
        msg={
            "type": "image",
            "image": {"id": "img1", "mime_type": "image/jpeg", "url": "https://lookaside.example/img1.jpg"},
        },
    )
    nm = ingest.normalize_message(raw, {"contacts": [{"wa_id": SENDER}]})
    assert nm is not None
    assert nm.msg_type == MessageType.IMAGE
    assert nm.media_url == "https://lookaside.example/img1.jpg"
    assert nm.text is None


def test_normalize_message_unknown_type_maps_to_other():
    raw = _message("wamid.3", msg={"type": "vcard", "vcard": "BEGIN:VCARD"})
    nm = ingest.normalize_message(raw, {"contacts": [{"wa_id": SENDER}]})
    assert nm is not None
    assert nm.msg_type == MessageType.OTHER


def test_normalize_message_missing_wamid_returns_none():
    raw = {"from": SENDER, "type": "text", "text": {"body": "x"}}
    assert ingest.normalize_message(raw, {"contacts": [{"wa_id": SENDER}]}) is None


# ---------------------------------------------------------------------------
# WH-2 / WH-4: signature gate + persistence
# ---------------------------------------------------------------------------


def test_post_valid_message_persists_normalized_row(client, monkeypatch):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    resp = _post(client, _payload([_message("wamid.p1", text="Hola")]))
    assert resp.status_code == 200

    rows = _message_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row.wamid == "wamid.p1"
    assert row.direction == MessageDirection.INBOUND
    assert row.msg_type == MessageType.TEXT
    assert row.text == "Hola"
    assert row.status == MessageStatus.RECEIVED  # not processed yet -> 200 came first
    assert row.payload is not None  # raw webhook payload persisted (WH-4)


def test_post_invalid_signature_rejected_and_dropped(client):
    body = json.dumps(_payload([_message("wamid.x", text="x")])).encode()
    resp = client.post(
        WEBHOOK_URL,
        content=body,
        headers={"X-Hub-Signature-256": "sha256=" + "0" * 64},
    )
    assert resp.status_code == 403
    assert _count_messages() == 0


def test_post_missing_signature_rejected(client):
    resp = client.post(
        WEBHOOK_URL,
        content=json.dumps(_payload([_message("wamid.y", text="y")])).encode(),
    )
    assert resp.status_code == 403
    assert _count_messages() == 0


def test_post_dedups_customer_and_conversation_by_phone(client, monkeypatch):
    """Same sender across two messages -> one customer, one open conversation."""
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    assert _post(client, _payload([_message("wamid.c1", text="uno")])).status_code == 200
    assert _post(client, _payload([_message("wamid.c2", text="dos")])).status_code == 200

    with SessionLocal() as session:
        customers = session.scalars(select(Customer)).all()
        conversations = session.scalars(select(Conversation)).all()
    assert len(customers) == 1
    assert customers[0].phone_e164 == "+56912345678"
    assert len(conversations) == 1


@pytest.mark.parametrize(
    "closed_state",
    [CustomerState.FINALIZADO, CustomerState.POSTVENTA, CustomerState.CANCELADO],
)
def test_inbound_restarts_closed_customer_cycle_once(client, monkeypatch, closed_state):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56912345678", state=closed_state)
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.commit()
        customer_id, conversation_id = customer.id, conversation.id

    assert _post(client, _payload([_message("wamid.cycle.1", text="primero")])).status_code == 200
    assert _post(client, _payload([_message("wamid.cycle.2", text="segundo")])).status_code == 200

    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        assert customer.state == CustomerState.NUEVO
        assert session.scalar(select(func.count(Conversation.id))) == 1
        assert session.get(Conversation, conversation_id) is not None
        audits = session.scalars(
            select(AuditLog).where(
                AuditLog.action == "customer.cycle_restarted",
                AuditLog.entity_id == str(customer_id),
            )
        ).all()
        assert len(audits) == 1
        assert audits[0].entity == "customer"
        assert audits[0].actor == "system"
        assert audits[0].before == {"state": closed_state.value}
        assert audits[0].after == {"state": "nuevo"}


def test_inbound_does_not_reset_active_customer(client, monkeypatch):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56912345678", state=CustomerState.AGENDADO)
        session.add(customer)
        session.commit()
        customer_id = customer.id

    assert _post(client, _payload([_message("wamid.cycle.active", text="hola")])).status_code == 200
    with SessionLocal() as session:
        assert session.get(Customer, customer_id).state == CustomerState.AGENDADO
        assert session.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.action == "customer.cycle_restarted")
        ) == 0


# ---------------------------------------------------------------------------
# WH-3: 200 before processing
# ---------------------------------------------------------------------------


def test_200_returned_before_processing_runs(client, monkeypatch):
    """WH-3: the 200 is returned with the message still 'received' — processing
    is decoupled (BackgroundTask) and has not completed when the client gets
    the response."""
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    resp = _post(client, _payload([_message("wamid.slow", text="hola")]))
    assert resp.status_code == 200
    rows = _message_rows()
    assert len(rows) == 1
    assert rows[0].status == MessageStatus.RECEIVED


def test_background_task_processes_message_after_200(client, mock_openai_chat, mock_meta_send):
    """Real wiring: after the 200, the BackgroundTask sweep marks it processed
    and the conversation graph (T3.2) answers with an outbound reply."""
    resp = _post(client, _payload([_message("wamid.bg", text="hola")]))
    assert resp.status_code == 200
    rows = _message_rows()
    assert _count_inbound() == 1
    inbound = [r for r in rows if r.direction == MessageDirection.INBOUND]
    assert len(inbound) == 1
    assert inbound[0].status == MessageStatus.PROCESSED
    outbound = [r for r in rows if r.direction == MessageDirection.OUTBOUND]
    assert len(outbound) >= 1  # bot replies persisted (send lands in T3.6)
    assert "asistente virtual" in outbound[0].text.lower()  # greeting first


# ---------------------------------------------------------------------------
# WH-5 / WH-7: dedup by wamid + retry storm
# ---------------------------------------------------------------------------


def test_wamid_dedup_keeps_single_row(client, monkeypatch):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    payload = _payload([_message("wamid.dup", text="mismo")])
    assert _post(client, payload).status_code == 200
    assert _post(client, payload).status_code == 200
    assert _count_messages() == 1


def test_retry_storm_single_processing_pass(
    client, mock_openai_chat, mock_meta_send, monkeypatch
):
    """WH-7: a batch re-delivered 10x yields exactly one processing pass each.

    Since chat-rafagas S1 the three messages are also ONE burst, so the batch gets
    one reply instead of three: the dedup guarantee (3 unique wamids, never 30) is
    what this test pins, and the reply count follows the turn model."""
    batch = [
        _message("wamid.r1", text="a"),
        _message("wamid.r2", text="b"),
        _message("wamid.r3", text="c"),
    ]
    payload = _payload(batch)
    for _ in range(10):
        assert _post(client, payload).status_code == 200

    rows = _message_rows()
    assert _count_inbound() == 3  # dedup: 3 unique wamids, never 30
    assert all(r.status == MessageStatus.PROCESSED for r in rows)
    outbound = [r for r in rows if r.direction == MessageDirection.OUTBOUND]
    # chat-rafagas S1: the three messages are one burst, so one turn and one reply.
    # chat-rafagas S3: and being the FIRST turn, it carries the first-contact
    # greeting instead of a clarification (the three inbound rows persist before
    # the sweep, which used to make this look like turn 3).
    assert len(outbound) == 1
    assert outbound[0].text == MESSAGE_DEFAULTS["greeting_short"]


# ---------------------------------------------------------------------------
# WH-6: unsupported events + error 131051
# ---------------------------------------------------------------------------


def test_unsupported_event_type_acknowledged_not_persisted(client, monkeypatch):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    # Meta sends status updates under field="statuses", no messages key
    resp = _post(client, _payload([], field="statuses"))
    assert resp.status_code == 200
    assert _count_messages() == 0


def test_error_131051_value_skipped(client, monkeypatch):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    value_error = {"error": {"code": 131051, "title": "Unsupported message type"}}
    resp = _post(client, _payload([], value_extra=value_error))
    assert resp.status_code == 200
    assert _count_messages() == 0


def test_error_131051_on_message_object_skipped(client, monkeypatch):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    raw = _message(
        "wamid.err",
        msg={"type": "text", "text": {"body": "x"}, "errors": [{"code": 131051, "title": "unsupported"}]},
    )
    resp = _post(client, _payload([raw]))
    assert resp.status_code == 200
    assert _count_messages() == 0


# ---------------------------------------------------------------------------
# Meta delivery statuses (S1-S3)
# ---------------------------------------------------------------------------


def _outbound_message(wamid: str, delivery_status: DeliveryStatus) -> int:
    with SessionLocal() as session:
        customer = Customer(phone_e164=f"+5691234{len(wamid):04d}")
        session.add(customer)
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        message = Message(
            wamid=wamid,
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            msg_type=MessageType.TEXT,
            text="mensaje",
            status=MessageStatus.PROCESSED,
            delivery_status=delivery_status,
            meta_media_id="poisoned-mid",
        )
        session.add(message)
        session.commit()
        return message.id


def test_failed_status_updates_message_and_audits_once(client, monkeypatch):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    message_id = _outbound_message("wamid.meta-failed", DeliveryStatus.SENT)
    failed = {
        "id": "wamid.meta-failed",
        "status": "failed",
        "errors": [{"code": 131053, "title": "Media upload error", "message": "Audio rejected"}],
    }

    assert _post(client, _statuses_payload([failed])).status_code == 200
    with SessionLocal() as session:
        row = session.get(Message, message_id)
        assert row.delivery_status == DeliveryStatus.FAILED
        assert row.delivery_error == "131053: Media upload error — Audio rejected"
        # Meta answered the send with a wamid and rejected the media afterwards, so
        # the cached id is the poisoned one: a retry has to upload again.
        assert row.meta_media_id is None
        audits = session.scalars(select(AuditLog).where(
            AuditLog.action == "message.delivery_failed", AuditLog.entity_id == str(message_id)
        )).all()
        assert len(audits) == 1
        audit_count = session.scalar(select(func.count(AuditLog.id)))

    assert _post(client, _statuses_payload([failed])).status_code == 200
    with SessionLocal() as session:
        row = session.get(Message, message_id)
        assert row.delivery_status == DeliveryStatus.FAILED
        assert row.delivery_error == "131053: Media upload error — Audio rejected"
        assert session.scalar(select(func.count(AuditLog.id))) == audit_count

    assert _post(client, _statuses_payload([{
        "id": "wamid.meta-failed", "status": "sent"
    }])).status_code == 200
    with SessionLocal() as session:
        row = session.get(Message, message_id)
        assert row.delivery_status == DeliveryStatus.FAILED
        assert row.delivery_error == "131053: Media upload error — Audio rejected"
        assert session.scalar(select(func.count(AuditLog.id))) == audit_count


def test_status_for_unknown_wamid_does_not_create_rows(client, monkeypatch):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    before = _count_messages()
    assert _post(client, _statuses_payload([{
        "id": "wamid.unknown", "status": "failed", "errors": [{"code": 1}]
    }])).status_code == 200
    assert _count_messages() == before
    assert _count_messages() == 0


def test_delivered_status_marks_sent_but_not_failed(client, monkeypatch):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    sent_id = _outbound_message("wamid.delivered", DeliveryStatus.SENT)
    failed_id = _outbound_message("wamid.already-failed", DeliveryStatus.FAILED)
    assert _post(client, _statuses_payload([
        {"id": "wamid.delivered", "status": "delivered", "timestamp": "1723000000"},
        {"id": "wamid.already-failed", "status": "read", "timestamp": "1723000000"},
    ])).status_code == 200
    with SessionLocal() as session:
        sent = session.get(Message, sent_id)
        failed = session.get(Message, failed_id)
        assert sent.delivery_status == DeliveryStatus.SENT
        assert sent.delivered_at is not None
        assert failed.delivery_status == DeliveryStatus.FAILED
        assert failed.delivered_at is None


# ---------------------------------------------------------------------------
# Rate limit (WH-7 availability guard)
# ---------------------------------------------------------------------------


def test_rate_limit_drops_overflow_after_15_per_minute(client, monkeypatch):
    monkeypatch.setattr(router_module, "sweep_received", lambda limit=50: 0)
    for i in range(16):  # 15 allowed, 16th dropped
        resp = _post(client, _payload([_message(f"wamid.rl{i}", text=str(i))]))
        assert resp.status_code == 200
    assert _count_messages() == 15


# ---------------------------------------------------------------------------
# WH-4: sweep recovery (crash after 200, before processing)
# ---------------------------------------------------------------------------


def test_sweep_recovers_stuck_received_messages(migrated_db, mock_openai_chat, mock_meta_send):
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56912345678", name="Ana")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56912345678")
        session.add(conv)
        session.flush()
        session.add_all(
            [
                Message(
                    wamid="wamid.sw1",
                    conversation_id=conv.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="uno",
                    status=MessageStatus.RECEIVED,
                ),
                Message(
                    wamid="wamid.sw2",
                    conversation_id=conv.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="dos",
                    status=MessageStatus.RECEIVED,
                ),
            ]
        )
        session.commit()

    processed = ingest.sweep_received()
    assert processed == 2

    with SessionLocal() as session:
        rows = session.scalars(select(Message).order_by(Message.id)).all()
    assert all(r.status == MessageStatus.PROCESSED for r in rows)


def test_processing_failure_marks_failed(monkeypatch, migrated_db):
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56998765432")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56998765432")
        session.add(conv)
        session.flush()
        msg = Message(
            wamid="wamid.fail",
            conversation_id=conv.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text="hola",
            status=MessageStatus.RECEIVED,
        )
        session.add(msg)
        session.commit()
        mid = msg.id

    # B1: `sweep_received` runs the burst through `process_turn`; patching
    # `process_message` no longer intercepts it and the sweep reached the real
    # send path. Patch the seam the sweep actually uses.
    monkeypatch.setattr(
        ingest, "process_turn", lambda session, messages: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monkeypatch.setattr(ingest, "_burst_idle_seconds", lambda: 0.0)
    ingest.sweep_received()

    with SessionLocal() as session:
        assert session.get(Message, mid).status == MessageStatus.FAILED


def test_coverage_handoff_followup_stays_silent_at_process_message_boundary(migrated_db, monkeypatch):
    """T5c: the real ingest entry point preserves operator ownership after transfer."""
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56955556666")
        session.add(customer)
        session.flush()
        conv = Conversation(
            customer_id=customer.id,
            wa_phone=customer.phone_e164,
            state=ConversationState.HUMAN,
        )
        session.add(conv)
        session.flush()
        handoff_reply = Message(
            wamid="wamid.coverage-handoff",
            conversation_id=conv.id,
            direction=MessageDirection.OUTBOUND,
            msg_type=MessageType.TEXT,
            text="Todavía no tenemos visitas técnicas en Providencia; un asesor coordinará.",
            status=MessageStatus.PROCESSED,
        )
        inbound = Message(
            wamid="wamid.coverage-followup",
            conversation_id=conv.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text="cuanto sale",
            status=MessageStatus.RECEIVED,
        )
        session.add_all([handoff_reply, inbound])
        session.commit()
        inbound_id = inbound.id
        conversation_id = conv.id

    graph_calls = []
    delivery_calls = []
    monkeypatch.setattr(ingest, "run_conversation", lambda *args: graph_calls.append(args))
    monkeypatch.setattr(ingest, "deliver_outbound", lambda *args: delivery_calls.append(args))
    with SessionLocal() as session:
        inbound = session.get(Message, inbound_id)
        ingest.process_message(session, inbound)
        session.commit()
        assert inbound.status == MessageStatus.PROCESSED
        assert session.get(Conversation, conversation_id).state == ConversationState.HUMAN
        outbound = list(session.scalars(select(Message).where(
            Message.conversation_id == conversation_id,
            Message.direction == MessageDirection.OUTBOUND,
        )))

    assert [message.text for message in outbound] == [handoff_reply.text]
    assert graph_calls == []
    assert delivery_calls == []


def test_human_inbound_is_processed_once_without_bot_outbound(migrated_db, mock_openai_chat):
    """WH-8/HH-5: human ownership keeps inbound history continuous."""
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56955556666")
        session.add(customer)
        session.flush()
        conv = Conversation(
            customer_id=customer.id,
            wa_phone=customer.phone_e164,
            state=ConversationState.HUMAN,
        )
        session.add(conv)
        session.flush()
        session.add(Message(
            wamid="wamid.human-regression",
            conversation_id=conv.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text="Sigo esperando",
            status=MessageStatus.RECEIVED,
        ))
        session.commit()
        conversation_id = conv.id

    assert ingest.sweep_received() == 1
    with SessionLocal() as session:
        rows = list(session.scalars(select(Message).where(Message.conversation_id == conversation_id)))
        assert len(rows) == 1
        assert rows[0].status == MessageStatus.PROCESSED
        assert not [row for row in rows if row.direction == MessageDirection.OUTBOUND]


def test_closed_inbound_is_persisted_without_reopening_or_bot_outbound(migrated_db, mock_openai_chat):
    """WH-8/closed continuity: closed history accepts inbound without reopening."""
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56977778888")
        session.add(customer)
        session.flush()
        conv = Conversation(
            customer_id=customer.id,
            wa_phone=customer.phone_e164,
            state=ConversationState.CLOSED,
        )
        session.add(conv)
        session.flush()
        session.add(Message(
            wamid="wamid.closed-continuity",
            conversation_id=conv.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text="Necesito revisar el historial",
            status=MessageStatus.RECEIVED,
        ))
        session.commit()
        conversation_id = conv.id

    assert ingest.sweep_received() == 1
    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        rows = list(session.scalars(select(Message).where(Message.conversation_id == conversation_id)))
        assert conversation.state == ConversationState.CLOSED
        assert len(rows) == 1
        assert rows[0].status == MessageStatus.PROCESSED
        assert rows[0].text == "Necesito revisar el historial"
        assert not [row for row in rows if row.direction == MessageDirection.OUTBOUND]


# ---------------------------------------------------------------------------
# Media: download + retry via sweep
# ---------------------------------------------------------------------------


def test_media_download_failure_retries_via_sweep(
    monkeypatch, tmp_path, migrated_db, mock_openai_chat, mock_meta_send
):
    media_url = "https://lookaside.example/img123.jpg"
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56911112222")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56911112222")
        session.add(conv)
        session.flush()
        msg = Message(
            wamid="wamid.media",
            conversation_id=conv.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.IMAGE,
            media_url=media_url,
            status=MessageStatus.RECEIVED,
        )
        session.add(msg)
        session.commit()
        mid = msg.id

    monkeypatch.setattr(
        ingest,
        "get_settings",
        lambda: SimpleNamespace(
            media_dir=str(tmp_path),
            meta_access_token="meta-test-token",
            burst_idle_seconds=0.0,
        ),
    )

    # First sweep: download fails (500) -> stays 'received', retried later
    with respx.mock:
        respx.get(media_url).mock(return_value=httpx.Response(500))
        ingest.sweep_received()
    with SessionLocal() as session:
        assert session.get(Message, mid).status == MessageStatus.RECEIVED

    # Second sweep: download succeeds -> processed, file written to media dir
    with respx.mock:
        respx.get(media_url).mock(
            return_value=httpx.Response(200, content=b"FAKEJPEG", headers={"content-type": "image/jpeg"})
        )
        ingest.sweep_received()
    with SessionLocal() as session:
        row = session.get(Message, mid)
        assert row.status == MessageStatus.PROCESSED
        assert Path(row.stored_path).read_bytes() == b"FAKEJPEG"
        assert row.content_type == "image/jpeg"
        assert row.filename == "wamid.media.jpg"
        assert row.size_bytes == len(b"FAKEJPEG")
        assert row.media_attempts == 1

    files = list(Path(tmp_path).iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".jpg"


def test_media_download_stops_after_five_failures(
    monkeypatch, tmp_path, migrated_db, mock_openai_chat
):
    media_url = "https://lookaside.example/never.jpg"
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56922223333")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56922223333")
        session.add(conv)
        session.flush()
        msg = Message(wamid="wamid.never", conversation_id=conv.id,
                      direction=MessageDirection.INBOUND, msg_type=MessageType.IMAGE,
                      media_url=media_url, status=MessageStatus.RECEIVED)
        session.add(msg)
        session.commit()
        mid = msg.id
    monkeypatch.setattr(ingest, "get_settings", lambda: SimpleNamespace(
        media_dir=str(tmp_path), meta_access_token="meta-test-token", burst_idle_seconds=0.0))
    with respx.mock:
        respx.get(media_url).mock(return_value=httpx.Response(500))
        for _ in range(5):
            ingest.sweep_received()
    with SessionLocal() as session:
        row = session.get(Message, mid)
        assert row.status == MessageStatus.PROCESSED
        assert row.media_attempts == 5
        assert row.stored_path is None
        event = session.scalar(select(ConversationEvent).where(
            ConversationEvent.conversation_id == row.conversation_id,
            ConversationEvent.event == "media_unavailable",
        ))
        assert event is not None
        assert str(mid) in event.cause
    with respx.mock:
        route = respx.get(media_url).mock(return_value=httpx.Response(500))
        assert ingest.sweep_received() == 0
        assert route.call_count == 0


def test_downloaded_media_metadata_survives_graph_failure(
    monkeypatch, tmp_path, migrated_db
):
    media_url = "https://lookaside.example/graph-fails.jpg"
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56922223334")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conv)
        session.flush()
        message = Message(
            wamid="wamid.graph-fails", conversation_id=conv.id,
            direction=MessageDirection.INBOUND, msg_type=MessageType.IMAGE,
            media_url=media_url, status=MessageStatus.RECEIVED,
        )
        session.add(message)
        session.commit()
        message_id = message.id
    monkeypatch.setattr(ingest, "get_settings", lambda: SimpleNamespace(
        media_dir=str(tmp_path), meta_access_token="meta-test-token", burst_idle_seconds=0.0))
    monkeypatch.setattr(ingest, "run_conversation", lambda *args: (_ for _ in ()).throw(RuntimeError("graph failed")))
    with respx.mock:
        respx.get(media_url).mock(return_value=httpx.Response(
            200, content=b"downloaded", headers={"content-type": "image/jpeg"}))
        assert ingest.sweep_received() == 0
    with SessionLocal() as session:
        row = session.get(Message, message_id)
        assert row.status == MessageStatus.FAILED
        assert Path(row.stored_path).read_bytes() == b"downloaded"
        assert row.content_type == "image/jpeg"
        assert row.size_bytes == len(b"downloaded")


def test_media_download_uses_bearer_token(
    monkeypatch, tmp_path, migrated_db, mock_openai_chat, mock_meta_send
):
    media_url = "https://lookaside.example/tok.jpeg"
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56933334444")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56933334444")
        session.add(conv)
        session.flush()
        msg = Message(
            wamid="wamid.tok",
            conversation_id=conv.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.IMAGE,
            media_url=media_url,
            status=MessageStatus.RECEIVED,
        )
        session.add(msg)
        session.commit()

    monkeypatch.setattr(
        ingest,
        "get_settings",
        lambda: SimpleNamespace(
            media_dir=str(tmp_path),
            meta_access_token="meta-test-token",
            burst_idle_seconds=0.0,
        ),
    )
    with respx.mock:
        route = respx.get(media_url).mock(
            return_value=httpx.Response(200, content=b"IMG", headers={"content-type": "image/jpeg"})
        )
        ingest.sweep_received()
    assert route.calls.last.request.headers["authorization"] == "Bearer meta-test-token"


# ---------------------------------------------------------------------------
# Startup sweep (design Webhook Pipeline: crash recovery)
# ---------------------------------------------------------------------------


def test_startup_sweep_reprocesses_received(migrated_db, mock_openai_chat, mock_meta_send):
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56944445555")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56944445555")
        session.add(conv)
        session.flush()
        msg = Message(
            wamid="wamid.startup",
            conversation_id=conv.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text="previo",
            status=MessageStatus.RECEIVED,
        )
        session.add(msg)
        session.commit()
        mid = msg.id

    with TestClient(create_app()) as _:
        pass  # lifespan runs the startup sweep

    with SessionLocal() as session:
        assert session.get(Message, mid).status == MessageStatus.PROCESSED


# ---------------------------------------------------------------------------
# Per-conversation exclusivity (chat-rafagas S4)
# ---------------------------------------------------------------------------


def test_same_conversation_never_runs_two_turns_at_once(migrated_db, monkeypatch):
    """S4: a message arriving mid-turn waits; it never opens a parallel turn.

    Two webhook POSTs enqueue two background sweeps, so the pipeline can enter
    `process_message` twice for the same conversation. Today each entry runs its
    own `run_conversation`: the second turn rebuilds state before the first reply
    is persisted and the model answers two consecutive user messages with no bot
    in between -- measured in production (Engram `chat/burst-de-mensajes`).
    """
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56911112222", name="Max")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56911112222")
        session.add(conv)
        session.flush()
        conversation_id = conv.id
        session.add(
            Message(
                wamid="wamid.ex1",
                conversation_id=conv.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="Hola",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()

    active = {"now": 0, "peak": 0}
    guard = threading.Lock()
    in_turn = threading.Event()
    release = threading.Event()

    def slow_turn(session, message):
        with guard:
            active["now"] += 1
            active["peak"] = max(active["peak"], active["now"])
        in_turn.set()
        release.wait(5.0)
        with guard:
            active["now"] -= 1
        return []

    monkeypatch.setattr(ingest, "run_conversation", slow_turn)
    # chat-rafagas T2 adds the silence window; this test pins exclusivity only.
    monkeypatch.setattr(ingest, "_burst_idle_seconds", lambda: 0.0)

    first = threading.Thread(target=ingest.sweep_received)
    first.start()
    assert in_turn.wait(5.0), "the first sweep never started the turn"

    # The customer's second message arrives while the first turn is running.
    with SessionLocal() as session:
        session.add(
            Message(
                wamid="wamid.ex2",
                conversation_id=conversation_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="¿Cómo estás?",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()

    second = threading.Thread(target=ingest.sweep_received)
    second.start()
    time.sleep(0.3)  # window for the second sweep to enter a parallel turn
    release.set()
    first.join(10.0)
    second.join(10.0)

    assert not first.is_alive() and not second.is_alive()
    assert active["peak"] == 1, "two turns of the same conversation overlapped"


def test_burst_of_two_messages_produces_one_reply(
    migrated_db, mock_openai_chat, mock_meta_send, monkeypatch
):
    """S1: messages sent before the bot answers are ONE turn with ONE reply.

    Production 2026-11-06 17:12: the customer wrote "Hola" and then the rest of
    the request before the bot answered, and received two messages -- the second
    one a canned line that answered nothing. The burst here carries content so the
    classifier runs: a greeting-only burst short-circuits in `receive` and never
    reaches it.
    """
    monkeypatch.setattr(ingest, "_burst_idle_seconds", lambda: 0.0)
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56933334444", name="Max Escanilla")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56933334444")
        session.add(conv)
        session.flush()
        conversation_id = conv.id
        session.add_all(
            [
                Message(
                    wamid="wamid.burst1",
                    conversation_id=conv.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="Hola",
                    status=MessageStatus.RECEIVED,
                ),
                Message(
                    wamid="wamid.burst2",
                    conversation_id=conv.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="Necesito una visita para revisar la caldera",
                    status=MessageStatus.RECEIVED,
                ),
            ]
        )
        session.commit()

    assert ingest.sweep_received() == 2

    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id)
            )
        )
    outbound = [row for row in rows if row.direction == MessageDirection.OUTBOUND]
    assert len(outbound) == 1, "a burst must receive exactly one reply"
    assert all(row.status == MessageStatus.PROCESSED for row in rows)

    # The turn reads the burst as ONE customer utterance, so the classifier sees
    # both messages instead of only the last one.
    inputs = [
        body["messages"][-1]["content"].split("<user_input>")[1].split("</user_input>")[0]
        for body in mock_openai_chat
        if "<user_input>" in body["messages"][-1]["content"]
    ]
    assert inputs, "the turn never reached the classifier"
    assert any(
        "Hola" in text and "Necesito una visita" in text for text in inputs
    )


def test_first_contact_survives_a_burst(
    migrated_db, mock_openai_chat, mock_meta_send, monkeypatch
):
    """S3: a new customer who writes twice still gets the first-contact greeting.

    `state.turn` used to count persisted inbound rows, so "Hola" + "¿Cómo estás?"
    arriving together made the very first turn look like turn 2 and every
    `turn <= 1` rule (the greeting header among them) was skipped.
    """
    monkeypatch.setattr(ingest, "_burst_idle_seconds", lambda: 0.0)
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56966667777", name="Max")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56966667777")
        session.add(conv)
        session.flush()
        conversation_id = conv.id
        session.add_all(
            [
                Message(
                    wamid="wamid.first1",
                    conversation_id=conv.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="Hola",
                    status=MessageStatus.RECEIVED,
                ),
                Message(
                    wamid="wamid.first2",
                    conversation_id=conv.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="¿Cómo estás?",
                    status=MessageStatus.RECEIVED,
                ),
            ]
        )
        session.commit()

    assert ingest.sweep_received() == 2

    with SessionLocal() as session:
        outbound = list(
            session.scalars(
                select(Message).where(
                    Message.conversation_id == conversation_id,
                    Message.direction == MessageDirection.OUTBOUND,
                )
            )
        )
        assert session.get(Conversation, conversation_id).turn_count == 1

    assert len(outbound) == 1
    assert outbound[0].text.startswith("Hola, Max.")


def test_burst_window_merges_a_message_that_arrives_during_the_wait(
    migrated_db, mock_openai_chat, mock_meta_send, monkeypatch
):
    """S1: the silence window is what makes two webhooks ONE turn.

    Without the wait, the first sweep answers "Hola" alone and the second message
    opens a second turn: exactly what production did. The test starts the sweep,
    lets the customer's second message land while it waits, and expects one reply.
    """
    monkeypatch.setattr(ingest, "_burst_idle_seconds", lambda: 0.5)
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56912340000", name="Max")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56912340000")
        session.add(conv)
        session.flush()
        conversation_id = conv.id
        session.add(
            Message(
                wamid="wamid.wait1",
                conversation_id=conv.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="Hola",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()

    sweep = threading.Thread(target=ingest.sweep_received)
    sweep.start()
    time.sleep(0.15)
    with SessionLocal() as session:
        session.add(
            Message(
                wamid="wamid.wait2",
                conversation_id=conversation_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="Necesito una visita para revisar la caldera",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
    sweep.join(20.0)
    assert not sweep.is_alive()

    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(Message).where(Message.conversation_id == conversation_id)
            )
        )
    outbound = [row for row in rows if row.direction == MessageDirection.OUTBOUND]
    assert len(outbound) == 1
    assert all(row.status == MessageStatus.PROCESSED for row in rows)


def test_failed_turn_releases_the_conversation_lock(migrated_db, monkeypatch):
    """S4: a turn that explodes must not wedge the conversation.

    The lock lives in a module-level registry, so a leak would silently stop every
    later message of that conversation from being answered.
    """
    monkeypatch.setattr(ingest, "_burst_idle_seconds", lambda: 0.0)
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56912341111")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56912341111")
        session.add(conv)
        session.flush()
        conversation_id = conv.id
        session.add(
            Message(
                wamid="wamid.lock1",
                conversation_id=conv.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="primero",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()

    def explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ingest, "run_conversation", explode)
    ingest.sweep_received()

    with SessionLocal() as session:
        assert session.scalar(
            select(Message.status).where(Message.wamid == "wamid.lock1")
        ) == MessageStatus.FAILED

    reached = []
    monkeypatch.setattr(ingest, "run_conversation", lambda session, message: reached.append(message.id))
    with SessionLocal() as session:
        session.add(
            Message(
                wamid="wamid.lock2",
                conversation_id=conversation_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="segundo",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()

    monkeypatch.setattr(ingest, "deliver_outbound", lambda *args: None)
    ingest.sweep_received()

    assert len(reached) == 1, "the lock leaked: the next message was never answered"


def test_media_failure_does_not_make_a_burst_answer_twice(
    migrated_db, mock_openai_chat, mock_meta_send, monkeypatch
):
    """S1/WH-4: a burst whose photo fails still answers once, and the photo retries."""
    monkeypatch.setattr(ingest, "_burst_idle_seconds", lambda: 0.0)
    media_url = "https://lookaside.example/burst-photo"
    with SessionLocal() as session:
        customer = Customer(phone_e164="+56912342222")
        session.add(customer)
        session.flush()
        conv = Conversation(customer_id=customer.id, wa_phone="+56912342222")
        session.add(conv)
        session.flush()
        conversation_id = conv.id
        session.add_all(
            [
                Message(
                    wamid="wamid.media1",
                    conversation_id=conv.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="Mira la foto de la caldera",
                    status=MessageStatus.RECEIVED,
                ),
                Message(
                    wamid="wamid.media2",
                    conversation_id=conv.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.IMAGE,
                    media_url=media_url,
                    status=MessageStatus.RECEIVED,
                ),
            ]
        )
        session.commit()

    with respx.mock:
        respx.get(media_url).mock(return_value=httpx.Response(500))
        ingest.sweep_received()

    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(Message).where(Message.conversation_id == conversation_id)
            )
        )
    outbound = [row for row in rows if row.direction == MessageDirection.OUTBOUND]
    photo = next(row for row in rows if row.wamid == "wamid.media2")
    text = next(row for row in rows if row.wamid == "wamid.media1")

    assert len(outbound) == 1
    assert text.status == MessageStatus.PROCESSED
    assert photo.status == MessageStatus.RECEIVED
    assert photo.media_attempts == 1
