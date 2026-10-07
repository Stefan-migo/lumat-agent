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
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models import (
    CustomerEquipment,
    CustomerState,
    Memory,
    MemoryRelation,
    MemoryStatus,
    MemoryType,
    User,
)
from app.panel.api.deps import require_operator_json
from app.panel.api.serializers import (
    to_customer_dict,
    to_equipment_dict,
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


class MergeBody(BaseModel):
    other_id: int


class NoteBody(BaseModel):
    note: str


class EquipmentBody(BaseModel):
    """Equipment fields are optional: omitted keeps the value; explicit null clears it."""

    equipment_type: str | None = None
    brand: str | None = None
    model: str | None = None
    age: str | None = None
    details: str | None = None


class CreateCustomerBody(BaseModel):
    phone: str
    name: str | None = None
    email: str | None = None
    comuna: str | None = None
    address: str | None = None


class CustomerProfileBody(BaseModel):
    name: str | None = None
    email: str | None = None
    comuna: str | None = None
    address: str | None = None


class ConsentBody(BaseModel):
    consent: bool


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


def _equipment_or_404(
    session: Session, customer_id: int, equipment_id: int
) -> CustomerEquipment:
    equipment = session.scalar(
        select(CustomerEquipment).where(
            CustomerEquipment.id == equipment_id,
            CustomerEquipment.customer_id == customer_id,
        )
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="equipment not found")
    return equipment


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
    consent: bool | None = None,
    sort: Literal["created_desc", "created_asc"] = "created_desc",
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """Search/list customers (AP-3), wrapped and capped at 100."""
    found = customers.search_customers(
        session, q, limit=100, include_archived=include_archived,
        consent=consent, sort=sort,
    )
    return {"clients": [to_customer_dict(c) for c in found], "query": q or ""}


@router.post("/clients", status_code=status.HTTP_201_CREATED)
def client_create(
    body: CreateCustomerBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    try:
        customer = customers.create_customer(
            session,
            body.phone,
            name=body.name,
            email=body.email,
            comuna=body.comuna,
            address=body.address,
            actor=current.username,
        )
    except customers.PhoneAlreadyExists as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "phone_exists", "message": str(exc), "customer_id": exc.customer_id},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail={"code": "invalid_phone", "message": str(exc)}
        )
    session.commit()
    return {"customer": to_customer_dict(customer)}


@router.patch("/clients/{customer_id}")
def client_profile_update(
    customer_id: int,
    body: CustomerProfileBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    customer = _customer_or_404(session, customer_id)
    provided = body.model_fields_set
    changes = {
        field: getattr(body, field)
        for field in ("name", "email", "comuna", "address")
        if field in provided
    }
    if any(value is not None and not value.strip() for value in changes.values()):
        raise HTTPException(
            status_code=400,
            detail={"code": "empty_profile_field", "message": "profile fields cannot be empty"},
        )
    before = {field: getattr(customer, field) for field, value in changes.items()
              if value is not None and getattr(customer, field) != value}
    after = {field: changes[field] for field in before}
    if changes:
        customers.update_captured_data(session, customer, **changes)
    if before:
        record_audit(
            session,
            actor=current.username,
            action="customer.profile_updated",
            entity="customer",
            entity_id=str(customer.id),
            before=before,
            after=after,
        )
    session.commit()
    return {"customer": to_customer_dict(customer)}


@router.post("/clients/{customer_id}/consent")
def client_consent_update(
    customer_id: int,
    body: ConsentBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    customer = _customer_or_404(session, customer_id)
    before = customer.consent_status
    if before != body.consent:
        customers.record_consent(session, customer, consent=body.consent)
        record_audit(
            session,
            actor=current.username,
            action="customer.consent_updated",
            entity="customer",
            entity_id=str(customer.id),
            before={"consent_status": before},
            after={"consent_status": body.consent},
        )
    session.commit()
    return {"customer": to_customer_dict(customer)}


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


@router.get("/clients/{customer_id}/merge-preview")
def client_merge_preview(
    customer_id: int,
    with_id: int = Query(alias="with"),
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    first = _customer_or_404(session, customer_id)
    second = _customer_or_404(session, with_id)
    try:
        return customers.preview_customer_merge(session, first, second)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/clients/{customer_id}/merge")
def client_merge(
    customer_id: int,
    body: MergeBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    first = _customer_or_404(session, customer_id)
    second = _customer_or_404(session, body.other_id)
    try:
        preview = customers.preview_customer_merge(session, first, second)
        survivor = customers.merge_customers(session, first, second, actor=current.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    session.commit()
    return {"survivor": to_customer_dict(survivor), "moved": preview["moved"]}


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


@router.get("/clients/{customer_id}/equipment")
def client_equipment_list(
    customer_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    _customer_or_404(session, customer_id)
    return {
        "equipment": [
            to_equipment_dict(row)
            for row in customers.list_customer_equipment(session, customer_id)
        ]
    }


@router.post("/clients/{customer_id}/equipment", status_code=status.HTTP_201_CREATED)
def client_equipment_create(
    customer_id: int,
    body: EquipmentBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    _customer_or_404(session, customer_id)
    equipment = customers.create_customer_equipment(
        session, customer_id, actor=current.username, **body.model_dump()
    )
    session.commit()
    return {"equipment": to_equipment_dict(equipment)}


@router.patch("/clients/{customer_id}/equipment/{equipment_id}")
def client_equipment_update(
    customer_id: int,
    equipment_id: int,
    body: EquipmentBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    """Patch equipment: omitted fields keep their values; explicit null clears them.

    Only fields in ``body.model_fields_set`` are forwarded to the update service.
    """
    _customer_or_404(session, customer_id)
    equipment = _equipment_or_404(session, customer_id, equipment_id)
    customers.update_customer_equipment(
        session,
        equipment,
        actor=current.username,
        **{field: getattr(body, field) for field in body.model_fields_set},
    )
    session.commit()
    return {"equipment": to_equipment_dict(equipment)}


@router.delete("/clients/{customer_id}/equipment/{equipment_id}")
def client_equipment_delete(
    customer_id: int,
    equipment_id: int,
    session: Session = Depends(get_db),
    current: User = Depends(require_operator_json),
) -> dict:
    _customer_or_404(session, customer_id)
    equipment = _equipment_or_404(session, customer_id, equipment_id)
    customers.delete_customer_equipment(session, equipment, actor=current.username)
    session.commit()
    return {"ok": True}


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
