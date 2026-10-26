"""Panel JSON API conversations (B3/T3.1; PDW-API, PDW-API-3, D4).

Thin JSON wrapper over the read-only conversation thread (same data the
Jinja route renders — AP-4/HH-1): one conversation + its messages in
chronological order (`created_at`, then `id` for same-timestamp ties), with
`media_url` files exposed as plain URLs so the SPA renders them as links
(PDW-TST-3 pattern). Read-only by design (H1: no reply-from-panel, HH-5).

Errors are JSON {"detail": ...} (PDW-API-3): 401 from the JSON-401 dep (D4,
PDW-AUTH-1), 404 for a missing conversation. No redirects, no CORS (D1).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, case as sql_case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import Case, Conversation, ConversationState, Customer, DeliveryStatus, Message, MessageDirection, User
from app.config import get_settings
from app.panel.api.deps import require_operator_json
from app.panel.api.serializers import to_active_conversation_dict, to_conversation_dict, to_message_dict
from app.panel.deps import get_db
from app.services.conversations import assign, change_state, retry_operator_message, send_operator_media, send_operator_message
from app.webhook.ingest import _safe_filename
from app.services.cases import case_is_open_expr
router = APIRouter(tags=["panel-api-conversations"])

_INLINE_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "video/3gpp",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp4",
    "audio/aac",
    "audio/amr",
}


class StateCommand(BaseModel):
    state: ConversationState
    expected_version: int = Field(ge=0)
    request_id: str = Field(min_length=1)


class AssignmentCommand(BaseModel):
    responsible_id: int | None
    expected_version: int = Field(ge=0)
    request_id: str = Field(min_length=1)


class MessageCommand(BaseModel):
    text: str
    request_id: str = Field(min_length=1)


class RetryCommand(BaseModel):
    request_id: str = Field(min_length=1)
    expected_status: str


def _conversation_or_404(session: Session, conversation_id: int) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conversation


def _conversation_payload(session: Session, conversation: Conversation) -> dict:
    latest_inbound_at = session.scalar(
        select(Message.created_at)
        .where(
            Message.conversation_id == conversation.id,
            Message.direction == MessageDirection.INBOUND,
        )
        .order_by(Message.created_at.desc(), Message.id.desc())
    )
    created = latest_inbound_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    open_window = created is not None and datetime.now(timezone.utc) - created < timedelta(hours=24)
    delivery_summary = {status.value: 0 for status in DeliveryStatus}
    for status in session.scalars(
        select(Message.delivery_status).where(
            Message.conversation_id == conversation.id,
            Message.direction == MessageDirection.OUTBOUND,
            Message.delivery_status.is_not(None),
        )
    ):
        delivery_summary[status.value] += 1
    return to_conversation_dict(
        conversation,
        customer=session.get(Customer, conversation.customer_id),
        case=_selected_case(session, conversation.id),
        latest_inbound_at=latest_inbound_at,
        reply_window_open=open_window,
        delivery_summary=delivery_summary,
    )


def _ranked_case_ids():
    priority = sql_case(
        (and_(Case.emergency.is_(True), Case.acknowledged_at.is_(None)), 0),
        (
            and_(
                case_is_open_expr(),
                Case.acknowledged_at.is_(None),
            ),
            1,
        ),
        else_=2,
    )
    return select(
        Case.id.label("case_id"),
        Case.conversation_id.label("conversation_id"),
        func.row_number().over(
            partition_by=Case.conversation_id,
            order_by=(priority, Case.created_at.desc(), Case.id.desc()),
        ).label("case_rank"),
    ).subquery("ranked_cases")


def _selected_case(session: Session, conversation_id: int) -> Case | None:
    ranked = _ranked_case_ids()
    return session.scalar(
        select(Case)
        .join(ranked, ranked.c.case_id == Case.id)
        .where(ranked.c.case_rank == 1, Case.conversation_id == conversation_id)
    )


def _queue_base(
    session: Session,
    *,
    q: str | None,
    state: ConversationState | None,
    responsible_id: int | None,
    exclude_closed: bool = False,
    emergency: bool = False,
    has_case: bool = False,
):
    ranked = _ranked_case_ids()
    selected_case = aliased(Case)
    query = (
        select(
            Conversation,
            Customer,
            selected_case,
            selected_case.id.label("selected_case_id"),
            selected_case.emergency.label("selected_case_emergency"),
            selected_case.acknowledged_at.label("selected_case_acknowledged_at"),
        )
        .join(Customer, Customer.id == Conversation.customer_id)
        .outerjoin(
            ranked,
            and_(ranked.c.case_rank == 1, ranked.c.conversation_id == Conversation.id),
        )
        .outerjoin(selected_case, selected_case.id == ranked.c.case_id)
    )
    # The ranked subquery is joined through the case primary key so each
    # conversation contributes at most one row, without per-row case queries.
    filters = []
    if state is not None:
        filters.append(Conversation.state == state)
    if exclude_closed:
        filters.append(Conversation.state != ConversationState.CLOSED)
    if emergency:
        filters.extend((selected_case.emergency.is_(True), selected_case.acknowledged_at.is_(None)))
    if has_case:
        filters.append(selected_case.id.is_not(None))
    if responsible_id is not None:
        filters.append(Conversation.responsible_id == responsible_id)
    if q:
        term = f"%{q}%"
        filters.append(or_(Customer.name.ilike(term), Customer.phone_e164.ilike(term), Conversation.summary.ilike(term)))
    return query.where(*filters)


def _queue_counts(session: Session, base) -> dict[str, int]:
    filtered = base.subquery()
    row = session.execute(
        select(
            func.count().filter(filtered.c.state != ConversationState.CLOSED).label("all"),
            func.count().filter(filtered.c.state == ConversationState.HUMAN).label("human"),
            func.count().filter(filtered.c.state != ConversationState.CLOSED, filtered.c.selected_case_emergency.is_(True), filtered.c.selected_case_acknowledged_at.is_(None)).label("emergency"),
            func.count().filter(filtered.c.state != ConversationState.CLOSED, filtered.c.selected_case_id.is_not(None)).label("case"),
            func.count().filter(filtered.c.state == ConversationState.CLOSED).label("closed"),
        ).select_from(filtered)
    ).one()
    return {key: int(getattr(row, key)) for key in ("all", "human", "emergency", "case", "closed")}


def _queue_response(
    session: Session,
    *,
    q: str | None = None,
    state: ConversationState | None = None,
    responsible_id: int | None = None,
    exclude_closed: bool = False,
    emergency: bool = False,
    has_case: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    limit = min(max(limit, 1), 100)
    counts_base = _queue_base(session, q=q, state=None, responsible_id=responsible_id)
    base = _queue_base(
        session, q=q, state=state, responsible_id=responsible_id,
        exclude_closed=exclude_closed, emergency=emergency, has_case=has_case,
    )
    filtered = base.subquery()
    total = session.scalar(select(func.count()).select_from(filtered)) or 0
    rows = session.execute(
        base.order_by(Conversation.last_message_at.desc().nulls_last(), Conversation.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    items = [
        to_conversation_dict(conversation, customer=customer, case=case)
        for conversation, customer, case, _, _, _ in rows
    ]
    return {
        "items": items,
        "conversations": items,
        "total": int(total),
        "offset": offset,
        "limit": limit,
        "counts": _queue_counts(session, counts_base),
    }


@router.get("/conversations")
def conversations_list(
    state: ConversationState | None = None,
    responsible_id: int | None = None,
    q: str | None = None,
    exclude_closed: bool = False,
    emergency: bool = False,
    has_case: bool = False,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """List conversation metadata, most recently active first."""
    return _queue_response(
        session, q=q, state=state, responsible_id=responsible_id,
        exclude_closed=exclude_closed, emergency=emergency, has_case=has_case,
        limit=limit, offset=offset
    )


@router.get("/conversations/active")
def active_conversations(
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """List bot/human conversations with activity in the last 24 hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = session.execute(
        select(Conversation, Customer.name)
        .join(Customer, Customer.id == Conversation.customer_id)
        .where(
            Conversation.state.in_((ConversationState.BOT, ConversationState.HUMAN)),
            Conversation.last_message_at.is_not(None),
            Conversation.last_message_at >= cutoff,
        )
        .order_by(Conversation.last_message_at.desc(), Conversation.id.desc())
    ).all()
    return {
        "conversations": [
            to_active_conversation_dict(conversation, customer_name=customer_name)
            for conversation, customer_name in rows
        ]
    }


@router.post("/conversations/{conversation_id}/state")
def state_command(conversation_id: int, body: StateCommand, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    conversation = change_state(session, conversation_id, current, body.state, body.expected_version, body.request_id)
    return {"ok": True, "conversation": _conversation_payload(session, conversation)}


@router.post("/conversations/{conversation_id}/assignment")
def assignment_command(conversation_id: int, body: AssignmentCommand, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    conversation = assign(session, conversation_id, current, body.responsible_id, body.expected_version, body.request_id)
    return {"ok": True, "conversation": _conversation_payload(session, conversation)}


@router.post("/conversations/{conversation_id}/messages")
def message_command(conversation_id: int, body: MessageCommand, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    if not body.text.strip():
        _conversation_or_404(session, conversation_id)
        from app.services.audit import record_audit
        record_audit(session, actor=current.username, action="message.send_rejected", entity="conversation", entity_id=str(conversation_id), after={"request_id": body.request_id, "detail": "message text must not be blank"})
        session.commit()
        raise HTTPException(status_code=422, detail="message text must not be blank")
    message = send_operator_message(session, conversation_id, current, body.text, body.request_id)
    if message.delivery_status != DeliveryStatus.SENT:
        raise HTTPException(status_code=502, detail="message delivery failed")
    return {"ok": True, "message": to_message_dict(message)}


@router.post("/conversations/{conversation_id}/media")
def media_command(
    conversation_id: int,
    file: UploadFile = File(...),
    request_id: str = Form(..., min_length=1),
    caption: str | None = Form(None),
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    media_dir = Path(get_settings().media_dir).resolve()
    media_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix
    safe_filename = _safe_filename(f"{request_id}{suffix}")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f"{safe_filename}-", suffix=".upload",
            dir=media_dir, delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            size = 0
            while chunk := file.file.read(64 * 1024):
                temporary.write(chunk)
                size += len(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="file must not be empty")
        try:
            message = send_operator_media(
                session, conversation_id, path=temporary_path,
                content_type=file.content_type or "application/octet-stream",
                filename=safe_filename, caption=caption, actor=current, request_id=request_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        # Same contract as the text endpoint: a failed delivery is recorded on the row and the
        # operator gets it back with `delivery_status: failed` plus the retry action, not a 502.
        return {"ok": True, "message": to_message_dict(message)}
    finally:
        file.file.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@router.post("/conversations/{conversation_id}/messages/{message_id}/retry")
def retry_message(conversation_id: int, message_id: int, body: RetryCommand, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    message = retry_operator_message(session, conversation_id, message_id, current, body.request_id, body.expected_status)
    if message.delivery_status != DeliveryStatus.SENT:
        raise HTTPException(status_code=502, detail="message delivery failed")
    return {"ok": True, "message": to_message_dict(message)}


@router.get("/conversations/{conversation_id}/messages/{message_id}/media")
def conversation_message_media(
    conversation_id: int,
    message_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> FileResponse:
    message = session.scalar(select(Message).where(
        Message.id == message_id, Message.conversation_id == conversation_id
    ))
    if message is None or not message.stored_path:
        raise HTTPException(status_code=404, detail="media not found")
    root = Path(get_settings().media_dir).resolve()
    path = Path(message.stored_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(status_code=404, detail="media not found")
    content_type = message.content_type or "application/octet-stream"
    disposition = "inline" if content_type.lower() in _INLINE_MEDIA_TYPES else "attachment"
    return FileResponse(
        path,
        filename=message.filename or path.name,
        media_type=content_type,
        content_disposition_type=disposition,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/conversations/{conversation_id}")
def conversation_thread(
    conversation_id: int,
    messages_limit: int | None = None,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """Conversation metadata + chronological messages (media as URL links)."""
    conversation = _conversation_or_404(session, conversation_id)
    messages_query = select(Message).where(Message.conversation_id == conversation_id)
    messages_total = session.scalar(
        select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
    )
    if messages_limit is not None and messages_limit > 0:
        messages = list(
            session.scalars(
                messages_query.order_by(Message.created_at.desc(), Message.id.desc())
                .limit(messages_limit)
            )
        )
        messages.reverse()
    else:
        messages = list(
            session.scalars(messages_query.order_by(Message.created_at, Message.id))
        )
    return {
        "conversation": _conversation_payload(session, conversation),
        "messages": [to_message_dict(m) for m in messages],
        "messages_total": messages_total,
    }
