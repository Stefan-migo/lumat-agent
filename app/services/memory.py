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
`close_conversation`, and `record_observation`; `suggest_relations` is deferred
(YAGNI — no consumer until the relations worker). This slice ships only the
CRUD + hybrid search primitives; `REL_MIN_SIM` is declared now so S3 reuses the
agreed constant (design "fines de detalle fino").
"""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Memory, MemoryStatus, MemoryType
from app.services import kb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Concrete thresholds (design "fines de detalle fino")
# ---------------------------------------------------------------------------
MEM_MIN_SIM = 0.55          # fused score gate for hybrid_search
REL_MIN_SIM = 0.85          # cosine pair gate for suggest_relations (S3+)
FTS_BOOST = 0.3             # fused = vector + 0.3 * fts (vector dominates)
DEFAULT_TOP_K = 5
WRITABLE_PROYECTO = "default"

# Embedder resilience (R4-001): bounded retry with short backoff on transient
# model-init or network failures, then a clear logged failure.
EMBED_RETRIES = 2
EMBED_BACKOFF_SECONDS = (0.1, 0.3)


def _guard_writable_project(proyecto: str) -> None:
    """Reject writes targeting a non-default project (MEM-2)."""
    if proyecto != WRITABLE_PROYECTO:
        raise ValueError(
            f"memory writes are restricted to proyecto='default', got {proyecto!r}"
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
) -> Memory:
    """Create-or-update one memory by (proyecto, scope, entity_id, topic_key).

    Embeds `contenido` via `kb.embed_texts()` (384d). Rejects `proyecto !=
    'default'` before any DB write and persists nothing (MEM-2). On the same
    key the existing row is reused and its content/embedding refreshed —
    uniqueness enforced by `UNIQUE(proyecto, scope, entity_id, topic_key)`.
    """
    _guard_writable_project(proyecto)

    embeddings = _embed([contenido])
    if not embeddings:
        raise ValueError("cannot embed empty memory content")
    embedding = embeddings[0]

    row = session.execute(
        select(Memory).where(
            Memory.proyecto == proyecto,
            Memory.scope == scope,
            Memory.entity_id == entity_id,
            Memory.topic_key == topic_key,
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
            pin=pin,
        )
        session.add(row)
    else:
        row.tipo = tipo
        row.titulo = titulo
        row.contenido = contenido
        row.embedding = embedding
        row.pin = pin
    session.flush()
    return row


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
    rows = list_for_entity(session, scope="customer", entity_id=str(customer_id))
    return "\n".join(f"{m.titulo}: {m.contenido}" for m in rows)


def persist_memory_session(session: Session, state: Any) -> None:
    """Flush the current turn as a session memory before END (CM-8).

    Upserts a single `topic_key='session'` memory under the customer so a
    subsequent turn's `load_customer_context` sees the previous exchange — the
    "persisted next turn" guarantee. KB-style contract: the caller commits.
    """
    text = _current_turn_text(state)
    if not text:
        return
    upsert(
        session,
        scope="customer",
        entity_id=str(state.customer_id),
        topic_key="session",
        tipo=MemoryType.SESSION,
        titulo="session",
        contenido=text,
    )


def _current_turn_text(state: Any) -> str:
    """The latest inbound user text from a rebuilt ConversationState (CM-8)."""
    return state.window[-1]["text"] if state.window else ""
