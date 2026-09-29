# ODD: clientes-historial-collapsible

## Objective

Make the customer ficha's `Historial` section a native disclosure so the four history
sub-regions (Visitas, Conversaciones, Casos anteriores, Mensajes) sit behind one
collapsible control, **closed by default**, instead of rendering as the longest
unconditionally-expanded block on the page.

This is **slice B3** of the Clientes visual-refinement thread (Unit B), following the
already-merged B1 (`clientes-surface-refinement`, PR #427, merge `e0c1a219`) and B2
(`clientes-memo-fusion`, PR #429, merge `76eefbb4`). Both are delivered; neither is
reopened here.

## Problem

Verified against base `c0c78ebe` (= current `origin/main`; PR #431 landed after the
handoff was written).

### The history block is unconditionally expanded

`web/src/components/pages/ClientFicha.tsx` is 556 lines. Inside
`<div className="detail-region__main">` (`:430`), the `Historial` surface is:

- `:501` `<section aria-label="Historial">`
- `:502` `<h2>Historial</h2>`
- `:503-527` Visitas — `<section aria-labelledby="ficha-visits-heading" className="client-ficha__history-block">`
- `:529-534` Conversaciones — same shape, `ficha-conversations-heading`
- `:536-541` Casos anteriores — `ficha-cases-heading`
- `:543-550` Mensajes — `ficha-messages-heading`
- `:551` the section closes

The four sub-regions share `.client-ficha__history-block` (`primitives.css:422-431`:
`display: grid; gap: var(--space-3); margin-top: var(--space-4)`, plus an `h3` rule).
They are reused exactly as they are; nothing inside them is rebuilt.

All three `DataTable`s in the ficha live inside those four sub-regions, so the history
is what makes the ficha's main column a wall of tables on first paint.

### `CollapsibleMessages` is not the substrate for this

`web/src/components/shared/CollapsibleMessages.tsx` exists and is consumed by both
`ClientFicha.tsx:546` and `ConversationThread.tsx:101`, but its contract is
message-specific: it renders `children` unchanged when `total <= previewCount`
(default 10) and otherwise appends a `Button` reading `Ver todos (${total})` /
`Ver menos`. In the ficha it is wired to `messagesExpanded` (`:81`) and
`toggleMessages` (`:314`), which **refetches with a different `messages_limit`**
(`:116`). Applying it to the `Historial` section would be a semantic mismatch and
would drag a network round-trip into a pure presentation change. It is left alone.

### The house pattern for a plain disclosure is native `<details>`

Four real consumers already exist, so this is not a new idea:

- `web/src/components/pages/ConversationThread.tsx:51` — `<details open><summary>Datos capturados</summary>…`
- `web/src/components/pages/Settings.tsx:164` — `<details><summary>Sintaxis avanzada · categoría=mode</summary>…`
- `web/src/components/pages/AgentChat.tsx:222` — `<details className="assistant-chat__activity">`
- `web/src/components/pages/KbDocumentDetail.tsx:135` — `<details onToggle={…}><summary className="disclosure__summary">`

`DESIGN_SYSTEM.md:495` states the preference directly: *"Prefer native disclosure
(`details`) for optional inline editing when interruption is unnecessary."* The other
disclosure family in the repo is a controlled button carrying `aria-expanded`
(`PanelShell.tsx:341`, `:385`, `:406`, `:413`) — the right shape only when JS state is
actually needed. `<details>` gets open/closed, keyboard and assistive-technology
semantics from the platform for free.

`.disclosure__summary` (`primitives.css:339-345`) is **not** reused: it sets
`list-style: none` and hides the `::-webkit-details-marker`, because its single
consumer (`KbDocumentDetail`) supplies its own visible control. Here the native
marker IS the affordance, so it must stay visible.

## Scope

**In:** `web/src/components/pages/ClientFicha.tsx` (the `Historial` surface only),
`web/src/components/primitives/primitives.css` (the new disclosure rules only),
`web/src/components/pages/ClientFicha.test.tsx` (the new disclosure tests), and this
document.

**Out:** everything inside the four sub-regions; `CollapsibleMessages.tsx` and its
test; the messages-expansion state, handlers and `messages_limit` refetch;
`ConversationThread.tsx`; `Settings.tsx`; `AgentChat.tsx`; `KbDocumentDetail.tsx`;
`tokens.css`; `web/src/types.ts`; `web/src/api.ts`; the whole backend and panel API;
Storybook stories; B4 (the list's Cliente resource cell); the four remaining
`DataTable.actions` consumers; client KPIs; any new dependency.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-historial-collapsible`
- Branch: `odd/clientes-historial-collapsible`
- Base: `c0c78ebe` (= `origin/main` at branch time; the handoff's `76eefbb4` was
  already superseded by PR #431, which touches none of this slice's files)
- Files: as listed under **In** above.

## Constraints

- `strict_tdd: true` (`openspec/config.yaml`). Web runner: `cd web && npm run test`
  (Vitest). RED before GREEN, observed.
- `DS-GRAMMAR-2`: styles live in the tokenized stylesheet boundary
  (`primitives.css`); no component-owned `<style>`, no inline `style={{}}`, no
  hard-coded colour.
- `Button.test.tsx` asserts `primitives.css` is hex-free, and that every `var()`
  inside a `.btn--*` rule resolves to a declared custom property. **A referenced
  custom property that does not exist is invalid at computed-value time and the
  declaration drops silently** — this shipped once in B1 with every test green.
- No new token and no new dependency.
- Reuse what already exists: the four `.client-ficha__history-block` regions, the
  `Historial` heading, `detail-region__main`.
- `DESIGN_SYSTEM.md:365`: "The ficha groups identity, consent, state control, notes,
  and history." Collapsing history does not remove the group; it changes how it is
  revealed.
- Authority order (`DESIGN_SYSTEM.md:31-37`): OpenSpec requirements > `tokens.css` >
  `DESIGN_SYSTEM.md` > Storybook > the Jinja panel.
- Code and identifiers in English; user-facing copy in approved Chilean Spanish.
- Review freeze: any tracked byte changed after `review start` invalidates the
  receipt, this document included. **Receipts go in the PR body, never in this
  document**, and after the review there must be no docs-only commit.

## Decisions

- **D1 — The history is collapsed by default.** Owner decision, 2026-09-29, taken
  explicitly before any source change. The slice's purpose is that the ficha stops
  being a wall of tables on first paint; a disclosure that starts open delivers no
  visible change and would make B3 a no-op. Progressive disclosure of the deep-dive
  history is the correct pattern for a detail page whose primary surfaces are the
  rail, the active case, memories and notes.
- **D2 — Native `<details>`/`<summary>`, not a controlled button and not
  `CollapsibleMessages`.** Rationale in *Problem*. The platform owns open/closed,
  keyboard activation and the AT semantics, which is both less code and more
  correct than a hand-rolled equivalent. No new component is extracted: on-demand
  substrate extraction is this repository's rule (D3 of `clientes-product-register`),
  and no second consumer shares these semantics.
- **D3 — The `<h2>Historial</h2>` heading moves inside `<summary>`.** This keeps the
  document outline intact — the ficha's history stays a level-2 heading — and gives
  the `<details>` group its accessible name from its own summary. The existing
  `aria-label="Historial"` section wrapper is replaced by the `<details>` rather than
  nested inside it, because nesting would produce a landmark wrapping a single group
  with the same name and no added navigation value. No test asserts the `Historial`
  region role (verified by grep across `web/src` and `web/playwright`).
- **D4 — The native marker stays visible.** `.disclosure__summary` is deliberately not
  reused (it hides the marker). The disclosure triangle is the affordance; hiding it
  would leave a bare heading with no indication it is interactive.
- **D5 — Only the heading needs styling.** The `<details>` is a block and the four
  sub-regions keep their own `margin-top: var(--space-4)` rhythm, so the disclosure
  itself needs no box rules. What does need a rule is the `<h2>` inside `<summary>`:
  it currently relies on user-agent margins, which would make the summary row
  unnecessarily tall. No colour, no var(), no token.
- **D6 — The suite cannot prove the content is hidden, and the tests do not pretend
  to.** Empirically probed on this exact stack (jsdom 25, `vitest` 3,
  `@testing-library/react` 16, throwaway test, deleted after): a `region`, a `heading`
  and a `table` inside a **closed** `<details>` are all still returned by `getByRole`,
  because jsdom does not apply the UA stylesheet rule
  `details:not([open]) > :not(summary) { display: none }`. The consequence is recorded
  honestly rather than papered over:
  1. The pre-existing role assertions (`ClientFicha.test.tsx:135-139`, `:149`,
     `:533-536`; `ClientFicha.stories.test.tsx:97`, `:100`) stay green in **either**
     state, so they are **not** a regression guard for the disclosure, and they are
     therefore **not modified** — they keep asserting what they always asserted, that
     the four history surfaces exist.
  2. The new tests assert the **mechanism** (`details.open === false` on first render;
     `true` after the summary is activated), which is the maximum this environment can
     observe. They must not assert visibility, because a passing visibility assertion
     here would be a false negative.
  3. The real hiding is guaranteed by the **browser platform**, not by this suite.
     That is a further argument for D2: we are relying on semantics the platform owns
     and we cannot test, rather than on a bespoke class we would also be unable to
     test.
- **D7 — B4 and the remaining slices stay out.** The list's Cliente resource cell, the
  four `DataTable.actions` consumers and client KPIs are untouched so this review stays
  focused.

## Graph check (Step 1)

The fresh worktree arrived with a **stale** graph: `GRAPH_REPORT.md` read
`Built from commit: 76eefbb4` while the worktree HEAD is `c0c78ebe`. Fixed with one
`graphify . --update` followed by `graphify cluster-only .`; `GRAPH_REPORT.md` now
reads `c0c78ebe`. Resulting graph: **8580 nodes, 18427 edges, 747 communities**.

Nodes and edges consulted for this slice:

- `ClientFicha()` — `web/src/components/pages/ClientFicha.tsx:79`, community
  `ClientFicha.tsx`. Its community also contains `ClientFicha.test.tsx`,
  `ClientFicha.stories.tsx` (+ test), the `toneMaps.ts` label/tone helpers and the
  `api.ts` client mutations, which is why the test file is treated as part of this
  slice.
- `CollapsibleMessages()` / `CollapsibleMessagesProps` / `CollapsibleMessages.test.tsx`
  — `web/src/components/shared/CollapsibleMessages.tsx`, community
  `TechnicianAgenda.tsx`. Confirms it is shared substrate, not ficha-local, and that
  changing it would reach `ConversationThread` — the reason D2 leaves it alone.
- Edges used: `ClientFicha` → `CollapsibleMessages` → `DataTable`;
  `ClientFicha` → `detail-region__main` → `.client-ficha__history-block` →
  `DataTable` / `Badge` / `EmptyState` / `StateMessage` / `Button`.
- `DESIGN_SYSTEM.md` node "Dialog and disclosure" (community
  `PageFrame/PageHeader shared header`), read at source `:493-498`.
- `.disclosure__summary` (`primitives.css:339`) and `.assistant-chat__activity summary`
  (`primitives.css:1866`) — the two existing `<summary>` styling precedents.
- No Graphify refresh is run during implementation; the next refresh is at session
  close.

## Tasks

Route declaration (ODD "Route declaration" rule): **T1-T3 are delegated to one bounded
writer** — three files, two of them non-trivial, and the writer is given every piece of
evidence below so its work is mechanical. **T4 is inline** (the orchestrator owns this
document). **T5 verification is delegated to the same writer** under the RDD-on gate,
whose report is the verification of record, followed by a parent spot check.

- [x] **T1 — RED.** In `ClientFicha.test.tsx`, add the disclosure tests **before**
  touching the component, and observe them fail against the unmodified ficha:
  - the `Historial` surface is a `<details>` carrying the history class, and its
    `open` property is `false` on first render;
  - the `Historial` heading is still exposed as a heading while the disclosure is
    closed (it lives in the `<summary>`);
  - activating the summary sets `open` to `true`.
  Add a short comment stating **why** the test asserts `open` and not visibility
  (D6), so the next reader does not "fix" it into a false negative.
- [x] **T2 — GREEN.** In `ClientFicha.tsx`, replace the
  `<section aria-label="Historial">` + `<h2>Historial</h2>` opening with
  `<details className="…history…">` + `<summary>` carrying the `<h2>`, keep the four
  `.client-ficha__history-block` sub-regions byte-identical, and close with
  `</details>` instead of `</section>`.
- [x] **T3 — GREEN.** In `primitives.css`, next to `.client-ficha__history-block`, add
  the two disclosure rules per D5 (summary cursor; the `<h2>` inside the summary has
  its user-agent margin dropped and flows inline with the marker). No colour, no
  token, no `var()`, no hex.
- [x] **T4 —** Keep this document current: Progress, Size, and any decision that
  changed. Finalise it **before** `review start`.
- [x] **T5 — verification of record.** Run the Commands below in the foreground and
  report `<command>: <observed result>` for each.

## Acceptance criteria

1. The ficha's `Historial` surface is a native `<details>` and its `open` property is
   `false` on first render.
2. The `Historial` heading is still a level-2 heading and is still exposed while the
   disclosure is closed.
3. Activating the summary opens the disclosure.
4. The four history sub-regions — Visitas, Conversaciones, Casos anteriores, Mensajes
   — are unchanged in content, class and heading, and the three `DataTable`s still
   render.
5. `CollapsibleMessages` is unchanged, and the messages `Ver todos (N)` control with
   its `messages_limit` refetch behaves exactly as before.
6. No inline `style={{}}`, no component-owned `<style>`, no hard value, no new token,
   no new dependency; `tokens.css` is unchanged and `primitives.css` stays hex-free.
7. Only the authorized files change.
8. The pre-existing assertions that the history surfaces exist are **not deleted and
   not weakened** (D6.1).
9. No other page's disclosure changes: `ConversationThread`, `Settings`, `AgentChat`
   and `KbDocumentDetail` keep their current behaviour.

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
  `rapso worktree create clientes-historial-collapsible --yes` from `main` at
  `c0c78ebe`.
- [x] Graph check (Step 1) passed: stale graph detected on arrival, refreshed with one
  `graphify . --update` + `graphify cluster-only .`; `GRAPH_REPORT.md` now reads
  `c0c78ebe`.
- [x] Stale-graph trap confirmed as documented in the handoff (trap 3): the fresh
  worktree's report read `76eefbb4` while HEAD was `c0c78ebe`.
- [x] **D1 decided by the owner before any source change**, on an explicitly stated
  cost. **The cost stated to the owner was wrong and is corrected here**: it was
  presented as requiring nine existing assertions to be rewritten. The jsdom probe
  (D6) proves otherwise — those assertions are insensitive to disclosure state and
  none of them is modified. The decision itself is unaffected: it was taken on product
  merit, and collapsed is now strictly cheaper than stated, not more expensive.
- [x] Created this ODD record in the unit worktree before the first source change.
- [x] **T1 RED observed.** Both new tests failed against the unmodified ficha:
  `collapses the history behind a native disclosure that starts closed` —
  `AssertionError: expected null not to be null` (the `.client-ficha__history` selector
  returned `null`); `opens the history disclosure when the operator activates its
  summary` — `TypeError: Cannot read properties of null (reading 'open')`. Run result:
  `2 failed | 38 skipped`, 1 failed test file.
- [x] **T2/T3 GREEN.** `59d3ded3` (tests) and `78faf204` (component + stylesheet). The
  four `.client-ficha__history-block` occurrences are intact and **not re-indented**:
  the `<details>` sits at the old `<section>`'s indentation and the `<summary>` at the
  old `<h2>`'s, so the sub-regions keep 12 spaces and the diff stays at 8 changed lines
  in `ClientFicha.tsx`.
- [x] **T5 — writer's verification of record.** `npx tsc -b --noEmit`: exit 0, no
  output. `npm run build`: exit 0 (existing chunk-size warning). `npm run
  build-storybook`: exit 0 (existing `eval` and chunk-size warnings). `git diff
  --check`: exit 0. The writer reported the bounded full-suite run as **`partial`**: it
  exceeded its own 120 s command timeout before Vitest printed totals, so it declined to
  claim a pass. That is the correct call.
- [x] **Parent resolution of the `partial`, and the parent spot check.** Re-ran the
  heaviest required command on the frozen candidate with a long timeout:
  `cd web && npm run test -- --maxWorkers=2` → **90 files passed, 861 tests passed,
  exit 0**, duration 171.76 s. The count reconciles exactly: the handoff's 858 was
  measured at `76eefbb4`, PR #431 added 1 test on top of it (859 at this slice's base
  `c0c78ebe`), and this slice adds 2 → 861. No flake was observed on this run.
- [x] Scope confirmed on the frozen candidate: `git diff --name-only c0c78ebe` lists
  exactly the four authorized files; `git status --short` is empty; `git diff --check`
  exits 0; `grep -c 'client-ficha__history-block'` on the component returns 4.
- [x] Pre-existing history assertions (`ClientFicha.test.tsx:135-139`, `:149`,
  `:533-536`; `ClientFicha.stories.test.tsx:97`, `:100`) are **untouched** and pass, as
  D6.1 predicts: they are insensitive to the disclosure state.
- [ ] RDD gate, then push and PR (owner-gated).

## Size

Measured, `git diff --stat c0c78ebe` over the source files only: **48 authored changed
lines** — `ClientFicha.tsx` 8 (4 insertions, 4 deletions), `primitives.css` 12
insertions, `ClientFicha.test.tsx` 28 insertions. Far inside the ~400 review-focus
budget. This document is committed separately (`ad4bb73b`) and must be final before
`review start`; the receipt belongs in the PR body, never here.

## Deferred and follow-ups

- **B4 — the list's Cliente resource cell.** `ClientesList.tsx` renders the name as
  `<a className="table__link">` with the phone in a separate `Teléfono` column;
  `DESIGN_SYSTEM.md:364` makes the customer name the drill-down link, so it becomes a
  resource cell (avatar/initials + semibold name, phone muted underneath) and the
  separate column goes away. Verify line numbers before writing; they moved in B1.
- **The four remaining `DataTable.actions` consumers**, one slice each:
  `ClientMemories.tsx`, `UserManagement.tsx`, `AgendaPage.tsx`, `PlanningSessions.tsx`.
  Extract `RowActions` from `Menu` when the second one lands.
- **Client KPIs** — explicitly not design work. `DESIGN_SYSTEM.md:359` forbids metrics
  until the backend defines and verifies their formulas, and
  `GET /panel/api/clients` is capped at 100 rows, so any client-side KPI would lie past
  100 customers.
- **Carried from the handoff, untouched here:** R3-001 (the `ClientMemories` empty-state
  contradiction, `odd/tasks/r3-001.md` already exists); the unconsumed `memo` API
  projection and its per-load `memory_by_key` query; the unbounded vitest pool
  (`web/vite.config.ts` sets no `testTimeout` and no `maxWorkers`, which is why the
  handoff's bounded-pool workaround is used below); the `--danger-700` fill treatment.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-historial-collapsible`,
  branch `odd/clientes-historial-collapsible`, base `c0c78ebe`.
- On resume: read this file and reconcile the checkbox state against `git log` before
  continuing.
- The four disclosure implementation sites and the reason `CollapsibleMessages` is
  excluded are both in *Problem*; do not re-derive them.
- The jsdom finding in D6 is durable and was saved to Engram as
  `testing/jsdom-details-a11y`; do not re-probe it.
- Sibling slices: B1 `odd/tasks/clientes-surface-refinement.md` (PR #427),
  B2 `odd/tasks/clientes-memo-fusion.md` (PR #429). Both merged; neither is reopened.
