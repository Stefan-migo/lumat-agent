# ODD: memory-write-conflict

**Branch**: `odd/memory-write-conflict`
**Worktree**: `../lumat-agent-odd-memory-write-conflict`
**Base**: `481f9cd9`
**Status**: completed

## Objective

Make `upsert()` safe under concurrent writers on the same memory identity. Today the loser of a race
raises `IntegrityError` instead of folding into the winner; after this change it folds (duplicate
identity) or revises in place (same `topic_key`), with no change to single-writer behavior.

## Problem (verified)

`upsert()` (`app/services/tukulpan.py:190-293`) resolves app-side and then writes: it SELECTs by
`(proyecto, scope, entity_id, topic_key)`, falls back to a SELECT by
`(proyecto, scope, entity_id, normalized_hash)`, and only then INSERTs. Two writers can both miss.

Two unique constraints can then reject the loser:

- `UNIQUE(proyecto, scope, entity_id, topic_key)` — `app/models.py:467`, pre-existing.
- `uq_memories_normalized_content` — partial unique on
  `(proyecto, scope, entity_id, normalized_hash) WHERE normalized_hash IS NOT NULL`
  (`app/models.py:469-477`, `db/migrations/028_memory_dedup.sql:8-10`), added by #252.

PostgreSQL makes this a deterministic failure, not a coin flip: the loser's INSERT waits on the
index entry and then raises `unique_violation` as soon as the winner commits. The loser's work is
lost and the caller sees an exception.

**Reachable, not theoretical.** Panel writes are thread-scoped and an assistant run per thread is
serialized by `active_run_id`, but the semantic axis `agent:{proyecto}` is cross-thread, and
WhatsApp webhooks for the same customer can run concurrently over the same
`(proyecto, scope, entity_id)`. That is the shape `#252` armed.

Origin: native review advisory `R3-concurrent-dedup-write`, round 2, lineage
`review-7b9167d0351bca3a` — WARNING, non-blocking, `evidence_class: inferential`,
`causal_disposition: behavior-activated`. Recorded as `followup/memory-write-conflict` (Engram
#4426). The TOCTOU shape is **pre-existing** in this function for the composite unique; #252 only
activated it on a new surface.

## Decisions

- **Savepoint + one bounded retry, not `ON CONFLICT`.** A single `INSERT ... ON CONFLICT` can carry
  only one conflict target, and this race has two; worse, the hash-collision resolution is a *fold*
  (`duplicate_count += 1`, keep the survivor) while the keyed rewrite must also delete a sibling and
  re-point its `MemoryObservation`/`MemoryRelation` references (`_fold_duplicate`,
  `app/services/tukulpan.py:164-188`) — that is not expressible as a conflict update. The savepoint
  keeps every existing branch of `upsert()` byte-for-byte and only re-runs it after the winner has
  committed and become visible (READ COMMITTED gives the retry a fresh snapshot per statement).
- **One retry, ceiling named.** Two concurrent writers is the reachable shape. A third writer racing
  both attempts is not a shape this app produces; the `ponytail:` comment names the ceiling and the
  upgrade path (bounded loop / conflict-target upsert) instead of pretending it is covered.
- **No change to observable single-writer semantics.** Same key → revision; different key with
  identical normalized content → fold with `duplicate_count += 1`; `_memory_equivalent` untouched.
- **Reuse the in-module precedent.** `session.begin_nested()` is already used in this same file
  (`app/services/tukulpan.py:446-464`, `write_recap`) and in the assistant write path
  (`app/chat/assistant/tools/registry.py:262-279`), so no new mechanism is introduced.
- **Cover both identities with the one mechanism.** The composite-unique case is the older instance
  of the same bug; fixing only the hash index would leave it open.

## Known trade-off (accepted)

`Session.begin_nested()` flushes pending state before establishing the SAVEPOINT. Callers that hold
pending changes now flush one statement earlier. The flush stays inside the caller's transaction, so
its rollback semantics are unchanged. If foreign pending state itself raises `IntegrityError`, the
retry consumes one extra attempt and then re-raises the same error — never a silent misresolution.

## Authorized scope

- `app/services/tukulpan.py` — `upsert()` and a private resolution helper.
- `tests/integration/test_memory_write_conflict.py` — new concurrency regression test.

## Out of scope (do not touch)

- Decay/TTL, relations worker, batch compression, user-prompt store, sync, WhatsApp memory push.
- Embedding/semantic dedup (deterministic hash only).
- `_fold_duplicate` semantics, `_memory_equivalent`, `projects.merge`.
- The spec: concurrency safety is not currently a `MEM-*` requirement. If the reviewer judges it
  belongs in the spec, that is a separate change.

## Tasks

- [x] **T1 — RED.** `tests/integration/test_memory_write_conflict.py` reproduces the collision
      deterministically: the loser's `before_flush` hook parks it after its lookups and before its
      INSERT; the winner then upserts and commits; the loser proceeds. Assert no exception, one row,
      `duplicate_count == 2`. Must fail against unmodified `upsert()`.
- [x] **T2 — RED (older instance).** Same harness, both writers using the **same** `topic_key`.
      Assert no exception and exactly one row. Must fail against unmodified `upsert()`.
- [x] **T3 — GREEN.** `upsert()` wraps its write resolution in `session.begin_nested()` and retries
      once on `IntegrityError`, then re-raises. Extraction into a private helper is acceptable;
      duplicated blocks are not.
- [x] **T4 — Verify.** Focused suites green, then the full suite green, with the count measured and
      reported (never asserted from memory).

## Acceptance criteria

1. Both regression tests pass, and each one **provably failed before the fix** (RED evidence recorded
   in Progress).
2. No existing memory test changes behavior: `tests/spec/test_memory_spec.py`,
   `tests/spec/test_projects_spec.py`, `tests/functional/test_api_memories.py`,
   `tests/integration/test_memory_*.py`, `tests/integration/test_sdb_persistence.py` all green.
3. Full suite green at `tests/`.
4. The diff touches only the two authorized files.

## Checks

```bash
eval "$(infra/test-db.sh env)"
uv run pytest tests/integration/test_memory_write_conflict.py -v      # RED, then GREEN
uv run pytest tests/spec/test_memory_spec.py tests/integration/test_memory_pipeline.py
uv run pytest tests/                                                   # full count
```

`pyproject.toml` sets `addopts = "-q"`; a second `-q` suppresses the summary line, so do not add
one. There is no linter, type checker, or formatter — the tests are the verification.

## Progress

- [x] Worktree created and provisioned; `.opencode/tools/package-lock.json` removed before the RDD
      preflight (it is untracked noise `rapso worktree create` leaves behind).
- [x] Graph Check: `upsert()` (`tukulpan.py:190`), `Memory` (`models.py:457`), `normalized_hash`,
      community `tukulpan.py`; `graphify affected upsert` matched the caller map.
- [x] T1/T2 RED: `eval "$(infra/test-db.sh env)"; uv run pytest tests/integration/test_memory_write_conflict.py -v`
      failed with `2 failed in 2.04s`. T1 failure text: `E assert not [IntegrityError('(psycopg.errors.UniqueViolation) duplicate key value violates unique constraint "uq_memories_normaliz...ized_hash)=(default, customer, 42, b06a990509975e0b1757061d5d1d86bb5a679ef2aaf8f156e4abb21a66ad5ab0) already exists.')]`.
      T2 failure text: `E assert not [IntegrityError('(psycopg.errors.UniqueViolation) duplicate key value violates unique constraint "memories_proyecto_sc...d_topic_key_key"\nDETAIL:  Key (proyecto, scope, entity_id, topic_key)=(default, customer, 42, fact) already exists.')]`.
- [x] T3 GREEN: extracted `_upsert_resolved()` and added a `begin_nested()` savepoint with one
      `IntegrityError` retry; second failure re-raises. Focused regression: `2 passed in 0.96s`.
- [x] T4: targeted memory suites: `81 passed, 1 warning in 20.15s`; full suite: `964 passed, 2 warnings in 125.57s (0:02:05)`.

## Next step

Commit the completed work unit.
