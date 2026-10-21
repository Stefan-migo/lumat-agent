from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.db import SessionLocal
from app.models import (
    Case,
    Conversation,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.ops.daily_summary import build_digest


@pytest.fixture
def session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


def _seed_customer_conversation(session):
    customer = Customer(phone_e164=f"+569{uuid4().int % 10**8:08d}")
    session.add(customer)
    session.flush()
    conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
    session.add(conversation)
    session.flush()
    return customer, conversation


def test_daily_digest_reports_real_open_cases_questions_and_spend(session):
    now = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
    customer, conversation = _seed_customer_conversation(session)
    session.add_all(
        [
            Case(customer_id=customer.id, conversation_id=conversation.id, status="abierto"),
            Case(customer_id=customer.id, conversation_id=conversation.id, status="escalado"),
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                status=MessageStatus.RECEIVED,
                payload={"unresolved": True},
                cost_llm=0.125,
                created_at=now,
            ),
        ]
    )
    session.flush()

    digest = build_digest(session, period="daily", now=now)

    assert "Casos abiertos: 2" in digest
    assert "Preguntas sin resolver: 1" in digest
    assert "0.125" in digest
    assert "diario" in digest.lower()


def test_weekly_digest_sums_spend_for_seven_utc_days(session):
    now = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
    customer, conversation = _seed_customer_conversation(session)
    for offset in range(7):
        session.add(
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                status=MessageStatus.PROCESSED,
                cost_llm=Decimal("0.10"),
                created_at=datetime.combine(
                    now.date() - timedelta(days=offset), datetime.min.time(), timezone.utc
                ),
            )
        )
    session.flush()

    digest = build_digest(session, period="weekly", now=now)

    assert "0.7" in digest


def test_empty_digest_says_there_is_nothing_to_report(session):
    digest = build_digest(
        session, period="daily", now=datetime(2026, 10, 10, tzinfo=timezone.utc)
    )

    assert "Sin novedades para el período." in digest


def test_invalid_period_raises_value_error(session):
    with pytest.raises(ValueError):
        build_digest(session, period="monthly", now=datetime.now(timezone.utc))
