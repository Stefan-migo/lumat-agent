"""Inline memory relation candidate search and hybrid LLM judging."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Memory, MemoryRelation, MemoryStatus
from app.services import llm
from app.services.tukulpan import DECAYING_TYPES, REL_MIN_SIM

RELATION_VOCAB = frozenset(
    {"supersedes", "conflicts", "related", "compatible", "scoped", "not_conflict"}
)
AUTO_JUDGE_CONFIDENCE = 0.7


def find_candidates(session: Session, memory: Memory, *, top_k: int = 5) -> list[Memory]:
    """Return the bounded, same-axis cosine candidates for one assertion."""
    if memory.tipo in DECAYING_TYPES or top_k <= 0:
        return []

    distance = Memory.embedding.cosine_distance(memory.embedding)
    rows = session.execute(
        select(Memory)
        .where(
            Memory.id != memory.id,
            Memory.proyecto == memory.proyecto,
            Memory.scope == memory.scope,
            Memory.entity_id == memory.entity_id,
            Memory.status != MemoryStatus.ARCHIVED,
            Memory.tipo.notin_(DECAYING_TYPES),
            distance <= 1 - REL_MIN_SIM,
        )
        .order_by(distance)
        .limit(top_k)
    ).scalars().all()
    return list(rows)


def _judge_payload(memory: Memory, candidates: list[Memory]) -> str:
    candidate_text = "\n".join(
        f"- candidate_id={candidate.id}: {candidate.titulo}: {candidate.contenido}"
        for candidate in candidates
    )
    return (
        "Judge the new memory against every candidate. Return JSON only, with exactly one "
        "verdict per candidate in this shape: {\"verdicts\":[{\"candidate_id\":number,"
        "\"relation\":string,\"confidence\":number,\"reason\":string}]}. "
        "relation must be one of supersedes, conflicts, related, compatible, scoped, "
        "not_conflict. confidence must be between 0 and 1.\n\n"
        f"New memory: {memory.titulo}: {memory.contenido}\nCandidates:\n{candidate_text}"
    )


def _parse_verdicts(content: str, candidate_ids: set[int]) -> list[dict[str, Any]]:
    payload = json.loads(content)
    if not isinstance(payload, dict) or set(payload) != {"verdicts"}:
        raise ValueError("judge response must contain only verdicts")
    verdicts = payload["verdicts"]
    if not isinstance(verdicts, list) or len(verdicts) != len(candidate_ids):
        raise ValueError("judge response must contain one verdict per candidate")

    parsed: list[dict[str, Any]] = []
    seen: set[int] = set()
    for verdict in verdicts:
        if not isinstance(verdict, dict) or set(verdict) != {
            "candidate_id", "relation", "confidence", "reason"
        }:
            raise ValueError("invalid verdict shape")
        candidate_id = verdict["candidate_id"]
        relation = verdict["relation"]
        confidence = verdict["confidence"]
        reason = verdict["reason"]
        if (
            type(candidate_id) is not int
            or candidate_id not in candidate_ids
            or candidate_id in seen
            or relation not in RELATION_VOCAB
            or type(confidence) not in (int, float)
            or not 0 <= confidence <= 1
            or not isinstance(reason, str)
        ):
            raise ValueError("invalid verdict value")
        seen.add(candidate_id)
        parsed.append(verdict)
    if seen != candidate_ids:
        raise ValueError("judge response omitted a candidate")
    return parsed


def judge_memory_relations(
    session: Session, memory: Memory, *, top_k: int = 5
) -> list[MemoryRelation]:
    """Judge one written assertion, degrading to no-op on an invalid LLM answer."""
    candidates = find_candidates(session, memory, top_k=top_k)
    if not candidates:
        return []

    try:
        response = llm.openai_client().chat.completions.create(
            model=llm.CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You classify memory relations. Never invent facts and return strict JSON.",
                },
                {"role": "user", "content": _judge_payload(memory, candidates)},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        verdicts = _parse_verdicts(content, {candidate.id for candidate in candidates})
    except Exception:
        return []

    rows = [
        MemoryRelation(
            id_a=memory.id,
            id_b=verdict["candidate_id"],
            relation=verdict["relation"],
            confidence=float(verdict["confidence"]),
            reason=verdict["reason"],
            source="judge",
        )
        for verdict in verdicts
    ]
    try:
        with session.begin_nested():
            session.add_all(rows)
            session.flush()
    except Exception:
        return []
    return rows


def latest_relations(session: Session, memory_ids: list[int]) -> dict[int, MemoryRelation]:
    """Return the newest relation signal for each requested memory id."""
    if not memory_ids:
        return {}
    rows = session.execute(
        select(MemoryRelation)
        .where(or_(MemoryRelation.id_a.in_(memory_ids), MemoryRelation.id_b.in_(memory_ids)))
        .order_by(MemoryRelation.created_at.desc(), MemoryRelation.id.desc())
    ).scalars().all()
    result: dict[int, MemoryRelation] = {}
    for row in rows:
        result.setdefault(row.id_a, row)
        result.setdefault(row.id_b, row)
    return result


def relation_annotation(memory_id: int, relation: MemoryRelation | None) -> str | None:
    """Describe a relation for prompt context without changing its vocabulary."""
    if relation is None:
        return None
    if relation.relation == "supersedes" and relation.id_b == memory_id:
        return "superseded"
    if relation.relation == "conflicts":
        return "contradicted"
    return relation.relation


__all__ = [
    "AUTO_JUDGE_CONFIDENCE",
    "RELATION_VOCAB",
    "find_candidates",
    "judge_memory_relations",
    "latest_relations",
    "relation_annotation",
]
