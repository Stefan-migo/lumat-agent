"""T3.6 integration tests — Meta send + cost services (SS-4 tracking basis).

- send.py: Meta Cloud API outbound text send returns the wamid; `cost_meta`
  recorded per pricing settings (service-message unit, default reference)
- costs.py: `record_llm_cost` = tokens x rate (D6); `conversation_spend` /
  `daily_spend` = SQL SUM of cost_llm + cost_meta
- End-to-end: a received message through the sweep answers AND delivers the
  outbound reply via Meta (mocked), recording wamid + cost_meta

Meta and OpenAI are mocked via respx — never real calls.
"""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import httpx

import psycopg
import pytest
import respx
from sqlalchemy import select

from app.chat.state import get_or_create_conversation  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    Settings,
)
from app.services import costs, send  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from app.webhook import ingest  # noqa: E402

ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE kb_chunks, kb_documents, audit_log, conversation_events, "
            "cases, messages, conversations, customer_notes, customers, settings "
            "RESTART IDENTITY CASCADE"
        )
    yield


# ---------------------------------------------------------------------------
# send.py — Meta outbound text send
# ---------------------------------------------------------------------------


def test_send_text_posts_to_meta_and_returns_wamid(mock_meta_send):
    wamid = send.send_text("+56912345678", "Hola, este es un mensaje de prueba")

    assert wamid == "wamid.out123"
    request = mock_meta_send.calls.last.request
    assert request.headers["authorization"] == "Bearer meta-test-token"
    body = json.loads(request.content)
    assert body["to"] == "+56912345678"
    assert body["type"] == "text"
    assert body["text"]["body"] == "Hola, este es un mensaje de prueba"


def test_send_text_raises_on_meta_error(mock_meta_send):
    mock_meta_send.routes[0].mock(
        return_value=httpx.Response(400, json={"error": {"code": 100, "message": "invalid"}})
    )
    with pytest.raises(httpx.HTTPStatusError):
        send.send_text("+56912345678", "hola")


# ---------------------------------------------------------------------------
# send.py — deliver_outbound: wamid + cost_meta per pricing settings
# ---------------------------------------------------------------------------


def _seed_outbound_row(text: str = "respuesta del bot") -> tuple[int, int]:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        session.add(
            Message(
                conversation_id=conv.id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.PROCESSED,
            )
        )
        session.commit()
        return conv.id, conv.customer_id


def test_deliver_outbound_sends_and_records_cost_meta(mock_meta_send):
    conv_id, _ = _seed_outbound_row()
    with SessionLocal() as session:
        sent = send.deliver_outbound(session, conv_id)
        session.commit()
        rows = list(
            session.scalars(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.direction == MessageDirection.OUTBOUND,
                )
            )
        )
    assert sent == 1
    assert rows[0].wamid == "wamid.out123"
    assert float(rows[0].cost_meta) == pytest.approx(send.DEFAULT_META_COST)


def test_deliver_outbound_uses_settings_pricing(mock_meta_send):
    conv_id, _ = _seed_outbound_row()
    with SessionLocal() as session:
        session.add(
            Settings(key="meta_pricing", value={"service_message_cost": 0.0234})
        )
        session.commit()
    with SessionLocal() as session:
        send.deliver_outbound(session, conv_id)
        session.commit()
        rows = list(
            session.scalars(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.direction == MessageDirection.OUTBOUND,
                )
            )
        )
    assert float(rows[0].cost_meta) == pytest.approx(0.0234)


def test_deliver_outbound_skips_already_sent_rows(mock_meta_send):
    conv_id, _ = _seed_outbound_row()
    with SessionLocal() as session:
        send.deliver_outbound(session, conv_id)  # first pass sends
        session.commit()
        calls_after_first = len(mock_meta_send.calls)
        send.deliver_outbound(session, conv_id)  # second pass must skip
        session.commit()
    assert len(mock_meta_send.calls) == calls_after_first  # no double-send


def test_legacy_sweep_does_not_resend_h2_delivery_states(mock_meta_send):
    conv_id, _ = _seed_outbound_row(text="legacy")
    with SessionLocal() as session:
        legacy = session.scalars(
            select(Message).where(Message.conversation_id == conv_id)
        ).one()
        h2_rows = [
            Message(
                conversation_id=conv_id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                text=status.value,
                status=MessageStatus.PROCESSED,
                request_id=f"h2-{status.value}",
                delivery_status=status,
            )
            for status in (
                send.DeliveryStatus.PENDING,
                send.DeliveryStatus.SENDING,
                send.DeliveryStatus.FAILED,
                send.DeliveryStatus.UNKNOWN,
            )
        ]
        session.add_all(h2_rows)
        session.commit()

    assert send.deliver_all_pending() == 1
    assert len(mock_meta_send.calls) == 1
    with SessionLocal() as session:
        assert session.get(Message, legacy.id).wamid == "wamid.out123"
        assert all(session.get(Message, row.id).wamid is None for row in h2_rows)


def test_legacy_delivery_path_only_sends_unmarked_legacy_rows(mock_meta_send):
    conv_id, _ = _seed_outbound_row(text="legacy")
    with SessionLocal() as session:
        h2_row = Message(
            conversation_id=conv_id,
            direction=MessageDirection.OUTBOUND,
            msg_type=MessageType.TEXT,
            text="h2",
            status=MessageStatus.PROCESSED,
            request_id="h2-request",
            delivery_status=send.DeliveryStatus.PENDING,
        )
        session.add(h2_row)
        session.commit()

    with SessionLocal() as session:
        assert send.deliver_outbound(session, conv_id) == 1
        session.commit()

    with SessionLocal() as session:
        assert session.get(Message, h2_row.id).delivery_status == send.DeliveryStatus.PENDING
        assert session.get(Message, h2_row.id).wamid is None


# ---------------------------------------------------------------------------
# costs.py — record_llm_cost + SQL SUMs (D6)
# ---------------------------------------------------------------------------


def test_record_llm_cost_computes_token_rate():
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        session.add(
            Message(
                conversation_id=conv.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="pregunta",
                status=MessageStatus.PROCESSED,
            )
        )
        session.commit()
        msg = session.scalars(
            select(Message).where(Message.direction == MessageDirection.INBOUND)
        ).one()
        # gpt-4o-mini: 100k in @$0.15/1M + 50k out @$0.60/1M
        cost = costs.record_llm_cost(
            session, msg.id, "gpt-4o-mini", prompt_tokens=100_000, completion_tokens=50_000
        )
        session.commit()
        assert cost == pytest.approx(Decimal("0.045"))
        assert float(msg.cost_llm) == pytest.approx(0.045)


def test_record_llm_cost_accumulates_on_message():
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        session.add(
            Message(
                conversation_id=conv.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="pregunta",
                status=MessageStatus.PROCESSED,
            )
        )
        session.commit()
        msg = session.scalars(
            select(Message).where(Message.direction == MessageDirection.INBOUND)
        ).one()
        costs.record_llm_cost(session, msg.id, "gpt-4o-mini", 1_000_000, 0)
        costs.record_llm_cost(session, msg.id, "gpt-4o-mini", 0, 1_000_000)
        session.commit()
        # 0.15 (in) + 0.60 (out) accumulated on the same row
        assert float(msg.cost_llm) == pytest.approx(0.75)


def _seed_cost_messages() -> tuple[int, float]:
    """Seed 2 conversations (different customers) with known costs."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        customer2 = get_or_create_customer(session, "+56922223333")
        conv2 = get_or_create_conversation(session, customer2, "+56922223333")
        session.add(
            Message(
                conversation_id=conv.id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                text="a",
                status=MessageStatus.PROCESSED,
                cost_llm=0.10,
                cost_meta=0.01,
            )
        )
        session.add(
            Message(
                conversation_id=conv2.id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                text="b",
                status=MessageStatus.PROCESSED,
                cost_llm=0.20,
                cost_meta=0.02,
            )
        )
        session.commit()
        return conv.id, 0.11  # conv1: 0.10 + 0.01


def test_conversation_spend_sums_cost_columns():
    conv_id, expected = _seed_cost_messages()
    with SessionLocal() as session:
        assert costs.conversation_spend(session, conv_id) == pytest.approx(expected)


def test_daily_spend_sums_all_conversations():
    _, _ = _seed_cost_messages()
    with SessionLocal() as session:
        # conv1 0.11 + conv2 0.22 = 0.33 today
        assert costs.daily_spend(session) == pytest.approx(0.33)


def test_daily_spend_scoped_to_day():
    conv_id, _ = _seed_cost_messages()
    with SessionLocal() as session:
        yesterday = datetime(2020, 1, 1, tzinfo=timezone.utc)
        session.add(
            Message(
                conversation_id=conv_id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                text="viejo",
                status=MessageStatus.PROCESSED,
                cost_llm=99.0,
                created_at=yesterday,
            )
        )
        session.commit()
        # today's spend excludes the 2020 row
        assert costs.daily_spend(session) == pytest.approx(0.33)
        assert costs.daily_spend(session, day=yesterday.date()) == pytest.approx(99.0)


# ---------------------------------------------------------------------------
# End-to-end: webhook -> sweep -> graph -> Meta send (all mocked)
# ---------------------------------------------------------------------------


def test_sweep_delivers_outbound_reply_via_meta(mock_openai_chat, mock_meta_send):
    """A received text through the sweep answers AND sends via Meta."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        session.add(
            Message(
                wamid="wamid.e2e",
                conversation_id=conv.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="hola",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        conv_id = conv.id

    ingest.sweep_received()

    with SessionLocal() as session:
        outbound = list(
            session.scalars(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.direction == MessageDirection.OUTBOUND,
                )
            )
        )
        inbound = session.scalars(
            select(Message).where(Message.wamid == "wamid.e2e")
        ).one()
    assert inbound.status == MessageStatus.PROCESSED
    assert len(outbound) >= 1
    assert outbound[0].wamid == "wamid.out123"  # Meta confirmed delivery
    assert float(outbound[0].cost_meta) == pytest.approx(send.DEFAULT_META_COST)
