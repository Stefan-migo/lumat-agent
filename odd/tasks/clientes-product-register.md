# ODD: clientes-product-register

## Objective

Raise the Clientes surface (`ClientesList` + `ClientFicha`) to the panel's product
register, and extract on demand the reusable substrate it forces into existence.
This is the pilot for the panel-wide design-debt plan: it must prove the register
and produce the first shared pieces, not merely look better.

## Problem

Verified against the code at base `64972a26`. Every claim is evidence, not
impression.

**The user's report was half right, and the half that was right is this surface.**
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
- `Cliente` has **no page-specific CSS at all**: `primitives.css` contains zero
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

**In:** `web/src/components/pages/ClientesList.tsx`,
`web/src/components/pages/ClientFicha.tsx`, new
`web/src/components/pages/ClientesList.test.tsx`,
`web/src/components/pages/ClientFicha.test.tsx`, the Clientes stories and their
tests, the shared pieces slice 1 and slice 2 promote under
`web/src/components/shared/`, and the Clientes section of
`web/src/components/primitives/primitives.css`.

**Out:** any change to `tokens.css` values; the assistant surface
(`AgentChat.tsx`, `AssistantTabs.tsx`, `ConversationThread.tsx`),
`AppShell.tsx` and `ProjectsPage.tsx`; the backend and the panel API; any new
dependency; any other page surface; `DESIGN_SYSTEM.md` (the addendum is a
separate follow-up).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-product-register`
- Branch: `odd/clientes-product-register`
- Base: `64972a26`
- Files: `odd/tasks/clientes-product-register.md`,
  `web/src/components/pages/ClientesList.tsx`,
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
- **`DS-GRAMMAR-1` binds this surface.** Dense pages `MUST retain control-room
  DataTable, KPI, Badge, filter, and state primitives`. This pilot keeps those
  primitives and improves them; it does not adopt the agent-app grammar here.
  See D1.
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

- **D1 — This pilot does not require an OpenSpec delta.** `DS-GRAMMAR-1` states
  that `ClientesList` and `ClientFicha` `MUST retain control-room DataTable, KPI,
  Badge, filter, and state primitives`, while only the conversation surfaces
  expose the agent-app grammar. The session's decision "one product register"
  is therefore read as *shared composition, hierarchy and affordance quality*,
  not as *adopting the agent grammar on dense pages*. Under that reading this
  change is spec-compliant: it keeps `DataTable`, `Badge`, `StateMessage` and
  `EmptyState`, and raises their composition. If the intent was instead to give
  dense pages the agent grammar, `DS-GRAMMAR-1` must be amended first and this
  unit becomes a spec change.
- **D2 — The substrate promotion rule is a constraint, not a preference.** A
  piece moves to `shared/` only when a slice needs it AND a second consumer
  elsewhere can be named here. Production components live in `src/components/`
  from day one; Storybook is a viewer, not staging (2026-09-14 correction).
- **D3 — The two real defects are fixed in slice 1, not deferred.** The
  search-clear bug and the singular count are observable wrong behaviour on this
  surface; a redesign that leaves them is cosmetic.
- **D4 — `ClientesList` gets a component test before it changes.** Strict TDD has
  nowhere to observe RED today, and the state model (loading, empty,
  filtered-empty, stale, partial-error, fatal-error, denied) is exactly what the
  redesign must not regress.
- **D5 — No `tokens.css` change in slice 1.** If a repeated semantic role is
  proven by two consumers and no existing token carries it, it is added
  additively per `DS-TKN-2`; otherwise the existing roles are reused. The default
  is reuse.
- **D6 — Delivery is chained, not one PR.** The forecast across both slices
  exceeds the 400-line review-focus budget, so slice 1 and slice 2 ship as
  separate PRs, `stacked-to-main`.

## Tasks

### Slice 1 — Clientes list

- [ ] **T1** — RED first: create `ClientesList.test.tsx` covering the existing
  state model (loading, ready with rows, empty, filtered-empty, stale,
  partial-error, fatal-error with retry, denied) and the drill-down link. GREEN
  against the unmodified component; this task changes no source.
- [ ] **T2** — RED/GREEN: clearing the search resets the list. Going from a
  non-empty query back to `""` must trigger a fresh unfiltered fetch (D3).
- [ ] **T3** — RED/GREEN: the count is correct in singular and plural (`1
  cliente` / `N clientes`) (D3).
- [ ] **T4** — RED/GREEN: the drill-down link no longer carries an inline style;
  the accessible link treatment is a shared contract with its second consumer
  named (candidates: `CasesList`, `AutomationRulesPage`) (D2).
- [ ] **T5** — RED/GREEN: the `Reintentar` control is the `Button` primitive, not
  a raw `<button>`. No raw `<button>` remains in `ClientesList`.
- [ ] **T6** — RED/GREEN: search and export move into a region-bound toolbar tied
  to the list it controls, replacing the page-header action cluster. Second
  consumer named before promotion: `ConversationsList`, `KbList`.
- [ ] **T7** — RED/GREEN: filtered-empty is distinguishable from empty, and
  filtered-empty offers the recovery action (clear the search). Second consumer
  named: `ConversationsList`, `KbList`.
- [ ] **T8** — stories: `ClientesList.stories.tsx` covers the register's state
  matrix at the 640/1024/1280 viewports; its test stays green.

### Slice 2 — ClientFicha

- [ ] **T9** — RED/GREEN: the four raw `<button>`s become `Button`, the raw
  `<select>` becomes `Select`, the raw `<textarea>` becomes `Textarea`
  (`DS-GRAMMAR-3`).
- [ ] **T10** — RED/GREEN: the `customer_memo` badge no longer exposes a backend
  identifier; the memo region carries a user-facing label.
- [ ] **T11** — RED/GREEN: the identity region renders a label/value structure
  instead of six bare `<p>` elements.
- [ ] **T12** — RED/GREEN: save feedback appears at the locus of the action that
  caused it, not in the `PageFrame` state slot; one save action per independently
  persisted group.
- [ ] **T13** — RED/GREEN: the `Historial` card is decomposed into named regions;
  visits render as a real list, and dates render through the Chilean locale
  instead of a raw `slice(0, 16)` of an ISO string.
- [ ] **T14** — stories: `ClientFicha.stories.tsx` covers the state matrix,
  including calendar-sync failure and retry.
- [ ] **T15** — resolve the ficha layout question (single column of grouped
  sections vs a two-region detail layout with a summary rail) before changing the
  page skeleton, and record the choice in this file.

## Acceptance criteria

1. No raw `<button>`, `<select>` or `<textarea>` remains on either Clientes
   surface; the panel's primitives are used (`DS-GRAMMAR-3`).
2. No inline `style={{}}` visual decision remains in the shared pieces this pilot
   touches.
3. No raw backend identifier is rendered in the product UI.
4. The search-clear bug and the singular count are fixed with tests that fail
   before the fix.
5. Filtered-empty is distinguishable from empty and offers recovery.
6. No hard-coded colour value is introduced; no new dependency is added; every
   pre-existing token keeps its exact value (`DS-TKN-2`).
7. Only the authorized files change.
8. `cd web && npm run test`, `cd web && npx tsc -b --noEmit` and
   `cd web && npm run build` pass.
9. Rows-per-screen on the Clientes table does not regress against base
   `64972a26`.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `cd web && npm run build-storybook` (after the stories in T8/T14)
- density comparison against base `64972a26` at 1366×768
- `git status --short` / `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create clientes-product-register`),
  provisioned, and `npm ci` completed in `web/`.
- [x] Baseline established on the untouched worktree:
  `cd web && npm run test` → **79 files, 625 tests, all passing**, 54.47s.
- [ ] Slice 1.
- [ ] Slice 2.

## Open item

- **Ficha layout (T15).** The ficha today is five stacked blocks, one of which
  (`Historial`) carries four unrelated regions. Whether it becomes a single column
  of grouped sections or a two-region layout with a summary rail is a product
  decision, unresolved at the session close and deferred to the start of slice 2.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-product-register`,
  branch `odd/clientes-product-register`, base `64972a26`.
- Dev server for this worktree: `cd web && npm run dev -- --host 127.0.0.1 --port
  5176` with `VITE_API_TARGET` pointed at the running API. (`5174` and `5175` are
  taken by other worktrees.)
- On resume: read this file and reconcile the checkbox state against `git log`
  before continuing. `main` moved during this session — the `tukulpan-memory`
  slices (PRs #321, #322, #324) merged into `64972a26`, which is this unit's base;
  rebase only if `main` moves again.
- Session of record:
  `.rapsodia-code/sessions/ready-for-odd/2026-09-23-frontend-design-foundation/`
  (`session.md` + `report.md`).
