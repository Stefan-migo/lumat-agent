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
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.webhook import ingest  # noqa: E402
from app.webhook import router as router_module  # noqa: E402

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


ADMIN_DB_URL = "postgresql://lumat:lumat@localhost:5432/lumat"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset webhook-related tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE conversation_events, cases, messages, conversations, customers "
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


def test_retry_storm_single_processing_pass(client, mock_openai_chat, mock_meta_send):
    """WH-7: a batch re-delivered 10x yields exactly one processing pass each.
    Each processed inbound also produces one bot reply (B3 behavior)."""
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
    # The first inbound answers (clarification); the SECOND unknown escalates
    # (HH-3) and hands off to a human; the third inbound lands in `human`
    # state and is persisted WITHOUT a bot reply (HH-5) — the human owns the
    # channel from there. 2 outbound rows = clarification + handoff reply.
    assert len(outbound) == 2
    assert any("entend" in (m.text or "") for m in outbound)  # clarification
    assert any("asesor" in (m.text or "") for m in outbound)  # handoff reply


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

    monkeypatch.setattr(
        ingest, "process_message", lambda session, message: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    ingest.sweep_received()

    with SessionLocal() as session:
        assert session.get(Message, mid).status == MessageStatus.FAILED


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
        lambda: SimpleNamespace(media_dir=str(tmp_path), meta_access_token="meta-test-token"),
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
        assert session.get(Message, mid).status == MessageStatus.PROCESSED

    files = list(Path(tmp_path).iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".jpg"


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
        lambda: SimpleNamespace(media_dir=str(tmp_path), meta_access_token="meta-test-token"),
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
