"""Transactional commands for the production human inbox."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.state import set_conversation_state
from app.models import AuditLog, Conversation, ConversationState, User
from app.services.audit import record_audit
from app.panel.api.serializers import to_conversation_dict

LEGAL_TRANSITIONS = {
    ConversationState.BOT: {ConversationState.HUMAN},
    ConversationState.HUMAN: {ConversationState.BOT, ConversationState.CLOSED},
    ConversationState.CLOSED: {ConversationState.BOT},
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
        entity_id=str(conversation.id), before=to_conversation_dict(conversation),
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

    before = to_conversation_dict(conversation)
    set_conversation_state(session, conversation, state, cause=f"panel:{request_id}", actor=actor.username)
    if state == ConversationState.HUMAN and conversation.responsible_id is None:
        conversation.responsible_id = actor.id
    elif state == ConversationState.BOT and conversation.responsible_id == actor.id:
        conversation.responsible_id = None
    conversation.version += 1
    record_audit(
        session, actor=actor.username, action="conversation.state_changed", entity="conversation",
        entity_id=str(conversation.id), before=before,
        after={**to_conversation_dict(conversation), "request_id": request_id, "operation": "state", "payload": payload},
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

    before = to_conversation_dict(conversation)
    conversation.responsible_id = responsible_id
    conversation.version += 1
    record_audit(
        session, actor=actor.username, action="conversation.assignment_changed", entity="conversation",
        entity_id=str(conversation.id), before=before,
        after={**to_conversation_dict(conversation), "request_id": request_id, "operation": "assignment", "payload": payload},
    )
    session.flush()
    return conversation
