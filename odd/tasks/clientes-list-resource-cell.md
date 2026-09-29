# ODD: clientes-list-resource-cell

## Objective

Turn the `Cliente` cell of the Clientes list into a **resource cell** — `Avatar`
initials plus the customer name as the drill-down link, with the phone muted
underneath — and remove the separate `Teléfono` column, so the name stops being a bare
link floating beside a detached phone number.

This is **slice B4** of the Clientes visual-refinement thread (Unit B), following the
merged B1 (`clientes-surface-refinement`, PR #427), B2 (`clientes-memo-fusion`, PR #429)
and B3 (`clientes-historial-collapsible`, PR #432). None is reopened here.

## Problem

Verified against base `4644ba99` (= current `origin/main`; PR #433 landed after B3).

### The name and the phone are two unrelated cells

`web/src/components/pages/ClientesList.tsx` is 274 lines. Its column factory `columns()`
starts at `:32`:

- `:33-40` `key: "name"`, `header: "Cliente"` — renders
  `<a className="table__link" href={pathForRoute({ view: "clients", clientId: customer.id })} onClick={…onOpenClient…}>{customer.name ?? "—"}</a>`.
  The name is the drill-down link, which is correct.
- `:41` `key: "archived"`, `header: "Registro"` — `Archivado` badge or `—`
- `:42` `key: "phone"`, `header: "Teléfono"` — `customer.phone_e164 ?? "—"`
- `:43` `key: "state"`, `header: "Estado"` — state badge via `customerStateTone` / `customerStateLabel`
- `:44` `key: "consent"`, `header: "Consentimiento"` — `Sí` / `No`
- `:45` `key: "created"`, `header: "Creado"` — `created_at?.slice(0, 10) ?? "—"`

The name is one column and the phone is another, so the operator reads the identity of the
row in two disconnected places. `.table__link` (`primitives.css:327-329`) only sets
`color: var(--primary-700)` — there is no resource idiom in the table at all.

### `DESIGN_SYSTEM.md:364` is what makes the phone a column

`web/DESIGN_SYSTEM.md:364` states: *"Customer name is the drill-down link; phone, state,
consent, and creation date are supporting columns."* That sentence is the design authority
for the current shape, and this slice deliberately changes it, so it must change with the
code. Leaving it would put the document at odds with the surface — the exact drift this
repository has had to reconcile twice before (`odd/tasks/docs-status-reconciliation.md`
and `-2.md`).

### The house already has this exact pattern

`web/src/components/pages/ConversationsList.tsx:79-86` renders a queue row as `Avatar`
(initials) + `conversations-queue__body` containing `__headline` (a `<strong>` name that is
the open control) and `__meta` (`phone_e164` plus a muted reference). That is the same
visual language, already shipped and already tested:

- `:79` `<Avatar name={name} className="conversations-queue__avatar" />`
- `:1964` `.conversations-queue__avatar { align-self: start; }`
- `:1965` `.conversations-queue__body { display: grid; gap: var(--space-1); min-width: 0; }`
- `:1966` `.conversations-queue__headline { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); min-width: 0; }`
- `:1967-1968` `.conversations-queue__identity` — the button that carries the name and is the click target

`Avatar` (`web/src/components/primitives/Avatar.tsx`) already derives initials from a name
and needs no change: it takes `name`, `src?` and `className?`, and callers size it through a
class (`ConversationsList:79`, `PanelShell:98`, `ClientFicha:349`). It is **not** imported by
`ClientesList.tsx` today.

So this slice applies a proven pattern to a table cell. It does not invent one, and it does
not touch `ConversationsList`.

## Scope

**In:** `web/src/components/pages/ClientesList.tsx` (the `name` and `phone` column entries
only, plus the `Avatar` import), `web/src/components/primitives/primitives.css` (the new
resource-cell rules only), `web/src/components/pages/ClientesList.test.tsx` (the column
assertions for this cell), `web/DESIGN_SYSTEM.md` (line 364 only), and this document.

**Out:** the other four columns; the `Menu` row actions and the `Acciones para …` contract;
the create/archive/state-change dialogs; the search/filter/count toolbar; `DataTable` and
its `Column` type; `Avatar`; `ConversationsList` and `.conversations-queue__*`; the four
standby `DataTable.actions` consumers; the ClientFicha redesign; the backend and panel API;
any new dependency.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-list-resource-cell`
- Branch: `odd/clientes-list-resource-cell`
- Base: `4644ba99` (= `origin/main` at branch time; `main` moved twice during this session —
  `76eefbb4` → `c0c78ebe` via PR #431 → `189d6ba5` via PR #432 → `4644ba99` via PR #433,
  which touched only `AgendaPage.tsx`, `AgendaPage.test.tsx` and its own ODD record)
- Files: as listed under **In** above.

## Constraints

- `strict_tdd: true` (`openspec/config.yaml`). Web runner: `cd web && npm run test`
  (Vitest). RED before GREEN, observed.
- `DS-GRAMMAR-2`: styles live in the tokenized stylesheet boundary (`primitives.css`); no
  component-owned `<style>`, no inline `style={{}}`, no hard-coded colour.
- `Button.test.tsx` asserts `primitives.css` is hex-free, and that every `var()` inside a
  `.btn--*` rule resolves to a declared custom property. **A referenced custom property that
  does not exist drops the declaration silently at computed-value time** — this shipped once
  in B1 with every test green.
- No new token and no new dependency. `Avatar` already exists and needs no change.
- Reuse what already exists: `Avatar`, `.table__link` (the link colour), `.table__*` as the
  table-cell idiom family, `.data-region`, and the `--space-*`, `--text-*`, `--corp-fg-muted`
  tokens already used by the sibling queue row.
- Authority order (`DESIGN_SYSTEM.md:31-37`): OpenSpec requirements > `tokens.css` >
  `DESIGN_SYSTEM.md` > Storybook > the Jinja panel. This slice edits the third level
  deliberately and records it.
- Code and identifiers in English; user-facing copy in approved Chilean Spanish.
- Review freeze: any tracked byte changed after `review start` invalidates the receipt, this
  document included. **Receipts go in the PR body, never in this document**, and after the
  review there must be no docs-only commit.

## Decisions

- **D1 — The cell is a resource cell, and the phone moves into it.** The name stays the
  drill-down link, and the phone becomes a muted second line inside the same cell, so the
  row's identity reads in one place. This is the change `DESIGN_SYSTEM.md:364` describes
  being superseded, and the document is updated in the same commit as the code.
- **D2 — `.table__resource` is a table-family class, not a page class.** The table cell
  idiom family in `primitives.css` is generic (`.table__link`, `.table__stale`,
  `.table__actions`), and the resource cell is a *table* idiom rather than a Clientes
  concern, so it belongs with its siblings in the shared boundary. Naming it
  `.clientes-list__resource` would put a page-scoped name in a shared stylesheet. No
  second consumer is invented and no component is extracted.
- **D3 — No `Avatar` change.** `Avatar` already derives initials and is sized by the caller's
  class, which is how `ConversationsList`, `PanelShell` and the ficha rail all use it. Adding
  a `size` prop now would be speculative: one table consumer does not justify a prop that
  the existing four call sites do not need. Sizing lives in the new rules.
- **D4 — When there is no phone, the second line is omitted, not a dash.** A muted `—`
  underneath a name reads as a broken value rather than an absent one. The cell then shows
  avatar plus name only. The `—` placeholders in the other four columns are untouched, so the
  existing `getAllByText("—")` assertion keeps its meaning.
- **D5 — The row actions are not touched.** `DataTable.actions` renders `Menu` with
  `Acciones para ${name}` as its accessible name, and `ClientesList` is its **first and only**
  consumer. The `RowActions` extraction and the four standby consumers wait for the redesign
  to fix the final row-action idiom, which the new design draws as a kebab in card and row
  headers rather than a table action cell.
- **D6 — The redesign is not pre-empted.** This slice implements the structural change with
  today's tokens. The ficha redesign does not cover the list, and the pattern it uses in its
  own header (monogram + semibold name + muted secondary line) is the same one, so the
  structure is expected to survive; a token pass afterwards is accepted as possible and is
  not a reason to block.

## Graph check (Step 1)

The fresh worktree arrived with a **stale** graph: `GRAPH_REPORT.md` read
`Built from commit: 189d6ba5` while HEAD is `4644ba99`. Fixed with one `graphify . --update`
followed by `graphify cluster-only .`; the report now reads `4644ba99`. Resulting graph:
**8588 nodes, 18432 edges, 762 communities**.

Nodes and edges consulted:

- `columns()` — `web/src/components/pages/ClientesList.tsx:32`, community `ClientFicha.tsx`;
  `ClientesList()` — same file, `:70`. The graph places `columns()`, `ClientesList()` and
  `ClientesList.tsx` in the `ClientFicha.tsx` community, which is why the page, its columns and
  its test are treated as one slice.
- `Avatar` — `web/src/components/primitives/Avatar.tsx`. Existing consumers found by the graph
  and by direct search: `ConversationsList.tsx:79`, `PanelShell.tsx:98`, `ClientFicha.tsx:349`,
  `ConversationThread.tsx:28`/`:35`, `AgentChat.tsx:960`/`:1047`. **`graphify path Avatar
  ClientesList` returns no directed path**, which is the graph confirming that this edge does
  not exist yet — it is exactly the edge this slice adds.
- `Column<T>` — `web/src/components/shared/DataTable.tsx:4`; `DataTable` — same file. Note the
  graph places these in a different community from `ClientesList`, which is why they are out
  of scope: the contract is unchanged, only one `render` is.
- Edges used: `ClientesList` → `columns()` → `DataTable` / `Badge` / `pathForRoute` /
  `Menu`, and `ClientesList` → `useAsyncData` / `api`.
- `.table__link` (`primitives.css:327`), `.table__stale` (`:330`), and the sibling resource
  idiom `.conversations-queue__avatar` / `__body` / `__headline` / `__identity` / `__meta`
  (`:1964-1975`) — the pattern this cell mirrors.
- No Graphify refresh is run during implementation; the next refresh is at session close.

## Tasks

Route declaration (ODD "Route declaration" rule): **T1-T3 are delegated to one bounded
writer** — three files, two of them non-trivial, with every piece of evidence below so its
work is mechanical. **T4 is inline** (the orchestrator owns this document). **T5 verification
is delegated to the same writer** under the RDD-on gate, whose report is the verification of
record, followed by a parent spot check.

- [x] **T1 — RED.** In `ClientesList.test.tsx`, before touching the component, assert the
  resource cell and drop the `Teléfono` column assertion (`:69`). The phone assertion
  (`getByText("+56912345678")`) **stays at table level** — it is the guard that the phone is
  not lost, and it must keep finding exactly one occurrence after the move. Add: the cell
  carries the avatar (initials of the name), the name link still points at the client route,
  and there is no `Teléfono` columnheader. Observe the test fail against the unmodified list.
- [x] **T2 — GREEN.** In `ClientesList.tsx`, make `name` render the resource cell and delete
  the `phone` column entry, importing `Avatar`.
- [x] **T3 — GREEN.** In `primitives.css`, next to the `.table__*` family, add the
  `.table__resource` rules per D2/D3/D4 using existing tokens only. No colour literal, no new
  token, no `var()` that is not declared.
- [x] **T4 —** Update `DESIGN_SYSTEM.md:364` so it no longer lists the phone as a supporting
  column, and keep this document current (Progress, Size). Finalise both **before**
  `review start`.
- [x] **T5 — verification of record.** Run the Commands below in the foreground and report
  `<command>: <observed result>` for each.

## Acceptance criteria

1. The `Cliente` cell renders the customer's `Avatar` initials and the customer name.
2. The name remains the drill-down link: same `pathForRoute({ view: "clients", clientId })`
   target, same `onOpenClient` interception, same accessible role.
3. The phone renders exactly once, as a muted second line inside that cell.
4. There is no `Teléfono` columnheader, and the `phone` column key is gone from `columns()`.
5. When `phone_e164` is null the second line is omitted; the cell shows avatar plus name only.
6. The other four columns — `Registro`, `Estado`, `Consentimiento`, `Creado` — render exactly
   as before, including their `—` placeholders and their badges.
7. The row action menu keeps its accessible name `Acciones para ${name}` and its items.
8. `DESIGN_SYSTEM.md` no longer claims the phone is a supporting column.
9. No inline `style={{}}`, no component-owned `<style>`, no hard value, no new token, no new
   dependency; `tokens.css` unchanged and `primitives.css` hex-free.
10. Only the authorized files change.
11. `Avatar`, `DataTable` and `ConversationsList` are byte-identical to the base.

## Checks

- `cd web && npm run test -- --maxWorkers=2`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `cd web && npm run build-storybook`
- `git diff --check`
- `git status --short`

The backend suite is **not** run: no Python path is in this candidate.

## Progress

- [x] Owner consented per-feature to the worktree on 2026-09-29; created with
  `rapso worktree create clientes-list-resource-cell --yes` from `main`.
- [x] Graph check (Step 1) passed: stale graph detected on arrival, refreshed with one
  `graphify . --update` + `graphify cluster-only .`; `GRAPH_REPORT.md` now reads `4644ba99`.
- [x] Base verified as `4644ba99` and confirmed equal to `origin/main`; PR #433's three paths
  (`AgendaPage.tsx`, `AgendaPage.test.tsx`, its ODD record) have **no** overlap with this
  slice. The consent was given against `189d6ba5`; `main` moved to `4644ba99` before the
  worktree was cut, which is recorded here rather than silently absorbed.
- [x] The house precedent located before any design work: `ConversationsList.tsx:79-86`
  already renders avatar + name + muted meta, so this is an application of a proven pattern.
- [x] Created this ODD record in the unit worktree before the first source change.
- [x] **T1 RED observed.** Focused run failed against the unmodified list with
  `2 failed | 31 passed`: `renders the operational table with the client columns and
  values` — `expected document not to contain element, found <th …>Teléfono</th> instead`
  (`ClientesList.test.tsx:69`); `omits the muted phone line when the customer has no phone`
  — `expected null not to be null` (`.table__resource` absent).
- [x] **T2/T3/T4 GREEN.** `c2dc487d` (tests) and `2d81ff76` (component, stylesheet and the
  `DESIGN_SYSTEM.md:364` line). The `phone` column entry is gone; the `Cliente` cell renders
  `Avatar` + `.table__resource-body` with the link and the muted phone; the four untouched
  columns are unchanged.
- [x] **T5 — writer's verification of record.** `npm run test -- --maxWorkers=2` → 90 files,
  863 tests. `npx tsc -b --noEmit` → exit 0, no output. `npm run build` → exit 0.
  `npm run build-storybook` → exit 0. `git diff --check` → exit 0. `git status --short` →
  empty. The writer reported `completed` and confirmed all four referenced tokens are declared
  in `tokens.css`.
- [x] **Parent re-run and spot check.** Re-ran the heaviest required command on the frozen
  candidate with a long timeout: `cd web && npm run test -- --maxWorkers=2` → **90 files
  passed, 863 tests passed, exit 0**, duration 281.79 s. The count reconciles: 861 at the base
  `4644ba99` plus the 2 tests added here.
- [x] Scope confirmed on the frozen candidate: `git diff --name-only 4644ba99` lists exactly
  the four authorized files plus this record; `Avatar.tsx`, `DataTable.tsx`,
  `ConversationsList.tsx` and `tokens.css` are **byte-identical** to the base (empty
  `git diff --stat` over those paths); `git diff --check` exits 0.
- [x] The phone guard survives the move: `getByText("+56912345678")` at
  `ClientesList.test.tsx:82` requires exactly one occurrence and passes, so the phone is
  proved present exactly once rather than merely assumed.
- [ ] RDD gate, then push and PR (owner-gated).

## Size

Measured, `git diff --numstat 4644ba99 -- web/`: **52 authored changed lines** — 46
insertions, 6 deletions. `ClientesList.tsx` 10/4, `primitives.css` 18/0,
`ClientesList.test.tsx` 17/1, `DESIGN_SYSTEM.md` 1/1. Far inside the ~400 review-focus
budget. This document is committed separately and must be final before `review start`; the
receipt belongs in the PR body, never here.

## Deferred and follow-ups

- **The four standby `DataTable.actions` consumers** — `ClientMemories.tsx`,
  `UserManagement.tsx`, `AgendaPage.tsx`, `PlanningSessions.tsx` — all still render
  `variant="secondary"` buttons with no `Menu`. Put on standby by owner decision on
  2026-09-29 until the new design fixes the final row-action idiom, which the design draws as
  a kebab in card and row headers rather than a table action cell. `RowActions` does not exist
  yet; the only occurrence of the name is a local helper in `ClientesList.test.tsx:55`.
- **The ClientFicha redesign** — an owner-provided design restructures the ficha into tabs
  (Resumen / Casos / Visitas / Conversaciones) plus a rail, with `Historial del cliente` as a
  nav row rather than an inline disclosure. That **supersedes B3's inline `<details>`**, which
  will be removed rather than extended. It needs a spec first: the repository's design
  authority is OpenSpec > `tokens.css` > `DESIGN_SYSTEM.md`, and an image is in none of them.
  Nine primitives are new or need extension (eyebrow-with-dot, count pill, accent-bar list
  row, stacked date chip, nav row, `EmptyState` illustration, `Avatar` sizing, copy affordance,
  plus a Tabs variant); `Tabs.tsx` already exists with the right semantics. It gets its own
  worktree.
- **This slice's own debt from B3**, untouched: `ClientFicha.test.tsx:559` clicks the heading
  rather than the `summary` (R3-001, advisory).
- **B2's R3-001** — `ClientMemories.tsx:89` renders `emptyMessage="Sin memorias todavía"`
  even when the featured memo is the only memory, contradicting it. Note: `odd/tasks/r3-001.md`
  is **not** this debt — it is a merged KB `top_k`/`min_sim` bounds task (PR #264), and the
  filename is ambiguous. This debt has no ODD record yet.
- **The unconsumed `memo` projection** — `app/panel/api/routes/clients.py:274` still runs one
  `memory_service.get_by_key(…)` per ficha load and `:281` returns it; `types.ts:458` declares
  it; nothing in `web/src` reads it. Backend change with its own verification.
- **The unbounded vitest pool** — `web/vite.config.ts` sets neither `testTimeout` nor
  `maxWorkers`, which is why the bounded-pool workaround is used below.
- **The `--danger-700` solid fill treatment** for `.btn--danger` (owner decision, from B1).

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-list-resource-cell`,
  branch `odd/clientes-list-resource-cell`, base `4644ba99`.
- On resume: read this file and reconcile the checkbox state against `git log` before
  continuing.
- The precedent to mirror and the reason the phone is currently a column are both in
  *Problem*; do not re-derive them.
- The jsdom finding that made B3 cheap is durable and is in Engram as
  `testing/jsdom-details-a11y`; it is not needed here.
- Sibling slices: B1 `odd/tasks/clientes-surface-refinement.md` (PR #427),
  B2 `odd/tasks/clientes-memo-fusion.md` (PR #429), B3
  `odd/tasks/clientes-historial-collapsible.md` (PR #432). All merged; none is reopened.
