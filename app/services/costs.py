"""Cost tracking service (design D6; SS-3/SS-4 basis).

`record_llm_cost` writes the token-based cost of an LLM call onto the message
row (`messages.cost_llm`, USD). Rates are reference prices: gpt-4o-mini
~$0.15/1M in + $0.60/1M out (OpenRouter default model), deepseek-chat
reference from DeepSeek API docs — verify at activation. Local fastembed
embeddings cost $0 (no token billing) and are never recorded here.
`conversation_spend`/`daily_spend` (T3.6) sum the columns per D6 (no separate
ledger table).

T4.5 adds the SS-3 guardrails on top of those sums:

- `conversation_cost_state` / `daily_cost_state` — total functions returning
  ``(percent, mode)`` with mode ``normal`` | ``conservative`` | ``blocked``,
  driven by the settings limits ``cost.conversation_limit`` (default $1.50)
  and ``cost.daily_limit`` (default $5.00). 80% -> conservative, 100% ->
  blocked (percent computed in Decimal so the 80/100 boundaries are exact).
- `maybe_alert_owner` — SS-3 owner alert, ONE per scope+threshold crossing,
  deduped through the audit_log (the row is both the SH-5 record and the
  dedupe marker): an audit entry + an email to ``notify.owner_email`` via the
  T4.3 notify service. Minimal H1 behavior (documented): no WhatsApp cost-
  alert template exists (Meta approval pending, T2.1), so the alert is email
  + audit only. Never raises.
- `spend_snapshot` — SS-4 read model (spend + limits + mode) for the panel
  (T5.5 consumes it; no UI here).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, InternalChatMessage, Message
from app.services.audit import record_audit
from app.services.notify import send_email
from app.services.settings import get_setting

logger = logging.getLogger(__name__)

# (input_rate_per_1M, output_rate_per_1M) USD — reference, verify at activation.
LLM_RATES: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
    "deepseek-chat": (Decimal("0.27"), Decimal("1.10")),  # DeepSeek reference, verify
}

# SS-3 guardrail defaults (settings keys registered in SETTINGS_DEFAULTS).
DEFAULT_CONVERSATION_LIMIT = Decimal("1.50")
DEFAULT_DAILY_LIMIT = Decimal("5.00")
THRESHOLD_CONSERVATIVE = 80.0
THRESHOLD_BLOCK = 100.0


def record_llm_cost(
    session: Session,
    message_id: int | None = None,
    model: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    *,
    target: InternalChatMessage | None = None,
    call_key: str | None = None,
) -> Decimal:
    """Accumulate one call on a WhatsApp or internal request row."""
    internal = target is not None
    if target is None:
        target = session.get(Message, message_id)
    elif call_key is not None:
        target = session.scalar(
            select(InternalChatMessage)
            .where(InternalChatMessage.id == target.id)
            .with_for_update()
        )
        calls = dict(target.assistant_metadata or {}).get("cost_calls", {})
        if call_key in calls:
            return Decimal("0")

    rates = get_setting(session, "cost.llm_rates", default=LLM_RATES)
    configured = rates.get(model) if isinstance(rates, dict) else None
    if configured is None:
        configured = LLM_RATES.get(model)
    if isinstance(configured, dict):
        in_rate = Decimal(str(configured.get("input_per_1m", configured.get("input", 0))))
        out_rate = Decimal(str(configured.get("output_per_1m", configured.get("output", 0))))
    else:
        in_rate, out_rate = configured or (Decimal("0"), Decimal("0"))
        in_rate, out_rate = Decimal(str(in_rate)), Decimal(str(out_rate))
    diagnostic = None
    if configured is None:
        diagnostic = {"type": "unknown_model", "model": model}
    elif prompt_tokens is None or completion_tokens is None:
        diagnostic = {"type": "usage_unavailable", "model": model}
    prompt_tokens = prompt_tokens or 0
    completion_tokens = completion_tokens or 0
    cost = (
        Decimal(prompt_tokens) / Decimal(1_000_000) * in_rate
        + Decimal(completion_tokens) / Decimal(1_000_000) * out_rate
    )
    if target is not None:
        previous = Decimal(target.cost_llm or 0)
        target.cost_llm = float(previous + cost)
        if internal and call_key is not None:
            metadata = dict(target.assistant_metadata or {})
            calls = dict(metadata.get("cost_calls", {}))
            calls[call_key] = {
                "model": model, "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens, "cost": float(cost),
            }
            metadata["cost_calls"] = calls
            if diagnostic is not None:
                metadata.setdefault("cost_diagnostics", []).append(diagnostic)
            target.assistant_metadata = metadata
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


def internal_thread_spend(session: Session, thread_id: int) -> float:
    """Total measured assistant spend for one internal thread."""
    value = session.scalar(
        select(func.sum(InternalChatMessage.cost_llm)).where(
            InternalChatMessage.thread_id == thread_id
        )
    )
    return float(value or 0)


def daily_spend(session: Session, day: date | None = None) -> float:
    """Total spend (LLM + Meta) of a calendar day, UTC (D6, SS-3 basis).

    Timestamps are UTC (DB now()); the default day is the UTC date so the
    window always matches the stored rows.
    """
    day = day or datetime.now(timezone.utc).date()
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = datetime.combine(day, time.max, tzinfo=timezone.utc)
    whatsapp = _sum_columns(session, Message.created_at >= start, Message.created_at <= end)
    internal = session.scalar(
        select(func.sum(InternalChatMessage.cost_llm)).where(
            InternalChatMessage.created_at >= start,
            InternalChatMessage.created_at <= end,
        )
    )
    return whatsapp + float(internal or 0)


# ---------------------------------------------------------------------------
# T4.5 — SS-3 guardrails: cost state, owner alerts, panel snapshot.
# ---------------------------------------------------------------------------


def _percent(spend: float, limit: float) -> float:
    """Spend as a percent of the limit, computed in Decimal (exact 80/100).

    float division would give 79.999.../80.000... at the boundaries; the
    Decimal(str()) round-trip makes `1.20 of 1.50` exactly 80.0.
    """
    if limit <= 0:
        return 0.0
    return float(Decimal(str(spend)) / Decimal(str(limit)) * 100)


def _mode_for(percent: float) -> str:
    """SS-3 mode from a percent: 100+ -> blocked, 80+ -> conservative."""
    if percent >= THRESHOLD_BLOCK:
        return "blocked"
    if percent >= THRESHOLD_CONSERVATIVE:
        return "conservative"
    return "normal"


def combined_cost_mode(*modes: str) -> str:
    """Worst mode wins (blocked > conservative > normal) for the gate."""
    if "blocked" in modes:
        return "blocked"
    if "conservative" in modes:
        return "conservative"
    return "normal"


def _limit(session: Session, scope: str) -> float:
    """Configured spend limit for a scope ("conversation" | "daily")."""
    default = (
        float(DEFAULT_CONVERSATION_LIMIT)
        if scope == "conversation"
        else float(DEFAULT_DAILY_LIMIT)
    )
    return float(get_setting(session, f"cost.{scope}_limit", default=default))


def conversation_cost_state(
    session: Session, conversation_id: int
) -> tuple[float, str]:
    """SS-3: (percent, mode) of one conversation against its limit.

    Total function used by the cost gate: reads the stored/ default
    ``cost.conversation_limit`` on every call (KV read, no cache).
    """
    percent = _percent(
        conversation_spend(session, conversation_id), _limit(session, "conversation")
    )
    return percent, _mode_for(percent)


def internal_thread_cost_state(
    session: Session, thread_id: int
) -> tuple[float, str]:
    """SS-3: (percent, mode) for one internal assistant thread."""
    percent = _percent(
        internal_thread_spend(session, thread_id), _limit(session, "conversation")
    )
    return percent, _mode_for(percent)


def daily_cost_state(session: Session, day: date | None = None) -> tuple[float, str]:
    """SS-3: (percent, mode) of the UTC day against its limit."""
    percent = _percent(daily_spend(session, day), _limit(session, "daily"))
    return percent, _mode_for(percent)


def maybe_alert_owner(
    session: Session,
    *,
    scope: str,
    entity_id: str,
    percent: float,
    spend: float,
) -> bool:
    """SS-3: one owner alert per scope+threshold crossing; audit-deduped.

    Fires only at 80%+; the 100% crossing is a separate alert from the 80%
    one (distinct audit actions). Dedupe = an audit row with the same
    action+entity+entity_id already exists, so a conversation stuck at 85%
    alerts once and a daily alert is per-UTC-day (entity_id = the date).

    Minimal H1 behavior (documented): the alert is an audit entry (SH-5) +
    an email to ``notify.owner_email`` via the T4.3 notify service. A
    WhatsApp cost-alert template would require Meta approval (T2.1) — the
    email fallback channel already covers the owner in H1. Never raises.

    Returns True when an alert was sent.
    """
    if percent < THRESHOLD_CONSERVATIVE:
        return False
    action = _alert_action(scope, percent)
    existing = session.scalar(
        select(AuditLog.id).where(
            AuditLog.action == action,
            AuditLog.entity == scope,
            AuditLog.entity_id == entity_id,
        )
    )
    if existing is not None:
        return False
    limit = _limit(session, scope)
    record_audit(
        session,
        actor="system",
        action=action,
        entity=scope,
        entity_id=entity_id,
        after={"percent": round(percent, 2), "spend": round(spend, 4), "limit": limit},
    )
    session.flush()
    _email_owner_alert(session, scope, entity_id, percent, spend, limit)
    return True


def _alert_action(scope: str, percent: float) -> str:
    threshold = "100" if percent >= THRESHOLD_BLOCK else "80"
    return f"cost.alert.{scope}.{threshold}"


def _email_owner_alert(
    session: Session,
    scope: str,
    entity_id: str,
    percent: float,
    spend: float,
    limit: float,
) -> None:
    """The email half of the SS-3 alert (never raises; alert is best-effort)."""
    subject = f"Lumat: alerta de costo {scope} al {percent:.0f}%"
    body = (
        f"El gasto {scope} {entity_id} alcanzó {percent:.0f}% del límite "
        f"(${spend:.2f} de ${limit:.2f}).\n"
        "Revisa los límites en la configuración o deriva a un asesor."
    )
    try:
        send_email(session, get_setting(session, "notify.owner_email"), subject, body)
    except Exception:
        logger.exception("cost alert email failed for %s %s", scope, entity_id)


def spend_snapshot(session: Session, conversation_id: int | None = None) -> dict:
    """SS-4 read model: current/daily spend + limits + mode for the panel.

    With ``conversation_id`` the snapshot includes the per-conversation
    scope and the combined mode (worst of both); without it, only the daily
    scope (T5.5 panel/settings view). No UI here — the panel consumes this.
    """
    today = datetime.now(timezone.utc).date()
    day_percent, day_mode = daily_cost_state(session)
    snapshot = {
        "date": today.isoformat(),
        "conversation_spend": None,
        "conversation_limit": _limit(session, "conversation"),
        "conversation_percent": None,
        "daily_spend": round(daily_spend(session), 4),
        "daily_limit": _limit(session, "daily"),
        "daily_percent": round(day_percent, 2),
        "mode": day_mode,
    }
    if conversation_id is not None:
        conv_percent, conv_mode = conversation_cost_state(session, conversation_id)
        snapshot.update(
            {
                "conversation_spend": round(conversation_spend(session, conversation_id), 4),
                "conversation_percent": round(conv_percent, 2),
                "mode": combined_cost_mode(conv_mode, day_mode),
            }
        )
    return snapshot
