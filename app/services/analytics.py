"""Read-only analytics aggregates for chatbot performance."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select

from app.models import Conversation, ConversationEvent, Message, MessageDirection


def chatbot_metrics(session, window_days: int) -> dict:
    """Return chatbot performance metrics over the requested UTC time window."""
    start = datetime.now(timezone.utc) - timedelta(days=window_days)
    conversations = set(session.scalars(
        select(Message.conversation_id).where(
            Message.direction == MessageDirection.INBOUND,
            Message.created_at >= start,
        ).distinct()
    ).all())

    escalation_rows = session.execute(
        select(ConversationEvent.conversation_id, ConversationEvent.cause).where(
            ConversationEvent.event == "escalation",
            ConversationEvent.created_at >= start,
        )
    ).all()
    handoffs = {conversation_id for conversation_id, _cause in escalation_rows}
    handoff_reasons: Counter[str] = Counter()
    for conversation_id, cause in escalation_rows:
        if cause and cause.startswith("handoff:"):
            reason = cause.removeprefix("handoff:")
            handoff_reasons[reason] += 1

    unknown_intents = session.scalar(
        select(func.count()).select_from(ConversationEvent).where(
            ConversationEvent.event == "unknown_intent",
            ConversationEvent.created_at >= start,
        )
    ) or 0
    kb_hits = session.scalar(
        select(func.count()).select_from(ConversationEvent).where(
            ConversationEvent.event == "kb_retrieved",
            ConversationEvent.created_at >= start,
        )
    ) or 0
    kb_misses = handoff_reasons.get("kb_miss", 0)

    inbound_counts = (
        select(Message.conversation_id, func.count().label("turns"))
        .where(Message.direction == MessageDirection.INBOUND)
        .group_by(Message.conversation_id)
        .subquery()
    )
    turns_to_resolve = session.scalar(
        select(func.avg(func.coalesce(inbound_counts.c.turns, 0)))
        .select_from(Conversation)
        .outerjoin(inbound_counts, inbound_counts.c.conversation_id == Conversation.id)
        .where(Conversation.closed_at >= start)
    )

    costs = []
    if conversations:
        from app.services.costs import conversation_spend

        costs = [conversation_spend(session, conversation_id) for conversation_id in conversations]

    conversation_count = len(conversations)
    handoff_count = len(handoffs)
    handoff_rate = handoff_count / conversation_count if conversation_count else 0.0
    kb_total = kb_hits + kb_misses
    return {
        "conversations": conversation_count,
        "handoffs": handoff_count,
        "handoff_rate": round(handoff_rate, 4),
        "containment_rate": round(1 - handoff_rate, 4),
        "handoff_reasons": dict(handoff_reasons),
        "unknown_intents": int(unknown_intents),
        "kb_hits": int(kb_hits),
        "kb_misses": kb_misses,
        "kb_hit_rate": round(kb_hits / kb_total, 4) if kb_total else None,
        "turns_to_resolve": float(turns_to_resolve) if turns_to_resolve is not None else None,
        "cost_per_conversation": sum(costs) / len(costs) if costs else None,
        "window_days": window_days,
    }


CHATBOT_SIGNALS = ("escalation", "unknown_intent", "kb_miss", "any")


def _signal_clause(signal: str):
    """The SQL predicate that defines one diagnostic signal (S4)."""
    if signal == "escalation":
        return ConversationEvent.event == "escalation"
    if signal == "unknown_intent":
        return ConversationEvent.event == "unknown_intent"
    if signal == "kb_miss":
        return and_(
            ConversationEvent.event == "escalation",
            ConversationEvent.cause == "handoff:kb_miss",
        )
    # "any" is the union of the three; kb_miss is already a subset of escalation.
    return or_(
        ConversationEvent.event == "escalation",
        ConversationEvent.event == "unknown_intent",
    )


def chatbot_conversations(session, window_days: int, signal: str = "any", limit: int = 10) -> dict:
    """List the conversations that tripped a chatbot failure signal in the window (S5)."""
    if signal not in CHATBOT_SIGNALS:
        raise ValueError(f"unknown chatbot signal: {signal}")
    start = datetime.now(timezone.utc) - timedelta(days=window_days)
    ranked = session.execute(
        select(
            ConversationEvent.conversation_id,
            func.max(ConversationEvent.created_at).label("last_at"),
        )
        .where(ConversationEvent.created_at >= start, _signal_clause(signal))
        .group_by(ConversationEvent.conversation_id)
        .order_by(func.max(ConversationEvent.created_at).desc(), ConversationEvent.conversation_id.desc())
        .limit(limit)
    ).all()
    if not ranked:
        return {"window_days": window_days, "signal": signal, "conversations": []}

    ids = [row.conversation_id for row in ranked]
    conversations = {
        row.id: row for row in session.scalars(select(Conversation).where(Conversation.id.in_(ids)))
    }
    counts: dict[int, dict[str, int]] = {
        conversation_id: {"escalation": 0, "unknown_intent": 0, "kb_miss": 0} for conversation_id in ids
    }
    for conversation_id, event, cause in session.execute(
        select(ConversationEvent.conversation_id, ConversationEvent.event, ConversationEvent.cause)
        .where(ConversationEvent.conversation_id.in_(ids), ConversationEvent.created_at >= start)
    ).all():
        if event == "escalation":
            counts[conversation_id]["escalation"] += 1
            if cause == "handoff:kb_miss":
                counts[conversation_id]["kb_miss"] += 1
        elif event == "unknown_intent":
            counts[conversation_id]["unknown_intent"] += 1

    return {
        "window_days": window_days,
        "signal": signal,
        "conversations": [
            {
                "conversation_id": conversation_id,
                "customer_id": conversations[conversation_id].customer_id,
                "wa_phone": conversations[conversation_id].wa_phone,
                "state": conversations[conversation_id].state.value,
                "last_message_at": (
                    conversations[conversation_id].last_message_at.isoformat()
                    if conversations[conversation_id].last_message_at
                    else None
                ),
                "signals": counts[conversation_id],
            }
            for conversation_id in ids
            if conversation_id in conversations
        ],
    }
