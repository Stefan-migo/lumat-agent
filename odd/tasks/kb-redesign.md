# ODD task — KB (conocimiento) panel redesign

## Objective
Match the KB section to the owner-approved references, implementing the validated findings
`conocimiento-001..030` across its two surfaces:
- landing (`/panel/app/kb`, `web/src/components/pages/KbList.tsx`),
- document detail (`/panel/app/kb/:id`, `web/src/components/pages/KbDocumentDetail.tsx`).

## Problem
The landing renders a single flat column (bare documents table, inline upload form, retrieval
form) and the detail consolidates everything into "Identidad" + "Operaciones" cards. Neither
follows the references. The owner ran the image-first analysis (machine v2): capture, owner
visual analysis (the gate), read-only code analysis, and a fresh-context validator that
returned `PASS` over 30 rows on 2026-10-02 (`odd/analysis/conocimiento/findings.md`). The
reference governs geometry/layout; the design system governs palette; the references are
AI-generated and compressed, so mobile/tablet must follow the design system's air and spacing
instead of the reference density.

## Why now
The KB analysis landed on `main` (PR #473, merge `ba413425`, 2026-10-05). The agenda and
usuarios sections are closed, so KB is the next section in the serial implementation order
(`panel-section-analysis` phase 5). All 30 findings are `local`: the shared primitives the
reference needs already exist (`Card` gained `icon`/`description`, `Dialog` gained
`icon`/`description` and mobile-sheet behaviour, `PageFrame`/`PageHeader` gained
`subtitle`/`titleAdornment`), so KB is pure local composition with no upstream unit.

## Scope
In:
- `web/src/components/pages/KbList.tsx`: two-column body, page header (subtitle + count chip),
  "Documentos" card (toolbar with search + "Filtros", identity/version/audience cells, footer
  count, mobile card rows), "Probar recuperación" card (icon, subtitle, inline search,
  advanced-options disclosure, initial empty state), "Agregar documento" card (icon, subtitle,
  dropzone, mobile primary action + bottom sheet).
- `web/src/components/pages/KbDocumentDetail.tsx`: header (metadata line, status badge, file
  icon, "Editar contenido" action), Resumen/Contenido/Versiones tabs, "Información del
  documento" / "Detalles técnicos" / "Versión activa" / "Audiencia" / "Disponibilidad" cards,
  tablet two-column composition.
- `.kb-*` / `.kb-list*` / `.kb-search*` / `.kb-actions*` rules in
  `web/src/components/primitives/primitives.css` (additive, section-scoped; the KB mobile add
  sheet follows the existing `.dialog:has(...)` mobile-sheet pattern).
- Tests for every touched file, plus `KbList.stories.tsx` / `KbDocumentDetail.stories.tsx`.

Out:
- `web/src/tokens/tokens.css`: palette is settled; no `token-palette` finding on KB.
- Backend (`app/…`): the KB API already returns the needed fields; no finding requires a
  payload change.
- Shared primitives: `Card`, `Dialog`, `PageFrame`, `PageHeader`, `Tabs`, `Badge`, `Input`,
  `Select`, `Textarea` are used as-is; if a change becomes necessary it is a finding for the
  owner, not a silent edit.
- Other panel sections and `TechnicianAgenda.tsx`.

## Constraints
- Tokens only. Do NOT touch `tokens.css`. No white element backgrounds; use `var(--surface)` /
  `var(--brand-bg-elevated)`.
- Follow the design system's air/spacing on mobile/tablet; do not copy the reference's
  compressed density.
- UI copy neutral Chilean Spanish; code, comments, commits and artifacts English.
- Preserve every existing behavior: document list load/retry, upload (extension/size
  validation, feedback, retry), retrieval search (topK/minSim, empty/denied/error), document
  edit (new version), visibility change, disable, restore, permissions and API calls.
- Tests and docs stay with the behavior in the same commit.

## Authorized scope
- Worktree: `/home/stefan/repos/lumat-agent-odd-kb-redesign`
- Branch: `odd/kb-redesign`
- Base: `ba413425` (`origin/main` after PR #473).
- No push, PR, or merge without explicit owner approval.

## Checks (run in the worktree, from `web/`)
- `npm run test`
- `npx tsc -b --noEmit`
- `npm run build`

## TDD mode
`openspec/config.yaml` declares `testing.strict_tdd: true` for the backend (`uv run pytest
tests/`). This pass is web-only with runner `cd web && npm run test` (vitest), consistent with
the usuarios and agenda passes: tests required alongside each behavior, full suite green before
each work-unit commit. Every behavioral change (upload, search, edit, visibility, disable,
restore) carries a test; pure layout/CSS findings assert structure.

## Graph nodes consulted (graphify)
`KbList()` (`KbList.tsx:98`), `KbDocumentDetail()` (`KbDocumentDetail.tsx:53`),
`KbList.tsx`, `KbDocumentDetail.tsx`, `PageFrame()` (`PageFrame.tsx:17`), `PageHeader`
(`PageHeader.tsx:14`), `Card()` (`Card.tsx:11`), `Dialog()` (`Dialog.tsx:18`), `Badge()`,
`Icon()`, `shared/toneMaps.ts` (`kbStatusLabel`, `kbStatusTone`), `panelRoutes.ts`
(`pathForRoute`), `api.ts` (`refreshKbDocuments`, `uploadKbDocument`, `searchKb`,
`getKbDocument`, `editKbDocument`, `setKbVisibility`, `disableKbDocument`,
`restoreKbDocument`), `primitives.css`. Community `KbList.tsx` groups `KbDocumentDetail.tsx`,
`KbList.stories.tsx` and `KbDocumentDetail.stories.tsx`.

## Work units
### WU1 — landing: header + "Documentos" card (findings 001-010)
- Body: replace the flat single column with the reference two-column composition (001).
- Header: subtitle sentence "Gestiona los documentos y prueba la recuperación de información."
  via `PageFrame.subtitle` (002); document count as a chip beside the title via
  `titleAdornment` + `Badge` (003).
- "Documentos" card: frame the bare table in a bordered `Card` titled "Documentos" (004);
  add the reference toolbar with a search input and "Filtros" control (005); rebuild the cells
  — identity (PDF icon + title + `#<id> · <format>` + chevron) (006), version (`v{n} · Activa`)
  (007), audience (lock icon + `Interno · Solo Lumat`) (008); add the "1 documento" footer
  count (009); render mobile as a card row instead of the overflowing table (010).
- Update `KbList.test.tsx`, `KbList.stories.tsx`.

### WU2 — landing: retrieval + upload cards + mobile (findings 011-019)
- "Probar recuperación" card: leading magnifier icon (011) and supporting subtitle (012) via
  `Card` `icon`/`description`; place "Buscar" inline inside the query field (013); collapse
  topK/minSim under an "Opciones avanzadas" disclosure (014); show the initial empty state
  "Los resultados aparecerán aquí después de buscar." before a search (015).
- "Agregar documento": present as a `Card` with icon, title and supporting subtitle instead of
  the inline heading + fields (016); replace the native file input with a dashed drag-and-drop
  zone plus a "Seleccionar archivo" button (017); add the full-width primary "Agregar
  documento" entry action under the header on mobile (018) and open the add form as a bottom
  sheet over the list (019), composing the existing `Dialog` + mobile-sheet CSS.
- Update `KbList.test.tsx`, `KbList.stories.tsx`.

### WU3a — landing: retrieval placement + results redesign (owner additions A1/A2)
Owner feedback delivered 2026-10-05 (during implementation); the reference layout governs and
this supersedes the WU2 secondary placement (where retrieval sat in the narrow right column).
- A1: move the "Probar recuperación" card into the **left column, directly below "Documentos"**.
  The right column holds only "Agregar documento". Reference: left = Documentos + Probar
  recuperación; right = Agregar documento.
- A2: redesign the search-results surface to be **content-first and never overflow**. The chunk
  `Contenido` becomes the prominent element (readable full-width block); document / version /
  fragment / similarity render as compact meta above it instead of dense table columns. Remove
  the 5-column `DataTable` and the forced-width cause of the horizontal break
  (`.kb-search__result-content { max-width: 32rem }` inside a squeezed table). No horizontal
  scroll at any breakpoint; keep the "N resultados ordenados por similitud." summary.
- Update `KbList.tsx`, `primitives.css`, `KbList.test.tsx`, `KbList.stories.test.tsx`.

### WU3b — detail: header + tabs + information cards (findings 020-027)
- Header: metadata line `#<id> · <format> · Creado el <date>` instead of the generic subtitle
  (020); `Activo` status badge beside the title (021); file icon tile (022); replace "Volver a
  documentos" with an "Editar contenido" action (023).
- Tabs: render the reference Resumen / Contenido / Versiones tabs, composing the existing
  `Tabs` primitive (024).
- Cards: split the consolidated "Identidad" into "Información del documento"
  (Título/Formato/Creado/Cantidad de versiones) (025) and "Detalles técnicos"
  (Proveedor/Modelo/Costo) (026); add the "Versión activa" surface (`v{n}`, `En uso` chip,
  "Ver versiones →") (027).
- Update `KbDocumentDetail.test.tsx`, `KbDocumentDetail.stories.tsx`.

### WU4 — detail: two-column reference layout + Audiencia/Disponibilidad cards (findings 028-030)
- 028 Audiencia card (right column): lock icon + title "Audiencia", subtitle "Define quién puede
  utilizar este documento.", label "Audiencia del documento", the audience `Select`, the info note
  ("Los documentos internos no se usan para responder a clientes.") and the "Guardar audiencia"
  button (disabled when unchanged — existing behavior).
- 029 Disponibilidad card (right column): title "Disponibilidad" with the status badge (`Activo`),
  subtitle "El documento está habilitado." and the full-width "Deshabilitar" button (pause icon).
- Audiencia (028) and Disponibilidad (029) move out of the old "Operaciones" card; the remaining
  mutation feedback and confirmation dialogs stay reachable (feedback at the page level).
- 030 two-column body: LEFT = "Información del documento" (facts: Título / Formato with a PDF icon
  chip / Creado / Cantidad de versiones), then the "Versión activa" row (layers icon, `v{n}`,
  `En uso` chip, "Ver versiones →"), then "Detalles técnicos" (collapsible, `</>` icon) with
  Proveedor | Costo on one row and Modelo full-width, rendered as disabled inputs per the
  reference. RIGHT = Audiencia + Disponibilidad. Tablet keeps the two-column composition; mobile
  stacks to a single column.
- Reference correction to WU3b: move "Versión activa" INSIDE the "Información del documento" card
  as a divider row (the reference does not show it as a separate card).
- Restore (`restoreKbDocument`) moves into the Versiones tab (or remains reachable there); keep the
  behavior, confirmation and payload intact. `editKbDocument` stays on the Contenido tab.
- Update `KbDocumentDetail.tsx`, `primitives.css`, `KbDocumentDetail.test.tsx`,
  `KbDocumentDetail.stories.test.tsx`.

### WU5 — owner additions (2026-10-05, post-WU4; approved)
Owner ruled the reference may be overridden here.
- O1 — unify tabs: merge "Contenido" + "Versiones" into a single tab "Contenido y versiones"
  (the detail then has Resumen | Contenido y versiones). Improve the content editor and place the
  version list (with restore) in that same tab.
- O2 — markdown edit/preview: in the content editor add an Editar | Vista previa toggle using the
  existing `web/src/components/shared/Markdown.tsx` (react-markdown + remark-gfm). Editing still
  creates a new version (`editKbDocument`). Honest caveat: `.md`/`.txt` preview well; PDF-extracted
  content is pypdf plain text and previews as paragraphs (no fabricated structure).
- O3 — enable path (backend scope expansion, approved): add `enable_document` (set `active=True`
  only — no version or visibility change) in `app/services/kb.py`, `POST /panel/api/kb/{id}/enable`
  in `app/panel/api/routes/kb.py`, `enableKbDocument` in `web/src/api.ts`, and a "Habilitar" action
  in the Disponibilidad card shown when the document is disabled. Restore is NOT a substitute: it
  also flips `active_version` and resets `visibility` to internal.
- Update backend (`app/services/kb.py`, `app/panel/api/routes/kb.py`, backend tests) and frontend
  (`api.ts`, `KbDocumentDetail.tsx/.test.tsx/.stories.test.tsx`, `primitives.css`).

## Delivery
- Forecast: ~650–950 authored changed lines across 2 pages + CSS + tests → over the 400-line
  review budget.
- Planned slices: PR1 = WU1+WU2 (landing foundation, reviewed), PR2 = WU3a (retrieval
  placement + results redesign), PR3 = WU3b (detail), PR4 = WU4 (detail follow-up), PR5 = WU5
  (owner additions).
- Chain strategy: pending owner decision (default `ask-on-risk`); decide before the first PR.
- Local work-unit commits are allowed on the branch without a chain decision.

## Acceptance criteria
- [ ] Findings `conocimiento-001..030` implemented.
- [ ] Owner additions A1/A2: "Probar recuperación" sits in the left column below "Documentos"
      per the reference; the results surface is content-first and never overflows.
- [ ] Owner additions O1/O2/O3: Contenido + Versiones unified in one tab; editable markdown
      preview; a short "Habilitar" path in the Disponibilidad card backed by `POST /kb/{id}/enable`.
- [ ] `npm run test`, `npx tsc -b --noEmit`, `npm run build` all green.
- [ ] Mobile landing uses a card list with no horizontal overflow; the add form opens as a
      bottom sheet.
- [ ] Tablet landing and detail use the reference two-column composition.
- [ ] Existing KB behaviors preserved (upload, search, edit, visibility, disable, restore;
      behavior tests green).
- [ ] `tokens.css` untouched; no white element backgrounds.
- [ ] `odd/analysis/conocimiento/` lifecycle moved to `implementing` on the first commit and
      `done` at close.

## Progress
- [x] WU1 — landing: header + "Documentos" card (findings 001-010)
- [x] WU2 — landing: retrieval + upload cards + mobile (findings 011-019)
- [x] WU3a — landing: retrieval placement + results redesign (owner additions A1/A2)
- [x] WU3b — detail: header + tabs + information cards (findings 020-027)
- [x] WU4 — detail: audience/disponibilidad + tablet (findings 028-030)
- [x] WU5 — owner additions: unify Contenido+Versiones tab, markdown preview, enable path

## Verification evidence
### WU5 — unified content/version tab, markdown preview and enable path
- WU5a backend commit: `a5834fbf` — `POST /panel/api/kb/{id}/enable` sets only `active=True`.
- WU5a functional: `eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_kb_settings.py -k kb_enable` — PASS, 2 passed.
- WU5a integration: `eval "$(infra/test-db.sh env)" && uv run pytest tests/integration/test_kb.py` — PASS, 19 passed.
- RED: `cd web && npx vitest run src/components/pages/KbDocumentDetail.test.tsx src/stories/pages/KbDocumentDetail.stories.test.tsx` — FAIL as expected, 6 failed / 10 passed; old tabs, missing preview, and disabled-document enable action did not meet the new assertions.
- GREEN focused: same Vitest command — PASS, 2 files / 16 tests.
- Final `cd web && npm run test` — PASS, 96 files / 1013 tests. An earlier run had failures only in the known-flaky `AgendaPage.stories.test.tsx`; isolated rerun passed 12/12, and the final full run passed.
- Final `cd web && npx tsc -b --noEmit` — PASS (exit 0; no diagnostics).
- Final `cd web && npm run build` — PASS; Vite built successfully with the existing >500 kB chunk-size warning.
- Frontend commit: `a1e25ee5` — `feat(kb): unify versions, markdown preview, and enable`.
- Graphify consulted: nodes `KbDocumentDetail.tsx` / `KbDocumentDetail()`, `KbDocumentDetail.test.tsx`, `Tabs.tsx` / `Tabs()`, `Markdown.tsx` / `Markdown()`, `api.ts`, `postJson()`, `disableKbDocument()`, `editKbDocument()`, `restoreKbDocument()`, and backend `enable_document()`. `graphify path "KbDocumentDetail.tsx" "Markdown.tsx"` found no directed path; the earlier undirected traversal linked the detail through `api.ts` and `AgentChat.tsx` to `Markdown.tsx`.
- Scope: API function, detail page and its component/story tests, and additive tokenized KB CSS only. Shared primitive components and token definitions were not changed; the pre-existing disable confirmation and restore endpoint/payload remain intact.

### WU4 — detail columns, audience and availability
- Baseline before edits: `cd web && npm run test` — PASS, 96 files / 1010 tests.
- RED: `cd web && npx vitest run src/components/pages/KbDocumentDetail.test.tsx src/stories/pages/KbDocumentDetail.stories.test.tsx` — FAIL as expected against the old surface, 3 failed / 11 passed; required two-column groups, Audience/Availability cards and restore-on-Versiones assertions were absent.
- GREEN focused: same command — PASS, 2 files / 14 tests.
- Final `cd web && npm run test` — PASS, 96 files / 1011 tests.
- Final `cd web && npx tsc -b --noEmit` — PASS (exit 0; no diagnostics).
- Final `cd web && npm run build` — PASS; Vite built successfully with the existing >500 kB chunk-size warning.
- Implementation commit: `1e1f9652` — `feat(kb): rebuild document audience and availability cards`.
- Graphify consulted nodes `KbDocumentDetail.tsx`, `KbDocumentDetail()`, `KbDocumentDetail.test.tsx`, `Card.tsx` / `Card()`, `Button.tsx` / `Button()`, and `primitives.css`; `graphify path "KbDocumentDetail.tsx" "Card.tsx"` returned `KbDocumentDetail.tsx --imports_from--> Card.tsx`.
- Scope: detail page, KB-scoped CSS, component/story tests; no shared primitives, tokens, or primary-worktree files changed. Visibility and disable mutations retain their API methods and payloads; restore remains confirmed and is now available in Versiones.

### WU3b — detail header, tabs + information cards
- Baseline before edits: `cd web && npm run test` — PASS, 95 files / 1008 tests.
- RED: `cd web && npx vitest run src/components/pages/KbDocumentDetail.test.tsx -t "redesigned header"` — FAIL as expected, 1 failed / 11 skipped; the metadata line was absent.
- GREEN: `cd web && npx vitest run src/components/pages/KbDocumentDetail.test.tsx src/stories/pages/KbDocumentDetail.stories.test.tsx` — PASS, 2 files / 13 tests.
- Final `cd web && npm run test` — PASS, 96 files / 1010 tests.
- Final `cd web && npx tsc -b --noEmit` — FAIL initially on the WU3a import regression (`KbList.tsx(72,42): Cannot find name 'KbSearchResult'`, present at the pre-WU3b base `8ae58e3c`). Fixed in `6931934c`; PASS (exit 0) after the fix.
- Final `cd web && npm run build` — FAIL initially at the `tsc -b` phase on the same error; PASS after `6931934c` (Vite built; existing >500 kB advisory).
- Commit: `bbee0523d379ba28934b8cc064c5973a00782068` — `feat(kb): rebuild document detail summary tabs`. Import fix: `6931934c`.
- Graphify nodes consulted: `KbDocumentDetail.tsx` / `KbDocumentDetail()`, `Tabs.tsx` / `Tabs()`, `PageFrame()` / `PageFrame.tsx`, `Badge()`, `Icon()`, `Card()`, `kbStatusLabel()` / `kbStatusTone()`, `getKbDocument()` / `editKbDocument()`, community hub `KbList.tsx`. `graphify path "KbDocumentDetail.tsx" "Tabs.tsx"` returned no directed path.
- Scope stayed on detail composition and its component/story tests plus KB-scoped CSS; no shared primitive or token files changed. The primary navigation still exposes “Base de Conocimientos” after replacing the detail back action. WU4 remains unchecked.
- Independent read-only verification (parent): findings 020-027 each mapped to a code anchor — all `implemented`; behaviors (content load, edit, visibility, disable, restore, confirmation, loading/denied/error) preserved; navigation not stranded; no `tokens.css` or shared-primitive change (confirmed by path diff). Remaining test gaps are minor: file icon (022), edit payload/refreshed version, and the “Ver versiones” affordance.
- Parent fix + reverification: `6931934c` restored `KbSearchResult` in `KbList.tsx`; after it `npx tsc -b --noEmit` PASS, `npm run build` PASS, full suite 96 files / 1010 tests PASS.

### WU3a — landing retrieval placement + results redesign
- Baseline before edits: `cd web && npm run test` — PASS, 95 files / 1007 tests.
- RED: `cd web && npx vitest run src/components/pages/KbList.test.tsx src/stories/pages/KbList.stories.test.tsx -t "stacks retrieval|makes documents and retrieval|renders loading, ready"` — FAIL as expected, 3 failed / 27 skipped; retrieval was still secondary and results lacked the fragment meta/content-first list.
- GREEN: `cd web && npx vitest run src/components/pages/KbList.test.tsx src/stories/pages/KbList.stories.test.tsx` — PASS, 2 files / 30 tests.
- Final `cd web && npm run test` — PASS, 95 files / 1008 tests.
- Final `cd web && npx tsc -b --noEmit` — **CORRECTED: the writer reported PASS, but the tree did not typecheck.** Deleting `searchColumns` also dropped `KbSearchResult` from the type import while the search state still used it (`KbList.tsx:72`). Fixed in `6931934c`; real result after the fix: PASS (exit 0).
- Final `cd web && npm run build` — **CORRECTED: FAILED at the `tsc -b` phase** on the same missing name; PASS after `6931934c`.
- Commit: `a85baa5b` — `feat(kb): move retrieval and redesign results`. Correction: `6931934c` — `fix(kb): restore the KbSearchResult type import`.
- Process learning: the writer's `tsc`/`build` PASS claims for WU3a were false; only a re-run in the parent spot check caught it. Always re-run `tsc -b --noEmit` and `npm run build`, not just the test suite.
- Graphify: queries consulted `KbList.tsx`/`KbList()`, `KbSearchResult` (`types.ts`), `shared/DataTable.tsx`, and `primitives.css`; the report identifies `KbList.tsx` as a community hub. `graphify path "KbList.tsx" "DataTable.tsx"` found no directed path. The requested image path was not present in this worktree.
- Changed files: `web/src/components/pages/KbList.tsx`, its component/story tests, and `web/src/components/primitives/primitives.css`; no shared primitives or tokens changed. Upload remains the only secondary card and is hidden on mobile behind the existing entry action/dialog.

### WU2 — landing retrieval + upload cards + mobile
- Baseline before edits: `cd web && npm run test` — PASS, 95 files / 1001 tests.
- RED — retrieval layout/disclosure/initial state: `cd web && npx vitest run src/components/pages/KbList.test.tsx src/stories/pages/KbList.stories.test.tsx -t "presents retrieval|shows the initial retrieval"` — FAIL as expected, 2 failed / 27 skipped; missing retrieval description and initial empty-state assertions.
- RED — upload card/dropzone: `cd web && npx vitest run src/components/pages/KbList.test.tsx src/stories/pages/KbList.stories.test.tsx -t "keyboard-operable upload dropzone|accepts a dropped file"` — FAIL as expected, 2 failed / 27 skipped; missing upload card description/dropzone assertions.
- RED — mobile add entry/sheet: `cd web && npx vitest run src/components/pages/KbList.test.tsx src/stories/pages/KbList.stories.test.tsx -t "mobile entry dialog|full-width entry action"` — FAIL as expected, 2 failed / 27 skipped; entry action and dialog were absent.
- GREEN — retrieval: same targeted command — PASS, 2 tests / 27 skipped.
- GREEN — upload: same targeted command — PASS, 2 tests / 27 skipped; the dropped file appears in the upload form and the picker input remains wired.
- GREEN — mobile: same targeted command — PASS, 2 tests / 27 skipped.
- Final `cd web && npm run test` — PASS, 95 files / 1007 tests.
- Final `cd web && npx tsc -b --noEmit` — PASS (exit 0).
- Final `cd web && npm run build` — PASS; Vite built successfully with the existing >500 kB chunk-size warning.
- Commit: `3b799ff4aff5eccbfdd1ab2ecadef4081dca57e0` — WU2 implementation and tests.
- Graph nodes/edges consulted: `KbList.tsx`, `KbList()`, `Card()` / `Card.tsx`, `Dialog()` / `Dialog.tsx`, `Icon.tsx`, and landing reference `BaseDeConocimiento.png`; undirected path `KbList.tsx --imports_from--> Icon.tsx <--imports_from-- Dialog.tsx`.

### WU1 — landing header + "Documentos" card
- Baseline before edits: `cd web && npm run test` — PASS, 94 files / 999 tests.
- RED: `cd web && npx vitest run src/components/pages/KbList.test.tsx` — FAIL as expected against the original page; the subtitle assertion reported that the required text was absent. This structural test also asserts the count badge, documents card/toolbar, identity/version/audience cells, footer and mobile list.
- GREEN: `cd web && npx vitest run src/components/pages/KbList.test.tsx src/stories/pages/KbList.stories.test.tsx` — PASS, 2 files / 23 tests.
- Final `cd web && npm run test` — PASS, 95 files / 1001 tests.
- Final `cd web && npx tsc -b --noEmit` — PASS (exit 0).
- Final `cd web && npm run build` — PASS; Vite built successfully (existing >500 kB chunk-size warning).
- Commits: lifecycle `d32564cc35fe2d791709c24bb926c9d3ca65a2aa`; WU1 code `c7a5befc4441e05dd7b74a4f2f845b891f9a8626`.
- Graph nodes/edges consulted: `KbList()` / `KbList.tsx`, `Card()` / `Card.tsx`, `DataTable()` / `DataTable.tsx`, `PageFrame()` / `PageFrame.tsx`, `Badge()` / `Badge.tsx`; edge `KbList.tsx --imports_from--> Card.tsx`. The directed path to `DataTable.tsx` was not found.
- Independent read-only verification (parent): findings 001-010 each mapped to a code/CSS anchor — all `implemented`; no upload/search/retry/permission regression; no literal white background; `tokens.css` untouched; scope confined to the landing page and KB-scoped CSS. Remaining test gaps are presentation-only (icon rendering for 006/008 and responsive-breakpoint CSS for 001/010).
- RDD assess (base `ba413425`, committed-only): risk `medium`, 7 paths / 341 changed lines, `review_due: false` (`under_budget`) — boundary stays pending in the slice.
- Note: the writer self-reported `partial` because the RED run stopped at the first failing assertion and did not demonstrate RED per finding; the functional checks (full suite 1001 tests, `tsc -b`, build) are green and verified.

### Review record — WU1+WU2 slice (2026-10-05)
- RDD assess (base `ba413425`, committed-only): risk `medium`, 7 paths / 494 changed lines, `review_due: true` (`slice_budget_reached`).
- Consent: owner granted ("Review this change").
- Native review lineage `review-04d267427e08e26a`, lens `review-reliability`, tier `medium`, correction budget 200.
- Outcome: **approved**, no findings; authority `burned` (`gentle-ai.review-acknowledged/v1`). Reviewed boundary advances to the WU2 head; WU3/WU4 start from that base.

### Review record — WU3a..WU5 slice (2026-10-05)
- RDD assess (base `5f96f193`, committed-only): risk `medium`, 12 paths / 562 changed lines, `review_due: true` (`slice_budget_reached`).
- Consent: owner granted ("Review this change").
- Native review lineage `review-380e022998683d90`, lens `review-reliability`, tier `medium`, correction budget 200.
- Outcome: **approved**, no findings; authority `burned` (`gentle-ai.review-acknowledged/v1`). Reviewed boundary = `1334ddff`.

## Follow-ups (not blocking)
- None identified yet. The KB API already returns every field the references need, so no
  backend follow-up is expected (unlike the agenda technician-name gap).
- Minor test gaps noted by independent verification: KB detail file icon (022), edit payload/refreshed
  version, and the "Ver versiones" affordance are not directly asserted.
