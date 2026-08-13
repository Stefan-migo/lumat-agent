"""Cost tracking service (design D6; SS-4 tracking basis).

`record_llm_cost` writes the token-based cost of an LLM call onto the message
row (`messages.cost_llm`, USD). Rates are the reference prices from the design
(LumatRequest §1.12): gpt-4o-mini ~$0.15/1M in + $0.60/1M out,
text-embedding-3-small $0.02/1M. `conversation_spend`/`daily_spend` (T3.6)
sum the columns per D6 (no separate ledger table).
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Message

# (input_rate_per_1M, output_rate_per_1M) USD — reference, verify at activation.
LLM_RATES: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
    "text-embedding-3-small": (Decimal("0.02"), Decimal("0.02")),
}


def record_llm_cost(
    session: Session,
    message_id: int,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal:
    """Accumulate the token cost of one LLM call on the message (D6)."""
    in_rate, out_rate = LLM_RATES.get(model, (Decimal("0"), Decimal("0")))
    cost = (
        Decimal(prompt_tokens) / Decimal(1_000_000) * in_rate
        + Decimal(completion_tokens) / Decimal(1_000_000) * out_rate
    )
    message = session.get(Message, message_id)
    if message is not None:
        previous = Decimal(message.cost_llm or 0)
        message.cost_llm = float(previous + cost)
    return cost


def _sum_columns(session: Session, *filters) -> float:
    """SUM(cost_llm) + SUM(cost_meta) over the filtered messages (D6)."""
    statement = select(
        func.sum(Message.cost_llm),
        func.sum(Message.cost_meta),
    )
    for condition in filters:
        statement = statement.where(condition)
    row = session.execute(statement).one()
    return float((row[0] or 0) + (row[1] or 0))


def conversation_spend(session: Session, conversation_id: int) -> float:
    """Total spend (LLM + Meta) of one conversation (D6, SS-3 basis)."""
    return _sum_columns(session, Message.conversation_id == conversation_id)


def daily_spend(session: Session, day: date | None = None) -> float:
    """Total spend (LLM + Meta) of a calendar day, UTC (D6, SS-3 basis).

    Timestamps are UTC (DB now()); the default day is the UTC date so the
    window always matches the stored rows.
    """
    day = day or datetime.now(timezone.utc).date()
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = datetime.combine(day, time.max, tzinfo=timezone.utc)
    return _sum_columns(session, Message.created_at >= start, Message.created_at <= end)
