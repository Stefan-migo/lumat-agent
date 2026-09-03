"""Deterministic, audited rule evaluation for domain events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutomationExecution, AutomationRule, DomainEvent
from app.services.audit import record_audit
from app.services.notifications import create_operation

ALLOWED_CHANNELS = {"whatsapp", "email"}
ALLOWED_EVENTS = {"message.received", "case.created", "case.updated", "appointment.booked", "appointment.cancelled"}


def _matches(conditions: dict, payload: dict) -> bool:
    return all(payload.get(key) == value for key, value in conditions.items())


def evaluate_event(session: Session, event: DomainEvent) -> list[int]:
    """Evaluate every applicable rule and return ids that created/reused work."""
    now = datetime.now(timezone.utc)
    operation_rule_ids: list[int] = []
    rules = session.scalars(
        select(AutomationRule).where(AutomationRule.event_type == event.event_type)
    ).all()
    for rule in rules:
        execution_key = f"automation:{rule.id}:event:{event.id}"
        existing = session.scalar(select(AutomationExecution).where(AutomationExecution.execution_key == execution_key))
        if existing is not None:
            if existing.operation_id is not None:
                operation_rule_ids.append(rule.id)
            continue
        reason = None
        operation = None
        if not rule.enabled:
            outcome, reason = "skipped", "disabled"
            record_audit(session, actor="system", action="automation.skipped", entity="automation_rule", entity_id=str(rule.id), after={"reason": reason, "event_id": event.id})
        elif event.event_type not in ALLOWED_EVENTS or rule.channel not in ALLOWED_CHANNELS or rule.template_event not in ALLOWED_EVENTS:
            outcome, reason = "skipped", "policy_not_allowed"
        elif not _matches(rule.conditions or {}, event.payload or {}):
            outcome, reason = "skipped", "conditions_not_matched"
        else:
            # Cooldown is scoped to the same source entity, not to event ids.
            recent = session.scalar(select(AutomationExecution).join(DomainEvent, AutomationExecution.event_id == DomainEvent.id).where(
                AutomationExecution.rule_id == rule.id,
                AutomationExecution.outcome == "enqueued",
                DomainEvent.entity_type == event.entity_type,
                DomainEvent.entity_id == event.entity_id,
                AutomationExecution.created_at >= now - timedelta(seconds=rule.cooldown_seconds),
            )) if rule.cooldown_seconds else None
            if recent is not None:
                outcome, reason = "skipped", "cooldown"
            else:
                recipient = event.payload.get("recipient") or event.payload.get("phone") or event.payload.get("email")
                content = event.payload.get("content") or event.payload.get("text") or rule.template_event
                if not recipient:
                    outcome, reason = "skipped", "missing_recipient"
                else:
                    operation = create_operation(session, recipient=recipient, channel=rule.channel, content=content, source_entity=event.entity_type, source_id=event.entity_id, idempotency_key=execution_key, event_id=event.id)
                    outcome, reason = "enqueued", "matched"
                    operation_rule_ids.append(rule.id)
        session.add(AutomationExecution(rule_id=rule.id, event_id=event.id, execution_key=execution_key, outcome=outcome, reason=reason, operation_id=operation.id if operation else None))
        record_audit(session, actor="system", action="automation.evaluated", entity="automation_rule", entity_id=str(rule.id), after={"event_id": event.id, "outcome": outcome, "reason": reason})
    session.flush()
    return operation_rule_ids
