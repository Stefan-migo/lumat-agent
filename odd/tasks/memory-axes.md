# ODD: two-axis memory, provenance, and the visibility rule

**Work unit:** #4 of the Tukulpan/Engram series (decisions D2 / D2a)
**Source session:** `.rapsodia-code/sessions/ready-for-odd/2026-09-17-memoria-tukulpan-vs-engram/report.md`
**Worktree:** `../lumat-agent-odd-memory-axes` · branch `odd/memory-axes` · base `745cf0b4`
**Status**: merged — PR #242 (`5a7297c3`). Complete, verified, RDD-approved (lineage `review-970417edde559528`, authority burned).

---

## Objective

Give the memory layer its second axis and the provenance D2 requires, with the
visibility rule D2a makes mandatory and that the recon proved does not exist.

## Problem

Today memory has two scopes in production — `panel` / `entity_id=thread:{id}`
(episodic) and `customer` / `entity_id=customer:{id}` (per-client memo, already
gated per client by the panel). There is **no** axis for knowledge that is bound
to neither a thread nor a single client, and **no provenance column of any kind**
on `memories`, `memory_observations`, or `memory_relations`. `tipo` is the only
row classifier.

D2a states the exposure risk plainly: if the agent writes something derived from
a client onto a thread-independent axis, that row surfaces in another client's
thread. Provenance alone does not stop it. A rule does.

## Decision (locked with the human)

**Transversal con visibilidad declarada.** The agent declares the blast radius at
write time (`thread` | `project`); the server derives and records the origin and
enforces the read. `thread` is visible only in its own thread; `project` is
visible from any thread of the same project. Client-derived content belongs on
the `customer` axis, which the panel already gates per client.

Rejected alternatives and what died with them:

| Rejected | What it would have cost |
|---|---|
| Confined by origin (every agent row pinned to its writing thread) | The axis degenerates to episodic for everything discussed in a client thread — D2 delivers no value |
| Persist and never read (defer the axis) | The axis is born dead; D2 ships nothing in this work unit |

## Authorized scope

Schema + provenance + the visibility rule, and the reads/writes that must honour
them, for the assistant's memory tools and the panel read paths.

## Explicitly out of scope

- **Reported defect, not absorbed here.** `memory.read` / `memory.search` accept a
  model-supplied `entity_id`, so a `panel` read may target `thread:{any id}` — not
  just the current thread. That is a real cross-thread exposure and it is the same
  risk *class* as D2a, but it is a pre-existing defect in the episodic axis, not a
  D2/D2a deliverable. It gets its own work unit. Do NOT fix it here.
- Relations, lifecycle decay, session entities, sync, prompt memory (deferred by
  the original design, still deferred).
- `memory.kpis` misnomer (WU#5) and the DSML leak in the responder (WU#6).
- Fixing the `customer` axis general `delete()` / `set_mark()` by-ID paths.

## Constraints

- **Strict TDD is active** (`apply.tdd=true`, `test_command "pytest tests/"`).
  RED must be observed **at assertion level** before implementation — a collection
  `ImportError` is not RED.
- Technical artifacts in English. No AI attribution. Conventional commits.
- `memory.write` stays the only member of `AUTONOMOUS_WRITE_ALLOWLIST`. Nothing in
  this work unit may widen it.
- The planner never supplies a write target. Same discipline WU#3 established.
- No new tool ⇒ the assistant tool whitelist count must not change.
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat` is required by
  the full suite. Never `docker compose down -v`.

## Graph check

Graph queried from the worktree (symlinked `graphify-out/`, main's graph).

- `graphify query "memory layer: memories table, memory service, tukulpan embeddings"` → communities `tukulpan.py`, `models.py`, `registry.py`, `memory.py`, `test_memory_spec.py`.
- `graphify query "memory scope entity_id memories table"` → god-ish nodes `memories`, `Memory`, `Scope`, "All memories for one (scope, entity_id), newest first (MEM-2)".
- Nodes/edges consulted for the touched files: `Memory` (`app/models.py:431`), `MemoryType`/`MemoryStatus` (`:120`, `:131`), `pg_enum` (`:40`), `app/services/tukulpan.py` community (`upsert` `:123`, `list_for_entity`, `hybrid_search`, `write_recap`), `app/chat/assistant/tools/registry.py` community (`TOOL_REGISTRY` `:302`, `execute_tool` `:338`), `app/panel/api/routes/clients.py` + `serializers.py` (`Memory row -> snake_case service dict`), spec nodes `memories MUST enforce UNIQUE(proyecto, scope, entity_id, topic_key)`.
- Graph is structurally current (built from `73175b1d`); `--update` is deferred to
  session close, per the Graphify policy.

## Design

### `visibility` is the axis selector

| declared `visibility` | derived `scope` | derived `entity_id` | meaning |
|---|---|---|---|
| `thread` (default) | `panel` | `thread:{trusted thread id}` | episodic, thread-local |
| `project` | `agent` | `agent:<project>` | semantic, transversal within that project only |

The server derives both values. The model declares only the visibility.

### Provenance is derived, never an argument

- `producer` ∈ `user | system | agent | pipeline` — `agent` on the autonomous
  write path, `pipeline` for recap/SDB, `system` for panel milestones and the
  close memo, `user` when an operator acts through the panel.
- `origin_thread_id` — the thread the row came from, where the call site already
  has it at hand.

### The agent entity is a canonical constant, not a model choice

`agent_memory_entity(proyecto)` lives in the service and returns `f"agent:{proyecto}"`.
The project is part of the entity so a project-visible row can never be reached by
a read bound to a different project. `visibility_target` takes `proyecto` as a
REQUIRED keyword-only argument — no default — so no caller can silently produce a
global entity. Reads and writes both validate against it, the same shape as the
existing `panel` `thread:` prefix rule, so no conditional-required schema.

### Trade-off check on the `visibility` column (Ponytail, two-sided)

If it were cut, the declaration would live only as the derived `scope`, and the DB
could no longer express "a `panel` row must not be project-visible". Recording the
declared value keeps the audit trail of what the agent *asked for* separate from
what the server *derived*, and makes the coherence rule enforceable in the schema
rather than only in application code. Cost accepted: `visibility` is functionally
determined by `scope` today (the biconditional `visibility='project' ⟺ scope='agent'`
holds), so the column is redundant by strict normalisation. It is kept as an
audited declaration with a coherence constraint; a `ponytail:` comment in the
migration names that ceiling and the upgrade path (widen the mapping, keep the
declaration).

### The panel promise is preserved by not changing it

`/clients/{id}/memories` filters `scope="customer"` and the selected client's
entity. Agent rows must never appear on a client ficha. This is already true; the
work unit locks it with a spec scenario and a test rather than with new code.

---

## Tasks

- [ ] **T1 — Migration `026_memory_provenance.sql`.**
  Two native enums (`memory_producer`, `memory_visibility`) following the file's own
  convention, three columns on `memories` with conservative backfill defaults
  (`producer='system'`, `visibility='thread'`, `origin_thread_id=NULL`), and an
  axis/visibility coherence constraint. No new index — `idx_memories_entity`
  already covers every read, which stays an exact `(proyecto, scope, entity_id)`
  match. Document honestly that the true producer of pre-existing rows is
  unrecoverable and `system` is a conservative placeholder.

- [ ] **T2 — `app/models.py`.**
  `MemoryProducer` and `MemoryVisibility` enums next to `MemoryType`/`MemoryStatus`,
  and the three mapped columns on `Memory` via the existing `pg_enum` helper.

- [ ] **T3 — `app/services/tukulpan.py`.**
  `AGENT_SCOPE`, `AGENT_MEMORY_ENTITY`, `visibility_target(visibility, *, thread_id)`
  returning `(scope, entity_id)`, and `upsert()` extended with `producer`,
  `origin_thread_id`, `visibility`. Existing call sites pass provenance explicitly
  where it is knowable (recap → `pipeline`, SDB → `pipeline`, milestone/close memo →
  `system`), and set `origin_thread_id` where the thread is already at hand.

- [ ] **T4 — `app/chat/assistant/tools/registry.py`.**
  `MemoryWriteArgs` gains `visibility: Literal["thread","project"] = "thread"`;
  `_write_memory` maps through `visibility_target` and stamps `producer=agent` and
  `origin_thread_id={trusted thread}`; `_MemoryScopeArgs` admits `agent` and
  enforces that the agent entity equals the canonical constant. `entity_id` stays a
  flat required string — no conditional-required schema. The write target remains
  server-derived; `scope`/`entity_id` remain forbidden on `memory.write`.

- [ ] **T5 — Specs.**
  `openspec/specs/assistant-tools/spec.md`: AT-8 admits the third scope and its
  canonical-entity rule; AT-9 records the declared `visibility`, its `thread`
  default, the server-derived producer/origin, and the `project` → agent axis
  mapping. `openspec/specs/memory/spec.md`: land MEM-3's *Role isolation* scenario
  (it promises the rule today without defining it) and add **MEM-9 — Memory
  Provenance and Axis Coherence**.

- [ ] **T6 — Tests (RED first, assertion level).**
  Migration/model shape; `visibility=project` lands at `agent`/`agent:assistant`
  with `producer=agent` and the origin thread; default `visibility=thread` leaves
  the episodic behaviour byte-identical; a non-canonical agent entity is rejected;
  `scope`/`entity_id` remain forbidden on `memory.write`; the coherence rule
  rejects a `panel` row declared project-visible; the agent entity constant matches
  the registry; the client ficha returns only `customer` rows while agent rows
  exist; tool count unchanged.

---

## Acceptance criteria

1. `memory.write(visibility="project")` persists a row readable from another thread
   of the same project, with `producer=agent` and `origin_thread_id` recording the
   writing thread.
2. `memory.write` without `visibility` behaves exactly as it does today.
3. No `memory.write` payload can name its own `scope`, `entity_id`, `producer`, or
   origin.
4. A `panel` row cannot be project-visible; a non-canonical agent entity cannot be
   read.
5. `/clients/{id}/memories` never returns an agent-axis row.
6. `AUTONOMOUS_WRITE_ALLOWLIST` still has exactly one member and the assistant tool
   whitelist count is unchanged.
7. Full suite green.

## Checks

- Targeted: `DATABASE_URL=... pytest tests/spec/test_memory_spec.py tests/unit/test_assistant_tools.py` (plus the touched integration/functional files).
- Full suite: `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat pytest tests/` — ~886 tests, ~8-9 minutes. `pyproject.toml` already sets `addopts = "-q"`; do not add a second `-q`.
- No linter, typechecker, or pre-commit hook exists in this repo. The tests are the verification.

## Progress and evidence

_(appended as tasks complete — RED output, GREEN output, suite result, review lineage)_

## Next step

T1: write the migration, then observe RED for the schema shape before T2.

## Apply progress

### T1 — Migration

- RED: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/integration/test_migrations.py::test_memory_provenance_schema -q` → `F [100%]`; assertion failed with `KeyError: 'memory_producer'`.
- GREEN: same command → `. [100%]`.
- Graph nodes consulted: `Schema (009_memory.sql)`, `test_enums_materialized()`, `test_migrations.py`, `memories`.
- Graph path query: `db/migrations/009_memory.sql` → `memories` returned no directed path; the query resolved the migration/schema nodes above.

### T2 — ORM model

- RED: `.venv/bin/pytest tests/unit/test_memory_model.py -q` → `F [100%]`; assertion failed with `assert hasattr(models, "MemoryProducer")`.
- GREEN: same command → `. [100%]`.
- Graph nodes consulted: `Memory`, `MemoryType`, `MemoryStatus`, `pg_enum()`.
- Graph path query: `Memory` → `pg_enum` returned no directed path; the query resolved both model nodes and their `models.py` community.

### T3 — Tukulpan provenance and target mapping

- RED: `.venv/bin/pytest tests/unit/test_tukulpan_provenance.py -q` → `FFF [100%]`; assertions failed because `AGENT_MEMORY_ENTITY` and `visibility_target` were absent.
- GREEN: `.venv/bin/pytest tests/unit/test_tukulpan_provenance.py tests/unit/test_memory_model.py -q` → `.... [100%]`.
- Graph nodes consulted: `upsert()`, `write_recap()`, `persist_sdb_artifact()`, `record_milestone()`, `archive_report()`, `close_conversation()`, `tukulpan.py`, `Memory`.
- Graph path query: `upsert()` → `write_recap` returned no directed path; the query resolved both Tukulpan nodes and the service community.

### T4 — Assistant memory tool contract

- RED: `.venv/bin/pytest tests/unit/test_memory_tool_axes.py -q` → `FFF [100%]`; visibility was rejected as an extra field, `agent` was rejected as a scope, and the pre-implementation write path lacked the requested mapping.
- GREEN: same command → `... [100%]`.
- Graph nodes consulted: `MemoryWriteArgs`, `_MemoryScopeArgs`, `_write_memory`, `execute_tool()`, `TOOL_REGISTRY`, `registry.py`, `upsert()`.
- Graph path query: `MemoryWriteArgs` → `_write_memory` returned no directed path; the query resolved both registry nodes and the execution boundary.

### T5 — Specifications

- Updated AT-8/AT-9 and MEM-3/MEM-9 with the canonical agent axis, declared visibility, provenance, and coherence rule.
- Graph nodes consulted: `assistant-tools Specification`, `Memory Specification`, `registry.py`, `tukulpan.py`, `Memory`.
- Graph path query: `AT-9` → `MEM-9` returned no directed path; the query resolved the two specification communities.

### T6 — Tests and verification

- Targeted GREEN: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/integration/test_migrations.py tests/spec/test_memory_spec.py tests/unit/test_memory_model.py tests/unit/test_tukulpan_provenance.py tests/unit/test_memory_tool_axes.py tests/unit/test_assistant_tools.py tests/functional/test_api_memories.py` → `97 passed in 30.23s`.
- Full-suite attempt: `TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5432/lumat' .venv/bin/pytest tests/` → `174 passed, 735 errors`; the environment was not exported, so the suite used the default port and failed to connect.
- Full-suite verification of record: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/` → `1 failed, 908 passed, 2 warnings`; the only failure was pre-existing `tests/integration/test_db.py::test_audit_is_append_only_via_grants`, which hard-codes `localhost:5432` while this worktree's namespaced test DB is on its derived port (`5537`). This is a test-harness contradiction with the worktree isolation contract, not a memory-axes failure.
- New test coverage: migration/model shape, project visibility across threads, thread default, canonical agent entity, provenance, coherence rejection, client-ficha filtering, forbidden write targets, and unchanged autonomous-write/tool whitelist contracts.
- Graph nodes consulted: `test_migrations.py`, `test_memory_spec.py`, `test_api_memories.py`, `test_assistant_tools.py`, `Memory row -> snake_case service dict`, `clients.py`, `registry.py`, `tukulpan.py`.
- Graph path query: `_write_memory` → `clients.py` returned no directed path; the query resolved the assistant registry and panel client serializer/read communities.

---

## Correction — R3-project-isolation (CRITICAL, one bounded round)

**Raised by the native review** (lineage `review-970417edde559528`, lens `review-reliability`) and **corroborated by the refuter**:

> Project-visible memories are mapped to one global agent entity without deriving or preserving the current project, so memories written from one project can be exposed to another project's agent reads.

**Root cause.** `AGENT_MEMORY_ENTITY = "agent:assistant"` was a single global constant and
`visibility_target()` ignored the project entirely, so a declared `visibility="project"` write was
never bound to a project namespace. The `proyecto` filter would have hidden it only by accident, and
only while one namespace stayed writable.

**Fix applied.**

- `AGENT_MEMORY_ENTITY` removed; replaced by `agent_memory_entity(proyecto) -> f"agent:{proyecto}"`.
  The project is now part of the entity, so a project-visible row cannot be reached by a read bound
  to a different project even when the writable namespace widens.
- `visibility_target(..., proyecto)` — `proyecto` is now a REQUIRED keyword-only argument with no
  default, which is the enforcement that stops any caller from silently producing a global entity.
- The assistant tool layer binds the project at the write boundary, which is where the binding is
  created: `_write_memory` passes `proyecto=WRITABLE_PROYECTO` through `visibility_target` and to
  `upsert`. The read side is deliberately NOT churned: `list_for_entity` / `hybrid_search` already
  resolve the same canonical namespace through their service default, so passing the constant again
  from the tool layer was redundant plumbing — and it broke the pinned call contract in
  `tests/integration/test_assistant_harness_compatibility.py`. Isolation is enforced by the
  project-qualified entity, not by restating the default.
- Specs updated: AT-8 (canonical project-scoped agent entity), AT-9 (`project` → `agent:<project>`,
  project bound server-side), MEM-9 (the entity MUST be project-qualified).
- Tests: the project-derivation assertion replaces the registry-name drift test (no longer
  applicable, since the entity no longer encodes the assistant name), plus a proof that a row
  written for one project is unreachable from a read bound to another.

**Scope of the round:** 9 files, +63/−37 (the declared `correction_lines`), inside the native
correction budget of 200. Targeted verification: `97 passed in 23.00s`. No commit was created by the
implementer; the correction is committed on the branch so the corrected candidate exists under the
`--committed-only` review projection.

**Regression found and fixed by the orchestrator's full-suite run.** The implementer verified only
the seven touched test files, and the first full suite on the corrected candidate showed
`2 failed, 907 passed`:

- `tests/integration/test_db.py::test_audit_is_append_only_via_grants` — pre-existing and unrelated:
  it hard-codes `localhost:5432` while every environment derives its own test-DB port (main `5986`,
  this worktree `5537`), so it fails with `Connection refused` on any checkout after the worktree
  isolation landed. Not caused by this work unit.
- `tests/integration/test_assistant_harness_compatibility.py::test_memory_read_rejects_cross_scope_entity_shapes`
  — **caused by this correction**. It pins the exact kwargs of the `memory.read` call, and the
  correction had added `proyecto` to the read path. Fixed by removing that redundant plumbing rather
  than by relaxing the pinned contract: the service default already resolves the same namespace, so
  the read-side pass-through changed nothing behaviourally while widening the blast radius of the
  correction.

Lesson recorded: a bounded correction must be verified with the full suite, not only with the test
files the implementer happened to touch.

**Honest limitation.** There is still no thread→project binding in the assistant: `InternalChatThread`
carries no project and `WRITABLE_PROYECTO` is the only writable namespace today. The fix makes the
project an explicit, required, recorded part of the agent axis, so the isolation is structural rather
than incidental — but it does not invent a per-thread project that the data model does not have.

---

## Review outcome — RDD lineage `review-970417edde559528`

- **Tier:** medium · **lenses:** one (`review-reliability`) · **correction budget:** 200 lines.
- **Frozen candidate:** base tree `3cc3abe1` (commit `745cf0b4`) → candidate tree `b27ca1fa`, 14
  paths, 656 changed lines.
- **Lens result:** one CRITICAL — `R3-project-isolation`, causal disposition `introduced`.
- **Refuter:** corroborated → `correction_required`.
- **Correction:** one bounded round, declared at 63 positive lines, committed as `4e4df1ca`
  (final tree `2c05a4b0`).
- **Targeted validation:** passed → **state `approved`**.
- **Acknowledgement:** `gentle-ai.review-acknowledged/v1`, `action: acknowledged`,
  `authority: burned`, consumed revision `sha256:25cb7a16…`.
- **Verification of record (orchestrator):** `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/`
  → `1 failed, 908 passed, 2 warnings in 403.60s`. The single failure is the pre-existing
  `tests/integration/test_db.py` hard-coded port, unrelated to this work unit.
- Commit, push, and PR remain separate human decisions under ordinary repository policy.

### Transport note (recorded honestly, root cause not established)

The first three `review-validator` Task launches were refused with
`opencode_provider_role_result_refused` — "OpenCode Task transport did not produce a capturable
reviewer result" — deterministically, and independently of the prompt shape (three different
shapes were tried). The fourth launch, on the fresh binding produced after the correction commit,
succeeded. `review-reliability` and `review-refuter` worked on their first attempts.

`~/.config/opencode/plugins/opencode-review-transport.ts` sends
`error: "opencode_task_host_output_unavailable"` when the host Task output is not a string, and the
`review-validator` agent declares `bash` as a permission **object** pattern while every other review
agent declares a flat `"deny"`. Neither observation was confirmed as the cause. Recorded as an
observation; no defect was filed and no report was opened.
