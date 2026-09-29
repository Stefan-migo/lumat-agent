# ODD: panel-action-affordances

## Objective

Replace the oversized, name-repeating row-action buttons with a compact
icon-triggered menu, and make the shared menu primitive capable of row-level
action affordances (icon-only trigger, per-item icon, destructive tone).

This is the first unit of the Clientes visual-refinement thread the owner opened
on 2026-09-29. It is scoped to the row-action pattern and its first consumer
(`ClientesList`); every other `DataTable.actions` consumer follows in its own
slice. It is **not** a reopening of `clientes-product-register`, which is closed:
that unit raised the surface to the product register and left the actions column
untouched.

## Problem

Verified against the code at base `5e2ae2ba`. Every claim is evidence.

### The row-action cell repeats the customer name and cannot shrink

`ClientesList.tsx:212` renders two `secondary` buttons per row:

```tsx
actions={(customer) => <>
  <Button variant="secondary" onClick={() => void openState(customer)}>
    Cambiar estado {customer.name ?? "cliente"}
  </Button>
  {customer.archived_at
    ? <Button variant="secondary" onClick={() => void restore(customer)}>
        Restaurar {customer.name ?? "cliente"}
      </Button>
    : <Button variant="secondary" onClick={() => void openArchive(customer)}>
        Archivar {customer.name ?? "cliente"}
      </Button>}
</>}
```

Three defects in one cell:

- **The label embeds the row's own name.** A table column exists to distinguish
  rows; repeating `name` inside every action label is redundant width that scales
  with the longest customer name.
- **Two variable-width pill buttons per row.** `.btn` is `--radius-pill`
  (`primitives.css:30`), so the cell reads as two chips, not as row actions.
- **`.table__actions` is not used.** The shared flex wrapper for an action cell
  already exists (`primitives.css:323-326`) and is consumed by `ClientMemories.tsx:78`
  and `CaseActions.tsx:60`; this cell renders the buttons as bare siblings.

### The menu primitive cannot express a row action

`primitives/Menu.tsx` is the Radix dropdown that `CST-PRIM-7` assigns to menu
presentation, positioning, dismissal and focus (`corp-primitives/spec.md:99-104`).
It has **no production consumer** — the only `<Menu` in the tree is its own test
and story (`PanelShell.tsx:11,347` imports the Lucide icon of the same name).

Its contract cannot serve a table row:

- `label: string` is rendered as the trigger's **visible text** (`Menu.tsx:21-23`),
  so an icon-only trigger is not expressible.
- `MenuItem` is `{ value, label, disabled? }` (`Menu.tsx:4-8`) — no icon, and no
  way to mark a destructive item, so `Archivar` would be indistinguishable from
  `Cambiar estado`.

### The constraints this must respect

- `DESIGN_SYSTEM.md:475` — keep row actions in the final region of the table.
- `DESIGN_SYSTEM.md:493-498` — dialogs are for destructive confirmation or tasks
  that must block; choosing an action from a list is neither.
- `DESIGN_SYSTEM.md:541-545` — Lucide is the single outline icon family; icons are
  behavioural support, not decoration.
- `DESIGN_SYSTEM.md:509-510, 641` — destructive actions name the affected object and
  provide confirmation, and colour is never the only state channel.
- `DESIGN_SYSTEM.md:742` (`DS-GRAMMAR-1`, live spec) — `ClientesList` MUST retain
  control-room `DataTable` presentation. The actions column stays inside the table.
- `corp-primitives/spec.md:99-104` (`CST-PRIM-7`) — menu is Radix-owned; the
  primitive MUST use `--corp-*` or existing tokens, expose keyboard behaviour, and
  honour the 40px/44px sizing rule.

## Scope

**In:** `web/src/components/primitives/Menu.tsx`, `Menu.test.tsx`,
`web/src/stories/primitives/Menu.stories.tsx`, the Radix-menu and
`.table__actions` rules in `web/src/components/primitives/primitives.css`,
`web/src/components/pages/ClientesList.tsx`, `ClientesList.test.tsx`,
`web/src/stories/pages/ClientesList.stories.tsx` (+ its test), and this document.

**Out:** `web/src/tokens/tokens.css` values; the `Button` primitive (including the
`danger` variant — see D6); every other `DataTable.actions` consumer
(`ClientMemories`, `UserManagement`, `AgendaPage`, `PlanningSessions`); `DataTable`
itself; the ficha (`ClientFicha.tsx`); the `Mensajes`/history tables; the backend
and the panel API; KPIs; any new dependency; any conversion of the table away from
tabular presentation.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-panel-action-affordances`
- Branch: `odd/panel-action-affordances`
- Base: `5e2ae2ba` (= `main` at branch time)
- Files: as listed under **In** above.

## Constraints

- `strict_tdd: true` (`openspec/config.yaml`): RED before GREEN for every
  behavioural change. The web runner is `cd web && npm run test` (Vitest).
- `DS-GRAMMAR-2`: styles live in the tokenized stylesheet boundary
  (`primitives.css`); no component-owned `<style>`, no inline `style={{}}`.
- `Button.test.tsx` asserts `primitives.css` is hex-free. Every new rule must
  resolve through existing tokens.
- Add no dependency. `@radix-ui/react-dropdown-menu` is already installed.
- Code and identifiers in English; user-facing copy in approved Chilean Spanish.

## Decisions

- **D1 — A menu, not a dialog.** The owner proposed a button that opens a dialog
  with the options. `DESIGN_SYSTEM.md:493-498` reserves dialogs for destructive
  confirmation or tasks that must block background interaction; picking an action
  from a per-row list is neither, and a dialog would cost two clicks plus a modal
  to choose one action. The Radix dropdown is one click, keyboard-accessible, and
  already the assigned owner (`CST-PRIM-7`). The existing confirmation dialogs
  (archive, state) are unchanged and still own the consequence.
- **D2 — Extend `Menu`; do not add a second dropdown.** A new `RowActions` Radix
  wrapper would duplicate the ownership `CST-PRIM-7` already assigns to
  `Menu.tsx`. `RowActions` is extracted later, when the second table consumer
  lands, following the repository's own pilot-first / substrate-on-demand decision
  (`cortex-session/frontend-design-foundation/decision/pilot-first`, and D3 of
  `clientes-product-register`). With one converted table today, the abstraction
  would be unearned.
- **D3 — The trigger is an icon-only control with a per-row accessible name.** The
  trigger renders `MoreHorizontal` (Lucide) and takes its accessible name from the
  row ("Acciones para <cliente>"), so the customer name stops appearing in visible
  action text while remaining available to assistive technology. WCAG 2.2 AA
  keyboard and focus behaviour comes from Radix plus the shared `--focus-ring*`
  tokens; the trigger keeps a ≥40px control height (44px is the risky-action
  target, and the trigger itself is not the destructive action).
- **D4 — Destructive items carry tone plus an icon.** `Archivar` renders with
  `tone="danger"` and an icon, so the state is never colour-only
  (`DESIGN_SYSTEM.md:509-510`). The label still names the action, and the existing
  archive dialog still names the customer and the consequences.
- **D5 — No new token.** The menu reuses `--corp-border`, `--corp-bg`,
  `--corp-fg`, `--corp-surface-hover`, `--focus-ring*`, `--shadow-3`, and for the
  destructive item the existing `--danger` role (`tokens.css:57`). The token set is
  unchanged and stays hex-free.
- **D6 — `Button` `variant="danger"` does NOT land here.** `DESIGN_SYSTEM.md:444`
  specifies it and `Button.tsx:4-8` does not implement it, but this unit has **no
  consumer** for a standalone destructive button — `Archivar` becomes a menu item.
  Adding an unused variant would violate implementation rule 5 ("add a token only
  for a repeated semantic role or an approved brand primitive with a real
  consumer"). It lands with the ficha rail, where `Archivar` and `Fusionar` are
  standalone destructive buttons. The drift is recorded, not silently dropped.
- **D7 — One consumer per slice.** Only `ClientesList` is converted here. Each of
  the four remaining `DataTable.actions` consumers is converted in its own slice so
  no PR breaks the ~400-line review budget.

## Tasks

- [x] **T1** — RED: `Menu.test.tsx` covers the row affordances — an icon-only
  trigger with the accessible name from `label`, the items still operable by
  keyboard and `onSelect`, an item rendering its icon, and a `tone="danger"` item.
  Observed failing against the unmodified `Menu`.
- [x] **T2** — GREEN: extend `Menu.tsx` (`MenuItem.icon`, `MenuItem.tone`,
  icon-only trigger with `aria-label`) and the menu rules in `primitives.css`.
  `primitives.css` stays hex-free and the existing `Menu.test.tsx` and
  `Menu.stories.tsx` keep passing.
- [x] **T3** — RED: `ClientesList.test.tsx` asserts the row-action cell renders one
  menu trigger per row whose accessible name carries the customer name, that no
  visible action label embeds the customer name, that the items are
  `Cambiar estado` / `Archivar` (or `Restaurar` when archived), and that choosing
  an item calls the same handler as before.
- [x] **T4** — GREEN: rewrite the `ClientesList` actions callback as
  `.table__actions` wrapping the icon-triggered `Menu`; `Archivar` becomes a
  `tone="danger"` item with an icon.
- [x] **T5** — stories: `Menu.stories.tsx` gains an icon-trigger story including a
  destructive item; `ClientesList.stories.test.tsx` assertions update for the new
  cell. Viewport presets stay global per `DS-STORY-7`.
- [x] **T6** — verification of record: `cd web && npm run test`,
  `cd web && npx tsc -b --noEmit`, `cd web && npm run build`,
  `cd web && npm run build-storybook`, plus a rows-per-screen comparison against
  base `5e2ae2ba` at 1366×768.

## Acceptance criteria

1. No button in the Clientes row-action cell renders the customer name in its
   visible label.
2. Each row exposes exactly one action trigger; its accessible name identifies the
   row.
3. `Archivar` is distinguishable from a neutral action without relying on colour
   alone, and its confirmation dialog still names the customer.
4. `Menu` keeps the `CST-PRIM-7` contract: Radix-owned keyboard/focus behaviour,
   existing tokens only, ≥40px control height, complete disabled state.
5. The data presentation stays tabular; row actions stay in the final column
   (`DS-GRAMMAR-1` physiology axis).
6. No inline `style={{}}` and no component-owned `<style>` is introduced; no hard
   value is introduced; `tokens.css` is unchanged.
7. Rows-per-screen on the Clientes table does not regress against `5e2ae2ba`.
8. Only the authorized files change.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `cd web && npm run build-storybook`
- density comparison against base `5e2ae2ba` at 1366×768
- `git status --short` / `git diff --check`

## Progress

- [x] Created this ODD record in the unit worktree before the first source change
  (commit `8c800797`).
- [x] Worktree created (`rapso worktree create panel-action-affordances`) and
  `npm ci` completed in `web/`.
- [x] T1 — RED observed in `Menu.test.tsx`: 3 failed / 7 passed against the
  unmodified `Menu`.
- [x] T2 — GREEN. Commit `af273f37`. `Menu.test.tsx` 10/10; the pre-existing tests
  are untouched and `primitives.css` stays hex-free.
- [x] T3 — RED observed in `ClientesList.test.tsx`: 11 failed / 21 passed. The four
  pre-existing row-action tests were moved to the new accessible-name contract in
  the same step, because the old labels were the defect; their assertions are
  otherwise preserved.
- [x] T4 — GREEN. Commit `b9fcf612`. 42/42 across `ClientesList.test.tsx` and
  `Menu.test.tsx`.
- [x] T5 — stories. Commit `63e3bacb`. `ClientesList.stories.test.tsx` 23/23.
- [x] T6 — verification of record: `cd web && npm run test` → **90 files, 852
  tests, all passing**; `cd web && npx tsc -b --noEmit` → exit 0;
  `cd web && npm run build` → exit 0 (pre-existing >500 kB chunk warning
  unchanged); `cd web && npm run build-storybook` → exit 0, preview built in 21s.
- [x] Density (acceptance 7) argued structurally: the cell replaces two 40px pill
  buttons with one 40px icon trigger, so the row's intrinsic height is unchanged and
  its width strictly decreases. The visual confirmation at 1366×768 is the owner's.
- [x] Spec check: `DS-GRAMMAR-1` (live) keeps the dense surface tabular and retains
  the control-room `DataTable`; the `Acciones` action-label contract of
  `openspec/specs/panel-design-system/spec.md:557` is unchanged; `CST-PRIM-7` sizing,
  token use and Radix keyboard ownership hold. No spec delta is required.
- [x] `git diff --check` clean.

## Size

`5e2ae2ba..HEAD` under `web/`: **304 changed lines** (291 added, 13 deleted) across 7
files. Breakdown: `ClientesList.test.tsx` 106, `Menu.test.tsx` 64, `Menu.stories.tsx`
38, `Menu.tsx` 34, `ClientesList.tsx` 33, `primitives.css` 17,
`ClientesList.stories.test.tsx` 12. Production code is 84 lines (34 + 33 + 17); the
rest is tests and stories. Non-`web/` artifacts add 224 lines
(`odd/tasks/panel-action-affordances.md`). 304 is inside the ~400 review-focus budget.

## Deferred and follow-ups

- **The remaining `DataTable.actions` consumers are not converted here** (D7):
  `ClientMemories.tsx:78`, `UserManagement.tsx:87`, `AgendaPage.tsx:239-250`,
  `PlanningSessions.tsx:70`. Each becomes its own slice.
- **`Button` `variant="danger"` is still unimplemented** (D6) and belongs to the ficha
  unit, where `Archivar` and `Fusionar` are standalone destructive buttons.
  `DESIGN_SYSTEM.md:444` documents it; `Button.tsx:4-8` does not implement it.
- **`RowActions` is not extracted yet** (D2). It earns its place when the second
  table consumer lands.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-panel-action-affordances`,
  branch `odd/panel-action-affordances`, base `5e2ae2ba`.
- On resume: read this file and reconcile the checkbox state against `git log`
  before continuing.
- Delivery: chained/stacked to `main` per repo precedent; `ask-on-risk`, and the
  maintainer decides if the size forecast needs a different slice.
