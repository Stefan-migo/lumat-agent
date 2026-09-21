# ODD: kb-audience-label

## Objective

Make the KB audience label tell the truth. The axis is already correct; the copy is not. Today the
panel shows `customer` documents as **"Cliente"**, which reads as "only the client sees this" — the
opposite of what the value means. After this change every surface says **"Cliente y Lumat"**, so the
two values finally declare *who reads the document*, in a symmetric pair.

## Problem

`odd/tasks/kb-audience.md` **D3** defines the audience as an explicit *consumer gate*: "A new
`audience` parameter, never a reuse of `scope`. The customer-facing consumers pass `customer`; the
internal consumers pass `None` explicitly." Under that contract:

- `customer` — **the customer channel may ground on it, and Lumat may still read it.** Lumat reads the
  whole corpus: the panel's retrieval probe passes `audience=None` (the unit's D6), and the Lumat
  assistant passes `audience=None` too. So a `customer` document is *both*.
- `internal` — only Lumat. Never returned to the customer channel.

Verified against the source. The carrier that can drift is the UI copy:

- `web/src/components/pages/KbList.tsx:62` — the reclassification `Select` option
  `{ value: "customer", label: "Cliente" }`.
- `web/src/components/pages/KbList.tsx:76` — the `Badge` in the audience column:
  `doc.visibility === "customer" ? "Cliente" : "Interno (solo Lumat)"`.
- `web/src/components/pages/KbList.tsx:157` — the upload `Select`, the same options array as `:62`,
  duplicated literally.

**The asymmetry is the defect.** `internal`'s label declares who reads it — "Interno (solo Lumat)".
`customer`'s label declares nothing about readership and, read literally, implies exclusivity: that
the document is *for* the client and *not* for Lumat. An admin choosing between the two is being
asked to compare a proposition ("only Lumat") against a bare noun ("Cliente").

**Not a schema problem.** The JSONB/column question was settled by the unit's D1; `customer` already
IS both, and a third value `both` would create an unresolvable ambiguity (nothing would distinguish
`customer` from `both`). The values, the DB type, the migration, the API, and the retrieval gate are
all correct and stay byte-identical. This is copy.

**No test pinned the copy at three of the four surfaces.** `KbList.stories.test.tsx:47` asserts the
badge text `"Cliente"` — the one string it got wrong. The two `Select`s are exercised only through
their *values* (`:146`, `:396`), so their labels could drift to anything unnoticed, and the restore
confirmation is asserted for the `internal` half of its sentence only (`:387`), never for the
`Cliente` name it tells the admin to pick. The duplication at `:62` and `:157` is the drift
mechanism, and nothing detected it.

**A fourth surface the inventory missed, found while fixing it.** The restore confirmation
(`KbList.tsx:161` at the time) reads *"…hasta que lo marques como **Cliente** nuevamente."* It names
the audience the admin must re-select **by its label**, so once the option label changes it points at
an option that no longer exists. It is the same defect class in the same file and belongs to this
unit; it is recorded here rather than left behind.

## Scope

**In:** the audience label on the four `KbList.tsx` surfaces (badge, upload selector,
reclassification selector, and the restore confirmation that names the option); one shared label
source so they cannot drift; the story-test assertions that pin the copy on each surface.

**Out:** the enum values `customer | internal`; `KbVisibility`; the `kb_visibility` DB type and
migration `027`; `retrieve`'s audience filter and its fail-safe default; `ingest_document`,
`set_visibility`, the restore-never-widens rule; the panel API and serializers; any canonical spec
(`openspec/specs/knowledge-base/spec.md` KB-5 constrains values and readership, never copy — no delta
is required); the visual design of `KbList`; the topic `scope` axis (AO-7); `min_sim`; chunking; the
embedding model; retrieval ranking.

## Spec constraints (binding — do not violate)

- `openspec/specs/knowledge-base/spec.md:60-90` — **KB-5**: the audience values stay
  `customer | internal`; `retrieve` still defaults to `customer`; restoring still never widens. None
  of these is touched.
- `odd/tasks/kb-audience.md` **D8** — in UI copy the axis is called **"Audiencia"**, never
  "Visibilidad". The field labels stay `Audiencia`.
- `web/DESIGN_SYSTEM.md:424` — UI copy in **neutral Chilean Spanish**; no Argentine voseo.
- `openspec/specs/panel-design-system/spec.md:742,749` — **DS-GRAMMAR-1/2**: the `DataTable` stays and
  no hard-coded colour or new dependency is introduced. This change adds no style.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-kb-audience-label`
- Branch: `odd/kb-audience-label`
- Base: `0e053d44` — verified with `git merge-base HEAD origin/main` **after** creation, and equal to
  both local and `origin/main` at that moment.
- Files:
  - `odd/tasks/kb-audience-label.md`
  - `web/src/components/pages/KbList.tsx`
  - `web/src/stories/pages/KbList.stories.test.tsx`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`). RED observed before the
  source change; no invented RED.
- Frontend only: `cd web && npm run test` and `cd web && npm run build`. No backend suite is needed
  (no Python file changes) — declared rather than silently skipped.
- Artifacts in English; UI copy in neutral Chilean Spanish.
- No commit, push, or PR unless the orchestrator authorizes it.

## Decisions

- **D1 — The fix is copy, and the copy is "Cliente y Lumat".** Chosen by the human between the two
  coherent framings: the visibility framing (who reads it — fits a field named "Audiencia") over the
  reach framing ("se usa con clientes": consistent with the existing hint, but reads wrong as
  "Audiencia: Se usa con clientes"). `internal` keeps **"Interno (solo Lumat)"** unchanged, because it
  was already truthful. The pair now answers the same question the same way.
- **D2 — One label source for every surface.** The options array at `:62` and `:157` was a literal
  duplicated twice, and the badge at `:76` encoded the customer string a third time. A single
  `AUDIENCE_LABEL` record plus an `AUDIENCE_OPTIONS` array derived from it removes the drift mechanism
  that let the two labels diverge in the first place. This is de-duplication of an existing literal,
  not a new abstraction: no new module, no new export, no new file. The restore confirmation keeps its
  own prose (it is a sentence, not an option label) but now names the same string.
- **D3 — No third value, no schema delta.** Rejected explicitly. `customer` already means "client and
  Lumat"; a `both` value would be indistinguishable from it. Consequently no spec delta is written:
  KB-5 governs values and readership, not copy.
- **D4 — The guard is an assertion per surface, not per string.** The new test asserts that the label
  is present on the badge **and** in both selectors, so a future edit that changes one surface only
  fails loudly. This is the assertion that would have caught the original defect. The restore
  confirmation is pinned by an assertion added to the existing restore test instead, so the fourth
  surface is guarded too.

## Tasks

- [x] **T1** — Pinned the approved copy in `KbList.stories.test.tsx`: the badge assertion at `:47` was
      updated and a new test reads the `Cliente y Lumat` option out of both the upload selector and the
      reclassification selector. **RED observed**: `npx vitest run
      src/stories/pages/KbList.stories.test.tsx` → **2 failed | 28 passed**, failing on
      `getAllByText("Cliente y Lumat")` and on the upload selector's option, against the unchanged
      component.
- [x] **T2** — `KbList.tsx`: added `AUDIENCE_LABEL` and `AUDIENCE_OPTIONS`, and used them in the badge,
      both `Select`s, and the restore confirmation. **GREEN observed**: same file → **30 passed**.
- [x] **T2b** — The restore-confirmation surface, done as its own RED→GREEN. **RED observed**:
      **1 failed | 29 passed**, the failure printing the stale text
      `…hasta que lo marques como Cliente nuevamente.` **GREEN observed** after the copy change:
      **30 passed**.
- [x] **T3** — Verification, all observed:
  - `cd web && npm run test` → **79 files / 610 tests passed** (exit `0`).
  - Baseline for that number, measured on `main` in the same session: **79 files / 609 tests passed**.
    The delta is exactly the one test this unit added; no pre-existing test was removed or weakened.
  - `cd web && npm run build` → **✓ built in 3.14s**, clean.
  - `npx tsc --noEmit` → **clean**.
  - `git diff --check` → no whitespace errors.
  - The backend suite was **not** run: no Python file is touched by this unit, so there is nothing for
    it to exercise. Declared rather than silently skipped.

## Acceptance criteria

1. Every surface that shows a document's audience reads **"Cliente y Lumat"** for `customer` and keeps
   **"Interno (solo Lumat)"** for `internal` — the audience column badge, the upload selector, and the
   reclassification selector — and the restore confirmation names the same label.
2. The customer label exists once in the source and the surfaces that render it consume it; no surface
   holds its own literal.
3. No enum value, DB type, migration, API field, serializer, retrieval filter, or spec file changes.
4. The frontend suite is green and `npm run build` is clean.
5. Only the three authorized files change.

## Checks

- `cd web && npm run test`
- `cd web && npm run build`
- `git status --short` / `git diff --check`

## Size

Source and tests: **2 files, 36 insertions, 6 deletions** — `KbList.tsx` 18/5, the story test 18/1.
Plus this record (199 lines, untracked at the time of writing). The test surface and the production
change are an even 18 lines each: the production insertions are the 13-line label source plus the 5
rewritten call sites, and the test insertions are the new test plus the two assertions added to
existing tests.

Comfortably under the 400-line review heuristic, with no split needed.

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create kb-audience-label`); base verified as `0e053d44`, equal
      to both local and `origin/main` at creation time. `web/node_modules` installed in the worktree (a
      fresh worktree has none). Backend `.venv` not needed: this unit touches no Python file.
- [x] Graph Check (Step 1): `graphify query "KbList audience visibility label"` run over the panel
      area. Nodes consulted: `KbList()` (`web/src/components/pages/KbList.tsx:132`), `KbList.tsx`
      (file node), `KbList.stories.test.tsx` (file node), `KB-5 Document Audience`
      (`openspec/specs/knowledge-base/spec.md`), `ODD record: kb-audience` (`odd/tasks/kb-audience.md`
      — the record that defines the axis), `AO-7 KB/Memory Scoping via Filter`, plus the
      `uploadKbDocument` / `setKbVisibility` / `refreshKbDocuments` API edges out of `web/src/api.ts`.
      A pre-existing untracked file, `.opencode/tools/package-lock.json`, is present in the worktree
      (a known `rapso worktree create` artefact, already documented in `kb-audience.md`).
- [x] T1, T2, T2b, T3 complete with the RED/GREEN evidence recorded above.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file.

## Next step

Implementation, verification and delivery are complete: commits `11b3f531` (the fix and its tests) and
`e1033846` (this record) on `odd/kb-audience-label`, pushed, with **PR #285** open against `main` under
the `type:bug` label and CI green. Merge remains the human's decision, under ordinary repository policy.

Deliberately NOT folded into this unit:

1. **The canonical spec.** KB-5 governs the audience *values* and *readership*, and neither changed.
   No delta was written: pinning UI copy in a canonical spec would freeze a label that is free to be
   reworded.
2. **The `min_sim` calibration, F7 (titles are not embedded), P8, P9, P10.** Separate units from the
   `handoff/kb-p6-p10` list — untouched here.
3. **The upload hint copy** ("Un documento interno nunca se usa para responder a clientes"). Left as
   is: it uses "interno" as a plain adjective rather than naming the option, so it stays truthful
   under the new label.
