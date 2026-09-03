"""Persistence and recovery boundary for owner/admin internal agent chat."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat import graph
from app.models import InternalChatMessage, InternalChatThread, User
from app.panel.api.serializers import to_internal_chat_message_dict, to_internal_chat_thread_dict
from app.services.audit import record_audit


def thread_dict(thread: InternalChatThread) -> dict:
    return to_internal_chat_thread_dict(thread)


def message_dict(message: InternalChatMessage) -> dict:
    return to_internal_chat_message_dict(message)


def create_thread(session: Session, user: User) -> InternalChatThread:
    thread = InternalChatThread(user_id=user.id)
    session.add(thread)
    session.flush()
    record_audit(session, actor=user.username, action="internal_chat.thread_created",
                 entity="internal_chat_thread", entity_id=str(thread.id))
    return thread


def submit_message(session: Session, thread: InternalChatThread, user: User, content: str) -> InternalChatMessage:
    message = InternalChatMessage(thread_id=thread.id, author="admin", content=content.strip(), status="processing")
    session.add(message)
    session.flush()
    try:
        response = graph.run_internal_conversation(session, thread, message.content)
        message.status = "processed"
        message.completed_at = datetime.now(timezone.utc)
        session.add(InternalChatMessage(thread_id=thread.id, author="agent", content=response,
                                         status="processed", completed_at=datetime.now(timezone.utc)))
    except Exception:
        message.status = "failed"
        message.error = "The agent could not process this message. Retry it."
        message.completed_at = datetime.now(timezone.utc)
    record_audit(session, actor=user.username, action="internal_chat.message_sent",
                 entity="internal_chat_message", entity_id=str(message.id),
                 after={"status": message.status})
    session.flush()
    return message


def get_thread(session: Session, thread_id: int, user_id: int) -> tuple[InternalChatThread, list[InternalChatMessage]] | None:
    thread = session.scalar(select(InternalChatThread).where(InternalChatThread.id == thread_id, InternalChatThread.user_id == user_id))
    if thread is None:
        return None
    messages = list(session.scalars(select(InternalChatMessage).where(InternalChatMessage.thread_id == thread.id).order_by(InternalChatMessage.created_at, InternalChatMessage.id)))
    return thread, messages
