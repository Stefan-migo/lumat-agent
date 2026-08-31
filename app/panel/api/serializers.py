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

from app.models import (
    Case,
    Conversation,
    Customer,
    CustomerNote,
    KbDocument,
    Memory,
    Message,
    User,
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
