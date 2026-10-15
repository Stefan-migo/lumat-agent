# ODD: kb-panel-scope

**Objective**: The panel's global "Base de conocimiento" section lists ONLY global KB documents
(`project_id IS NULL`). Project-scoped documents stay on their project page.
**Branch**: `odd/kb-panel-scope` | **Base**: `main` @ `9eaaceba` | **Runner**: `uv run pytest tests/`
**Risk**: item 3 (changes the default response of an existing panel endpoint).

## Problem

`kb_list` (`GET /panel/api/kb`, `app/panel/api/routes/kb.py:69-77`) runs
`select(KbDocument).order_by(KbDocument.id.desc())` with **no scope filter**, so documents with
`project_id != null` appear in the global KB list, labelled only by audience (`KbList.tsx` has no
project column). The admin retrieval probe (`GET /panel/api/kb/search`, `:81-94`) calls
`kb_service.retrieve(..., audience=None)` without `global_only=True`; because `retrieve` only applies
a scope filter when `global_only=True` or `project_id is not None` (`app/services/kb.py:424-429`), the
probe returns chunks from **every** project.

The assistant's own retrieval is already correctly scoped (`app/services/kb.py` `retrieve`); the leak
is a panel-surface problem only.

## Specs

**S1** — `GET /panel/api/kb` **without** `project_id` returns ONLY documents with `project_id IS NULL`.
**S2** — `GET /panel/api/kb?project_id=<id>` returns ONLY that project's documents.
**S3** — `GET /panel/api/kb/search` (admin probe) is scoped to global documents; `audience=None`
(the whole-corpus audience probe) is unchanged.
**S4** — The global "Base de conocimiento" section (`KbList`) does not list project documents.
**S5** — The project page (`ProjectResources`) keeps showing its project's KB documents.
**S6** — The assistant retrieval pipeline does not change.
**S7** — `KbVisibility` and the data model do not change; zero migrations.

Owner's requirement (recovered from Engram obs `6643`): *"project KB files are personal to the
project/user and must not surface in the global Base de conocimiento section."*

## Scope

**In**: `app/panel/api/routes/kb.py`, `web/src/api.ts`,
`web/src/components/pages/ProjectResources.tsx`, `tests/functional/test_api_kb_settings.py`,
`web/src/components/pages/ProjectResources.test.tsx`, `openspec/specs/knowledge-base/spec.md`.

**Out**: `app/services/kb.py` `retrieve` (already correct), `app/models.py` / `KbVisibility`,
migrations, `KbList.tsx` (needs no change once the API is scoped).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-kb-panel-scope`
- Branch: `odd/kb-panel-scope`
- Base: `9eaaceba`

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml` (`testing.strict_tdd: true`). Observe RED before
  each source change; never invent RED evidence.
- Integration/functional tests need `eval "$(bash infra/test-db.sh env)"` (this worktree's DB is on
  port **5897**).
- `pyproject` already adds `-q` to pytest; do NOT add a second `-q`.
- Conventional commits, no `Co-Authored-By`. One concern per commit, ≤5 files per commit.

## Design decisions

**D1 — Parameterize the list endpoint; do not hard-filter it.** `refreshKbDocuments`
(`web/src/api.ts:124`) is `GET /panel/api/kb` with no params, and it has **two** consumers:
`KbList.tsx` (the global section) and `ProjectResources.tsx:84`, which filters the same payload
client-side at `:478` (`doc.project_id === projectId`). A hard `project_id IS NULL` filter with no
parameter would silently empty the project page. The optional parameter keeps both surfaces working
on one endpoint.

**D2 — `?project_id=X` returns project-only, not global ∪ project.** The only consumer discards
non-matching rows at `ProjectResources.tsx:478`; returning globals would be rows the client throws
away. The parameter answers "the scope you asked for", mirroring the no-param case.

**D3 — No new `KbVisibility` value.** `visibility` (audience: `customer`/`internal`) and `project_id`
(scope) are orthogonal axes. Collapsing them produces an incoherent matrix (can a project document be
`customer`? `internal`?). The fix is scope-based, which is why the leak is fixed in the listing and
not in the audience enum.

## Tasks

### WU1 — scope the panel document list

- [x] **T1** — RED: `tests/functional/test_api_kb_settings.py` — a seeded document with `project_id`
      must NOT appear in `GET /panel/api/kb`; a global document must. Observe RED.
- [x] **T2** — GREEN: `app/panel/api/routes/kb.py` — `kb_list` takes an optional
      `project_id: int | None = Query(None, ge=1)` and filters (`IS NULL` when absent, `== id` when present).
- [x] **T3** — GREEN: `web/src/api.ts` — `refreshKbDocuments(projectId?: number)` appends the param;
      `web/src/components/pages/ProjectResources.tsx` passes its `projectId`.
- [x] **T4** — GREEN: `web/src/components/pages/ProjectResources.test.tsx` — asserts the page requests
      the project-scoped list.
- [x] **WU1 commit** — `fix(kb): scope the panel document list to global or one project`

### WU2 — scope the admin retrieval probe

- [x] **T5** — RED: `tests/functional/test_api_kb_settings.py` — a project-scoped document's chunk
      must NOT be returned by `GET /panel/api/kb/search`. Observe RED.
- [x] **T6** — GREEN: `app/panel/api/routes/kb.py` — pass `global_only=True` to the probe.
- [x] **WU2 commit** — `fix(kb): scope the admin retrieval probe to global documents`

### WU3 — spec delta

- [x] **T7** — `openspec/specs/knowledge-base/spec.md` — add the scope-boundary requirement / scenario
      that the current spec does not state (KB-3 covers the manager, KB-5 covers audience; neither
      covers listing scope).
- [x] **WU3 commit** — `docs(specs): state the KB listing scope boundary`

## Verification

- `eval "$(bash infra/test-db.sh env)"; uv run pytest tests/functional/test_api_kb_settings.py`
- `eval "$(bash infra/test-db.sh env)"; uv run pytest tests/` (full suite)
- `cd web && npx vitest run --maxWorkers=2`
- `cd web && npm run build` (tsc -b + vite; the type check is not optional)

## Acceptance criteria

1. `GET /panel/api/kb` (no param) returns no document with `project_id != null`.
2. `GET /panel/api/kb?project_id=X` returns X's documents.
3. `GET /panel/api/kb/search` returns no chunk belonging to a project-scoped document.
4. `ProjectResources` still shows its project's documents.
5. `KbVisibility`, `models.py`, and migrations are untouched.
6. Full backend suite, frontend suite, and `npm run build` pass.

## Log

**L1** — Owner, 2026-10-15 (verbatim): *"hey chat continuamos con Memoria guardada (session summary obs
6647, handoff obs 6649) y el handoff escrito en odd/handoffs/kb-panel-scope.md. puedes darme un
overview antes de continuarl. necesitamos hacer un rapso session para conversar el leak de la kb?"*
then *"si vamos con el ODD kb-panel-scope"* — explicit per-feature consent to start the ODD.

**L2** — Origin of the feature (previous session; recovered from Engram obs `6643`, handoff and memory
wording, not guaranteed verbatim): project KB files are personal to the project/user and must not
surface in the global Base de conocimiento section. Deferred by the owner from T9 of
`asistente-lumat-config-layer` (closed, T0–T9 merged).

**L3** — 2026-10-15, resumed session. Graph Check: `graphify query "kb panel list project scope leak
document visibility"` (889 nodes, truncated), `graphify query "... project_id scoped global list filter
KbVisibility audience"` and `graphify path "kb_list" "retrieve"` → **no directed path** between
`kb_list` and `retrieve`, confirming the panel listing and the retrieval pipeline are independent
mechanisms. Nodes consulted: `KbVisibility` (`app/models.py:126`), `retrieve()` (`app/services/kb.py:391`,
community `test_kb.py`), `ingest_document()` (`app/services/kb.py:184`), `routes/kb.py` (community
`routes/kb.py`), `services/kb.py`.

**L4** — 2026-10-15. **Deviation from the handoff (T1).** The handoff proposed filtering `kb_list` to
`project_id IS NULL` unconditionally. Verified evidence shows that would break the project page:
`ProjectResources.tsx:84` calls `refreshKbDocuments()` (`GET /panel/api/kb`, `web/src/api.ts:124`) and
filters the same payload client-side at `:478` (`doc.project_id === projectId`). A hard filter with no
parameter would leave that page empty. Corrected to an optional `project_id` parameter (D1/D2), which
preserves existing behavior the owner never asked to remove while still closing the leak.

**L5** — 2026-10-15. Rapso-session housekeeping: the `asistente-lumat-config-layer` session was still
sitting in `.rapsodia-code/sessions/ready-for-odd/` after its ODD task doc had been created and merged.
Consumed it into `archived/` per the mandatory inbox rule. `2026-09-24-harness-audit-y-cobertura-panel`
stays in `ready-for-odd/` (its ODD task doc does not exist yet).

**Next step**: T1 (RED).

## Execution evidence

- **WU1 RED (backend)** — `eval "$(bash infra/test-db.sh env)"; uv run --no-sync pytest
  tests/functional/test_api_kb_settings.py -k "kb_list"` — **2 failed, 1 passed**; the project-scoped
  document appeared in the global list and `?project_id=` returned every document.
- **WU1 GREEN (backend)** — same command — **3 passed**.
- **WU1 RED (frontend)** — reverted the `ProjectResources.tsx` line to the un-scoped call and ran
  `npx vitest run src/components/pages/ProjectResources.test.tsx` — **1 failed, 12 passed**; the page
  requested `/panel/api/kb` instead of `/panel/api/kb?project_id=7`. Restored the fix.
- **WU1 GREEN (frontend)** — `npx vitest run src/components/pages/ProjectResources.test.tsx
  src/components/pages/KbList.test.tsx` — **19 passed**.
- **Full backend suite** — `uv run --no-sync pytest tests/` — **2266 passed, 2 warnings** in 309.10s.
- **Full frontend suite** — `npx vitest run --maxWorkers=2` — **1228 passed** (108 files).
- **Build / type check** — `npm run build` — built in 4.93s (tsc -b + vite), no type errors.
- **WU1 commit** — `04dd2e54 fix(kb): scope the panel document list to global or one project`.
- **WU2 RED (backend)** — `uv run --no-sync pytest tests/functional/test_api_kb_settings.py -k
  "probe_excludes"` — **1 failed**; the probe returned `[1, 2]` (the project document leaked).
- **WU2 GREEN (backend)** — `uv run --no-sync pytest tests/functional/test_api_kb_settings.py` —
  **67 passed**.
- **WU2 commit** — `9fb983e1 fix(kb): scope the admin retrieval probe to global documents`.
- **WU3** — spec delta, no runnable RED (documentation). `openspec` CLI is not installed in this
  environment, so the markdown was reviewed by hand against the KB-1..KB-5 shape.
- **WU3 commit** — `06a1c2d3 docs(specs): state the KB document scope boundary`.
- **Full backend suite (final state)** — `uv run --no-sync pytest tests/` — **2267 passed, 2 warnings**
  in 281.34s.

**Status**: all work units complete; awaiting review and delivery.

**L6** — 2026-10-15. `origin/main` advanced to `3f329cb9` (PR #627, `odd/panel-tecnico-wu7`) before
push. That PR also touches `web/src/api.ts` — the file this branch edits — so the merge is a semantic
merge, not a textual one. Merged `origin/main` into the branch (`cfd04034`, auto-merged, no
conflicts) and re-ran the full integration over the merged tree: backend **2271 passed**, frontend
**1234 passed** (108 files), `npm run build` OK. `refreshKbDocuments`, `ProjectResources.tsx:84` and
`kb_list` all verified intact after the merge.

## Follow-ups

- `ProjectResources.tsx:478` still filters the payload client-side (`doc.project_id === projectId`).
  It is now redundant but harmless; removing it is a separate cleanup, not this fix.
- `KbDocument` has no user axis — scope is per project only. If a per-user scope is ever needed, it
  is a new axis and a new requirement, not a widening of `project_id`.
