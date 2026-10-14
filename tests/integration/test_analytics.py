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
from app.services.analytics import chatbot_conversations, chatbot_metrics


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


def _seed_signal_conversations(session, customer_id, now):
    """Three flagged conversations + one clean one; returns ids by tag."""
    handed = Conversation(customer_id=customer_id, wa_phone="+56911110003", state=ConversationState.BOT)
    unknown = Conversation(customer_id=customer_id, wa_phone="+56911110003", state=ConversationState.BOT)
    emergency = Conversation(customer_id=customer_id, wa_phone="+56911110003", state=ConversationState.BOT)
    clean = Conversation(customer_id=customer_id, wa_phone="+56911110003", state=ConversationState.BOT)
    session.add_all([handed, unknown, emergency, clean])
    session.flush()
    session.add_all([
        ConversationEvent(conversation_id=handed.id, event="escalation",
                          cause="handoff:kb_miss", created_at=now - timedelta(days=1)),
        ConversationEvent(conversation_id=handed.id, event="unknown_intent",
                          created_at=now - timedelta(days=3)),
        ConversationEvent(conversation_id=unknown.id, event="unknown_intent",
                          created_at=now - timedelta(days=2)),
        ConversationEvent(conversation_id=emergency.id, event="escalation",
                          cause="handoff:emergency", created_at=now - timedelta(days=5)),
        ConversationEvent(conversation_id=clean.id, event="kb_retrieved",
                          cause="chunks:3", created_at=now - timedelta(days=1)),
    ])
    session.flush()
    return handed.id, unknown.id, emergency.id, clean.id


def test_chatbot_conversations_any_lists_flagged_ordered_by_recent_signal(seed_customer):
    now = datetime.now(timezone.utc)
    customer_id = seed_customer("+56911110003")

    with SessionLocal() as session:
        handed, unknown, emergency, _clean = _seed_signal_conversations(session, customer_id, now)
        result = chatbot_conversations(session, 7, "any", 10)

    assert result["window_days"] == 7 and result["signal"] == "any"
    assert [row["conversation_id"] for row in result["conversations"]] == [handed, unknown, emergency]
    by_id = {row["conversation_id"]: row for row in result["conversations"]}
    assert by_id[handed]["signals"] == {"escalation": 1, "unknown_intent": 1, "kb_miss": 1}
    assert by_id[unknown]["signals"] == {"escalation": 0, "unknown_intent": 1, "kb_miss": 0}
    assert by_id[emergency]["signals"] == {"escalation": 1, "unknown_intent": 0, "kb_miss": 0}
    assert by_id[handed]["customer_id"] == customer_id
    assert by_id[handed]["wa_phone"] == "+56911110003"
    assert by_id[handed]["state"] == "bot"
    assert by_id[handed]["last_message_at"] is None


def test_chatbot_conversations_kb_miss_signal_excludes_other_escalations(seed_customer):
    now = datetime.now(timezone.utc)
    customer_id = seed_customer("+56911110004")

    with SessionLocal() as session:
        handed, _unknown, _emergency, _clean = _seed_signal_conversations(session, customer_id, now)
        result = chatbot_conversations(session, 7, "kb_miss", 10)

    assert [row["conversation_id"] for row in result["conversations"]] == [handed]
    assert result["conversations"][0]["signals"]["kb_miss"] == 1


def test_chatbot_conversations_unknown_intent_orders_by_recent_match(seed_customer):
    now = datetime.now(timezone.utc)
    customer_id = seed_customer("+56911110005")

    with SessionLocal() as session:
        handed, unknown, _emergency, _clean = _seed_signal_conversations(session, customer_id, now)
        result = chatbot_conversations(session, 7, "unknown_intent", 10)

    assert [row["conversation_id"] for row in result["conversations"]] == [unknown, handed]


def test_chatbot_conversations_respects_limit(seed_customer):
    now = datetime.now(timezone.utc)
    customer_id = seed_customer("+56911110006")

    with SessionLocal() as session:
        handed, _unknown, _emergency, _clean = _seed_signal_conversations(session, customer_id, now)
        result = chatbot_conversations(session, 7, "any", 1)

    assert [row["conversation_id"] for row in result["conversations"]] == [handed]


def test_chatbot_conversations_empty_window_returns_empty_list(seed_customer):
    now = datetime.now(timezone.utc)
    customer_id = seed_customer("+56911110007")

    with SessionLocal() as session:
        clean = Conversation(customer_id=customer_id, wa_phone="+56911110007")
        session.add(clean)
        session.flush()
        session.add(ConversationEvent(conversation_id=clean.id, event="kb_retrieved",
                                      cause="chunks:2", created_at=now - timedelta(days=1)))
        session.flush()
        result = chatbot_conversations(session, 7, "any", 10)

    assert result == {"window_days": 7, "signal": "any", "conversations": []}
