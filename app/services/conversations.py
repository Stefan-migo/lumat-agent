"""Transactional commands for the production human inbox."""

from __future__ import annotations

from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chat.state import set_conversation_state
from app.config import get_settings
from app.models import AuditLog, Conversation, ConversationEvent, ConversationState, Customer, DeliveryStatus, Message, MessageDirection, MessageStatus, MessageType, User
from app.services.audit import record_audit
from app.services.send import deliver_message
from app.webhook.ingest import _safe_filename


def _to_conversation_dict(conversation: Conversation) -> dict:
    # Defer the serializer -> project_config -> tool-registry cycle back to conversations.
    from app.panel.api.serializers import to_conversation_dict

    return to_conversation_dict(conversation)


LEGAL_TRANSITIONS = {
    ConversationState.BOT: {ConversationState.HUMAN},
    ConversationState.HUMAN: {ConversationState.BOT, ConversationState.CLOSED},
    ConversationState.CLOSED: {ConversationState.BOT},
}


def list_conversations(session: Session, query: str | None = None, limit: int = 20) -> list[Conversation]:
    """Bounded conversation read projection for panel consumers."""
    statement = select(Conversation).join(Customer, Customer.id == Conversation.customer_id)
    if query:
        statement = statement.where(
            Customer.name.ilike(f"%{query}%") | Conversation.wa_phone.contains(query)
        )
    return list(session.scalars(statement.order_by(Conversation.last_message_at.desc().nulls_last(), Conversation.id.desc()).limit(limit)))


def conversation_transcript(session: Session, conversation_id: int, limit: int = 20) -> dict:
    """Bounded read-only transcript of one conversation for the assistant (S6).

    Reads the last `limit` messages (returned oldest-first) plus the conversation
    events, so the assistant can diagnose why the bot behaved as it did.
    """
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise ValueError("conversation not found")

    def _iso(value):
        return value.isoformat() if value is not None else None

    total = session.scalar(
        select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
    ) or 0
    messages = list(
        session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
    )
    messages.reverse()
    events = list(
        session.scalars(
            select(ConversationEvent)
            .where(ConversationEvent.conversation_id == conversation_id)
            .order_by(ConversationEvent.created_at.desc(), ConversationEvent.id.desc())
            .limit(limit)
        )
    )
    events.reverse()
    return {
        "conversation": {
            "id": conversation.id,
            "customer_id": conversation.customer_id,
            "wa_phone": conversation.wa_phone,
            "state": conversation.state.value,
            "summary": conversation.summary,
            "last_message_at": _iso(conversation.last_message_at),
            "closed_at": _iso(conversation.closed_at),
        },
        "messages": [
            {
                "direction": message.direction.value,
                "msg_type": message.msg_type.value,
                "text": message.text,
                "created_at": _iso(message.created_at),
            }
            for message in messages
        ],
        "messages_total": int(total),
        "events": [
            {"event": event.event, "cause": event.cause, "created_at": _iso(event.created_at)}
            for event in events
        ],
    }


def _audits(session: Session, conversation_id: int) -> list[AuditLog]:
    return list(session.scalars(select(AuditLog).where(AuditLog.entity_id == str(conversation_id))))


def _duplicate(
    session: Session,
    conversation: Conversation,
    actor: User,
    request_id: str,
    operation: str,
    payload: dict,
):
    for entry in _audits(session, conversation.id):
        after = entry.after or {}
        if after.get("request_id") != request_id:
            continue
        if after.get("operation") == operation and after.get("payload") == payload:
            return True
        _reject(
            session,
            conversation,
            actor,
            "conversation.request_rejected",
            request_id,
            "request_id already used for another command",
            payload,
            409,
        )
    return False


def _reject(session: Session, conversation: Conversation, actor: User, action: str, request_id: str, detail: str, payload: dict, status: int | None = None):
    record_audit(
        session, actor=actor.username, action=action, entity="conversation",
        entity_id=str(conversation.id), before=_to_conversation_dict(conversation),
        after={"request_id": request_id, "operation": action, "payload": payload, "detail": detail},
    )
    session.commit()
    raise HTTPException(status_code=status or (409 if "version" in detail or "transition" in detail else 403), detail=detail)


def change_state(session: Session, conversation_id: int, actor: User, state: ConversationState, expected_version: int, request_id: str) -> Conversation:
    conversation = session.scalar(select(Conversation).where(Conversation.id == conversation_id).with_for_update())
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    payload = {"state": state.value, "expected_version": expected_version}
    if _duplicate(session, conversation, actor, request_id, "state", payload):
        return conversation
    if conversation.version != expected_version:
        _reject(session, conversation, actor, "conversation.state_rejected", request_id, "conversation version conflict", payload)
    if state not in LEGAL_TRANSITIONS.get(conversation.state, set()):
        _reject(session, conversation, actor, "conversation.state_rejected", request_id, "illegal conversation state transition", payload)

    before = _to_conversation_dict(conversation)
    set_conversation_state(session, conversation, state, cause=f"panel:{request_id}", actor=actor.username)
    if state == ConversationState.HUMAN and conversation.responsible_id is None:
        conversation.responsible_id = actor.id
    elif state == ConversationState.BOT and conversation.responsible_id == actor.id:
        conversation.responsible_id = None
    conversation.version += 1
    record_audit(
        session, actor=actor.username, action="conversation.state_changed", entity="conversation",
        entity_id=str(conversation.id), before=before,
        after={**_to_conversation_dict(conversation), "request_id": request_id, "operation": "state", "payload": payload},
    )
    session.flush()
    return conversation


def assign(session: Session, conversation_id: int, actor: User, responsible_id: int | None, expected_version: int, request_id: str) -> Conversation:
    conversation = session.scalar(select(Conversation).where(Conversation.id == conversation_id).with_for_update())
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    payload = {"responsible_id": responsible_id, "expected_version": expected_version}
    if _duplicate(session, conversation, actor, request_id, "assignment", payload):
        return conversation
    if conversation.version != expected_version:
        _reject(session, conversation, actor, "conversation.assignment_rejected", request_id, "conversation version conflict", payload)
    if actor.role.value == "operador" and responsible_id not in (None, actor.id):
        _reject(session, conversation, actor, "conversation.assignment_rejected", request_id, "operators may assign only themselves", payload)
    if actor.role.value == "operador" and responsible_id is None and conversation.responsible_id not in (None, actor.id):
        _reject(session, conversation, actor, "conversation.assignment_rejected", request_id, "operators may clear only their own assignment", payload)
    target = session.get(User, responsible_id) if responsible_id is not None else None
    if responsible_id is not None and (target is None or not target.active or target.role.value != "operador"):
        _reject(session, conversation, actor, "conversation.assignment_rejected", request_id, "assignment target must be an active operator", payload, 422)

    before = _to_conversation_dict(conversation)
    conversation.responsible_id = responsible_id
    conversation.version += 1
    record_audit(
        session, actor=actor.username, action="conversation.assignment_changed", entity="conversation",
        entity_id=str(conversation.id), before=before,
        after={**_to_conversation_dict(conversation), "request_id": request_id, "operation": "assignment", "payload": payload},
    )
    session.flush()
    return conversation


def _latest_inbound(session: Session, conversation_id: int) -> Message | None:
    return session.scalar(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.direction == MessageDirection.INBOUND)
        .order_by(Message.created_at.desc(), Message.id.desc())
    )


def send_operator_message(session: Session, conversation_id: int, actor: User, text: str, request_id: str) -> Message:
    conversation = session.scalar(select(Conversation).where(Conversation.id == conversation_id).with_for_update())
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    payload = {"text": text}
    existing = session.scalar(select(Message).where(Message.request_id == request_id, Message.direction == MessageDirection.OUTBOUND))
    if existing is not None:
        if existing.conversation_id != conversation_id or existing.text != text:
            _reject(session, conversation, actor, "message.send_rejected", request_id, "request_id already used for another message", payload, 409)
        if existing.delivery_status == DeliveryStatus.SENT:
            return existing
        if existing.delivery_status in (DeliveryStatus.PENDING, DeliveryStatus.SENDING):
            raise HTTPException(status_code=409, detail="message delivery in progress")
        raise HTTPException(status_code=502, detail="message delivery failed")
    if conversation.state != ConversationState.HUMAN:
        _reject(session, conversation, actor, "message.send_rejected", request_id, "operator messages require human conversation", payload, 422)
    inbound = _latest_inbound(session, conversation_id)
    if inbound is None or inbound.created_at is None:
        _reject(session, conversation, actor, "message.send_rejected", request_id, "customer reply window expired", payload, 422)
    created = inbound.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created >= timedelta(hours=24):
        _reject(session, conversation, actor, "message.send_rejected", request_id, "customer reply window expired", payload, 422)
    message = Message(
        conversation_id=conversation_id, author_id=actor.id, request_id=request_id,
        direction=MessageDirection.OUTBOUND, msg_type=MessageType.TEXT, text=text,
        status=MessageStatus.PROCESSED, delivery_status=DeliveryStatus.PENDING,
    )
    session.add(message)
    session.flush()
    conversation.last_message_at = datetime.now(timezone.utc)
    record_audit(session, actor=actor.username, action="message.send_requested", entity="message", entity_id=str(message.id), after={"request_id": request_id, "conversation_id": conversation_id, "text": text})
    session.commit()
    return deliver_message(message.id)


MEDIA_SIZE_LIMITS = {"image": 5 * 1024 * 1024, "video": 16 * 1024 * 1024, "audio": 16 * 1024 * 1024, "document": 100 * 1024 * 1024}


def send_operator_media(session: Session, conversation_id: int, *, path: Path, content_type: str, filename: str, caption: str | None, actor: User, request_id: str) -> Message:
    """Persist and synchronously deliver one operator-uploaded media message."""
    path = Path(path)
    kind = content_type.split("/", 1)[0].lower()
    msg_type = {"image": MessageType.IMAGE, "video": MessageType.VIDEO, "audio": MessageType.AUDIO}.get(kind, MessageType.DOCUMENT)
    limit = MEDIA_SIZE_LIMITS[msg_type.value]
    size_bytes = path.stat().st_size
    if size_bytes > limit:
        raise ValueError(f"{msg_type.value} file exceeds the {limit // (1024 * 1024)} MB limit")

    conversation = session.scalar(select(Conversation).where(Conversation.id == conversation_id).with_for_update())
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    payload = {"content_type": content_type, "filename": filename, "caption": caption, "size_bytes": size_bytes}
    existing = session.scalar(select(Message).where(Message.request_id == request_id, Message.direction == MessageDirection.OUTBOUND))
    if existing is not None:
        if existing.conversation_id != conversation_id or existing.content_type != content_type or existing.filename != filename or existing.caption != caption:
            _reject(session, conversation, actor, "message.send_rejected", request_id, "request_id already used for another message", payload, 409)
        if existing.delivery_status == DeliveryStatus.SENT:
            return existing
        if existing.delivery_status in (DeliveryStatus.PENDING, DeliveryStatus.SENDING):
            raise HTTPException(status_code=409, detail="message delivery in progress")
        raise HTTPException(status_code=502, detail="message delivery failed")
    if conversation.state != ConversationState.HUMAN:
        _reject(session, conversation, actor, "message.send_rejected", request_id, "operator messages require human conversation", payload, 422)
    inbound = _latest_inbound(session, conversation_id)
    if inbound is None or inbound.created_at is None:
        _reject(session, conversation, actor, "message.send_rejected", request_id, "customer reply window expired", payload, 422)
    created = inbound.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created >= timedelta(hours=24):
        _reject(session, conversation, actor, "message.send_rejected", request_id, "customer reply window expired", payload, 422)

    settings = get_settings()
    media_dir = Path(settings.media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix
    safe_name = _safe_filename(f"{uuid.uuid4().hex}{ext}")
    stored_path = media_dir / safe_name
    shutil.copyfile(path, stored_path)
    message = Message(
        conversation_id=conversation_id, author_id=actor.id, request_id=request_id,
        direction=MessageDirection.OUTBOUND, msg_type=msg_type,
        status=MessageStatus.PROCESSED, delivery_status=DeliveryStatus.PENDING,
        stored_path=str(stored_path), content_type=content_type, filename=filename,
        size_bytes=size_bytes, caption=caption,
    )
    session.add(message)
    session.flush()
    conversation.last_message_at = datetime.now(timezone.utc)
    record_audit(session, actor=actor.username, action="message.send_requested", entity="message", entity_id=str(message.id), after={"request_id": request_id, "conversation_id": conversation_id, **payload})
    session.commit()
    return deliver_message(message.id)


def retry_operator_message(session: Session, conversation_id: int, message_id: int, actor: User, request_id: str, expected_status: str) -> Message:
    message = session.scalar(select(Message).where(Message.id == message_id, Message.direction == MessageDirection.OUTBOUND).with_for_update())
    if message is None or message.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="message not found")
    audits = session.scalars(select(AuditLog).where(AuditLog.entity_id == str(message.id), AuditLog.action == "message.retry_requested")).all()
    for entry in audits:
        if (entry.after or {}).get("request_id") == request_id:
            return message
    if expected_status != "failed" or message.delivery_status == DeliveryStatus.UNKNOWN:
        raise HTTPException(status_code=409, detail="outcome unknown; manual reconciliation required" if message.delivery_status == DeliveryStatus.UNKNOWN else "only failed messages can be retried")
    if message.delivery_status != DeliveryStatus.FAILED:
        raise HTTPException(status_code=409, detail="only failed messages can be retried")
    record_audit(session, actor=actor.username, action="message.retry_requested", entity="message", entity_id=str(message.id), after={"request_id": request_id, "conversation_id": message.conversation_id})
    session.commit()
    return deliver_message(message.id)
