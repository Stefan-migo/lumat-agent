"""Owner-scoped audit API for the assistant's user-axis memories."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.assistant.tools.registry import BUSINESS_MEMORY_ROLES
from app.models import Memory, MemoryStatus, User
from app.panel.api.deps import get_current_user_json
from app.panel.api.serializers import to_assistant_memory_dict
from app.panel.deps import get_db
from app.services import tukulpan
from app.services.audit import record_audit

router = APIRouter(tags=["panel-api-assistant-memories"])

logger = logging.getLogger(__name__)


def _require_business_memory_role(current: User) -> None:
    if current.role.value not in BUSINESS_MEMORY_ROLES:
        raise HTTPException(status_code=403, detail="panel role required")


def _owned_user_memory_or_404(session: Session, current: User, memory_id: int) -> Memory:
    row = session.scalar(
        select(Memory).where(
            Memory.id == memory_id,
            Memory.scope == "user",
            Memory.entity_id == f"user:{current.id}",
            Memory.owner_id == current.id,
            Memory.proyecto == "default",
            Memory.status != MemoryStatus.ARCHIVED,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="memory not found")
    return row


@router.get("/assistant/memories")
def assistant_memories_list(
    session: Session = Depends(get_db),
    current: User = Depends(get_current_user_json),
) -> dict:
    """List only the caller's active user-axis memories, newest first."""
    _require_business_memory_role(current)
    rows = session.scalars(
        select(Memory)
        .where(
            Memory.scope == "user",
            Memory.entity_id == f"user:{current.id}",
            Memory.owner_id == current.id,
            Memory.proyecto == "default",
            Memory.status != MemoryStatus.ARCHIVED,
        )
        .order_by(Memory.created_at.desc(), Memory.id.desc())
    ).all()
    return {"memories": [to_assistant_memory_dict(row) for row in rows]}


@router.delete("/assistant/memories/{memory_id}", status_code=204)
def assistant_memory_delete(
    memory_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(get_current_user_json),
) -> Response:
    """Delete one of the caller's user-axis memories through Tukulpan."""
    _require_business_memory_role(current)
    row = _owned_user_memory_or_404(session, current, memory_id)
    try:
        tukulpan.delete(session, memory_id)
        record_audit(
            session,
            actor=current.username,
            action="memory.deleted",
            entity="memory",
            entity_id=str(memory_id),
            before={"owner_id": current.id, "topic_key": row.topic_key},
        )
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("assistant memory delete failed for memory %s", memory_id)
        raise HTTPException(status_code=500, detail="failed to delete memory")
    return Response(status_code=204)
