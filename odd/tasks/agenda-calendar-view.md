# ODD: agenda-calendar-view

## Objective

Give the operator Agenda a month/week calendar as its navigation surface, keeping the existing
`Hoy` / `Próximas` register tables but resizing them into the new layout. Selecting a day in the
calendar filters the register to that day; with no selection the register keeps its current shape.

The governing contract forbids this today, so the contract is corrected first and the calendar is
built as its first consumer — the pattern this repository already used for `panel-grammar-global`
and `ds-stylesheet-boundary`.

## Problem

Every claim below was verified in this session, not inherited.

**The live spec forbids a month grid.** `openspec/specs/agenda-calendar-ui/spec.md:11` (`AG-UI-1`)
reads: *"…MUST render chronological `Hoy` and `Próximas` sections in the request timezone, and
**MUST NOT render month grids**, availability blocks, or create/edit/rebook controls."*

**The design doc repeats the prohibition.** `web/DESIGN_SYSTEM.md:316` — *"Do not offer a month
grid…"* — and `:313` fixes the primary presentation as tabular. Per the authority order at
`DESIGN_SYSTEM.md:31-37`, OpenSpec requirements outrank this document.

**The original rationale is partly stale.** `changes/archive/2026-09-05-panel-agenda-calendar-ui/exploration.md:89`
cut the grid because *"a month-grid calendar would need new layout/accessibility behavior, dense
event rendering, date navigation semantics, and a range API"*. The range read exists today:
`app/scheduling.list_for_range` + `to_agenda_dict` return customer, service, technician, status and
calendar-sync state per appointment — everything a grid cell needs.

**One real constraint remains.** `scheduling.list_for_range` rejects a range whose
`(to_date - from_date).days >= 31`. A full 6-week grid with adjacent-month spillover (~42 days)
would fail. A month of its own days stays inside the guard.

**Nothing reusable exists.** No calendar/date-picker/grid component anywhere in `web/src`; no date
library is installed. `agendaTime.ts` exports only `formatAgendaSlot` and `agendaDayKey`.

**The stylesheet boundary is already decided.** `odd/tasks/ds-stylesheet-boundary.md` decision D2:
page rules go into their own commented section appended at the end of
`web/src/components/primitives/primitives.css`. Component `<style>` injection is forbidden and
guarded by `web/src/components/style-boundary.test.ts`.

## Scope

**In:** `openspec/specs/agenda-calendar-ui/spec.md` (`AG-UI-1`), `web/DESIGN_SYSTEM.md`,
`web/src/components/shared/agendaTime.ts` + its test, a new `AgendaCalendar` shared component + its
test, `web/src/components/pages/AgendaPage.tsx` + its test, a new commented CSS section in
`web/src/components/primitives/primitives.css`, and the Storybook surface for both.

**Out:** any backend file or contract (the fetch stays inside the existing range guard); any new
dependency (`Date` + `Intl` only); token value changes; adjacent-month spillover cells; availability
blocks; create/edit/rebook; the technician agenda (`TechnicianAgenda.tsx`) and its shell.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-agenda-calendar-view`
- Branch: `odd/agenda-calendar-view`
- Base: `fe221c0b` (main at creation; `3abe522d` is the agenda unit's merge, later main moved)
- Files:
  - `odd/tasks/agenda-calendar-view.md`
  - `openspec/specs/agenda-calendar-ui/spec.md`
  - `web/DESIGN_SYSTEM.md`
  - `web/src/components/shared/agendaTime.ts`
  - `web/src/components/shared/agendaTime.test.ts`
  - `web/src/components/shared/AgendaCalendar.tsx`
  - `web/src/components/shared/AgendaCalendar.test.tsx`
  - `web/src/components/pages/AgendaPage.tsx`
  - `web/src/components/pages/AgendaPage.test.tsx`
  - `web/src/components/primitives/primitives.css`
  - `web/src/stories/pages/AgendaPage.stories.tsx`
  - `web/src/stories/pages/AgendaPage.stories.test.tsx`
  - `web/src/stories/pages/AgendaCalendar.stories.tsx`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`). This slice is
  frontend-only, so the applicable runner is Vitest: `cd web && npm run test`. Observe RED before
  the source change; never invent RED evidence. The backend runner (`pytest`) is not applicable
  because no backend file changes.
- **No new dependency.** `Date` + `Intl` only (`DESIGN_SYSTEM.md` implementation rule 4).
- **Token-only styling.** New CSS uses existing `var(--*)` tokens and adds no hard-coded colour;
  rules go in one new commented section at the end of `primitives.css` (no `<style>` injection).
- **Timezone-safe.** All day keys and labels derive from the request timezone via `Intl`, matching
  `agendaDayKey`/`formatAgendaSlot`. Never assume the host offset.
- **Artifacts in English; UI copy in neutral Chilean Spanish** (`DESIGN_SYSTEM.md`).
- Conventional commits, no AI attribution. Work-unit commits on this branch are authorized by ODD;
  no push or PR without explicit orchestrator authorization.
- **Per-task Graph Check** before writing code in each area.
- **Ponytail post-write pass** per task: same behavior, less code. It never removes authorized
  behavior; simplifications that would change design or dependencies are reported, not applied.
- Only the authorized files change. If a real need for a file outside this list appears, stop and
  report it rather than widening the slice silently.

## Decisions

- **D1 — Contract first, as a direct live-spec edit.** `AG-UI-1` and `DESIGN_SYSTEM.md` are edited
  before any component code, so the implementation is built against a live contract it satisfies.
  The delta is applied directly to `openspec/specs/agenda-calendar-ui/spec.md` — the same shape
  `ds-stylesheet-boundary` used for `DS-GRAMMAR-2` — with this document as the change record. No
  separate OpenSpec change directory: this is an ODD unit, not an SDD pipeline run.
- **D2 — One cell, two grids.** Month and week share one day-cell contract; only the grid shape
  differs (6×7 vs 1×7). Two view modes must not become two calendar implementations.
- **D3 — Section titles follow the window.** `Hoy` + `Próximas` when the visible window contains
  today; a single `Visitas del período` otherwise. Labelling a past month's visits "Próximas" would
  be a lie.
- **D4 — No spillover days.** A month view renders only that month's days; leading/trailing cells
  stay empty. This keeps the fetched window inside the existing 31-day guard, so no backend change
  is needed. *Named ceiling: adjacent-month days are not shown; raising it requires a backend range
  change.*
- **D5 — The calendar drives the fetch window.** Month view fetches the 1st..last day of the visible
  month; week view fetches its seven days. Default window: the current month. A selected day is
  filtered client-side from the fetched window; it never triggers a second request.
- **D6 — Density is not colour-only.** Every day cell's accessible name carries its visit count, and
  the count is visible text or a labelled indicator. Colour is never the only state channel
  (`DESIGN_SYSTEM.md:500`).

## Tasks

- [x] **T1 — Contract delta (first).** Modify `AG-UI-1` so the agenda MAY render a month/week
  calendar, defines the day-selection filter, keeps `Hoy`/`Próximas` for the unselected window, and
  keeps availability blocks and create/edit/rebook out. Add scenarios for day selection and for the
  calendar's own state contract. Update `web/DESIGN_SYSTEM.md` (line 316 + an Agenda
  page-architecture paragraph for the calendar).
- [x] **T2 — RED/GREEN: date helpers.** Extend `agendaTime.test.ts` with month/week helpers
  (day-key list for a month, day-key list for a week with Monday-first weeks, month label, weekday
  labels, day-number, and navigation across month/year boundaries), watch it fail, then implement
  them in `agendaTime.ts`.
- [x] **T3 — RED/GREEN: `AgendaCalendar`.** New `AgendaCalendar.test.tsx` + `AgendaCalendar.tsx`:
  month and week grids, previous/next/today navigation, view toggle, day selection with an
  accessible selected state, per-day visit counts, keyboard operation, and an empty month. Add its
  commented CSS section in `primitives.css`.
- [x] **T3B — Correction (review finding, reopens T3).** Two defects found on orchestrator review of
  T3: (a) the calendar is ARIA-invalid — `role="grid"` with `role="gridcell"` children and no
  `role="row"`, plus `aria-selected` on a `<button>`, which is not an allowed role for that
  attribute; this contradicts `AG-UI-2`'s semantic-markup requirement and the WCAG 2.2 AA baseline.
  (b) The toolbar controls use raw `btn btn--secondary` classes instead of the `Button` primitive.
  **Resolution:** use native `<table>` semantics (platform-first, no ARIA grid roles needed) and the
  `Button` primitive for every toolbar control. The view switch becomes a SINGLE action-labelled
  `Button` (`Ver semana` / `Ver mes`) instead of two `aria-pressed` buttons: `Button.tsx` silently
  drops attributes it does not destructure, so `aria-pressed` cannot be passed through it — the
  current period is announced by the calendar heading, and the control states the action. The
  underlying primitive defect is recorded under Follow-ups, not fixed here. Behavior, the accessible
  visit count, and the selected/today state MUST NOT change.
- [x] **T4 — RED/GREEN: `AgendaPage` integration.** Wire the calendar as the fetch-window driver and
  the day filter; resize the register into the new layout; keep every existing state (loading,
  denied, error, stale, empty) and both row actions working. Update `AgendaPage.test.tsx`; existing
  assertions must keep passing unless the contract deliberately changed.
- [x] **T5 — Storybook.** Extend `AgendaPage.stories.tsx` (+ its stories test) and add
  `AgendaCalendar.stories.tsx`, covering month/week, selected day, empty month, dense month, and
  narrow widths.
- [ ] **T6 — Closeout.** Run the full checks, reconcile this progress list against `git log`, and
  harvest any `ponytail:` markers.

## Acceptance criteria

1. `AG-UI-1` no longer forbids a month grid; it defines the calendar, the day filter, and the
   unselected `Hoy`/`Próximas` behavior, with Given/When/Then scenarios.
2. `web/DESIGN_SYSTEM.md` no longer prohibits the month grid and documents the calendar in the
   Agenda architecture.
3. The Agenda renders a month and a week calendar, navigates periods, and filters the register to a
   selected day; clearing the selection restores `Hoy`/`Próximas` (or `Visitas del período` outside
   a window containing today).
4. Existing agenda behavior is preserved: cancellation for `booked` rows with confirmation and
   reason, calendar retry for `pending`/`failed`, and every loading/denied/error/stale/empty state.
5. No new dependency; no hard-coded colour; no component `<style>` injection; the style-boundary
   guard still passes.
6. The fetched range never reaches `(to - from).days >= 31`.
7. `cd web && npm run test`, `cd web && npm run build` and `cd web && npx tsc -b --noEmit` pass.
8. Only the authorized files change.

## Checks

- `cd web && npm run test`
- `cd web && npm run build`
- `cd web && npx tsc -b --noEmit`
- `git status --short` / `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create agenda-calendar-view`); `npm ci` completed in `web/`.
- [x] Baseline observed at `fe221c0b`: `npm run test` → **82 files, 670 tests, all passing** (52s).
      No known environmental failures.
- [x] Graph Check (Step 1): `graphify query "agenda page layout sections table styles"` and
      `graphify query "agenda appointments technician panel"` over the repo root graph. Nodes
      consulted: `AgendaPage()`, `AgendaPage.tsx`, `AgendaPageProps`, `PageFrame()`,
      `useAsyncData()`, `types.ts`, `api.ts`, `AppShell.tsx`, `TechnicianAgenda.tsx`,
      `shared/toneMaps.ts`, `ODD: ds-stylesheet-boundary`. The graph's agenda community is intact.
      Note: the graph was built from `3abe522d`; HEAD is `fe221c0b` (the KB slice), which does not
      touch agenda modules. Per repo policy the refresh runs once at session close, not mid-task.
- [x] **T1** — `AG-UI-1` rewritten (calendar navigation + register sections + four new scenarios);
      `AG-UI-2` extended with the shared calendar/register state contract; `AG-UI-4` extended with
      the calendar story coverage; the spec `Purpose` updated. `web/DESIGN_SYSTEM.md` Agenda section
      rewritten and the month-grid prohibition removed. No component code touched yet.
- [x] **T2** — `agendaTime.ts` now provides timezone-aware month/week labels, day lists, period
      navigation, and day formatting. RED: focused Vitest reported 10 failures with missing exported
      helper functions. GREEN: commit `b0f69ec6`; focused Vitest passed **12 tests**.
- [x] **T3** — `AgendaCalendar` now renders tokenized month/week grids with navigation, view toggle,
      selection, current-day marking, visit density, keyboard controls, and non-selectable empty cells.
      RED: focused Vitest failed to resolve `./AgendaCalendar` because the component did not exist.
      GREEN: commit `f86b0f83`; focused Vitest passed **6 tests**, with the stylesheet boundary green.
- [x] **T2/T3 verified independently by the orchestrator** — `npm run test` re-run on the worktree:
      **83 files, 686 tests, all passing** (76s), matching the writer's report. Working tree clean,
      only authorized files changed, `graphify-out` untracked.
- [ ] **T3 review — two defects found; reopened as T3B.** The month/week grid ships invalid ARIA
      (`role="grid"` without `role="row"`, and `aria-selected` on a `<button>`) and its toolbar
      bypasses the `Button` primitive with raw `btn` classes. Behavior and tests are otherwise sound.
      Recorded rather than silently accepted: an invalid ARIA grid is a real accessibility defect and
      the design system requires semantic markup and primitive reuse.
- [ ] **T3B first attempt — blocked honestly, then re-scoped.** The writer converted the grid to
      native `<table>` semantics but stopped when the typed view toggle could not pass `aria-pressed`
      through `Button` (it destructures without spreading). It refused to widen the slice on its own,
      which is the correct behaviour. Verified independently: `Button.tsx:19-27` destructures a fixed
      set of props and never spreads, so its type contract overpromises. Resolution recorded in T3B
  (single action-labelled toggle, no primitive change); the primitive defect is parked under
  Follow-ups.
- [x] **T3B** — Replaced the invalid ARIA grid with native table semantics, moved toolbar controls
      to the `Button` primitive, and changed the view switch to one action-labelled toggle. RED:
      focused Vitest found the old grid roles, old two-button toggle, and invalid selection assertion.
      GREEN: commit `49cdd91a`; focused Vitest passed **7 tests**.
- [x] **T4** — Integrated the calendar into `AgendaPage` as the month/week fetch-window driver,
      added selected-day filtering, preserved lifecycle and row-action behavior, and kept the
      register mobile-safe. RED: existing page assertions needed calendar-aware table/text scopes.
      GREEN: focused page Vitest passed **16 tests**, build and TypeScript checks passed.
- [x] **T5** — Added page state-matrix coverage and `AgendaCalendar` stories for month, week,
      selected, empty, dense, and narrow variants. RED: story tests exposed date-dependent expectations
      and fake-timer interaction; GREEN: focused Storybook tests passed **15 tests** and
      `npm run build-storybook` passed.

## Follow-ups

- **`Button` drops undeclared attributes (pre-existing defect).**
  `web/src/components/primitives/Button.tsx` extends
  `ButtonHTMLAttributes<HTMLButtonElement>` but destructures only a fixed set of props and never
  spreads the rest, so `aria-*`, `data-*` and other valid attributes are silently discarded. This is
  not introduced by this unit: `AgendaPage` already passes `aria-label="Reintentar calendario"` to a
  `Button` and that label never reaches the DOM. Deliberately out of scope here — it is a shared
  primitive with ~20 consumers and a wider blast radius, and binding it to this slice would put two
  risks in one diff. It needs its own ODD unit, which must settle the `<a>` branch contract
  (`href` renders an anchor, where button-only attributes do not apply) before spreading.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-agenda-calendar-view`, branch
  `odd/agenda-calendar-view`.
- Dev server for this worktree: `cd web && npm run dev -- --host 127.0.0.1 --port 5177`, with the API
  proxy pointed at the running `infra-api-1` on `:8000` via `VITE_API_TARGET`. `:5173` is main;
  `:5176` was the retired `ds-stylesheet-boundary` worktree.
- On resume: read this file and reconcile the checkbox state against `git log`.
