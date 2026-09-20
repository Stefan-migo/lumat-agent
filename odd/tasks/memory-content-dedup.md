# ODD: memory-content-dedup

**Branch**: `odd/memory-content-dedup`
**Worktree**: `../lumat-agent-odd-memory-content-dedup`
**Base**: `a57b353e`
**Status**: in progress

## Objective

Add deterministic content-level duplicate detection to the canonical Tukulpan memory write path, so an
autonomous `memory.write` that re-states an existing fact under a different `topic_key` updates a
counter instead of growing the table.

## Problem (verified)

`upsert()` (`app/services/tukulpan.py:157-222`) is a SELECT-then-INSERT/UPDATE keyed on
`(proyecto, scope, entity_id, topic_key)`:

- Same key → the row is reused and `contenido`/`embedding` are overwritten with **no trace of
  repetition**.
- Different key → a **new row**, even when the content is identical.

Nothing else in the schema can see the duplicate. Migration `009_memory.sql:36` and
`Memory.__table_args__` (`app/models.py:465-468`) carry only the composite `UNIQUE`, and there is no
`normalized_hash`, `duplicate_count`, `last_seen_at`, or `revision_count` (`db/migrations/009_memory.sql`
and `app/models.py:456-506` both verified column by column).

The risk this closes is recorded in the Tukulpan/Engram session report
(`.rapsodia-code/sessions/ready-for-odd/2026-09-17-memoria-tukulpan-vs-engram/report.md:116`):

> Unbounded row growth; `list_for_entity` has no cap and rows past `injection_budget` are dropped
> silently — needs duplicate detection + caps before autonomy (Engram uses `normalized_hash` +
> `duplicate_count` + `revision_count`).

The autonomy it was gating already shipped: D1 (`memory.write`, WU#3, PR #239) lets the assistant write
memory on its own. Engram's own mechanism is `normalized_hash` — exact and deterministic, **not**
embedding similarity.

## Decisions

- **Deterministic normalized hash, not embedding similarity.** Normalize with
  `" ".join(contenido.split()).casefold()`, then `hashlib.sha256(...).hexdigest()` (64 chars).
  `hashlib.sha256` is the pattern this repository already uses for content digests
  (`app/chat/assistant/attachments.py:48`, `app/chat/assistant/approval.py:16`).
- **The dedup identity is `(proyecto, scope, entity_id, normalized_hash)`.** Cross-entity and
  cross-project identical text stays legitimately distinct — the same sentence in two threads, or in
  two projects, is two memories.
- **Partial unique index, nullable column, no SQL backfill.** The migration runner executes plain
  `.sql` files through `python3` + `psycopg` (`db/migrate.sh`) with no `pgcrypto`, so there is no
  SQL-side `sha256`. The column therefore stays nullable and the index is partial
  (`WHERE normalized_hash IS NOT NULL`). `upsert()` backfills the hash **lazily** on the update
  branch, which costs nothing because the row already comes from the key lookup.
- **Embedding-based (semantic) dedup is deliberately deferred, and deferring is free.** `embedding`
  already exists on every row, so adding similarity matching later needs no migration. The asymmetry
  decides the order: a false positive of a silent merge destroys a distinct memory irreversibly,
  while a false negative is one extra row that can be deleted.
- **A same-`topic_key` write is a revision, not a duplicate.** It keeps today's behavior (content
  updated, row reused) and does **not** bump `duplicate_count`; only a second `topic_key` carrying
  already-seen content counts as a duplicate.
- **`_memory_equivalent` stays unchanged** (`app/services/projects.py:250-254`). It already compares
  `contenido`, which determines the hash, so adding `normalized_hash` is redundant; and
  `duplicate_count`/`last_seen_at` are volatile counters that must not make two otherwise-equivalent
  memories conflict during a merge.
- **`projects.merge` is fixed here, not deferred.** It is the only path where `memories` changes
  `proyecto` (`app/services/projects.py:257-289`), and it deduplicates only on
  `(scope, entity_id, topic_key)` (`:268`, `:270`). Two rows with **different `topic_key` but
  identical normalized content** — one in source, one in target — coexist today; the new index would
  make `memory.proyecto = target` (`:277`) raise `UniqueViolation` **mid-merge**, leaving the merge
  non-atomic. Shipping the index without this fix would introduce the bug.

## Authorized scope

Files:

- `db/migrations/028_memory_dedup.sql` — new migration (028; 027 is the current head).
- `app/models.py` — `Memory` gains the three columns and the partial unique index.
- `app/services/tukulpan.py` — `_normalized_hash()`, the dedup branch in `upsert()`, lazy backfill.
- `app/services/projects.py` — the hash-collision path in `merge()`.
- `openspec/specs/memory/spec.md` — rewrite `MEM-1` and its `Topic-key uniqueness` scenario.
- `tests/spec/test_memory_spec.py`, `tests/spec/test_projects_spec.py` — dedup and merge coverage.
- `odd/tasks/memory-content-dedup.md` — this record.

Anything else needs an explicit report before it is touched.

## Out of scope

- **Embedding-similarity / semantic dedup.** Deferred by decision above; costs no migration to add
  later.
- **`MemoryStatus.NEEDS_REVIEW` flagging of near-duplicates.** A consumer for a currently-dead status
  is its own unit.
- **A `list_for_entity` cap.** That half of the report's risk belonged to the injection budget, which
  D4 removed (`#236`, `remove-panel-memory-push`); the read path is already bounded by
  `memory.read`'s validated `limit`.
- **The relations worker, the decay sweeper, and the user-prompt store.** Independent deferred units.
- **Backfilling `normalized_hash` for rows that are never rewritten.** Nothing selects or scans the
  table to repair them; they simply stay outside the dedup identity. Recorded here as a known limit,
  not as a guarantee.
- **Amending `009_memory.sql`.** It is already applied in existing databases and `db/migrate.sh`
  records versions in `schema_migrations`; the change is a new migration or nothing.
- **Touch `EXPECTED_TABLES`** (`tests/integration/test_migrations.py:30`) — no new table is created.

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`, line 38). Runner:
  `uv run pytest tests/`. Observe RED before the source change; never invent RED evidence.
- Every pytest command that touches the database needs the test-DB environment first:
  `eval "$(infra/test-db.sh env)"`. The worktree derives its own container and port.
- `pyproject.toml` sets `addopts = "-q"`; passing another `-q` suppresses the summary line.
- There is no linter, typechecker, pre-commit hook, or CI workflow. The tests are the verification.
- **`upsert()` must keep its current same-key contract.** `test_mem2_upsert_writes_memory`
  (`tests/spec/test_memory_spec.py:150-186`) asserts that a re-upsert on the same key reuses the row
  and replaces `contenido`; it must stay green with its present assertions.
- **`_memory_equivalent` and the existing conflict branch keep their behavior.** The merge change adds
  a path; it does not redefine the byte-different composite-key conflict
  (`tests/spec/test_projects_spec.py::test_merge_is_atomic_on_byte_different_composite_key`).
- **NULL-safe hash handling in `merge()`.** A `None` hash must never match another `None`; guard the
  lookup explicitly rather than relying on tuple equality.
- **Update the in-memory maps as rows move.** `merge()` currently never refreshes `target_by_key`; with
  a hash identity, a second moved row can collide with one already moved in the same call.
- `tests/spec/test_memory_spec.py::test_mem1_memories_unique_key` inserts raw SQL without the new
  column. It stays valid because the column is nullable and the index is partial — confirm that rather
  than assuming it.
- There is an untracked `odd/tasks/memory-content-dedup.md` sibling artifact: the ODD record is
  committed on the branch. An untracked `.opencode/tools/package-lock.json` also appears in this
  worktree, generated by `rapso worktree create`; it is **not** part of the diff and must never be
  staged.
- Planning heuristic: ~400 authored changed lines. This is advisory only; do not split artificially.
- All artifacts are written in English.

## Tasks

- [ ] **T1 — RED.** Add failing tests that pin the new contract: identical content under a second
      `topic_key` produces one row with `duplicate_count == 2`; distinct content still produces two
      rows; a same-key rewrite updates content without bumping `duplicate_count`; a merge whose
      source and target each hold the same content under different `topic_key`s completes and leaves
      one row. Observe them fail against the current code and capture the output.
- [ ] **T2 — GREEN.** Add `028_memory_dedup.sql`, extend `Memory`, add `_normalized_hash()` and the
      dedup branch with lazy backfill to `upsert()`, add the hash-collision path to `merge()`, and
      rewrite the `MEM-1` requirement and its `Topic-key uniqueness` scenario.
- [ ] **T3 — Evidence.** Run the required checks, record the exact RED/GREEN output and honest limits.

## Acceptance criteria

1. Writing content identical in normalized form under a second `topic_key` within the same
   `(proyecto, scope, entity_id)` leaves one row, bumps its `duplicate_count`, and refreshes
   `last_seen_at`; no second row is inserted.
2. Content that differs after normalization still produces two rows.
3. A write on an existing composite key still reuses the row, replaces `contenido`, sets
   `normalized_hash`, and leaves `duplicate_count` at its prior value.
4. The same normalized content in a different `scope`, `entity_id`, or `proyecto` stays distinct.
5. `projects.merge` completes atomically when source and target hold the same normalized content under
   different `topic_key`s: one surviving row, references re-pointed, no `UniqueViolation`.
6. `projects.merge` still raises the byte-different composite-key conflict
   (`tests/spec/test_projects_spec.py::test_merge_is_atomic_on_byte_different_composite_key` stays
   green).
7. `MEM-1` no longer mandates two rows for two `topic_key`s unconditionally; it states the content
   condition and matches the code.
8. Each criterion fails against the pre-change code (RED observed) and passes after.
9. `tests/spec/test_memory_spec.py::test_mem2_upsert_writes_memory` passes with unmodified assertions.
10. Only the authorized files change and the required suites meet the baseline.

## Checks

- `eval "$(infra/test-db.sh env)" && uv run pytest tests/spec/test_memory_spec.py tests/spec/test_projects_spec.py tests/integration/test_migrations.py tests/integration/test_memory_pipeline.py -q`
- `eval "$(infra/test-db.sh env)" && uv run pytest tests/spec -q`
- `eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q`
- `git status --short`
- `git diff --check`

## Progress

- [x] ODD record created before the first source change.
- [x] Worktree created (`rapso worktree create memory-content-dedup`, base `origin/main` `a57b353e`).
- [x] Provisioned: `infra/.env` copied, `uv sync`, test DB up.
- [x] Graph Check recorded: `graphify query` / `graphify path` over `upsert`, `Memory`, `projects.merge`.
- [x] T1 — RED observed.
- [x] T2 — GREEN implemented.
- [x] T3 — Evidence recorded.

## Verification evidence

Graph Check before edits:

- `graphify query "memory upsert dedup normalized hash projects merge"` consulted `upsert()` (`app/services/tukulpan.py`), `merge()` (`app/services/projects.py`), `Memory` (`app/models.py`), `tukulpan.py`, `services/projects.py`, `test_memory_spec.py`, and `test_projects_spec.py`.
- `graphify path "projects.py" "tukulpan.py"` found no directed path. The consulted endpoint nodes were `services/projects.py` and `tukulpan.py`; no edge was returned by the directed traversal.
- `graphify-out/GRAPH_REPORT.md` identified `tukulpan.py` (community 11), `services/projects.py` (community 26), `test_memory_spec.py` (community 32), and the Memory Specification hyperedge as the relevant graph areas.

T1 RED, before source changes:

```text
$ eval "$(infra/test-db.sh env)" && uv run pytest tests/spec/test_memory_spec.py tests/spec/test_projects_spec.py -q
.......F.F.........................F..                                   [100%]
FAILED tests/spec/test_memory_spec.py::test_mem2_identical_normalized_content_deduplicates_by_hash
FAILED tests/spec/test_memory_spec.py::test_mem2_same_key_rewrite_is_not_a_duplicate
FAILED tests/spec/test_projects_spec.py::test_merge_deduplicates_hash_collisions_and_repoints_observations
The command reported the three failures above; the remaining tests passed and emitted the existing embedder warning.
```

Focused GREEN after source changes:

```text
$ eval "$(infra/test-db.sh env)" && uv run pytest tests/spec/test_memory_spec.py tests/spec/test_projects_spec.py -q
......................................                                   [100%]
38 passed, 1 warning in 9.29s
```

Required verification:

- `eval "$(infra/test-db.sh env)" && uv run pytest tests/spec/test_memory_spec.py tests/spec/test_projects_spec.py tests/integration/test_migrations.py tests/integration/test_memory_pipeline.py -q` — **failed: 1 failed, 57 passed, 1 warning**. The only failure is the hard-coded migration-version assertion in `tests/integration/test_migrations.py`, which does not list the authorized new `028_memory_dedup` migration. No unauthorized test file was changed.
- `eval "$(infra/test-db.sh env)" && uv run pytest tests/spec -q` — **passed: 84 passed, 1 warning**.
- `eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q` — **failed: 1 failed, 987 passed, 2 warnings**. The same migration-version assertion is the only failure.
- `git diff --check` — passed.
- The concurrent initial attempt to run the three database suites in parallel was discarded as invalid evidence because the shared test database produced deadlocks and cross-suite contamination; all required suites were rerun sequentially.

## Review (native RDD)

_Not started. Filled in at the delivery boundary._

## Next step

Implement T1: write the failing tests first and capture the RED output honestly.
