# ODD: asistente-kb-scope

**Branch**: `odd/asistente-kb-scope`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-asistente-kb-scope`
**Base**: `85d51825` (= `main` = `origin/main`, merge of PR #486)
**Status**: slice 3 complete (T1–T6). RDD review approved (lineage `review-e782e872429ef56b`, authority burned); a CRITICAL finding (R4-001) was found and fixed. Pending push/PR (owner decision).

## Objective

Slice 3 of the Asistente Lumat workspace: give knowledge-base documents a **project scope**.
A document is `global` (visible to every project — e.g. Lumat's own info) or bound to exactly
one **project** (exclusive to it). Effective retrieval for a project-aware caller =
`global ∪ project:<id>`, with strict isolation between projects. The existing `audience` axis
(`customer`/`internal`) stays orthogonal and intact. Legacy documents stay `global`.

## Problem

`KbDocument` (`app/models.py:465`) has no project binding, so every project's assistant sees
the same corpus. `kb.retrieve` (`app/services/kb.py:346`) filters only on `active`,
`active_version`, `distance`, and `visibility == audience` — there is no project filter and no
way to scope a document. The assistant reads the full corpus (`audience=None`), which is
correct for the internal panel but cannot isolate per project.

**Addressed by this slice** — the assistant now reads `global ∪ its project` (fail-closed to
`global` when no project resolves); the admin search probe stays full-corpus.

## Naming — do NOT reuse the retired `scope`

A previous axis named `kb_scope` / `retrieve(scope=...)` filtered **chunks** by
`source_meta.category`, never engaged in production, and was **retired** with a guard test
`test_kb_retrieve_has_no_scope_parameter` (`odd/tasks/retire-kb-scope-axis.md`). That guard
asserts `kb.retrieve` has no `scope` parameter. The new concept is **document-level project
binding**, semantically different. Therefore the new parameter/column is named **`project_id`**
(never `scope`), and the guard test stays green.

## Design source

`.rapsodia-code/sessions/ready-for-odd/2026-10-05-asistente-lumat-workspace-multiagente/{session.md,report.md}`
and Engram `cortex-session/2026-10-05-asistente-lumat-workspace-multiagente/decision/*`.
Key decision: **D13** (KB scope `global`/`project`, exclusive per project, `audience`
orthogonal, legacy → `global`).

## Scope

**In**

- `KbDocument.project_id` nullable FK (`NULL` = global) + migration `041`.
- `ingest_document(..., project_id=None)`.
- `retrieve(..., project_id=None, global_only=False)`: `global_only` → only global;
  `project_id=X` → `global ∪ X`; both default → all (unchanged, backward compatible).
- A `set_project` lifecycle method (parallel to `set_visibility`) for reclassification.
- **WhatsApp bot reads only global**: `app/chat/nodes/respond.py` and
  `app/chat/subgraphs/research_triage.py` pass `global_only=True` (audience stays `customer`).
- **Assistant reads `global ∪ current project`**: the `kb.retrieve` tool handler and the
  assistant pre-answer path resolve the thread's project and pass `project_id`.
- Admin upload accepts an optional `project_id`; serializers expose `project_id`; legacy
  uploads stay global. The admin search probe stays full-corpus (management view).
- Unit + integration tests.

**Out (later slices — do not build here)**

- The KB scope **UI** (project picker / badge) — Slice 6.
- Moving a project's KB documents when `project.merge`/`project.archive` runs — follow-up.
- Any change to `audience`, chunking, embedding, or versioning.
- Semantic retrieval changes; the retired chunk/topic `scope` axis is not restored.

## Model

| `project_id` | meaning | retrieval |
|---|---|---|
| `NULL` | global (visible to every project) | included by `global_only` and by any `project_id=X` query |
| `X` | bound to project X | included only when the caller resolves project X |

- `audience` (`customer`/`internal`) remains an independent filter, unchanged.
- Legacy documents have `project_id = NULL` → global automatically (no backfill).
- A document belongs to at most one project (no link table): a nullable FK is the minimum
  correct model.

## Assumptions

1. **A1 — global KB is company-wide.** KB documents have no owner today; `global` means
   visible to every project regardless of owner. Project-scoped documents are reached only
   through their project (which is owner-scoped).
2. **A2 — `project_id` is resolved from the thread's project.** The assistant already resolves
   the project per turn (`resolve_effective_config`); the KB call reuses that resolution.
3. **A3 — the admin search probe stays full-corpus.** It is a management probe, not a
   user-facing retrieval path.
4. **A4 — `ON DELETE CASCADE`.** A hard-deleted project takes its KB documents with it.
   Archiving/merging does not move KB documents (follow-up).
5. **A5 — no backfill.** Legacy rows are global by `NULL`; no data migration needed.

## Constraints

- **Strict TDD ON** (`openspec/config.yaml`): observe RED before GREEN.
  Runner: `uv run --no-sync pytest tests/`; test DB `eval "$(bash infra/test-db.sh env)"`;
  do **not** source `infra/.env`.
- **Migration `041`**: `040` is taken by Slice 1. The parallel `odd/clientes-panel` feature is
  still at `039`; renumber after merging `origin/main` if it lands `040`/`041` first.
- Never name the retrieve parameter `scope` (retired axis + guard test).
- Atomic commits, one concern each, ≤5 files; conventional commits; no `Co-Authored-By`.
- Preserve the audience axis and all existing KB behavior when no project is involved.

## Tasks

- [x] **T1 (RED)** Schema. `KbDocument.project_id` nullable FK to `projects.id`
      (`ON DELETE CASCADE`) + migration `041_kb_project_scope.sql` + index. Tests: default
      `NULL`; existing/legacy rows are global; a document can bind to a project.
- [x] **T2 (RED)** Service. `ingest_document(..., project_id=None)` and
      `retrieve(..., project_id=None, global_only=False)` with the filter rules; a
      `set_project` method. Tests: `global_only` returns only global; `project_id=X` returns
      `global ∪ X`; **project A never returns project B**; defaults unchanged (all); audience
      still applies.
- [x] **T3 (RED)** WhatsApp bot global-only. `respond.py` + `research_triage.py` pass
      `global_only=True`. Tests: a project-scoped doc is never returned to the WhatsApp path.
- [x] **T4 (RED)** Assistant project scope. `kb.retrieve` tool handler + pre-answer pass the
      resolved `project_id`. Tests: the assistant sees global ∪ its project, not another's.
- [x] **T5 (GREEN)** Admin surface. Upload accepts optional `project_id` (validated against
      the caller's projects); serializers expose it. Tests: upload with/without scope; invalid
      project rejected.
- [x] **T6** Verify: full suite green; spot check; RDD assessment.

## Acceptance criteria

- **AC1** `KbDocument.project_id` exists; `NULL` = global; legacy rows stay global without a
  backfill.
- **AC2** `retrieve(global_only=True)` returns only global; `retrieve(project_id=X)` returns
  `global ∪ X` and never another project's; both default → unchanged (all).
- **AC3** The WhatsApp bot reads only global (`respond` + `research_triage`).
- **AC4** The assistant (`kb.retrieve` tool + pre-answer) reads `global ∪ current project`.
- **AC5** Strict isolation: project A never sees project B's documents.
- **AC6** Admin upload can bind a document to a project; a legacy/global upload stays global.
- **AC7** The `audience` axis is untouched; full suite passes.

## Checks

- Graph nodes consulted (report `graphify-out/`, worktree build): `KbDocument`
  (`models.py:465`), `KbChunk` (`models.py:495`), `Project` (`models.py:178`),
  `retrieve`/`ingest_document` (`services/kb.py`), `routes/kb.py`, `serializers.py`,
  `agent/personas/retrieval.md`, `kb.retrieve` (`tools/registry.py:332`), `respond.py:135`,
  `research_triage.py:77`, `nodes.py:958`, `tests/integration/test_kb.py`,
  `tests/functional/test_api_kb_settings.py`.
- Strict TDD ON, runner `uv run --no-sync pytest tests/`.
- Test DB: `eval "$(bash infra/test-db.sh env)"`.

## Delivery

- Actual: **19 paths / 593 changed lines**, high risk → a 4-lens review was required (and, after
  the R4-001 fix, a second 4-lens review, approved). One cohesive feature → delivery strategy
  (`ask-on-risk`) to be applied by the owner: single PR with `size:exception`, or chained.

## Progress

- **2026-10-06** — Worktree `../lumat-agent-odd-asistente-kb-scope` created from `main`
  `85d51825` (branch `odd/asistente-kb-scope`). Graph Check run; KB seams mapped via read-only
  exploration. Design documented here. `94e62f76` commits this plan.
- **2026-10-06** — **T1 complete.** `e278dcab` adds `KbDocument.project_id` (nullable FK to
  `projects.id`, `ON DELETE CASCADE`) + `db/migrations/041_kb_project_scope.sql` + index.
  Legacy rows stay global (`NULL`), no backfill. **Verify:** `test_migrations` + `test_db` → 44 tests.
- **2026-10-06** — **T2 complete.** `df0a12b6` adds `ingest_document(project_id=...)`,
  `retrieve(project_id=..., global_only=...)` and `set_project`. Tests: global-only; `project_id=X`
  → `global ∪ X` (never another project's); defaults unchanged; audience orthogonal.
  **Verify:** `test_kb.py` → 25 tests.
- **2026-10-06** — **T3 complete.** `48e6f4c7` makes the WhatsApp/customer paths read only global
  (`respond.py` + `research_triage.py` pass `global_only=True`; audience unchanged). **Verify:** 44 tests.
- **2026-10-06** — **T4 complete.** `49822bd8` resolves `EffectiveConfig.project_id` and scopes the
  assistant (`kb.retrieve` tool handler + pre-answer) to `global ∪ its project`. **Verify:** 12 tests.
- **2026-10-06** — **T5 complete.** `561fd70e` lets the admin upload bind a document to one of the
  owner's projects (validated; foreign/unknown → 400) and exposes `project_id` in the serializer.
- **2026-10-06** — **T6 + full-suite verify.** `uv run --no-sync pytest tests/` → exit 0.
- **2026-10-06** — **RDD review #1 escalated on R4-001 (CRITICAL).** The `review-resilience` lens
  found that an unresolved project (`project_id is None`) omitted the filter, exposing every
  project's KB. Escalated with `unknown_causality`; the maintainer confirmed reachability
  (`default`/stale project threads) and authorized the fix.
- **2026-10-06** — **R4-001 fixed (fail-closed).** `f0b5e575` makes both assistant call sites read
  `global` only when no project resolves; `0e37a206` aligns the grounding-gate test. Full suite green.
- **2026-10-06** — **RDD re-review approved.** `review-e782e872429ef56b` (4 lenses): risk/resilience/
  reliability **0 findings**; readability 2 **advisory** findings (R2-001/R2-002) about this doc's
  stale status, resolved by this close. Acknowledgement `authority: burned`.
</content>
