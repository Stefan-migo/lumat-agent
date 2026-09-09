"""Panel JSON API serializers (B2/T2.1+T2.2; PDW-API, D4).

ORM rows -> plain dicts at the API boundary: no SQLAlchemy objects ever
leave the JSON layer (PDW-API "no ORM leak"). Field names are the service
dict keys (snake_case, same as `customer_history` in app/services/
customers.py), and datetimes are converted to ISO-8601 strings so the
response is fully JSON-native before FastAPI even encodes it.

Each serializer mirrors what the corresponding Jinja template renders —
the SPA must show the same fields the current panel shows.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

from app.models import (
    Case,
    Conversation,
    Customer,
    CustomerNote,
    KbDocument,
    Memory,
    Message,
    User,
    Appointment,
    AppointmentCalendarSync,
    NotificationTemplateVersion,
    NotificationOperation,
    PanelNotification,
    InternalChatMessage,
    InternalChatThread,
    AutomationRule,
)


def _iso(value) -> str | None:
    """ISO-8601 string for a tz-aware datetime, else None (PDW-API)."""
    return value.isoformat() if value is not None else None


def to_customer_dict(customer: Customer) -> dict:
    """Customer row -> snake_case service dict (ficha + clients list)."""
    return {
        "id": customer.id,
        "phone_e164": customer.phone_e164,
        "name": customer.name,
        "email": customer.email,
        "comuna": customer.comuna,
        "address": customer.address,
        "state": customer.state.value,
        "consent_status": customer.consent_status,
        "consent_at": _iso(customer.consent_at),
        "created_at": _iso(customer.created_at),
    }


def to_note_dict(note: CustomerNote) -> dict:
    """Internal staff note -> snake_case service dict (CR-4)."""
    return {
        "id": note.id,
        "customer_id": note.customer_id,
        "note": note.note,
        "author": note.author,
        "created_at": _iso(note.created_at),
    }


def to_message_dict(message: Message) -> dict:
    """Message row -> snake_case service dict (thread media link, PDW-TST-3)."""
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "author_id": message.author_id,
        "request_id": message.request_id,
        "direction": message.direction.value,
        "msg_type": message.msg_type.value,
        "text": message.text,
        "media_url": message.media_url,
        "delivery_status": message.delivery_status.value if message.delivery_status else None,
        "delivery_error": message.delivery_error,
        "delivery_attempts": message.delivery_attempts,
        "last_attempt_at": _iso(message.last_attempt_at),
        "delivered_at": _iso(message.delivered_at),
        "created_at": _iso(message.created_at),
    }


def to_conversation_dict(
    conversation: Conversation,
    *,
    latest_inbound_at=None,
    reply_window_open: bool = False,
    delivery_summary: dict[str, int] | None = None,
) -> dict:
    """Conversation row -> snake_case service dict (B3/T3.1).

    Window and delivery values are supplied by the API read model. Defaults
    are deliberately closed and empty so internal audit payloads cannot imply
    eligibility or pending work that was not observed.
    """
    delivery_summary = delivery_summary or {
        "pending": 0,
        "sending": 0,
        "sent": 0,
        "failed": 0,
        "unknown": 0,
    }
    return {
        "id": conversation.id,
        "customer_id": conversation.customer_id,
        "wa_phone": conversation.wa_phone,
        "state": conversation.state.value,
        "responsible_id": conversation.responsible_id,
        "version": conversation.version,
        "summary": conversation.summary,
        "latest_inbound_at": _iso(latest_inbound_at),
        "reply_window_open": reply_window_open,
        "delivery_summary": delivery_summary,
        "last_message_at": _iso(conversation.last_message_at),
        "created_at": _iso(conversation.created_at),
        "closed_at": _iso(conversation.closed_at),
    }


def to_active_conversation_dict(
    conversation: Conversation, *, customer_name: str | None
) -> dict:
    """Conversation row -> the compact active-summary rail shape."""
    return {
        "id": conversation.id,
        "customer_name": customer_name,
        "state": conversation.state.value,
        "last_message_at": _iso(conversation.last_message_at),
    }


def to_case_dict(case: Case) -> dict:
    """Case row -> snake_case service dict (B3/T3.2)."""
    return {
        "id": case.id,
        "conversation_id": case.conversation_id,
        "customer_id": case.customer_id,
        "created_at": _iso(case.created_at),
        "service": case.service,
        "priority": case.priority,
        "status": case.status,
        "emergency": case.emergency,
        "responsible_id": case.responsible_id,
        "summary": case.summary,
        "escalated_at": _iso(case.escalated_at),
        "closed_at": _iso(case.closed_at),
        "acknowledged_at": _iso(case.acknowledged_at),
        "ack_by": case.ack_by,
    }


def to_user_dict(user: User) -> dict:
    """User row -> minimal {id, username} dict (D8 — embedded in cases, no /users)."""
    return {"id": user.id, "username": user.username}


def to_appointment_dict(appointment: Appointment) -> dict:
    return {
        "id": appointment.id,
        "service": appointment.service,
        "customer_id": appointment.customer_id,
        "case_id": appointment.case_id,
        "technician_id": appointment.technician_id,
        "local_start": appointment.local_start.isoformat(),
        "timezone": appointment.timezone,
        "starts_at": _iso(appointment.starts_at),
        "ends_at": _iso(appointment.ends_at),
        "duration_minutes": appointment.duration_minutes,
        "status": appointment.status.value,
        "history": [
            {"id": h.id, "actor": h.actor, "action": h.action,
             "from_status": h.from_status.value if h.from_status else None,
             "to_status": h.to_status.value, "details": h.details,
             "created_at": _iso(h.created_at)}
            for h in appointment.history
        ],
    }


def to_today_appointment_dict(appointment: Appointment, customer_name: str | None) -> dict:
    return {
        "id": appointment.id,
        "service": appointment.service,
        "customer_name": customer_name,
        "local_start": appointment.local_start.isoformat(),
        "starts_at": _iso(appointment.starts_at),
        "ends_at": _iso(appointment.ends_at),
    }


def to_today_conversation_dict(conversation: Conversation, customer_name: str | None, last_message_at) -> dict:
    return {
        "id": conversation.id,
        "customer_name": customer_name,
        "last_message_at": _iso(last_message_at),
        "state": conversation.state.value.upper(),
    }


def to_today_case_dict(case: Case, customer_name: str | None) -> dict:
    return {
        "id": case.id,
        "customer_name": customer_name,
        "service": case.service,
        "summary": case.summary,
        "emergency": case.emergency,
        "escalated_at": _iso(case.escalated_at),
    }


def to_automation_rule_dict(rule: AutomationRule) -> dict:
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
        "created_at": _iso(rule.created_at),
        "updated_at": _iso(rule.updated_at),
    }


def to_agenda_dict(appointment: Appointment, *, customer_name: str | None, case_name: str | None, technician_name: str | None, timezone_name: str, sync: AppointmentCalendarSync | None) -> dict:
    local_start = appointment.starts_at.astimezone(ZoneInfo(timezone_name))
    return {
        "id": appointment.id,
        "service": appointment.service,
        "customer_id": appointment.customer_id,
        "customer_name": customer_name,
        "case_id": appointment.case_id,
        "case_name": case_name,
        "technician_id": appointment.technician_id,
        "technician_name": technician_name,
        "local_start": local_start.isoformat(),
        "timezone": timezone_name,
        "starts_at": _iso(appointment.starts_at),
        "ends_at": _iso(appointment.ends_at),
        "status": appointment.status.value,
        "sync": {
            "status": sync.status if sync else "pending",
            "error": sync.error if sync else None,
            "retry": sync.status in {"pending", "failed"} if sync else True,
        },
    }


def to_calendar_dict(sync: AppointmentCalendarSync) -> dict:
    return {
        "id": sync.id, "appointment_id": sync.appointment_id, "provider": sync.provider,
        "uid": sync.uid, "idempotency_key": sync.idempotency_key, "status": sync.status,
        "timezone": sync.timezone, "cancelled": sync.cancelled, "error": sync.error,
        "attempts": sync.attempts, "retry": sync.status in {"failed", "pending"},
        "synced_at": _iso(sync.synced_at),
    }


def to_template_dict(template: NotificationTemplateVersion) -> dict:
    return {
        "id": template.id, "event": template.event, "channel": template.channel,
        "locale": template.locale, "version": template.version, "content": template.content,
        "required_variables": template.required_variables, "approved": template.approved,
        "smtp_allowed": template.smtp_allowed, "created_at": _iso(template.created_at),
    }


def to_notification_dict(operation: NotificationOperation) -> dict:
    return {
        "id": operation.id,
        "recipient": operation.recipient,
        "channel": operation.channel,
        "source_entity": operation.source_entity,
        "source_id": operation.source_id,
        "status": operation.status,
        "attempts": operation.attempts,
        "error": operation.error,
        "next_attempt_at": _iso(operation.next_attempt_at),
        "last_attempt_at": _iso(operation.last_attempt_at),
        "delivered_at": _iso(operation.delivered_at),
        "action": "retry" if operation.status in {"retryable", "failed", "permanently_failed"} else None,
    }


def to_panel_notification_dict(notification: PanelNotification) -> dict:
    operation = notification.operation if hasattr(notification, "operation") else None
    return {
        "id": notification.id, "user_id": notification.user_id, "operation_id": notification.operation_id,
        "title": notification.title, "content": notification.content, "source": notification.source,
        "channel": operation.channel if operation else None, "status": notification.status,
        "read_at": _iso(notification.read_at), "created_at": _iso(notification.created_at),
    }


def to_internal_chat_thread_dict(thread: InternalChatThread) -> dict:
    return {
        "id": thread.id, "user_id": thread.user_id, "status": thread.status,
        "assistant_state": thread.assistant_state or {},
        "current_plan": thread.current_plan,
        "active_run_id": thread.active_run_id,
        "created_at": _iso(thread.created_at), "updated_at": _iso(thread.updated_at),
    }


def to_internal_chat_message_dict(message: InternalChatMessage) -> dict:
    return {
        "id": message.id, "thread_id": message.thread_id, "author": message.author,
        "content": message.content, "status": message.status, "error": message.error,
        "created_at": _iso(message.created_at), "completed_at": _iso(message.completed_at),
    }


def to_doc_dict(doc: KbDocument) -> dict:
    """KB document row -> snake_case dict (B4/T4.1; provider/model/cost, KB-3)."""
    return {
        "id": doc.id,
        "title": doc.title,
        "format": doc.format.value,
        "version": doc.version,
        "active_version": doc.active_version,
        "active": doc.active,
        "provider": doc.provider,
        "model": doc.model,
        "cost_meta": float(doc.cost_meta) if doc.cost_meta is not None else None,
        "created_at": _iso(doc.created_at),
    }


def to_memory_dict(memory: Memory) -> dict:
    """Memory row -> snake_case service dict (MEM-6 panel /clients/{id}/memories).

    Shape mirrors the design "Panel API + UI" payload: id, scope, entity_id,
    tipo, titulo, contenido, topic_key, pin, status, ISO datetimes.
    """
    return {
        "id": memory.id,
        "scope": memory.scope,
        "entity_id": memory.entity_id,
        "tipo": memory.tipo.value,
        "titulo": memory.titulo,
        "contenido": memory.contenido,
        "topic_key": memory.topic_key,
        "pin": memory.pin,
        "status": memory.status.value,
        "created_at": _iso(memory.created_at),
        "updated_at": _iso(memory.updated_at),
    }
