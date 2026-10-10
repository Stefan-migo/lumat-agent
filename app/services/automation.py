"""Deterministic, audited rule evaluation for domain events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutomationExecution, AutomationRule, DomainEvent
from app.services.audit import record_audit
from app.services.notifications import create_operation
from app.services.settings import get_setting

ALLOWED_CHANNELS = {"whatsapp", "email"}
ALLOWED_EVENTS = {"message.received", "case.created", "case.updated", "appointment.booked", "appointment.rescheduled", "appointment.cancelled", "appointment.completed", "appointment.no_show", "appointment.review_due", "customer.maintenance_due", "admin.daily_summary_due", "admin.weekly_summary_due"}
MAX_AUTHORING_COOLDOWN_SECONDS = 2_592_000


class RuleValidationError(ValueError):
    def __init__(self, field: str, detail: str):
        self.field = field
        self.detail = detail
        super().__init__(detail)


def validate_rule_input(data: dict) -> dict:
    """Validate the bounded authoring contract without changing evaluation policy."""
    for field in ("name", "event_type", "channel", "template_event"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise RuleValidationError(field, "must be a non-empty string")
    if data["event_type"] not in ALLOWED_EVENTS:
        raise RuleValidationError("event_type", "unsupported event")
    if data["template_event"] not in ALLOWED_EVENTS:
        raise RuleValidationError("template_event", "unsupported event")
    if data["channel"] not in ALLOWED_CHANNELS:
        raise RuleValidationError("channel", "unsupported channel")
    cooldown = data.get("cooldown_seconds")
    if isinstance(cooldown, bool) or not isinstance(cooldown, int) or not 0 <= cooldown <= MAX_AUTHORING_COOLDOWN_SECONDS:
        raise RuleValidationError("cooldown_seconds", "must be an integer between 0 and 2592000")
    conditions = data.get("conditions")
    if not isinstance(conditions, dict):
        raise RuleValidationError("conditions", "must be a flat object")
    for key, value in conditions.items():
        if not isinstance(key, str) or not key.strip() or isinstance(value, (dict, list)):
            raise RuleValidationError("conditions", "must contain only scalar exact-match values")
    return {
        "name": data["name"].strip(),
        "event_type": data["event_type"],
        "conditions": conditions,
        "channel": data["channel"],
        "template_event": data["template_event"],
        "cooldown_seconds": cooldown,
    }


def rule_snapshot(rule: AutomationRule) -> dict:
    return {
        "id": rule.id,
        "name": rule.name,
        "event_type": rule.event_type,
        "conditions": rule.conditions or {},
        "channel": rule.channel,
        "template_event": rule.template_event,
        "cooldown_seconds": rule.cooldown_seconds,
        "enabled": rule.enabled,
        "created_by": rule.created_by,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


def create_rule(
    session: Session,
    data: dict,
    *,
    actor: str,
    executor_origin: bool = False,
) -> AutomationRule:
    if actor == "assistant" and not executor_origin:
        raise PermissionError("assistant rules must originate from the approved tool executor")
    values = validate_rule_input(data)
    rule = AutomationRule(**values, enabled=True, created_by=actor)
    session.add(rule)
    session.flush()
    record_audit(session, actor=actor, action="automation.rule.create", entity="automation_rule", entity_id=str(rule.id), after=rule_snapshot(rule))
    return rule


def update_rule(session: Session, rule: AutomationRule, data: dict, *, actor: str) -> AutomationRule:
    before = rule_snapshot(rule)
    values = validate_rule_input(data)
    for field, value in values.items():
        setattr(rule, field, value)
    session.flush()
    record_audit(session, actor=actor, action="automation.rule.update", entity="automation_rule", entity_id=str(rule.id), before=before, after=rule_snapshot(rule))
    return rule


def set_rule_enabled(session: Session, rule: AutomationRule, enabled: bool, *, actor: str) -> AutomationRule:
    before = rule_snapshot(rule)
    rule.enabled = enabled
    session.flush()
    action = "automation.rule.enable" if enabled else "automation.rule.disable"
    record_audit(session, actor=actor, action=action, entity="automation_rule", entity_id=str(rule.id), before=before, after=rule_snapshot(rule))
    return rule


def _matches(conditions: dict, payload: dict) -> bool:
    return all(payload.get(key) == value for key, value in conditions.items())


def _resolve_recipient(session: Session, rule: AutomationRule, event: DomainEvent):
    if rule.recipient_target == "admin":
        key = "notify.owner_whatsapp" if rule.channel == "whatsapp" else "notify.owner_email"
        return get_setting(session, key)
    payload = event.payload or {}
    return payload.get("recipient") or payload.get("phone") or payload.get("email")


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
                payload = event.payload or {}
                recipient = _resolve_recipient(session, rule, event)
                content = payload.get("content") or payload.get("text") or rule.content or rule.template_event
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
