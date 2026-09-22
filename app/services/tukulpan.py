"""Persistent, domain-aware memory layer (MEM-1..MEM-3; design "Memory Service").

Typed memories per `(proyecto, scope, entity_id)` keyed by `topic_key`, with a
384d local embedding (reuses `kb.embed_texts()` — same multilingual fastembed
model as kb_chunks, $0). Hybrid recall = pgvector cosine + 0.3 * pg_trgm FTS,
fused and entity-scoped, filtered to the configured threshold with no
out-of-scope fallback. Only `proyecto='default'` is writable (MEM-2); cross-
project recall is out of scope (design D4).

KB-style contract: the caller owns the session transaction and commits.
This service only stages rows — it never commits.

Later slices (S2/S3) own `load_customer_context`, `persist_memory_session`,
`close_conversation`, and `record_observation`. Relation judging lives in
`app.services.relations`; `REL_MIN_SIM` remains the shared candidate gate.
"""

from __future__ import annotations

import json
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Case,
    Conversation,
    ConversationState as ConversationStateEnum,
    Memory,
    MemoryObservation,
    MemoryProducer,
    MemoryRelation,
    MemoryStatus,
    MemoryType,
    MemoryVisibility,
    Message,
    MessageDirection,
    ObservationType,
)
from app.services import kb, projects

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Concrete thresholds (design "fines de detalle fino")
# ---------------------------------------------------------------------------
MEM_MIN_SIM = 0.55          # fused score gate for hybrid_search
REL_MIN_SIM = 0.85          # cosine pair gate for suggest_relations (S3+)
FTS_BOOST = 0.3             # fused = vector + 0.3 * fts (vector dominates)
DEFAULT_TOP_K = 5
WRITABLE_PROYECTO = "default"
AGENT_SCOPE = "agent"
MEMORY_DECAY_DAYS = 30
DECAYING_TYPES = frozenset({MemoryType.SUMMARY, MemoryType.SESSION, MemoryType.DISCOVERY})

__all__ = [
    "DEFAULT_TOP_K",
    "AGENT_SCOPE",
    "EMBED_BACKOFF_SECONDS",
    "EMBED_RETRIES",
    "FTS_BOOST",
    "MEM_MIN_SIM",
    "MEMORY_DECAY_DAYS",
    "DECAYING_TYPES",
    "REL_MIN_SIM",
    "WRITABLE_PROYECTO",
    "close_conversation",
    "archive_report",
    "delete",
    "get_by_key",
    "hybrid_search",
    "list_for_entity",
    "load_customer_context",
    "persist_memory_session",
    "record_decision",
    "record_milestone",
    "persist_sdb_artifact",
    "write_recap",
    "set_mark",
    "upsert",
    "agent_memory_entity",
    "thread_memory_entity",
    "visibility_target",
]

# Embedder resilience (R4-001): bounded retry with short backoff on transient
# model-init or network failures, then a clear logged failure.
EMBED_RETRIES = 2
EMBED_BACKOFF_SECONDS = (0.1, 0.3)
SDB_SPEC_LIMIT = 8 * 1024
SDB_CHECKPOINT_LIMIT = 4 * 1024


def agent_memory_entity(proyecto: str) -> str:
    """Canonical agent-axis entity for one project namespace.

    The project is part of the entity so a project-visible memory cannot be
    reached by a read bound to a different project, even when the writable
    namespace widens.
    """
    return f"agent:{proyecto}"


def thread_memory_entity(thread_id: int) -> str:
    """Canonical panel entity for one conversation thread."""
    return f"thread:{thread_id}"


def visibility_target(
    visibility: MemoryVisibility | str, *, thread_id: int, proyecto: str
) -> tuple[str, str]:
    """Derive the persisted axis from the declared visibility and its project."""
    value = visibility.value if isinstance(visibility, MemoryVisibility) else visibility
    if value == MemoryVisibility.THREAD.value:
        return "panel", thread_memory_entity(thread_id)
    if value == MemoryVisibility.PROJECT.value:
        return AGENT_SCOPE, agent_memory_entity(proyecto)
    raise ValueError(f"unknown memory visibility: {visibility!r}")


def _guard_writable_project(
    proyecto: str, authorization: projects._ProjectAuthorization | None = None
) -> None:
    """Require the project service capability for every non-default write."""
    if proyecto == WRITABLE_PROYECTO:
        return
    if not isinstance(authorization, projects._ProjectAuthorization) or authorization.slug != proyecto:
        raise ValueError(
            f"unauthorized memory write for proyecto={proyecto!r}; "
            "legacy default guard is proyecto='default'"
        )


def _embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch locally; empty text -> empty list (reuses kb seam).

    Retries transient embedder failures with a short backoff (R4-001) and logs
    the final failure before re-raising so the caller can degrade explicitly.
    """
    if not texts:
        return []
    last_error: Exception | None = None
    for attempt in range(EMBED_RETRIES + 1):
        try:
            embeddings, _ = kb.embed_texts(texts)
            return embeddings
        except Exception as exc:  # transient model init / network
            last_error = exc
            if attempt < EMBED_RETRIES:
                time.sleep(EMBED_BACKOFF_SECONDS[attempt])
    logger.error("memory embedding failed after %d attempts: %s", EMBED_RETRIES + 1, last_error)
    raise last_error


def _normalized_hash(contenido: str) -> str:
    normalized = " ".join(contenido.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _review_after(tipo: MemoryType, *, now: datetime | None = None) -> datetime | None:
    """Return the review instant for a decaying type, or None otherwise."""
    if tipo not in DECAYING_TYPES:
        return None
    if now is None:
        now = datetime.now(timezone.utc)
    return now + timedelta(days=MEMORY_DECAY_DAYS)


def _is_stale(review_after: datetime | None, *, now: datetime | None = None) -> bool:
    """Return whether an existing review instant has passed."""
    if review_after is None:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    return review_after <= now


def _fold_duplicate(session: Session, duplicate: Memory, *, survivor: Memory) -> None:
    """Move a duplicate row's references onto its survivor and delete it.

    `projects.merge()` performs the same fold inline: it cannot import this helper
    without creating a cycle, because this module already imports `projects`.
    """
    session.execute(
        update(MemoryObservation)
        .where(MemoryObservation.memory_id == duplicate.id)
        .values(memory_id=survivor.id)
    )
    session.execute(
        update(MemoryRelation)
        .where(MemoryRelation.id_a == duplicate.id)
        .values(id_a=survivor.id)
    )
    session.execute(
        update(MemoryRelation)
        .where(MemoryRelation.id_b == duplicate.id)
        .values(id_b=survivor.id)
    )
    survivor.duplicate_count += duplicate.duplicate_count
    survivor.last_seen_at = func.now()
    session.delete(duplicate)


def _upsert_resolved(
    session: Session,
    *,
    scope: str,
    entity_id: str,
    topic_key: str,
    tipo: MemoryType,
    titulo: str,
    contenido: str,
    proyecto: str,
    pin: bool,
    producer: MemoryProducer,
    origin_thread_id: str | None,
    visibility: MemoryVisibility,
    embedding: list[float],
    normalized_hash: str,
) -> Memory:
    """Resolve and write one already-validated memory payload."""
    now = datetime.now(timezone.utc)
    review_after = _review_after(tipo, now=now)
    row = session.execute(
        select(Memory).where(
            Memory.proyecto == proyecto,
            Memory.scope == scope,
            Memory.entity_id == entity_id,
            Memory.topic_key == topic_key,
        )
    ).scalar_one_or_none()

    if row is None:
        row = session.execute(
            select(Memory).where(
                Memory.proyecto == proyecto,
                Memory.scope == scope,
                Memory.entity_id == entity_id,
                Memory.normalized_hash == normalized_hash,
            )
        ).scalar_one_or_none()

    if row is None:
        row = Memory(
            proyecto=proyecto,
            scope=scope,
            entity_id=entity_id,
            topic_key=topic_key,
            tipo=tipo,
            titulo=titulo,
            contenido=contenido,
            embedding=embedding,
            normalized_hash=normalized_hash,
            duplicate_count=1,
            last_seen_at=func.now(),
            pin=pin,
            producer=producer,
            origin_thread_id=origin_thread_id,
            visibility=visibility,
            review_after=review_after,
        )
        session.add(row)
    elif row.topic_key != topic_key:
        row.duplicate_count += 1
        row.last_seen_at = func.now()
        row.review_after = _review_after(row.tipo, now=now)
    else:
        # Same key: a revision. Its new content may already belong to a sibling row
        # under the hash identity, a state the partial unique index cannot hold. The
        # written key wins, so the sibling is folded into this row. The delete is
        # flushed first because the update below would otherwise trip the index.
        duplicate = session.execute(
            select(Memory).where(
                Memory.proyecto == proyecto,
                Memory.scope == scope,
                Memory.entity_id == entity_id,
                Memory.normalized_hash == normalized_hash,
                Memory.id != row.id,
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            _fold_duplicate(session, duplicate, survivor=row)
            session.flush()
        row.tipo = tipo
        row.titulo = titulo
        row.contenido = contenido
        row.embedding = embedding
        row.normalized_hash = normalized_hash
        row.last_seen_at = func.now()
        row.pin = pin
        row.producer = producer
        row.origin_thread_id = origin_thread_id
        row.visibility = visibility
        row.review_after = review_after
    session.flush()
    return row


def upsert(
    session: Session,
    *,
    scope: str,
    entity_id: str,
    topic_key: str,
    tipo: MemoryType,
    titulo: str,
    contenido: str,
    proyecto: str = WRITABLE_PROYECTO,
    pin: bool = False,
    producer: MemoryProducer = MemoryProducer.SYSTEM,
    origin_thread_id: str | None = None,
    visibility: MemoryVisibility = MemoryVisibility.THREAD,
    authorization: projects._ProjectAuthorization | None = None,
) -> Memory:
    """Create-or-update one memory by (proyecto, scope, entity_id, topic_key).

    Embeds `contenido` via `kb.embed_texts()` (384d). Rejects `proyecto !=
    'default'` before any DB write and persists nothing (MEM-2). On the same
    key the existing row is reused and its content/embedding refreshed —
    uniqueness enforced by `UNIQUE(proyecto, scope, entity_id, topic_key)`.
    ``begin_nested()`` may flush pending caller state before the savepoint;
    that remains inside the caller's transaction and preserves rollback semantics.
    """
    _guard_writable_project(proyecto, authorization)

    normalized_hash = _normalized_hash(contenido)
    embeddings = _embed([contenido])
    if not embeddings:
        raise ValueError("cannot embed empty memory content")
    embedding = embeddings[0]

    # ponytail: two concurrent writers are the ceiling; a third is not covered.
    # Upgrade to a bounded loop or conflict-target upsert if that ceiling changes.
    for attempt in range(2):
        try:
            with session.begin_nested():
                return _upsert_resolved(
                    session,
                    scope=scope,
                    entity_id=entity_id,
                    topic_key=topic_key,
                    tipo=tipo,
                    titulo=titulo,
                    contenido=contenido,
                    proyecto=proyecto,
                    pin=pin,
                    producer=producer,
                    origin_thread_id=origin_thread_id,
                    visibility=visibility,
                    embedding=embedding,
                    normalized_hash=normalized_hash,
                )
        except IntegrityError:
            if attempt == 1:
                raise


def record_milestone(
    session: Session,
    *,
    thread_id: int,
    topic_key: str,
    title: str,
    content: str,
    proyecto: str = WRITABLE_PROYECTO,
    authorization: projects._ProjectAuthorization | None = None,
) -> Memory:
    """Stage a panel milestone under the canonical memory contract."""
    return upsert(
        session,
        scope="panel",
        entity_id=f"thread:{thread_id}",
        topic_key=topic_key,
        tipo=MemoryType.SUMMARY,
        titulo=title,
        contenido=content,
        proyecto=proyecto,
        producer=MemoryProducer.SYSTEM,
        origin_thread_id=str(thread_id),
        authorization=authorization,
    )


def record_decision(
    session: Session,
    *,
    thread_id: int,
    topic_key: str,
    title: str,
    content: str,
    proyecto: str = WRITABLE_PROYECTO,
    authorization: projects._ProjectAuthorization | None = None,
) -> Memory:
    """Stage an explicit panel decision under the canonical memory contract."""
    return upsert(
        session,
        scope="panel",
        entity_id=f"thread:{thread_id}",
        topic_key=topic_key,
        tipo=MemoryType.DECISION,
        titulo=title,
        contenido=content,
        proyecto=proyecto,
        producer=MemoryProducer.SYSTEM,
        origin_thread_id=str(thread_id),
        authorization=authorization,
    )


def archive_report(
    session: Session,
    *,
    thread_id: int,
    topic_key: str,
    title: str,
    content: str,
    proyecto: str = WRITABLE_PROYECTO,
    authorization: projects._ProjectAuthorization | None = None,
) -> Memory:
    """Write a report, then mark that same memory archived as a closed report."""
    row = upsert(
        session,
        scope="panel",
        entity_id=f"thread:{thread_id}",
        topic_key=topic_key,
        tipo=MemoryType.SUMMARY,
        titulo=title,
        contenido=content,
        proyecto=proyecto,
        producer=MemoryProducer.SYSTEM,
        origin_thread_id=str(thread_id),
        authorization=authorization,
    )
    return set_mark(session, row.id, status=MemoryStatus.ARCHIVED)


def _bounded_json(payload: Any, limit: int) -> str:
    """Serialize an artifact without allowing the memory row to exceed its bound."""
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) <= limit:
        return encoded
    marker = json.dumps({"truncated": True, "preview": ""}, separators=(",", ":"))
    available = max(0, limit - len(marker.encode("utf-8")) + 2)
    preview = encoded.encode("utf-8")[:available].decode("utf-8", errors="ignore")
    while len(json.dumps({"truncated": True, "preview": preview}, separators=(",", ":")).encode("utf-8")) > limit:
        preview = preview[:-1]
    return json.dumps({"truncated": True, "preview": preview}, separators=(",", ":"))


def persist_sdb_artifact(
    session: Session,
    *,
    thread_id: int,
    run_id: str,
    kind: str,
    payload: Any,
    sequence: int | None = None,
    task_id: str | None = None,
    proyecto: str = WRITABLE_PROYECTO,
    authorization: projects._ProjectAuthorization | None = None,
) -> Memory:
    """Persist one bounded typed SDB artifact through the canonical memory seam."""
    _guard_writable_project(proyecto, authorization)
    if kind == "spec":
        tipo, topic_key, limit = MemoryType.PATTERN, f"sdb:{run_id}:spec", SDB_SPEC_LIMIT
        title = "SDB specification"
    elif kind == "state" and sequence is not None:
        tipo, topic_key, limit = MemoryType.SESSION, f"sdb:{run_id}:state:{sequence}", SDB_CHECKPOINT_LIMIT
        title = "SDB checkpoint"
    elif kind == "result" and task_id:
        tipo, topic_key, limit = MemoryType.DISCOVERY, f"sdb:{run_id}:result:{task_id}", SDB_CHECKPOINT_LIMIT
        title = "SDB result"
    else:
        raise ValueError("SDB artifact requires kind spec, state+sequence, or result+task_id")
    return upsert(
        session,
        scope="panel",
        entity_id=f"thread:{thread_id}",
        topic_key=topic_key,
        tipo=tipo,
        titulo=title,
        contenido=_bounded_json(payload, limit),
        proyecto=proyecto,
        producer=MemoryProducer.PIPELINE,
        origin_thread_id=str(thread_id),
        authorization=authorization,
    )


def write_recap(
    session: Session,
    *,
    thread_id: int,
    source_message_ids: list[int],
    recap: str,
    source_tokens: int,
    truncated: bool,
) -> dict[str, Any]:
    """Persist one bounded, retry-safe panel recap without owning the transaction."""
    source_message_ids = [int(message_id) for message_id in source_message_ids]
    key = f"assistant-recap:{thread_id}:{source_message_ids[-1]}" if source_message_ids else f"assistant-recap:{thread_id}:empty"
    bounded_recap = recap[:8_000]
    payload = {
        "schema_version": 1,
        "thread_id": thread_id,
        "source_message_ids": source_message_ids,
        "source_tokens": min(max(0, int(source_tokens)), 2_000),
        "truncated": bool(truncated or len(recap) > len(bounded_recap)),
        "recap": bounded_recap,
    }
    try:
        # A savepoint contains both embedding and flush failures, keeping the
        # caller's outer transaction usable for the turn.
        with session.begin_nested():
            row = upsert(
                session,
                scope="panel",
                entity_id=f"thread:{thread_id}",
                topic_key=key,
                tipo=MemoryType.SUMMARY,
                titulo="Assistant session recap",
                contenido=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                producer=MemoryProducer.PIPELINE,
                origin_thread_id=str(thread_id),
            )
        return {"written": True, "id": row.id, "topic_key": key}
    except Exception as exc:
        logger.warning("panel recap degraded for thread %s: %s", thread_id, exc)
        return {"written": False, "degraded_reason": str(exc), "topic_key": key}


def get_by_key(
    session: Session,
    *,
    scope: str,
    entity_id: str,
    topic_key: str,
    proyecto: str = WRITABLE_PROYECTO,
) -> Memory | None:
    """Return one memory by its composite key, or None when absent (MEM-2)."""
    return session.execute(
        select(Memory).where(
            Memory.proyecto == proyecto,
            Memory.scope == scope,
            Memory.entity_id == entity_id,
            Memory.topic_key == topic_key,
        )
    ).scalar_one_or_none()


def list_for_entity(
    session: Session,
    *,
    scope: str,
    entity_id: str,
    proyecto: str = WRITABLE_PROYECTO,
) -> list[Memory]:
    """All memories for one (scope, entity_id), newest first (MEM-2)."""
    rows = session.execute(
        select(Memory)
        .where(
            Memory.proyecto == proyecto,
            Memory.scope == scope,
            Memory.entity_id == entity_id,
        )
        .order_by(Memory.updated_at.desc())
    ).scalars().all()
    return list(rows)


def delete(session: Session, memory_id: int) -> Memory:
    """Delete one memory row by id (MEM-2). Raises ValueError if absent."""
    row = session.get(Memory, memory_id)
    if row is None:
        raise ValueError(f"memory {memory_id} not found")
    session.delete(row)
    session.flush()
    return row


def set_mark(
    session: Session,
    memory_id: int,
    *,
    pin: bool | None = None,
    status: MemoryStatus | None = None,
) -> Memory:
    """Toggle pin and/or status on one memory (MEM-2). Raises ValueError if absent."""
    row = session.get(Memory, memory_id)
    if row is None:
        raise ValueError(f"memory {memory_id} not found")
    if pin is not None:
        row.pin = pin
    if status is not None:
        row.status = status
    session.flush()
    return row


def hybrid_search(
    session: Session,
    query: str,
    *,
    scope: str,
    entity_id: str,
    proyecto: str = WRITABLE_PROYECTO,
    min_sim: float = MEM_MIN_SIM,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    """Hybrid retrieval over one entity's memories (MEM-3).

    Two-phase recall that stays bounded on high-cardinality entities (R4-002):
    1. candidate pre-filter by vector cosine distance using the HNSW index
       (proyecto/scope/entity_id scoped, `candidate_factor * top_k` rows);
    2. fused score = vector_sim + FTS_BOOST * fts_sim computed per candidate,
       threshold-filtered and re-ranked in memory, capped at `top_k`.

    No out-of-scope fallback (design + MEM-3 Empty result).
    """
    query_embedding = _embed([query])
    if not query_embedding:
        return []
    vec = query_embedding[0]

    candidate_factor = 4
    candidate_limit = max(candidate_factor * top_k, 20)

    distance = Memory.embedding.cosine_distance(vec)
    vector_sim = 1 - distance
    fts_sim = func.similarity(Memory.contenido, query)
    fused = vector_sim + FTS_BOOST * fts_sim

    candidates = session.execute(
        select(
            Memory,
            fused.label("fused"),
            vector_sim.label("vector_sim"),
            fts_sim.label("fts_sim"),
        )
        .where(
            Memory.proyecto == proyecto,
            Memory.scope == scope,
            Memory.entity_id == entity_id,
            Memory.status != MemoryStatus.ARCHIVED,
        )
        .order_by(distance)
        .limit(candidate_limit)
    ).all()

    ranked = [
        (m, float(fused_score), float(vs), float(fts))
        for m, fused_score, vs, fts in candidates
        if float(fused_score) >= min_sim
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)

    from app.services import relations

    relation_map = relations.latest_relations(session, [m.id for m, *_ in ranked[:top_k]])
    return [
        {
            "id": m.id,
            "scope": m.scope,
            "entity_id": m.entity_id,
            "tipo": m.tipo.value,
            "titulo": m.titulo,
            "contenido": m.contenido,
            "topic_key": m.topic_key,
            "pin": m.pin,
            "status": m.status.value,
            "needs_review": m.status is MemoryStatus.NEEDS_REVIEW,
            "relation": relation_map[m.id].relation if m.id in relation_map else None,
            "relation_confidence": (
                relation_map[m.id].confidence if m.id in relation_map else None
            ),
            "relation_reason": relation_map[m.id].reason if m.id in relation_map else None,
            "stale": _is_stale(m.review_after),
            "score": round(float(score), 4),
        }
        for m, score, _, _ in ranked[:top_k]
    ]


def load_customer_context(session: Session, customer_id: int) -> str:
    """Return the customer's memory context as text for prompt injection (CM-7).

    Reads all `scope='customer'` memories for the entity and renders them as
    `titulo: contenido` lines. Empty when the customer has no memories yet — the
    caller proceeds with an empty context and never blocks the reply.
    """
    from app.services import relations

    rows = [
        row
        for row in list_for_entity(session, scope="customer", entity_id=str(customer_id))
        if row.status is not MemoryStatus.ARCHIVED
    ]
    relation_map = relations.latest_relations(session, [row.id for row in rows])
    now = datetime.now(timezone.utc)
    return "\n".join(
        (
            f"{m.titulo}"
            + (
                f" (stale since {m.review_after.date().isoformat()})"
                if _is_stale(m.review_after, now=now)
                else ""
            )
            + (
                f" ({relations.relation_annotation(m.id, relation_map[m.id])})"
                if m.id in relation_map
                else ""
            )
            + f": {m.contenido}"
        )
        for m in rows
    )


def persist_memory_session(session: Session, state: Any) -> None:
    """Flush the current turn into the session memory before END (CM-8).

    Accumulates the exchange: reads the existing `topic_key='session'` memory
    (if any) and appends the latest inbound user text, so a subsequent turn's
    `load_customer_context` sees the full conversation recap rather than only
    the most recent message (R3-001). KB-style contract: the caller commits.
    """
    text = _current_turn_text(state)
    if not text:
        return
    previous = get_by_key(
        session,
        scope="customer",
        entity_id=str(state.customer_id),
        topic_key="session",
    )
    combined = (
        f"{previous.contenido}\n{text}" if previous and previous.contenido else text
    )
    upsert(
        session,
        scope="customer",
        entity_id=str(state.customer_id),
        topic_key="session",
        tipo=MemoryType.SESSION,
        titulo="session",
        contenido=combined,
    )


def _current_turn_text(state: Any) -> str:
    """The latest inbound user text from a rebuilt ConversationState (CM-8).

    Only the final window entry when it is the user's inbound message; empty
    otherwise so an outbound reply is never recorded as the turn's recap.
    """
    if not state.window:
        return ""
    entry = state.window[-1]
    if entry.get("direction") != "inbound":
        return ""
    return entry.get("text") or ""


# ---------------------------------------------------------------------------
# S3 — close event: customer_memo + typed observations (MEM-4, MEM-5, CM-9)
# ---------------------------------------------------------------------------


def close_conversation(session: Session, conversation: Conversation, *, acta_text: str) -> None:
    """Close-time handler: upsert the customer_memo and persist observations.

    MEM-4/CM-9: upserts the customer_memo (`scope=customer`,
    `topic_key='customer_memo'`) under the conversation's customer, reusing the
    CM-5 acta content (`conversation.summary`) VERBATIM — the acta is consumed,
    never rewritten (CM-9 boundary). Then derives and persists the typed
    observations for the close (MEM-5) against persisted data (case row,
    message flow, prior closes) since a panel close has no in-run
    `ConversationState`.

    KB-style contract: the caller owns the session and commits.
    """
    customer_id = conversation.customer_id
    memo = upsert(
        session,
        scope="customer",
        entity_id=str(customer_id),
        topic_key="customer_memo",
        tipo=MemoryType.CUSTOMER_MEMO,
        titulo="customer_memo",
        # Reuse the CM-5 acta verbatim. A conversation with no summary yet
        # degrades to an empty memo rather than inventing content (CM-9).
        contenido=acta_text or "",
        producer=MemoryProducer.SYSTEM,
        origin_thread_id=str(conversation.id),
    )
    from app.services import relations

    relations.judge_memory_relations(session, memo)
    _record_observations(session, conversation)


def _record_observations(session: Session, conversation: Conversation) -> None:
    """Persist any typed observations that fire for the close (MEM-5).

    The patterns read persisted data so they work for a panel close (no in-run
    state): recurrencia (prior closes in window), sin_respuesta (last message
    inbound, no bot reply), riesgo (escalated emergency case row), oportunidad
    (case left with no ticket). Each writes a `memory_observations` row scoped
    to the customer.
    """
    settings = get_settings()

    if _fires_recurrencia(session, conversation, settings):
        _write_observation(
            session,
            conversation.customer_id,
            ObservationType.RECURRENCIA,
            {
                "window_days": settings.obs_recur_window_days,
                "count": settings.obs_recur_count,
                "topic_key": "customer_memo",
            },
        )

    if _fires_sin_respuesta(session, conversation, settings):
        _write_observation(
            session,
            conversation.customer_id,
            ObservationType.SIN_RESPUESTA,
            {"hours": settings.obs_no_reply_hours},
        )

    if _fires_riesgo(session, conversation):
        _write_observation(session, conversation.customer_id, ObservationType.RIESGO, {})

    if _fires_oportunidad(session, conversation):
        _write_observation(
            session, conversation.customer_id, ObservationType.OPORTUNIDAD, {}
        )


def _write_observation(
    session: Session, customer_id: int, tipo: ObservationType, detalle: dict
) -> None:
    """Insert a customer-scoped observation row (MEM-5). Caller commits."""
    session.add(
        MemoryObservation(
            scope="customer",
            entity_id=str(customer_id),
            tipo=tipo,
            detalle=detalle,
        )
    )
    session.flush()


def _fires_recurrencia(session: Session, conversation: Conversation, settings) -> bool:
    """MEM-5 recurrence: this close makes N closes in window reach the count.

    Counts prior CLOSED conversations for the same customer within
    `obs_recur_window_days`; fires when the count plus this close reaches
    `obs_recur_count` (the design threshold, configurable via Settings).
    """
    window_start = datetime.now(timezone.utc) - timedelta(days=settings.obs_recur_window_days)
    prior_closes = session.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.customer_id == conversation.customer_id,
            Conversation.state == ConversationStateEnum.CLOSED,
            Conversation.closed_at >= window_start,
            Conversation.id != conversation.id,
        )
    ) or 0
    return prior_closes + 1 >= settings.obs_recur_count


def _fires_sin_respuesta(session: Session, conversation: Conversation, settings) -> bool:
    """Inbound with no bot reply within the configured hours (MEM-5).

    Fires when the conversation's newest message is an inbound the bot never
    answered: no OUTBOUND reply newer than that inbound. The age is bounded by
    `obs_no_reply_hours` (a reply older than the window is dismissed).
    """
    last = session.scalar(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id.desc())
        .limit(1)
    )
    if last is None or last.direction != MessageDirection.INBOUND or not last.created_at:
        return False
    # An inbound answered right away, or one so old the wait is no longer this
    # close's concern, does not count as "no response" (bounded by the SLA).
    if last.created_at < datetime.now(timezone.utc) - timedelta(hours=settings.obs_no_reply_hours):
        return False
    # No outbound reply after the last inbound.
    reply = session.scalar(
        select(Message.id)
        .where(
            Message.conversation_id == conversation.id,
            Message.direction == MessageDirection.OUTBOUND,
            Message.id > last.id,
        )
        .limit(1)
    )
    return reply is None


def _fires_riesgo(session: Session, conversation: Conversation) -> bool:
    """An escalated emergency case flags a risk on close (reuses EM-1 flag)."""
    case = session.scalar(
        select(Case)
        .where(Case.conversation_id == conversation.id)
        .order_by(Case.id.desc())
        .limit(1)
    )
    return bool(case is not None and case.emergency)


def _fires_oportunidad(session: Session, conversation: Conversation) -> bool:
    """A case left with no ticket is a follow-up opportunity (MEM-5)."""
    case = session.scalar(
        select(Case)
        .where(Case.conversation_id == conversation.id)
        .order_by(Case.id.desc())
        .limit(1)
    )
    # No ticket yet -> the case was closed without a resolution ticket, so it is
    # a potential follow-up / sales opportunity.
    return bool(case is None or case.status is None)
