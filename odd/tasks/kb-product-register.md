# ODD: kb-product-register

Repository-relative locator: `odd/tasks/kb-product-register.md`
Worktree: `/home/stefan/repos/lumat-agent-odd-kb-product-register` | Branch `odd/kb-product-register` | Base `9b83e27f`
Session seed: `.rapsodia-code/sessions/ready-for-odd/2026-09-23-kb-product-register/report.md`

## Objective

Raise the Base de Conocimientos (KB) surface to the panel's single product
register by making its **contract honest** and recomposing it as a
**document-first admin workspace**. It is the second dense surface to apply the
agent-app appearance under the amended `DS-GRAMMAR-1`.

This unit is NOT a repeat of `clientes-product-register`. KB already uses every
shared primitive and has zero raw HTML controls. Its debt is consistency, contract
and composition.

## Problem

Verified against the code and the database at base `9b83e27f`. Every claim is
evidence, not impression.

### Defect 1 — the document-status vocabulary is half fiction

`KbDocument` has no status column: only `active: bool` (`app/models.py:419-429`,
`app/models.py:421`). Yet `web/DESIGN_SYSTEM.md:397` documents four approved KB
labels (`Activo | Deshabilitado | Procesando | Error`) and
`web/src/components/shared/toneMaps.ts:31` maps all four, while `docStatus()`
(`web/src/components/pages/KbList.tsx:33`) can only return two.

Confirmed why no processing state can exist: ingestion is synchronous —
`POST /kb` calls `ingest_document` inline (`app/panel/api/routes/kb.py:143`) — and
retrieval filters `active AND version == active_version`
(`app/services/kb.py:354-355`).

This is the same class as the Clientes `Bloqueado` label: documented with no
domain state behind it.

### Defect 2 — a binding MUST is violated in production, behind a green test

`DESIGN_SYSTEM.md:332` requires disabling a KB document to confirm and state the
effect on agent answers; `DS-UI-STATES` (`openspec/specs/panel-design-system/spec.md:496-504`)
requires the `disable-confirmation` state.

- `web/src/components/domain/AppShell.tsx:119` mounts `<KbList />` with no props,
  so `KbListProps.state` is always `undefined` in production.
- `onDisable` (`KbList.tsx:171`) calls `mutate("disable", …)` immediately.
- The confirmation (`KbList.tsx:175`) is gated on
  `controlledState === "disable-confirmation"` and is therefore **unreachable in
  the real app**.
- `web/src/stories/pages/KbList.stories.tsx:32` and
  `web/src/stories/pages/KbList.stories.test.tsx:140-141` assert exactly that
  unreachable state and pass.

The old detail text also picked the first active document
(`docs.find((doc) => doc.active)`), not the clicked one — unfixable while the
state lives outside the page. Restore does confirm, via local state
(`KbList.tsx:154,174`). The asymmetry is in the code, not the policy.

### Defect 3 — the mock/test contract is stale

`visibility` is emitted by the API (`app/panel/api/serializers.py:412`) and
required by TS (`web/src/types.ts:328`), but the mock test omits it from
`DOC_KEYS` and the fixture makes `visibility` non-enumerable to keep the stale
assertion green.

### Composition — the page is not the workspace the gate describes

`DESIGN_SYSTEM.md:327`: "This is an admin workspace, not a file gallery." Today KB
is three stacked blocks: `Card(Agregar documento)` above the documents,
`DataTable` bare in the middle, `Card(Probar recuperación)` below — with the
upload above the collection and every document operation crammed into a row
`<details>`.

Measured debt: **23 unique `.kb*` selectors** (`primitives.css:1892-1959`: 15
layout, 7 visual chrome, 0 state, 1 one-off hack) and the documents table bypasses
the shared `.data-region` (`primitives.css:295-305`) that already has two named
consumers (`ClientesList.tsx:101`, `ClientFicha.tsx:230`).

## Decisions carried from the session

- **D1 — Two status planes.** Document status is persisted and has two values
  (`Activo`, `Deshabilitado`). Operation lifecycle is transient and page-owned
  (`Procesando`, `Error`). The design system KB row is amended to match.
- **D2 — The page owns its workflow states.** `KbListProps.state` stops being the
  model; stories drive states through data/fetch. Disable confirms with page-owned
  local state, mirroring restore, naming the clicked document.
- **D3 — Adopt `.data-region`** for the documents table and shed `.kb*` layout
  classes that duplicate shared structure.
- **D4 — Style the disclosure in the shared tokenized stylesheet.** Disclosure is
  appearance, not control-room physiology, so the two-axis split does not apply.
  Four named consumers exist (`KbList.tsx:58`, `Settings.tsx:164`,
  `ConversationThread.tsx:50`, `AgentChat.tsx:284`) — proven reuse, so it clears
  the "no premature abstraction" non-goal.
- **D5 — Recompose KB as a document-first workspace.** Documents become the
  primary region; upload is demoted to a secondary affordance; a document gains
  its own region (metadata, versions, audience, actions); the retrieval probe
  becomes a tool region. Reuse the proven `ClientFicha` two-region pattern.
- **D6 — The document's own region is a drill-down view (owner's call,
  2026-09-23).** `AppShell.tsx:114` already renders three drill-downs the same way
  (`clients` + `clientId` → `ClientFicha`; `conversations` + `conversationId` →
  `ConversationThread`; `automation-rules` + `automationRuleId` →
  `AutomationRuleDetailPage`), and the handoff §4.4 requires one back-control
  pattern for every detail view. So KB adds a fourth: `kb` + `kbDocId` →
  `KbDocumentDetail` (identity rail + operations main, with the back control).
  This authorizes `AppShell.tsx` and `panelRoutes.ts` and a new page component.
  Rejected: an inline region on the same page — smaller, but a pattern the panel
  does not have and with no back control, because it is not a view.

## Authorized scope

- `web/src/components/pages/KbList.tsx`
- **`web/src/components/pages/KbDocumentDetail.tsx` (new) and its test**
- **`web/src/components/domain/AppShell.tsx` and `web/src/components/domain/panelRoutes.ts`**
  (the KB drill-down route only)
- **`web/src/stories/pages/KbDocumentDetail.stories.tsx` (new) and its test**
- **`web/src/components/pages/ClientFicha.tsx` and `ClientFicha.test.tsx`** — only to
  promote the two-region grid to a neutral shared contract. The KB detail needs the
  same `.detail-region` grid; borrowing `.client-ficha*` would make the names lie and
  couple two unrelated pages, which is exactly what this repo refused to do when it
  created the neutral `.data-region` instead of borrowing a page class.
- the KB section of `web/src/components/primitives/primitives.css`
- `web/src/components/shared/toneMaps.ts`
- `web/src/stories/pages/KbList.stories.tsx` and its test
- `web/src/stories/pages/_shared/mockData/kb.ts` and its test
- `web/src/types.ts` (only if the plane split or the detail fetch requires it)
- `web/DESIGN_SYSTEM.md` (KB status row amendment only)

**No backend change. No new dependency. No new token without a repeated
consumer.** Preexisting token values are not touched (`DS-TKN-2` is additive).

## Non-goals

- Async ingestion or a persisted processing status (D1 rejected alternative).
- Promoting the disclosure editor, technical metadata block, upload workspace or
  search panel to substrate — none has a named second consumer.
- Touching `SearchInput`. The handoff claimed KB consumes it; verified FALSE
  (`KbList.tsx:130` uses `Input`; consumers are only `ConversationsList.tsx:71`
  and `ClientesList.tsx:96`).
- Adopting the shared disclosure in the other three consumers: they sit on the
  other grammar axis or carry their own local grammar. Recorded as the named
  second consumers that justify the substrate; their adoption is a follow-up.
- Card-on-card. Note `DataTable` already renders its own `.empty-state`, so
  wrapping an empty table in another surface nests.
- Dark mode, CSS framework, component library, new font, rebrand.

## Constraints

- Strict TDD is ON (`openspec/config.yaml`): **RED observed before every source
  change**, never invented.
- UI copy in neutral Chilean Spanish; artifacts and identifiers in English.
- No `Co-Authored-By` or AI attribution in commits. Conventional commits.
- One concern per commit, ≤5 files, work-unit commits on the branch.
- Graph Check before each task: `graphify query "<area>"`, record the nodes
  consulted in the task's progress note.
- Ponytail after each task: can the same authorized behavior be expressed with
  stdlib → native → already-installed dependency → one line? Authorized behavior
  is never removed; design/dependency/structure findings go to the human.
- Do not touch the other active worktree `odd/assistant-web-search`.

## Checks

```
cd web && npm run test          # Vitest — baseline 80 files / 665 tests, all green
cd web && npx tsc -b --noEmit
cd web && npm run build
cd web && npm run build-storybook
```

The final acceptance gate is **visual and human**, at 1366×768.

## Delivery plan

Chained PRs, `stacked-to-main`. One honest cut pass; never compress code, tests or
comments to fit a budget. If a slice does not fit ~400 review lines, report the
real number and recommend `size:exception`.

| Slice | PR | Content | Route |
|---|---|---|---|
| 0 | — | This task doc, committed before the first source change | inline |
| 1 | PR 1 | T1–T3: contract honesty (never design on an untrue contract) | delegated writer |
| 2 | PR 2 | T4: the disable MUST violation, standalone and small | delegated writer |
| 3 | PR 3 | T5–T7: the document surface (drill-down, per D6) | delegated writer |
| 4 | PR 4 | T8–T10: the corpus and completeness | delegated writer |

Slice 3 grows the unit's authorized scope (D6): it touches `AppShell.tsx`,
`panelRoutes.ts` and adds `KbDocumentDetail.tsx`. PR 2 is stacked on PR 1; PR 3 is
stacked on PR 2; PR 4 on PR 3. Retarget each to `main` as its parent merges.

## Tasks

### T1 — Restore mock/test fidelity (slice 1)

RED: the mock test must fail because `visibility` is missing/unhidden.
GREEN: add `visibility` to `DOC_KEYS`, make it enumerable in the fixture, assert
the field set matches the API contract.
Files: `web/src/_shared/mockData/kb.ts` + its test.
Graph nodes: `web/src/types.ts` (`Doc`), `to_doc_dict`.

### T2 — Two-plane status vocabulary (slice 1)

RED: a test asserting the document status is only ever `activo`/`deshabilitado`,
and that operation lifecycle labels are not reachable as document badges.
GREEN: split `KB_STATUS_LABELS` into document status and operation lifecycle; add
`kbStatusTone` mapping both planes to approved tones (this closes the handoff's
unused-`danger` item — the KB operation-error state is its legitimate consumer);
`KbList` uses the split.
Files: `web/src/components/shared/toneMaps.ts`, `web/src/components/pages/KbList.tsx`.

### T3 — Amend the design system KB status row (slice 1)

GREEN: `web/DESIGN_SYSTEM.md:397` KB row states the two planes explicitly:
document status `Activo | Deshabilitado` (persisted) and operation lifecycle
`Procesando | Error` (transient, page-level, paired with a next action).
Files: `web/DESIGN_SYSTEM.md`. Ships with T2 as its first consumer.

### T4 — The page owns its workflow states; disable confirms (slice 2)

RED: a test that mounts the REAL path (bare `<KbList />` with the data source
mocked, the way `AppShell.tsx:119` does), clicks `Deshabilitar`, and asserts the
confirmation appears, names the CLICKED document, and that NO disable mutation ran
yet. This test must fail on `main`.
GREEN: the page owns the confirmation state; `KbListProps.state` no longer carries
`disable-confirmation`; stories drive workflow states through data/fetch, not
through a prop production ignores.
Files: `web/src/components/pages/KbList.tsx`, stories + test.
Graph nodes: `KbList()`, `AppShell.tsx`, `useAsyncData`.

## Slice 3 — the document surface (T5–T7)

Drill-down, per D6. Read `ClientFicha.tsx` (the two-region rail + main, the
responsive collapse) and `AutomationRuleDetailPage` (the route-driven drill-down
shape) before writing. Reuse those patterns; invent nothing.

### T5 — The route and the skeleton

Route: `panelRoutes.ts` gains the KB document id for the `kb` view, mirroring how
`clientId` and `automationRuleId` are carried. `AppShell.tsx` gains the branch:
`view === 'kb'` renders `KbDocumentDetail` when the id is present, `KbList`
otherwise, and `KbList` gains `onOpenDocument`.

`KbDocumentDetail` renders through `PageFrame` with the back control in
`PageFrame actions` — `Button variant="secondary"` with `window.history.back()`,
exactly as `ClientFicha.tsx:160-165`.

RED: a test that the document route renders the detail and the back control, and
that `KbList` without an id still renders the list.

### T6 — The two regions, and the operations move in

Rail: the document's identity facts, labelled — title, format, active version and
version count, status, audience, provider/model, cost, created_at. Main: the
document's operations.

Move the operations out of the row's `DocActions` and into the main region:
content editing behind the disclosure, version restore, audience change, and
disable — carrying the page-owned confirmation (D2/T4) with it. The content comes
from `GET /kb/{id}` (`getKbDocument`), which already returns it.

The disclosure must use the shared styled appearance class (T5 in the old plan),
which removes the browser-default `<summary>` marker. Add that class to the
tokenized stylesheet and adopt it here. Do not restyle the other three consumers
(see Non-goals).

RED: the detail renders the identity rail, and each operation still works from its
new locus — including that disable still confirms and still names the document.

### T7 — The list links to the document

Rows stop carrying an action cell. The document's title becomes the row's link
using the existing shared `.table__link` contract (`primitives.css:292-294`), which
already has three consumers, and opens the detail.

RED: the list no longer offers inline document operations, and the row link
navigates to the document.

## Slice 4 — the corpus and completeness (T8–T10)

### T8 — Adopt `.data-region`; trim duplicated `.kb*`

RED: a test asserting the documents table is wrapped in `.data-region` and that no
`.kb*` selector duplicates shared structure.
GREEN: wrap the populated table in `.data-region`; delete the `.kb*` layout rules
that duplicate `.data-region`/shared structure; keep the pieces with no shared
equivalent (technical metadata block, search affordance).
Files: `web/src/components/pages/KbList.tsx`, `primitives.css`.

### T9 — Documents-first recomposition

GREEN: the documents become the primary region; the upload is demoted to a
secondary affordance instead of the card that currently sits above the collection;
the retrieval probe becomes a tool region. No card-on-card — and a populated
`DataTable` already renders its own surface, so the table must not be wrapped in
another one.
Files: `web/src/components/pages/KbList.tsx`, `primitives.css`.

### T10 — Upload validation feedback and the full state matrix

GREEN: `DESIGN_SYSTEM.md:333` requires format, size, processing, failure and
retry. Add the visible size constraint, the processing/failure feedback and the
upload-specific retry at the upload locus. Then make loading / empty / denied /
error / processing / success all render from the page's own states, with stories
driving data rather than a workflow prop, and hand the branch to the human for the
1366×768 visual gate.

## Acceptance criteria

1. No KB document badge can display a state the domain cannot produce.
2. Disabling a document from the real app requires an explicit confirmation that
   names the clicked document and states the effect on agent answers.
3. `DESIGN_SYSTEM.md` KB row matches what the code and the database can produce.
4. The mock/test contract matches the API contract.
5. Documents are the primary region; a document has its own region for its
   metadata, versions, audience and actions.
6. `.kb*` selectors are either removed or justified as having no shared equivalent.
7. `npm run test`, `npx tsc -b --noEmit`, `npm run build` and
   `npm run build-storybook` are green.
8. Human visual acceptance at 1366×768.

## Progress

- [x] Session closed with ODD handoff (`ready-for-odd/`)
- [x] Worktree created and `npm ci` run
- [x] T0: this doc committed on the branch (`8f194da9`)
- [x] Slice 1 (T1–T3) — merged to `main` as `a937f81e` (PR #328)
- [x] Slice 2 (T4) — PR #330, open, retargeted to `main`, CI green
- [x] Slice 3 (T5–T7) — PR 3, open, CI green
- [ ] Slice 4 (T8–T10)

## Verification evidence

### Slice 1 (T1–T3)

Commits: `c039b968` (T1), `fa34f8cc` (T2), `7a872d35` (T3), plus correction
`4bf8bd10`. Weight: 47 insertions / 17 deletions across 6 files under `web/`.

RED/GREEN observed: T1 `1 failed, 8 passed` → `9 passed` (missing `visibility` in
the shape assertion). T2 `5 failed, 36 passed` → `41 passed` (missing lifecycle
exports; document status still exposed operation states). T3 `1 failed, 41 passed`
→ `42 passed` (row lacked the two-plane contract).

Parent readback found two real defects in `fa34f8cc` and they were corrected:

1. **Behavioural regression.** `procesando` mapped to `warning`. Verified against
   the repo: `warning` means "stale data" (`CasesList.tsx:117`,
   `ConversationThread.tsx:92`, `Settings.tsx:30`, `ClientesList.tsx:50`) and every
   in-flight state is `info` + spinner. KB processing was `info` before the change.
   Now `info`.
2. **Unnecessary complexity.** The overload pair and `?? "neutral"` fallback in
   `kbOperationTone` existed only because the operation map was typed `BadgeTone`
   (`Badge.tsx:4`, no `info`) while feeding `StateMessage`
   (`StateMessage.tsx:1`, no `neutral`). Now a total `Record<"procesando" |
   "error", StateTone>` with no accessor, no overload, no fallback.

Also relaxed: the design-system assertion matched one exact markdown sentence from
an unrelated test file (a maintenance trap); it now asserts the semantic claim.

Not dead code: `KB_OPERATION_LABELS` has no rendering consumer, but
`DS-UI-LABELS` (`openspec/specs/panel-design-system/spec.md:454-468`) is a MUST that
`toneMaps` map KB states to approved labels including `Procesando`/`Error`, with a
test as the expected verifier. Kept deliberately.

Parent re-ran every slice check on the corrected candidate:

- `npm run test`: **80 files / 668 tests passed**
- `npx tsc -b --noEmit`: passed
- `npm run build`: passed (pre-existing chunk-size warning only)
- `npm run build-storybook`: passed (pre-existing warnings only)

Assessment for the writer's diff (`8f194da9..4bf8bd10`): `medium`, 6 paths,
`under_budget`. RDD is `off` for this clone, so no native review lifecycle runs;
the medium tier is covered by the writer's self-verification plus the parent
readback and the four re-run checks above.

### Slice 2 (T4) — branch `odd/kb-disable-confirmation`

Commits: `4764b516` (the confirmation) and `196da565` (the unification), on branch
`odd/kb-disable-confirmation` based on the slice-1 branch.

The fix: `KbListState` no longer carries `disable-confirmation`; the page owns a
single discriminated `Confirmation` state (`{ kind: "disable", doc } | { kind:
"restore", doc, version }`), `onDisable` opens it with the clicked document, and only
`Confirmar` runs the mutation. Restore and disable share one confirmation block and
one class (`.kb-actions__confirmation`, renamed from
`.kb-actions__restore-confirmation`, which had come to name only one of its two users).

RED verified independently by the parent, not taken on report: with the base
`KbList.tsx` and the new test, it fails on the confirmation assertion (the base fires
the mutation immediately and surfaces the mutation error).

Parent readback found one defect the writer did not, and it was corrected:

- **Two confirmations could be open at once.** `restoreConfirmation` and
  `disableConfirmation` were independent and neither cleared the other, and opening a
  confirmation does not set `busy`, so clicking `Restaurar` on one row and then
  `Deshabilitar` on another rendered two warning banners with two ambiguous
  `Confirmar` buttons — in the destructive flow the handoff flags as KB's highest
  domain risk. The discriminated state makes the overlap unrepresentable and collapsed
  the duplicated markup. The regression test asserts exactly one alert and one
  `Confirmar`, and that the surviving `Confirmar` disables the clicked document.

Parent re-ran the checks on the corrected candidate:

- `npm run test`: **80 files / 669 tests passed**
- `npx tsc -b --noEmit`: passed

Writer-reported, not re-run by the parent: `npm run build` passed,
`npm run build-storybook` passed.

Process note: the slice-2 writer ran an early `graphify` refresh. The repo rule is one
refresh per work session, at close. It wrote only inside the unit worktree (untracked),
so the branch is unaffected; recorded here so the deviation is visible.

### Base movement during the unit

`main` advanced from `9b83e27f` to `a94a98b4` (merge of PR #329,
`odd/assistant-web-search`) while this unit was in flight, and a new unit
(`odd/agenda-product-register`) appeared. PR #329 changed **no file under `web/`**
(`git diff --stat 9b83e27f..a94a98b4 -- web/` is empty), so there is no conflict with
this work; PR #328 reported `MERGEABLE` / `CLEAN` against the moved base.

### Slice 3 (T5–T7) — branch `odd/kb-document-surface`

Commits: `d7f0e1f8` (route), `70c0d6ef` (operations move), `66b1d1a0` (list link),
`b6d767bc` (test ownership), plus the correction `163eaa41` and `12d7bf69`.

The document now has its own surface: `panelRoutes.ts` carries the KB document id,
`AppShell.tsx` renders `KbDocumentDetail` on the drill-down, the detail renders an
identity rail plus an operations main (content editor behind a styled disclosure,
version restore, audience, disable with its page-owned confirmation), and the list rows
link to it through the shared `.table__link` instead of carrying an action cell.

Parent readback found four defects the writer did not, and they were corrected:

1. **The KB detail borrowed the client ficha's classes.** `.client-ficha`,
   `__rail`, `__facts`, `__main` were used by `KbDocumentDetail.tsx`, so the names lied
   and the two unrelated pages were coupled — the same move this repo refused when it
   created the neutral `.data-region` instead of borrowing a page class. Promoted to
   `.detail-region`, with both consumers updated.
2. **Two assertions were lost, not moved.** The slice-2 overlap regression test
   (`keeps only the latest confirmation open when workflows overlap`) was dropped, and
   the document-status triangulation was weakened to a tautological ternary
   (`first.active ? "activo" : "deshabilitado"`) that cannot fail for the other value.
   Both restored.
3. **Dead CSS plus a silently dropped copy block.** The `kb-actions__technical` block
   left the list and never arrived at the detail, leaving five rules with zero
   consumers. Deleted, and the provider/model identity facts are now asserted in the
   detail's test. The copy removal is deliberate: the rail shows them as labelled facts.
4. **`const document = …` shadowed the DOM global**, which is why the edit path needed
   `globalThis.document.getElementById`. Renamed, and the repeated status ternary became
   the `docStatus()` helper.

Parent re-ran the checks on the corrected candidate:

- `npm run test`: **81 files / 662 tests passed**
- `npx tsc -b --noEmit`: passed

Writer-reported, not re-run by the parent: `npm run build` passed,
`npm run build-storybook` passed.

**Review size: 1041 changed lines (524 added, 517 deleted)** — over the ~400 budget, and
presented honestly rather than compressed:

| Side | Changed lines |
|---|---|
| Production source (`KbDocumentDetail.tsx`, `AppShell.tsx`, `panelRoutes.ts`, `KbList.tsx`, `primitives.css`, `ClientFicha.tsx`) | 301 |
| Tests and stories | 740 |

The test side dominates because 415 lines were deleted from `KbList.stories.test.tsx` and
re-homed in `KbDocumentDetail.test.tsx` (176) and its stories (32): the operations moved,
so their tests moved with them. One honest cut pass was attempted and no cohesive split
exists — separating the tests would orphan them from the code they cover, and separating
the list link from the detail would leave the operations duplicated in two places. The
number is reported as-is.

Process note: the slice-3 writer also ran an `graphify` refresh early (twice). Verified
that it wrote only inside the unit worktree and left the main worktree's graph
untouched.

## Next step

Slice 4 (T8–T10): the corpus and completeness — `.data-region` on the documents table,
the `.kb*` trim, the documents-first recomposition with the upload demoted, the retrieval
probe as a tool region, upload validation feedback, and the full state matrix.
