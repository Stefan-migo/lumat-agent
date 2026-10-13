"""Read-only analytics aggregates for chatbot performance."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

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
