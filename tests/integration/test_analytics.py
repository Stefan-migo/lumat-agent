from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import (
    Case,
    Conversation,
    ConversationEvent,
    ConversationState,
    Message,
    MessageDirection,
)
from app.services.analytics import chatbot_metrics


def test_chatbot_metrics_aggregates_window_and_returns_null_for_missing_averages(seed_customer):
    now = datetime.now(timezone.utc)
    customer_id = seed_customer("+56911110001")

    with SessionLocal() as session:
        handed_off = Conversation(
            customer_id=customer_id, wa_phone="+56911110001", state=ConversationState.CLOSED,
            closed_at=now - timedelta(days=1),
        )
        contained = Conversation(
            customer_id=customer_id, wa_phone="+56911110001", state=ConversationState.CLOSED,
            closed_at=now - timedelta(days=2),
        )
        empty = Conversation(customer_id=customer_id, wa_phone="+56911110001")
        session.add_all([handed_off, contained, empty])
        session.flush()

        session.add_all([
            Message(conversation_id=handed_off.id, direction=MessageDirection.INBOUND,
                    created_at=now - timedelta(days=1), cost_llm=0.2, cost_meta=0.1),
            Message(conversation_id=handed_off.id, direction=MessageDirection.INBOUND,
                    created_at=now - timedelta(days=1), cost_llm=0.1, cost_meta=0.1),
            Message(conversation_id=contained.id, direction=MessageDirection.INBOUND,
                    created_at=now - timedelta(days=2), cost_llm=0.2, cost_meta=0.0),
            Message(conversation_id=contained.id, direction=MessageDirection.OUTBOUND,
                    created_at=now - timedelta(days=2), cost_llm=0.0, cost_meta=0.1),
        ])
        session.add_all([
            ConversationEvent(conversation_id=handed_off.id, event="escalation",
                              cause="handoff:kb_miss", created_at=now - timedelta(days=1)),
            ConversationEvent(conversation_id=contained.id, event="kb_retrieved",
                              cause="chunks:3", created_at=now - timedelta(days=2)),
            ConversationEvent(conversation_id=contained.id, event="unknown_intent",
                              created_at=now - timedelta(days=2)),
            ConversationEvent(conversation_id=handed_off.id, event="escalation",
                              cause="handoff:kb_miss", created_at=now - timedelta(days=1)),
        ])
        session.add(Case(
            conversation_id=handed_off.id, customer_id=customer_id,
            escalated_at=now - timedelta(days=1),
        ))
        session.flush()

        result = chatbot_metrics(session, 7)

    assert result == {
        "conversations": 2,
        "handoffs": 1,
        "handoff_rate": 0.5,
        "containment_rate": 0.5,
        "handoff_reasons": {"kb_miss": 2},
        "unknown_intents": 1,
        "kb_hits": 1,
        "kb_misses": 2,
        "kb_hit_rate": 0.3333,
        "turns_to_resolve": 1.5,
        "cost_per_conversation": 0.4,
        "window_days": 7,
    }


def test_chatbot_metrics_empty_window_returns_zero_counts_and_null_averages(seed_customer):
    seed_customer("+56911110002")
    with SessionLocal() as session:
        result = chatbot_metrics(session, 7)

    assert result == {
        "conversations": 0,
        "handoffs": 0,
        "handoff_rate": 0.0,
        "containment_rate": 1.0,
        "handoff_reasons": {},
        "unknown_intents": 0,
        "kb_hits": 0,
        "kb_misses": 0,
        "kb_hit_rate": None,
        "turns_to_resolve": None,
        "cost_per_conversation": None,
        "window_days": 7,
    }
