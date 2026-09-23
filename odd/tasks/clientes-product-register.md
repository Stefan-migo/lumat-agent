# ODD: clientes-product-register

## Objective

Raise the Clientes surface (`ClientesList` + `ClientFicha`) to the panel's product
register — the **first dense surface to apply the agent-app appearance under the
amended `DS-GRAMMAR-1`** — and extract on demand the reusable substrate it forces
into existence. This is the pilot for the panel-wide design-debt plan: it must
prove the register and produce the first shared pieces, not merely look better.

This unit also carries the contract amendment it depends on, so the spec change
ships with its first real consumer.

## Problem

Verified against the code at base `64972a26`. Every claim is evidence, not
impression.

### The contract drifted from the product decision

The owner decided on 2026-09-04: *"Gramática AI-agent global: apariencia de app de
agente en **toda la app**, fisiología de control room en primitivas de contenido
denso."* The `panel-ai-agent-grammar` change declared that same capability as
*"appearance of agent app, physiology of control room"* — and then wrote a delta
that kept the physiology half and dropped the app-wide appearance half.

The result is live at `openspec/specs/panel-design-system/spec.md:742`
(`DS-GRAMMAR-1`): only the conversation surfaces expose the grammar, and dense
pages `MUST retain` control-room primitives. That is the spec the panel was built
against, and it is why the panel reads as two products — an agent application for
conversations, an unstyled admin tool everywhere else.

The amendment is `openspec/changes/panel-grammar-global/`. `panel-app` needs no
delta: the duplicate clause lived in the former `PNL-APP-12`, which
`panel-conversaciones-redesign` replaced with `PNL-APP-12 — Conversation Workspace
Context` and no dense-page clause (verified: the live spec contains no `dense` or
`control-room` match).

### The user's report was half right, and the half that was right is this surface

The shared primitives are not unstyled HTML — they carry tokens, classes and full
interaction states. The "plain HTML" reading comes from `ClientFicha`, which
barely uses them.

**Raw native controls instead of the panel's primitives** (`ClientFicha.tsx`)

- `<select id="client-state">` (line 142) — the `Select` primitive exists and is
  not used.
- `<textarea id="new-note">` (line 164) — the `Textarea` primitive exists and is
  not used.
- Four raw `<button type="button">` (lines 145, 165, 177) — the `Button` primitive
  exists and is not used. These inherit the UA font size and metrics, the same
  defect class recorded in `odd/tasks/technician-surface.md` T7.

**Raw implementation label exposed to the user** (`ClientFicha.tsx:156`)

- `<Badge tone="neutral">customer_memo</Badge>` renders the backend identifier
  `customer_memo` in the product UI. `DESIGN_SYSTEM.md:444` forbids exposing raw
  implementation labels; the badge has no user-facing label at all.

**Visual decisions at the call site**

- `ClientesList.tsx:29` — the drill-down link carries
  `style={{ color: "var(--primary-700)" }}`. The accessible link colour is already
  a spec requirement (`DS-UI-LINK`), so the inline style duplicates a contract
  that belongs to a shared link treatment.
- `shared/DataTable.tsx` (4), `shared/StatCard.tsx` (2), `shared/StateMessage.tsx`
  (2) — inline `style={{}}` visual decisions, measured by count.

**Missing composition** (`ClientFicha.tsx:131-190`)

- The ficha is five stacked blocks: a `<section>` `aria-label="Resumen del
  cliente"`, a `Memo` card, `ClientMemories`, a `Notas` card, and one `Historial`
  card that contains four unrelated regions (visits, conversations, cases,
  messages) and three nested `DataTable`s under `<h3>` headings.
- The identity region renders six bare `<p>` elements with no label/value
  structure (lines 139-150).
- Clientes has **no page-specific CSS at all**: `primitives.css` contains zero
  `.clientes` / `.ficha` selectors. The surface is driven entirely by generic
  classes, which is why it reads as unattributed default layout.

**Real defects found while reading**

- **Clearing the search does not clear the list.** `ClientesList.tsx:68-70` retries
  only when `query` is truthy, so going from a non-empty query back to `""` leaves
  the previous filtered result on screen with no request.
- **Singular/plural is wrong.** `ClientesList.tsx:78` renders `${data.length}
  clientes`, so a single result reads `1 clientes`. Same defect class as the
  `1 visitas` bug closed in `technician-surface` T6.
- **No component test exists.** `ClientesList.test.tsx` is absent; the surface is
  covered only by `stories/pages/ClientesList.stories.test.tsx`. Under
  `strict_tdd: true`, a source change here has no place to observe RED.

## Scope

**In:** `openspec/changes/panel-grammar-global/**`, `web/DESIGN_SYSTEM.md` (the
two-axis clause), `web/src/components/pages/ClientesList.tsx`,
`web/src/components/pages/ClientFicha.tsx`, new
`web/src/components/pages/ClientesList.test.tsx`,
`web/src/components/pages/ClientFicha.test.tsx`, the Clientes stories and their
tests, the shared pieces the slices promote under
`web/src/components/shared/`, and the Clientes section of
`web/src/components/primitives/primitives.css`.

**Out:** any change to `tokens.css` values; the assistant surface
(`AgentChat.tsx`, `AssistantTabs.tsx`, `ConversationThread.tsx`),
`AppShell.tsx` and `ProjectsPage.tsx`; the backend and the panel API; any new
dependency; any other page surface; and any conversion of dense data presentation
away from tables (the physiology axis is preserved, not renegotiated).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-product-register`
- Branch: `odd/clientes-product-register`
- Base: `64972a26`
- Files: `odd/tasks/clientes-product-register.md`,
  `openspec/changes/panel-grammar-global/proposal.md`,
  `openspec/changes/panel-grammar-global/tasks.md`,
  `openspec/changes/panel-grammar-global/specs/panel-design-system/spec.md`,
  `web/DESIGN_SYSTEM.md`, `web/src/components/pages/ClientesList.tsx`,
  `web/src/components/pages/ClientFicha.tsx`,
  `web/src/components/pages/ClientesList.test.tsx` (new),
  `web/src/components/pages/ClientFicha.test.tsx`,
  `web/src/stories/pages/ClientesList.stories.tsx` (+ its test),
  `web/src/stories/pages/ClientFicha.stories.tsx` (+ its test),
  promoted pieces under `web/src/components/shared/`, and the Clientes section of
  `web/src/components/primitives/primitives.css`.

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml` (`testing.strict_tdd: true`).
  The configured runner is pytest; this is a frontend-only change, so the
  applicable runner is Vitest via `cd web && npm run test`. Observe RED before
  each source change; never invent RED evidence.
- **`DS-GRAMMAR-1` as amended by this unit** is the target contract. Until the
  delta lands, the live requirement forbids this work; that is exactly why the
  amendment ships in the same PR.
- **The physiology axis is binding.** Dense pages keep `DataTable`, KPI, `Badge`,
  filter and state primitives as their data layer. Bubbles, composer shell, thread
  rail and inspector are barred from them.
- **`DS-GRAMMAR-2` / `DS-UI-PRIMS`** — styles live in the tokenized stylesheet
  boundary, resolve through `var(--*)`, add no dependency, and contain no
  hard-coded colour. No component may inject `<style>`.
- **`DS-TKN-2`** — any token addition is additive only; every pre-existing
  declaration keeps its exact value.
- **`DS-GRAMMAR-3`** — reuse `Avatar`, `Badge`/`StatusBadge`, `Button`,
  `Textarea`, `DataTable`, `StateMessage`, `EmptyState` where their contracts
  apply.
- UI copy stays neutral Chilean Spanish (`DESIGN_SYSTEM.md:425`); no raw backend
  identifiers reach the surface.
- Artifacts in English. Conventional commits, no AI attribution.
- Work-unit commits on this branch are authorized. Push and PR require explicit
  orchestrator authorization.
- Graph Check (Rapsodia Step 1) runs before each task; record the nodes consulted
  in this file's Progress section.

## Decisions

- **D1 — The single-register decision means two axes, and the spec is amended to
  say so.** Confirmed by the owner: the agent-app appearance applies to the whole
  panel; dense content keeps control-room physiology. This is the 2026-09-04
  decision restored, not a new direction. It requires the `DS-GRAMMAR-1`
  amendment; it does not require converting tables into another presentation.
- **D2 — The amendment ships inside slice 1, not as a standalone spec-only unit.**
  Revised from the initial plan. Evidence: the only live blocker is a single
  requirement (`panel-app` needs no delta), and every archived OpenSpec change in
  this repository pairs its delta with an implementation and an apply/verify
  record. A contract change with no consumer would be abstract ceremony; a
  contract change reviewed together with its first real use is not.
- **D3 — The substrate promotion rule is a constraint, not a preference.** A piece
  moves to `shared/` only when a slice needs it AND a second consumer elsewhere
  can be named here. Production components live in `src/components/` from day one;
  Storybook is a viewer, not staging (2026-09-14 correction).
- **D4 — The two real defects are fixed in slice 1, not deferred.** The
  search-clear bug and the singular count are observable wrong behaviour on this
  surface; a redesign that leaves them is cosmetic.
- **D5 — `ClientesList` gets a component test before it changes.** Strict TDD has
  nowhere to observe RED today, and the state model (loading, empty,
  filtered-empty, stale, partial-error, fatal-error, denied) is exactly what the
  redesign must not regress.
- **D6 — No `tokens.css` change in slice 1.** If a repeated semantic role is
  proven by two consumers and no existing token carries it, it is added additively
  per `DS-TKN-2`; otherwise the existing roles are reused. The default is reuse.
- **D7 — Delivery is chained, not one PR.** PR 1 carries the amendment plus slice
  1; PR 2 carries slice 2, `stacked-to-main`. The amendment is roughly 60 lines
  across three files and does not change the slice budget materially.

## Tasks

### Slice 1 — contract amendment (ships in PR 1)

- [ ] **T0** — Write `openspec/changes/panel-grammar-global/` (proposal, delta for
  `DS-GRAMMAR-1`, tasks). Done; kept here as the record of the contract change.
- [ ] **T0b** — State the two axes in `web/DESIGN_SYSTEM.md`: the "Direction at a
  glance" row and the "Grammar scope — two axes" subsection. Done.

### Slice 1 — Clientes list (ships in PR 1)

- [x] **T1** — RED first: create `ClientesList.test.tsx` covering the existing
  state model (loading, ready with rows, empty, filtered-empty, stale,
  partial-error, fatal-error with retry, denied) and the drill-down link. GREEN
  against the unmodified component; this task changes no source (D5). Done:
  9 tests, all passing against the untouched component. The singular count and
  the shared empty/filtered-empty behaviour are deliberately not blessed.
- [x] **T2** — RED/GREEN: clearing the search resets the list. Going from a
  non-empty query back to `""` now triggers a fresh unfiltered fetch (D4). RED
  observed: after clearing, the table kept the single filtered row and
  `Pedro Soto` never returned. Fix: the query drives the fetch through the hook's
  own `refreshKey` instead of the old `useEffect` + `retry()` guard — the effect
  was deleted, so the change is net-negative in code and cannot double-fetch on
  mount.
- [x] **T3** — RED/GREEN: the count is correct in singular and plural (`1
  cliente` / `N clientes`) (D4). Fixed inline, following the existing repo
  convention (`ConversationsList`, `TechnicianAgenda`, `AgentChat` all inline the
  same ternary). No helper was invented for a single call site; the repeated
  pattern is a candidate for the substrate layer once it is touched again.
- [x] **T4** — RED/GREEN: the drill-down link no longer carries an inline style.
  The accessible link treatment is now the shared `.table__link` rule in
  `primitives.css`. Second consumer proven, not assumed: `CasesList.tsx:106` and
  `:148` carried the identical inline style, and `AutomationRulesPage.tsx:24`
  renders the same drill-down link on the UA default colour (`primitives.css` had
  no anchor rule at all). `.btn--tertiary` was rejected for this role: its contract
  is a 40px control and would have grown every dense row, breaking acceptance
  criterion 11.
- [x] **T5** — RED/GREEN: the `Reintentar` control is the `Button` primitive
  (`variant="secondary"`). `grep -c "<button" ClientesList.tsx` → 0.
- [x] **T6** — RED/GREEN: search and export moved into a region-bound `.toolbar`
  inside the content, replacing the page-header action cluster. No new class was
  invented: `.toolbar` was added to the existing selector group that already
  carries `.ai-agent-grammar__filters` and `.conversations-queue__toolbar`, so the
  contract is shared with two proven consumers from the start.
- [x] **T7** — RED/GREEN: filtered-empty is distinguishable from empty and offers
  recovery. The state is derived from the applied query, checked before the empty
  branch, and the recovery clears both the query and the scroll of results. The
  reset remounts the search control (keyed), because `SearchInput` owns its own
  text and cannot be cleared programmatically — see the open item.
- [x] **T8** — RED/GREEN: the appearance axis landed as a named region
  (`role="region"` "Listado de clientes") wrapping the toolbar and the data
  surface, plus the shared `.data-region` surface for the table (border, radius,
  elevation, no padding). `.empty-state` was deliberately left outside that
  surface: it is already a bordered elevated block and nesting would be
  card-on-card, which `DESIGN_SYSTEM.md` forbids. This is the acceptance evidence
  for the amended `DS-GRAMMAR-1`, and it is asserted twice: the region and surface
  compose, and no conversation component appears on the dense surface.
- [x] **T9** — stories: added `Denied` and `FilteredEmpty` (the latter needed the
  new controlled `query` prop, because the state depends on the search round-trip
  and cannot be expressed with `data`/`state` alone — the same pattern
  `CasesList`, `TechnicianAgenda` and `Settings` already use). Story test extended
  with the two story cases and three appearance-axis assertions. Viewport
  presets (640/1024/1280) are global Storybook configuration per `DS-STORY-7`, so
  they are not duplicated per story.

### Slice 2 — ClientFicha (ships in PR 2)

- [ ] **T10** — RED/GREEN: the four raw `<button>`s become `Button`, the raw
  `<select>` becomes `Select`, the raw `<textarea>` becomes `Textarea`
  (`DS-GRAMMAR-3`).
- [ ] **T11** — RED/GREEN: the `customer_memo` badge no longer exposes a backend
  identifier; the memo region carries a user-facing label.
- [ ] **T12** — RED/GREEN: the identity region renders a label/value structure
  instead of six bare `<p>` elements.
- [ ] **T13** — RED/GREEN: save feedback appears at the locus of the action that
  caused it, not in the `PageFrame` state slot; one save action per independently
  persisted group.
- [ ] **T14** — RED/GREEN: the `Historial` card is decomposed into named regions;
  visits render as a real list, and dates render through the Chilean locale
  instead of a raw `slice(0, 16)` of an ISO string.
- [ ] **T15** — RED/GREEN: the appearance axis reaches the ficha chrome as in T8;
  the data layer stays control-room and no conversation component appears.
- [ ] **T16** — stories: `ClientFicha.stories.tsx` covers the state matrix,
  including calendar-sync failure and retry.
- [ ] **T17** — resolve the ficha layout question (single column of grouped
  sections vs a two-region detail layout with a summary rail) before changing the
  page skeleton, and record the choice in this file.

## Acceptance criteria

1. No raw `<button>`, `<select>` or `<textarea>` remains on either Clientes
   surface; the panel's primitives are used (`DS-GRAMMAR-3`).
2. No bubble, composer shell, thread rail or inspector is rendered on either
   Clientes surface, and the data presentation stays tabular (amended
   `DS-GRAMMAR-1`, physiology axis).
3. The appearance axis is verifiable: the Clientes chrome resolves through the
   same tokens and shared appearance contracts as the conversation surfaces, with
   no element left on browser-default control styling (amended `DS-GRAMMAR-1`).
4. No inline `style={{}}` visual decision remains in the shared pieces this pilot
   touches.
5. No raw backend identifier is rendered in the product UI.
6. The search-clear bug and the singular count are fixed with tests that fail
   before the fix.
7. Filtered-empty is distinguishable from empty and offers recovery.
8. No hard-coded colour value is introduced; no new dependency is added; every
   pre-existing token keeps its exact value (`DS-TKN-2`).
9. Only the authorized files change.
10. `cd web && npm run test`, `cd web && npx tsc -b --noEmit` and
    `cd web && npm run build` pass.
11. Rows-per-screen on the Clientes table does not regress against base
    `64972a26`.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `cd web && npm run build-storybook` (after the stories in T9/T16)
- density comparison against base `64972a26` at 1366×768
- `git status --short` / `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create clientes-product-register`),
  provisioned, and `npm ci` completed in `web/`.
- [x] Baseline established on the untouched worktree:
  `cd web && npm run test` → **79 files, 625 tests, all passing**, 54.47s.
- [x] Contract drift verified against the 2026-09-04 decision, the
  `panel-ai-agent-grammar` proposal, and the live specs; `panel-app` confirmed to
  need no delta.
- [x] Amendment written: `openspec/changes/panel-grammar-global/` (proposal,
  `DS-GRAMMAR-1` delta, tasks) and the two-axis clause in `web/DESIGN_SYSTEM.md`.
- [x] Graph Check (Step 1) for the Clientes area: `graphify query "ClientesList
  ClientFicha DataTable StateMessage clientes page components"`. Nodes consulted:
  `ClientesList()` (`pages/ClientesList.tsx:61`), `DataTable()`
  (`shared/DataTable.tsx:32`), `ClientFicha()` (`pages/ClientFicha.tsx:40`),
  `PageFrame()`, `StateMessage()`, `ClientMemories.tsx`, `useAsyncData()`,
  `shared/toneMaps.ts`, `apiFetch()`. Communities: `ClientFicha.tsx`,
  `Settings.tsx`, `AutomationRulesPage.tsx`, `useAsyncData`. Signal: `DataTable`,
  `PageFrame` and `StateMessage` sit in communities driven by other pages
  (`Settings`, `AutomationRulesPage`), which is graph-level support for promoting
  them as shared pieces with real second consumers.
- [x] T1 — `ClientesList.test.tsx` created with 9 tests covering the state model,
  the drill-down link, the export controls and the uncontrolled mount fetch.
  Verified GREEN against the untouched component: `npx vitest run
  src/components/pages/ClientesList.test.tsx` → 9/9 passing; `npx tsc -b --noEmit`
  → exit 0.
- [x] T2 — RED/GREEN: clearing the search resets the list. RED observed (the table
  kept the filtered row), then GREEN via the hook's `refreshKey`. Commit
  `81ab2c32`.
- [x] T3 — RED/GREEN: singular count. RED observed (`1 clientes`), then GREEN.
  Commit `7c9fb607`.
- [x] T4 — RED/GREEN: the `.table__link` shared contract replaces the inline style.
  RED observed (no class, inline `style` attribute present), then GREEN. Commit
  `9d839dd5`.
- [x] T5 — RED/GREEN: the `Button` primitive for the recovery control. RED observed
  (control had no `.btn` class), then GREEN; `grep -c "<button"` → 0. Commit
  `d79e27ff`.
- [x] Full suite after T2–T5, including the shared stylesheet change:
  `cd web && npm run test` → **80 files, 638 tests, all passing**, 57.67s. Baseline
  was 79 files / 625 tests; the delta is `ClientesList.test.tsx`. No other page
  regressed from the new `.table__link` rule.
- [x] T6 — RED/GREEN: `.toolbar` generalised from the existing selector group;
  RED observed (no `.toolbar` node), then GREEN. Commit `90472b85`.
- [x] T7 — RED/GREEN: filtered-empty + recovery. RED observed (`Sin resultados`
  absent), then GREEN, including the assertion that the field is actually cleared.
  Commit `cbdf31c9`.
- [x] T8 — RED/GREEN: named region + `.data-region`. RED observed (no region
  role), then GREEN. Commit `e1dafbeb`.
- [x] T9 — RED/GREEN: controlled `query` prop + `Denied`/`FilteredEmpty` stories +
  story assertions. RED observed (`Sin resultados` absent for the controlled
  query), then GREEN. Commit `8c04c4b2`.
- [x] Slice 1 verification of record: `cd web && npm run test` → **80 files, 648
  tests, all passing**; `npx tsc -b --noEmit` → exit 0; `npm run build` → exit 0
  (pre-existing >500 kB chunk warning unchanged); `npm run build-storybook` →
  exit 0, preview built in 15s.
- [x] Slice 1 complete (T0–T9).
- [ ] Slice 2.

## Size

`64972a26..HEAD` under `web/`: **422 changed lines** (396 added, 26 deleted).
Breakdown: `ClientesList.test.tsx` 253 (a test file that did not exist before this
unit), `ClientesList.tsx` 64, `primitives.css` 25, `DESIGN_SYSTEM.md` 22, stories
58. Production is roughly 111 lines; the rest is tests and stories. Non-`web/`
artifacts add 519 lines (`odd/tasks/clientes-product-register.md` 365, the
`panel-grammar-global` change 154).

422 is marginally over the ~400 review-focus budget, and the total including the
planning and spec artifacts is well over it. The dominant term is the new test
file, which pays existing coverage debt rather than adding behaviour. Splitting
the amendment out of PR 1 was already considered and rejected in D2; splitting the
test file from the code it covers would defeat strict TDD. The maintainer decides
whether to accept the size or slice PR 1 differently.

## Open item

- **`SearchInput` cannot be cleared programmatically.** The primitive owns its own
  text and exposes only a debounced `onSearch`, so the filtered-empty recovery has
  to remount it with a `key`. The honest fix is an optional controlled `value` on
  the primitive, which would also serve `ConversationsList` and `KbList`. Not done
  here: it changes a primitive shared by surfaces this unit is not authorized to
  touch.
- **`.data-region` has one consumer.** `DS-GRAMMAR-2` forces every style into the
  shared stylesheet, so it lives in `primitives.css`; but `D3` says a piece is not
  substrate until a second consumer is named. It is therefore marked in the CSS
  comment as unproven for generalisation. Candidates to name it against:
  `AgendaPage` and `AutomationRulesPage` tables.
- **Ficha layout (T17).** The ficha today is five stacked blocks, one of which
  (`Historial`) carries four unrelated regions. Whether it becomes a single column
  of grouped sections or a two-region layout with a summary rail is a product
  decision, unresolved at the session close and deferred to the start of slice 2.
- **Density (acceptance 11) is argued structurally, not measured.** The additions
  are a border, radius, elevation and a moved toolbar; no padding, height or font
  change was introduced on rows or cells, so rows-per-screen cannot regress. The
  visual confirmation at 1366×768 is the owner's, and it is the gate before slice 2.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-product-register`,
  branch `odd/clientes-product-register`, base `64972a26`.
- Dev server for this worktree: `cd web && npm run dev -- --host 127.0.0.1 --port
  5176` with `VITE_API_TARGET` pointed at the running API. (`5174` and `5175` are
  taken by other worktrees.)
- Archive the OpenSpec change after PR 1 merges, syncing the delta into
  `openspec/specs/panel-design-system/spec.md`.
- On resume: read this file and reconcile the checkbox state against `git log`
  before continuing. `main` moved during this session — the `tukulpan-memory`
  slices (PRs #321, #322, #324) merged into `64972a26`, which is this unit's base;
  rebase only if `main` moves again.
- Session of record:
  `.rapsodia-code/sessions/archived/2026-09-23-frontend-design-foundation/`
  (`session.md` + `report.md`).
