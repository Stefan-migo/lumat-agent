"""Panel JSON API clients (B2/T2.2; PDW-API, PDW-API-3, D4).

Thin JSON wrappers over `app/services/customers.py` — no new business
logic, audits preserved (SH-5):

- GET  /clients?q=            -> {"clients": [...], "query": q} (search,
                                 cap 100)
- GET  /clients/{id}          -> {"customer", "history", "notes", "states"}
- POST /clients/{id}/state    -> {"ok", "state"} (CR-3 transition validated,
                                 audited with the actor)
- POST /clients/{id}/notes    -> {"ok", "note"} (empty note rejected 400,
                                 audited)

All errors are JSON {"detail": ...} (PDW-API-3): 401 from the JSON-401 dep
(D4, PDW-AUTH-1), 404 for a missing customer, 400 for an invalid CR-3
transition or an empty note. No redirects, no CORS (D1).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models import CustomerState, Memory, MemoryRelation, MemoryStatus, MemoryType, User
from app.panel.api.deps import require_operator_json
from app.panel.api.serializers import (
    to_customer_dict,
    to_memory_dict,
    to_memory_relation_dict,
    to_note_dict,
    to_user_dict,
)
from app.panel.deps import get_db
from app.services import customers
from app.services import memory as memory_service
from app.services import relations
from app.services.audit import record_audit

router = APIRouter(tags=["panel-api-clients"])


class StateBody(BaseModel):
    state: str


class NoteBody(BaseModel):
    note: str


class MemoryBody(BaseModel):
    tipo: str = "decision"
    titulo: str = "customer_memo"
    contenido: str
    topic_key: str | None = None


class MarkBody(BaseModel):
    pin: bool | None = None
    status: str | None = None


class MemoryRelationBody(BaseModel):
    relation: str


def _customer_or_404(session: Session, customer_id: int) -> customers.Customer:
    customer = session.get(customers.Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return customer


def _ficha_memory_or_404(
    session: Session, customer_id: int, memory_id: int
) -> Memory:
    """Return a memory ONLY when it belongs to this customer's ficha (MEM-6).

    Scoped guard: the memory must be `scope='customer'`, under this customer's
    `entity_id`, and in the writable `default` project. Anything else — another
    customer's memory, a non-customer scope, or a non-default project — is
    treated as not found so listing stays client-scoped (no cross-entity leak).
    """
    memory = session.get(Memory, memory_id)
    if (
        memory is None
        or memory.scope != "customer"
        or memory.entity_id != str(customer_id)
        or memory.proyecto != memory_service.WRITABLE_PROYECTO
    ):
        raise HTTPException(status_code=404, detail="memory not found")
    return memory


@router.get("/clients")
def clients_list(
    q: str | None = None,
    include_archived: bool = False,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """Search/list customers (AP-3), wrapped and capped at 100."""
    found = customers.search_customers(
        session, q, limit=100, include_archived=include_archived
    )
    return {"clients": [to_customer_dict(c) for c in found], "query": q or ""}


@router.get("/clients/{customer_id}")
def client_ficha(
    customer_id: int,
    messages_limit: int | None = None,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """Full ficha: customer + history (CR-5) + notes (CR-4) + lifecycle.

    CR-7: the living `customer_memo` (scope='customer', topic_key
    'customer_memo') is surfaced separately from staff notes — `memo` holds the
    latest auto-generated acta-based memo, `notes` stays the CR-4 staff notes.
    Empty when no conversation has closed yet (no error, CR-7).
    """
    customer = _customer_or_404(session, customer_id)
    memo = memory_service.get_by_key(
        session, scope="customer", entity_id=str(customer_id), topic_key="customer_memo"
    )
    return {
        "customer": to_customer_dict(customer),
        "history": customers.customer_history(session, customer_id, messages_limit),
        "notes": [
            to_note_dict(n) for n in customers.list_notes(session, customer_id)
        ],
        "memo": memo.contenido if memo is not None else "",
        "states": [s.value for s in CustomerState],
        "users": [
            to_user_dict(u)
            for u in session.scalars(select(User).order_by(User.username)).all()
        ],
    }


@router.post("/clients/{customer_id}/state")
def client_state_change(
    customer_id: int,
    body: StateBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """CR-3 lifecycle transition, validated and audited with the actor."""
    customer = _customer_or_404(session, customer_id)
    try:
        customers.set_customer_state(
            session, customer, CustomerState(body.state), actor=current.username
        )
    except (customers.InvalidStateTransition, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    session.commit()
    return {"ok": True, "state": customer.state.value}


@router.post("/clients/{customer_id}/archive")
def client_archive(
    customer_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    customer = _customer_or_404(session, customer_id)
    customers.archive_customer(session, customer, actor=current.username)
    session.commit()
    return {"customer": to_customer_dict(customer)}


@router.post("/clients/{customer_id}/unarchive")
def client_unarchive(
    customer_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    customer = _customer_or_404(session, customer_id)
    customers.unarchive_customer(session, customer, actor=current.username)
    session.commit()
    return {"customer": to_customer_dict(customer)}


@router.post("/clients/{customer_id}/notes")
def client_add_note(
    customer_id: int,
    body: NoteBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """CR-4 internal staff note; audited with the actor (SH-5)."""
    _customer_or_404(session, customer_id)
    note = body.note.strip()
    if not note:
        raise HTTPException(status_code=400, detail="note cannot be empty")
    entry = customers.add_note(session, customer_id, note, actor=current.username)
    record_audit(
        session,
        actor=current.username,
        action="customer.note_added",
        entity="customer",
        entity_id=str(customer_id),
        after={"note": note},
    )
    session.commit()
    return {"ok": True, "note": to_note_dict(entry)}


# ---------------------------------------------------------------------------
# Memories (MEM-6) — customer-scoped, thin wrappers over app/services/memory.py
# ---------------------------------------------------------------------------


@router.get("/clients/{customer_id}/memories")
def client_memories_list(
    customer_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """All customer-scoped memories for this ficha, newest first (MEM-6).

    Scoped to `scope='customer'` + this ficha's `entity_id`; a different
    customer's memories are never visible here. Empty list when none exist.
    """
    _customer_or_404(session, customer_id)
    rows = memory_service.list_for_entity(session, scope="customer", entity_id=str(customer_id))
    return {"memories": [to_memory_dict(m) for m in rows]}


def _pending_relation_rows(session: Session, customer_id: int):
    memory_a = aliased(Memory)
    memory_b = aliased(Memory)
    return session.execute(
        select(MemoryRelation, memory_a, memory_b)
        .join(memory_a, MemoryRelation.id_a == memory_a.id)
        .join(memory_b, MemoryRelation.id_b == memory_b.id)
        .where(
            MemoryRelation.source == "judge",
            MemoryRelation.human_resolved_at.is_(None),
            MemoryRelation.confidence < relations.AUTO_JUDGE_CONFIDENCE,
            memory_a.proyecto == memory_service.WRITABLE_PROYECTO,
            memory_a.scope == "customer",
            memory_a.entity_id == str(customer_id),
            memory_b.proyecto == memory_service.WRITABLE_PROYECTO,
            memory_b.scope == "customer",
            memory_b.entity_id == str(customer_id),
        )
        .order_by(MemoryRelation.created_at.desc(), MemoryRelation.id.desc())
    ).all()


@router.get("/clients/{customer_id}/memory-relations/pending")
def client_pending_memory_relations(
    customer_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """List judge relations below the auto-resolution threshold for this ficha."""
    _customer_or_404(session, customer_id)
    rows = [
        (relation, memory_a, memory_b)
        for relation, memory_a, memory_b in _pending_relation_rows(session, customer_id)
        if relations.is_pending(relation)
    ]
    return {
        "relations": [
            to_memory_relation_dict(relation, memory_a, memory_b)
            for relation, memory_a, memory_b in rows
        ]
    }


@router.post("/clients/{customer_id}/memory-relations/{relation_id}")
def client_resolve_memory_relation(
    customer_id: int,
    relation_id: int,
    body: MemoryRelationBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """Resolve one pending customer relation with a fixed-vocabulary human verdict."""
    if body.relation not in relations.RELATION_VOCAB:
        raise HTTPException(status_code=400, detail=f"unknown memory relation: {body.relation!r}")
    _customer_or_404(session, customer_id)
    pending = next(
        (
            (relation, memory_a, memory_b)
            for relation, memory_a, memory_b in _pending_relation_rows(session, customer_id)
            if relation.id == relation_id and relations.is_pending(relation)
        ),
        None,
    )
    if pending is None:
        raise HTTPException(status_code=404, detail="pending memory relation not found")

    relation, memory_a, memory_b = pending
    before = {
        "relation": relation.relation,
        "source": relation.source,
        "confidence": relation.confidence,
    }
    try:
        relation.relation = body.relation
        relation.source = "human"
        relation.human_resolved_at = datetime.now(timezone.utc)
        record_audit(
            session,
            actor=current.username,
            action="memory_relation.resolved",
            entity="memory_relation",
            entity_id=str(relation.id),
            before=before,
            after={"relation": relation.relation, "source": relation.source},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="failed to resolve memory relation")
    return {
        "ok": True,
        "relation": to_memory_relation_dict(relation, memory_a, memory_b),
    }


@router.post("/clients/{customer_id}/memories")
def client_memory_upsert(
    customer_id: int,
    body: MemoryBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """Create/update one customer memory on this ficha (MEM-6, audited).

    Upserts under `scope='customer'`, `proyecto='default'` (MEM-2). Rejects
    empty content with 400 and a non-default project before any write.
    """
    _customer_or_404(session, customer_id)
    contenido = body.contenido.strip()
    if not contenido:
        raise HTTPException(status_code=400, detail="memory content cannot be empty")

    try:
        tipo = MemoryType(body.tipo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown memory type: {body.tipo!r}")

    topic_key = body.topic_key or "general"
    titulo = body.titulo.strip() or topic_key

    try:
        row = memory_service.upsert(
            session,
            scope="customer",
            entity_id=str(customer_id),
            topic_key=topic_key,
            tipo=tipo,
            titulo=titulo,
            contenido=contenido,
        )
        relations.judge_memory_relations(session, row)
        record_audit(
            session,
            actor=current.username,
            action="memory.upserted",
            entity="memory",
            entity_id=str(row.id),
            after={
                "customer_id": customer_id,
                "tipo": tipo.value,
                "topic_key": topic_key,
                "titulo": titulo,
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="failed to persist memory")
    return {"ok": True, "memory": to_memory_dict(row)}


@router.delete("/clients/{customer_id}/memories/{memory_id}")
def client_memory_delete(
    customer_id: int,
    memory_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """Delete one customer-scoped memory from this ficha (MEM-6, audited)."""
    _customer_or_404(session, customer_id)
    row = _ficha_memory_or_404(session, customer_id, memory_id)
    try:
        memory_service.delete(session, memory_id)
        record_audit(
            session,
            actor=current.username,
            action="memory.deleted",
            entity="memory",
            entity_id=str(memory_id),
            before={"customer_id": customer_id, "topic_key": row.topic_key},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="failed to delete memory")
    return {"ok": True, "deleted": memory_id}


@router.post("/clients/{customer_id}/memories/{memory_id}/mark")
def client_memory_mark(
    customer_id: int,
    memory_id: int,
    body: MarkBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """Toggle pin and/or status on a ficha memory (MEM-6, audited).

    Only the customer-scoped memory belonging to this ficha is touchable; the
    bare `MemoryRow` from `session.get` is defended by `_ficha_memory_or_404`.
    """
    _customer_or_404(session, customer_id)
    _ficha_memory_or_404(session, customer_id, memory_id)

    status = None
    if body.status is not None:
        try:
            status = MemoryStatus(body.status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"unknown memory status: {body.status!r}")

    try:
        row = memory_service.set_mark(session, memory_id, pin=body.pin, status=status)
        record_audit(
            session,
            actor=current.username,
            action="memory.marked",
            entity="memory",
            entity_id=str(memory_id),
            before={
                "customer_id": customer_id,
                "pin": bool(getattr(row, "pin", None)),
                "status": getattr(row.status, "value", None),
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="failed to update memory")
    return {"ok": True, "memory": to_memory_dict(row)}
