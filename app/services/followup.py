"""Detect idle conversations and overdue commitments for operational follow-up."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Commitment,
    Conversation,
    ConversationEvent,
    ConversationState,
    Customer,
    Message,
    MessageDirection,
)
from app.services import notify
from app.services.settings import (
    get_followup_idle_enabled,
    get_followup_idle_hours,
    get_followup_idle_template_name,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PendingFollowup:
    conversation_id: int
    event: str
    cause: str


def _idle_thread(session: Session, conversation: Conversation, *, now: datetime, hours: int):
    """Return the last inbound only when it is older than the follow-up threshold.

    Tukulpan's `_fires_sin_respuesta` is intentionally not reused: that close-time
    predicate has the inverse age window (it rejects messages older than the SLA)
    and reads `datetime.now()`/`obs_no_reply_hours`, while this sweep evaluates an
    explicit `now` and finds messages older than the configured idle threshold.
    """
    last = session.scalar(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id.desc())
        .limit(1)
    )
    if (
        last is None
        or last.direction != MessageDirection.INBOUND
        or last.created_at is None
        or last.created_at >= now - timedelta(hours=hours)
    ):
        return None
    return last


def detect_pending(session: Session, *, now: datetime) -> list[PendingFollowup]:
    """Find idle inbound threads and pending commitments past their due date.

    One query for the whole sweep, not one per conversation: the cron runs every
    few minutes over every open conversation, and a per-conversation read is the
    N+1 that turns a five-second job into a timeout as the table grows.
    """
    hours = get_followup_idle_hours(session)
    threshold = now - timedelta(hours=hours)
    found: list[PendingFollowup] = []

    latest = (
        select(Message.conversation_id, func.max(Message.id).label("last_id"))
        .group_by(Message.conversation_id)
        .subquery()
    )
    idle_rows = session.execute(
        select(Message.conversation_id, Message.id, Message.created_at)
        .join(latest, Message.id == latest.c.last_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.state != ConversationState.CLOSED,
            Message.direction == MessageDirection.INBOUND,
            Message.created_at < threshold,
        )
    ).all()
    for conversation_id, message_id, created_at in idle_rows:
        silent_hours = (now - created_at).total_seconds() / 3600
        found.append(PendingFollowup(
            conversation_id=conversation_id,
            event="idle_thread",
            # Stable on purpose: this exact string is the dedupe key, so the same
            # silence is never recorded twice and a NEW silence (a newer inbound)
            # is a new fact.
            cause=f"mensaje {message_id} sin respuesta ({silent_hours:.0f} h)",
        ))

    commitments = session.scalars(
        select(Commitment).where(
            Commitment.status == "pendiente",
            Commitment.due_at.is_not(None),
            Commitment.due_at < now,
            Commitment.conversation_id.is_not(None),
        )
    ).all()
    for commitment in commitments:
        days_overdue = (now - commitment.due_at).total_seconds() / 86400
        found.append(PendingFollowup(
            conversation_id=commitment.conversation_id,
            event="commitment_overdue",
            cause=f"compromiso {commitment.id} vencido hace {days_overdue:.0f} días",
        ))
    return found


def _record_once(session: Session, item: PendingFollowup) -> bool:
    """Record a fact unless this exact fact is already recorded.

    The key is (event, cause) and the cause is stable per fact, so a second
    overdue commitment on the same conversation is recorded too, and a thread
    that goes silent again after a reply is a new fact rather than a duplicate.
    Deduplicating by event type alone lost both.
    """
    exists = session.scalar(
        select(ConversationEvent.id)
        .where(
            ConversationEvent.conversation_id == item.conversation_id,
            ConversationEvent.event == item.event,
            ConversationEvent.cause == item.cause,
        )
        .limit(1)
    )
    if exists is not None:
        return False
    session.add(ConversationEvent(
        conversation_id=item.conversation_id,
        event=item.event,
        cause=item.cause,
        actor="bot",
    ))
    session.flush()
    return True


def _send_idle_followup(session: Session, conversation_id: int) -> bool:
    """Send one owner-configured approved WhatsApp template, never raising."""
    if not get_followup_idle_enabled(session):
        return False
    template_name = get_followup_idle_template_name(session)
    if not template_name:
        return False
    if session.scalar(select(ConversationEvent.id).where(
        ConversationEvent.conversation_id == conversation_id,
        ConversationEvent.event == "idle_followup_sent",
    ).limit(1)) is not None:
        return False

    # The owner asserts the name is an approved Meta template, exactly like the
    # technician visit actions: requiring a locally published version row would
    # silently disable this feature for a name the operator already knows works.
    try:
        conversation = session.get(Conversation, conversation_id)
        customer = session.get(Customer, conversation.customer_id) if conversation else None
        if customer is None:
            logger.warning("idle follow-up conversation %s has no customer", conversation_id)
            return False
        notify.send_template(customer.phone_e164, [], template_name=template_name)
    except Exception:
        logger.exception("idle follow-up send failed for conversation %s", conversation_id)
        return False

    session.add(ConversationEvent(
        conversation_id=conversation_id,
        event="idle_followup_sent",
        cause=f"plantilla aprobada {template_name}",
        actor="bot",
    ))
    session.flush()
    return True


def sweep_followup(session: Session, *, now: datetime) -> int:
    """Record newly observed follow-up facts and send only when explicitly enabled."""
    recorded = 0
    for item in detect_pending(session, now=now):
        recorded += _record_once(session, item)
        if item.event == "idle_thread":
            _send_idle_followup(session, item.conversation_id)
    return recorded
