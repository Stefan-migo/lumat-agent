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

## Authorized scope

- `web/src/components/pages/KbList.tsx`
- the KB section of `web/src/components/primitives/primitives.css`
- `web/src/components/shared/toneMaps.ts`
- `web/src/stories/pages/KbList.stories.tsx` and its test
- `web/src/_shared/mockData/kb.ts` and its test
- `web/src/types.ts` (only if the plane split requires it)
- `web/DESIGN_SYSTEM.md` (KB status row amendment only)
- `web/src/components/primitives/primitives.css` (shared disclosure appearance only)

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
| 3 | PR 3 | T5–T8: workspace recomposition | delegated writer |

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

### T5 — Shared styled disclosure (slice 3)

RED: a test asserting the disclosure renders the shared appearance class and no
browser-default marker contract is relied on.
GREEN: add the appearance class to the shared tokenized stylesheet and adopt it in
KB. Do not restyle the other three consumers (see Non-goals).
Files: `web/src/components/primitives/primitives.css`, `web/src/components/pages/KbList.tsx`.

### T6 — Adopt `.data-region`; trim duplicated `.kb*` (slice 3)

RED: a test asserting the documents table is wrapped in `.data-region` and that no
`.kb*` selector duplicates shared structure.
GREEN: wrap the populated table in `.data-region`; delete the `.kb*` layout rules
that duplicate `.data-region`/shared structure; keep the pieces with no shared
equivalent (technical metadata block, search affordance).
Files: `web/src/components/pages/KbList.tsx`, `web/src/components/primitives/primitives.css`.

### T7 — Recompose as a document-first workspace (slice 3)

GREEN: documents become the primary region; upload is demoted to a secondary
affordance; a document gains its own region (metadata, versions, audience,
actions) instead of the row-crammed disclosure; the retrieval probe becomes a tool
region. Reuse the `ClientFicha` two-region pattern
(`ClientFicha.tsx:166-202`, `primitives.css:307-325`, responsive collapse at
`:377-383`). No card-on-card.
Files: `web/src/components/pages/KbList.tsx`, `primitives.css`, stories + test.

### T8 — Upload validation feedback (slice 3)

GREEN: `DESIGN_SYSTEM.md:333` requires format, size, processing, failure and
retry. Add the visible size constraint, the processing/failure feedback and the
upload-specific retry at the upload locus.
Files: `web/src/components/pages/KbList.tsx`.

### T9 — Full state matrix and visual acceptance (slice 3)

GREEN: loading / empty / denied / error / processing / success all render from the
page's own states (D2), with stories driving data rather than a workflow prop.
Hand the branch to the human for the 1366×768 visual gate.

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
- [x] Slice 1 (T1–T3)
- [x] Slice 2 (T4)
- [ ] Slice 3 (T5–T9)

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

## Next step

Slice 2 (T4): the disable MUST violation, standalone and small. RED must mount the
real path (`<KbList />` bare, as `AppShell.tsx:119` does), click `Deshabilitar`,
and assert the confirmation names the clicked document with no mutation yet.

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

## Next step

Slice 3 (T5–T9): the workspace recomposition. Start at T5 with the shared styled
disclosure, then T6 (`.data-region`), T7 (document-first composition), T8 (upload
validation feedback), T9 (full state matrix).
