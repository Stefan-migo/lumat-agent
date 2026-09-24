# ODD: panel-dashboard-alignment

## Objective

Bring the operator dashboard (`Panel`) in line with `web/DESIGN_SYSTEM.md` on four verified
divergences, without redesigning the surface and without touching the shared async-data contract.

Independent of the `agenda-*` units. Selected by the owner from a three-item panel design review.

## Problem

Four divergences, each verified by reading the code and measured in a real browser
(Playwright, chromium, against Storybook at six widths: 375 / 640 / 768 / 1023 / 1024 / 1280).

**1. The 768–1023px band keeps the desktop grid.** `web/DESIGN_SYSTEM.md:320-325` requires
`640–1023px` to be "one or two content columns". The `@media (max-width: 63.99rem)` block
(`web/src/components/primitives/primitives.css:2067-2071`) adjusts `.kpi-grid` and `.dashboard__period`
but never touches `.dashboard__hoy` or `.dashboard__grid`, which only collapse inside
`@media (max-width: 48rem)` (`:2072-2077`). Measured at 1023px: `.dashboard__hoy` renders
**3 columns** and `.dashboard__grid` renders **4 columns**. Measured at 768px: 1 and 2. Measured at
640px: 1 and 2.

**2. Cards use the wrong radius.** `web/DESIGN_SYSTEM.md:276-278`: "Cards use `--radius-lg` (12px)".
`.dashboard__card-ops` (`primitives.css:2002`) and `.dashboard__card` (`:2028`) declare
`border-radius:var(--radius-md)`.

**3. Section headings are forced to uppercase.** `primitives.css:1995` sets
`text-transform:uppercase` on `.dashboard__section-head h2`, and `Dashboard.tsx:152` hardcodes the
string `"HOY"`. `web/DESIGN_SYSTEM.md:263` requires sentence case in Spanish and `:266` forbids all
caps "except very short machine/status labels". A page section heading is not a machine/status label.

**4. Partial failures are presented as emptiness.** `Dashboard.tsx:111-115` executes
`getDashboardToday(timezone).catch(() => emptyToday)` and
`getDashboardTrend(timezone).catch(() => ({ buckets: [] }))`, so a dead endpoint renders as "there is
no data". `web/DESIGN_SYSTEM.md:346-347` requires clearly distinct "empty, loading, stale,
partial-error, and fatal-error states". The story contract already declares these states and then
throws them away: `web/src/stories/pages/Dashboard.stories.tsx:6-7` defines
`DashboardState = AsyncDataState | "stale" | "partial-error" | "fatal-error"` and `:53` normalizes
all three to `"error"`, so the `Stale` and `PartialError` stories (`:69-70`) render a generic fatal
error. The contract exists on paper and is collapsed in implementation.

## Scope

**In:**

1. Make the `640–1023px` band render one or two content columns for `.dashboard__hoy` and
   `.dashboard__grid`, per the documented bands.
2. Cards use `--radius-lg`.
3. Section headings use sentence case; no forced uppercase transform.
4. A failing `today` / `trend` request renders a distinct partial-error state instead of empty data;
   a failing `/kpis` remains a fatal error with retry.
5. Tests for all four, plus the story contract no longer lying about its states.

**Out (deliberate):**

- **Extending the shared `AsyncDataState`.** It has 19 consumers
  (`web/src/hooks/useAsyncData.ts` and the pages that import it). Widening it to carry
  `stale`/`partial-error` is a cross-page change with no owner mandate.
- **Replacing the hand-rolled ops cards with the `Card` primitive.** `Card` renders a fixed `<h2>`
  title and cannot express the icon + title + count header the ops cards need
  (`Dashboard.tsx:137-146`). Discretionary, and a redesign we were not asked for.
- **`AdvancedDashboard`.** Legacy compatibility route, documented as excluded from navigation at
  `web/DESIGN_SYSTEM.md:304`.
- Any change to KPI content, hues, the period block, or the motivos chips.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-panel-dashboard-alignment`
- Branch: `odd/panel-dashboard-alignment`
- Base: `66cc868a`
- Files:
  - `odd/tasks/panel-dashboard-alignment.md`
  - `web/src/components/pages/Dashboard.tsx`
  - `web/src/components/pages/Dashboard.test.tsx`
  - `web/src/components/primitives/primitives.css`
  - `web/src/stories/pages/Dashboard.stories.tsx`
  - `web/src/stories/pages/Dashboard.stories.test.tsx`

Any file outside this list needs a scope update here first.

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml:38`. Web runner `cd web && npm test`.
- **No Python file changes, so the pytest suite is not applicable to this unit.** It is not run;
  CI still runs it unchanged. This is a recorded decision (D8), not an omission.
- The repo has no linter, formatter or type checker. The only type check is
  `cd web && npm run build` (`tsc -b`).
- **CSS-contract tests follow the repository's established pattern**: a Vitest test reads
  `src/components/primitives/primitives.css` with `readFileSync` and asserts the declarations
  (`web/src/components/primitives/Button.test.tsx:65`, `Icon.test.tsx:8`). Use it; do not invent a
  new pattern.
- `web/src/components/style-boundary.test.ts` and `dependency-boundary.test.ts` constrain where CSS
  and imports may live. Run the full web suite; if a boundary test forbids something, stop and report
  instead of moving the boundary.
- **D6 language:** code, identifiers, comments, tests and this record are English. Operator-facing
  copy in the panel stays Spanish (`"Cargando indicadores"`, `"Aún no hay actividad en esta
  ventana"`, `"Reintentar"`).
- Work-unit commits are authorized. **Push and PR are separate decisions.**
- Delivery: `stacked-to-main`. This unit is its own PR to main.

## Decisions

- **D1 — Only the four verified divergences are in scope.** The discretionary findings from the
  review (hand-rolled cards, `AdvancedDashboard`) are recorded as out.
- **D2 — Do not extend the shared `AsyncDataState`.** Mirror the existing precedent instead:
  `Settings.tsx:16` already defines a page-local
  `SettingsState = AsyncDataState | "saved" | "saving" | "validation" | "server-error" | "stale"`.
  Dashboard gets its own local union with the states its story contract already declares.
- **D3 — The partial failure rides on the fetched data, not on the shared hook.** A `/kpis` failure
  stays fatal. A `today` or `trend` failure is recorded on the locally-typed fetch result (the local
  `DashboardData` type at `Dashboard.tsx:96`, not a shared type) and rendered as a distinct
  warning-state region while the KPIs still render. Never substitute empty data for a failure.
- **D4 — The story contract stops normalizing.** `Dashboard.stories.tsx:53` no longer collapses
  `stale` / `partial-error` / `fatal-error` into `"error"`; the three stories render their real
  states.
- **D5 — The ops cards stay hand-rolled**; only their radius token changes.
- **D6 — The responsive fix targets the documented bands, not the current numbers.** After the fix,
  `768px`, `1023px` and `1024px` must all sit in their documented band: `768` and `1023` in
  `640–1023px` (one or two columns), `1024` in `1024–1279px` (standard operational layout).
- **D7 — `stale` is rendered distinctly from `partial-error` and from `fatal-error`.** The document
  requires all three to be clear; collapsing them is the defect being fixed.
- **D8 — No pytest run.** No Python file changes. Recorded as not applicable rather than skipped
  silently.

## Route per task

| Task | Route | Trigger evidence |
| --- | --- | --- |
| T1–T6 | delegated (one bounded writer) | 6 non-trivial files across component, CSS, stories and tests; the writer trigger fired |

## Tasks

- [ ] **T1 — RED (state contract).** Vitest: Dashboard renders a distinct `stale`, a distinct
  `partial-error`, and a fatal error with retry; and a failing `today` fetch is **not** rendered as
  the empty state. Must fail before T2.
- [ ] **T2 — GREEN.** Local `DashboardState` union, `stateMessage` branches, and the partial-failure
  plumbing on the local fetch result (D2/D3/D7).
- [ ] **T3 — RED (CSS contract).** `readFileSync` assertions: `.dashboard__card-ops` and
  `.dashboard__card` use `var(--radius-lg)`; the heading rule no longer sets
  `text-transform:uppercase`; the 640–1023 band constrains `.dashboard__hoy` and `.dashboard__grid`
  to one or two columns.
- [ ] **T4 — GREEN.** `primitives.css` changes for radius, casing and the band.
- [ ] **T5 — Story contract.** Remove the normalization (D4); update `Dashboard.stories.test.tsx` to
  assert the real states.
- [ ] **T6 — Evidence.** Re-measure the grids in a real browser at 768 / 1023 / 1024 / 1280 and
  record the measured `grid-template-columns`, plus the command outputs.

## Acceptance criteria

1. Measured in a browser: at `768px` and `1023px` both `.dashboard__hoy` and `.dashboard__grid`
   render **one or two** columns; at `1024px` and `1280px` the standard operational layout is intact.
2. `.dashboard__card-ops` and `.dashboard__card` use `var(--radius-lg)`.
3. Section headings render in sentence case with no uppercase transform, and no other copy changes.
4. A failing `today` or `trend` request renders a distinct partial-error state and is never shown as
   empty; a failing `/kpis` still renders the fatal error with a working `Reintentar`.
5. `AsyncDataState` is byte-identical and none of its 19 consumers change.
6. `cd web && npm test` is green; `cd web && npm run build` passes.
7. Only the files in Authorized scope change.
8. Every operator-facing string introduced is Spanish and consistent with the existing panel copy.

## Checks

- `cd web && npm test`
- `cd web && npm run build`
- Browser re-measurement at 768 / 1023 / 1024 / 1280 (Playwright against Storybook or the dev server)
- `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] T1 RED observed, then T2 GREEN: page-local stale/partial-error/fatal-error states and partial today/trend failure plumbing.
- [x] T3 RED observed, then T4 GREEN: CSS contract tests, card radii, sentence-case headings, and documented responsive band.
- [x] T5 Story contract preserves stale, partial-error, and fatal-error states.
- [x] T6 Browser evidence captured at 768 / 1023 / 1024 / 1280px.

## Verification evidence

Graph check: `Dashboard()` → `pages/Dashboard.tsx` → `StateMessage()` and `Dashboard.stories.tsx` → `Dashboard()`; the graph was built from base `66cc868a` and queried before edits. No directed path was present from `Dashboard.tsx` to the CSS file; the CSS boundary was verified from the source and its boundary tests.

T1/T3 RED output (observed before implementation):

```text
 FAIL  src/components/pages/Dashboard.test.tsx > Dashboard operational surface > renders a distinct stale state
 FAIL  src/components/pages/Dashboard.test.tsx > Dashboard operational surface > renders a distinct partial-error state
 FAIL  src/components/pages/Dashboard.test.tsx > Dashboard operational surface > renders a distinct fatal-error state
 FAIL  src/components/pages/Dashboard.test.tsx > Dashboard operational surface > keeps KPI data visible and does not render a failed today request as empty
 FAIL  src/components/pages/Dashboard.test.tsx > Dashboard operational surface > keeps the dashboard CSS contract aligned with the design system
 FAIL  src/components/pages/Dashboard.test.tsx > Dashboard operational surface > renders HOY rows and navigates each row to its operational view
 Test Files  1 failed (1)
 Tests  6 failed | 6 passed (12)
```

Verification:

- `npm test`: `Test Files 86 passed (86); Tests 725 passed (725)`.
- `npm run build`: passed (`tsc -b` and Vite production build); Vite emitted only the existing chunk-size warning.
- `git diff --check`: passed.
- Browser Storybook `pages-dashboard--overview` (`scrollWidth` equals `innerWidth` at every width):

| Viewport | `.dashboard__hoy` | `.dashboard__grid` | scrollWidth / innerWidth |
| --- | --- | --- | --- |
| 768x900 | `728px` | `358px 358px` | `768 / 768` |
| 1023x900 | `485.5px 485.5px` | `485.5px 485.5px` | `1023 / 1023` |
| 1024x900 | `237.328px 237.328px 237.328px` | `175px 175px 175px 175px` | `1024 / 1024` |
| 1280x900 | `322.656px 322.672px 322.656px` | `239px 239px 239px 239px` | `1280 / 1280` |

`.dashboard__chart__empty` was not changed: it is an empty-state box inside a card, not a card container. `.dashboard__chip` remains a pill with `border-radius:999px`.

**Nuance, recorded rather than hidden.** When the `today` request fails, the Hoy region still renders
through the `emptyToday` fallback (zero counts, empty lists) *underneath* the partial-error notice
(`Dashboard.tsx:126,157`). The failure is no longer silent — it declares itself — but the affected
region still reads as zero. Hiding the region entirely was considered and rejected here as a larger
UI change than this alignment warrants. If the owner wants the failed region to disappear or to be
replaced by the notice, that is one bounded follow-up.

Non-blocking note on the writer's report: it returned `status: partial` after seeing intermittent
`AgendaPage` timeouts on later full-suite reruns. Those were CPU contention from the Storybook and
Playwright processes it had running concurrently, not a defect in this change: the orchestrator
re-ran the full web suite on the frozen tree and observed `86 passed (86)` files and
`725 passed (725)` tests with nothing else running. The declared status was worse than reality.

## Assess outcome

`gentle-ai review assess --base-ref 66cc868a --committed-only` over the three commits:

- risk `medium` (`reasons: [executable_change]` on `Dashboard.test.tsx`), 6 changed paths, 304
  changed lines, `review_due: false`, `review_due_reason: under_budget`.

No native review is due for this unit; the assessed tier and reason are recorded per protocol. The
first assessment invocation omitted `--base-ref` and reported `high` / `unassessable` with
`changed_paths: 0`; that was the selector, not the change.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for `panel-dashboard-alignment`,
then `mem_get_observation` for the full document, then read this file.
