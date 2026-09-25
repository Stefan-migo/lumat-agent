# ODD — agenda-visual-alignment

## Objective

Align the Agenda header, calendar, and visit register as a coherent page without
changing behavior or adding backend work.

## Problem

The owner verified six visual issues: the primary action renders below the header;
calendar days are pure white against an elevated card; extra status lines make rows
uneven; the month label starts lowercase; today is weakly indicated; and the calendar
and register do not read as sibling surfaces.

## Why

These defects obscure page hierarchy and make the calendar harder to scan. The fixes
preserve accessible state and visit density while aligning the two page regions.

## Scope (authorized by the owner)

**In:** `AgendaPage`, `AgendaCalendar`, `agendaTime`, their tests, and Agenda selectors
in `web/src/components/primitives/primitives.css`; this task document.

**Out:** `TechnicianAgenda`, list-page toolbar alignment, the day dialog and
per-appointment page (U5), the visit dialog redesign (U4), and any backend work.

## Decision

- **D1 — Put `Nueva visita` in `PageFrame.actions`.** This explicitly supersedes
  `agenda-design-alignment` D2, which kept the action in content because list pages
  did likewise. The action belongs in the shared header alongside title and meta.
  This establishes the precedent that page-level primary actions live in the header;
  list pages (`ClientesList` uses a `.toolbar` in content) are now the deviation.
  Aligning those pages is a separate future unit and is out of scope here.
- **D2 — Keep day density and state accessible without relying on color.** Every day
  has only its number, textual visit count, and one combined status marker at most.
  Today retains `aria-current="date"`; selection is a toggle button exposed with
  `aria-pressed` (not `aria-selected`, which is not supported on `role=button`).
- **D3 — Reuse existing design tokens.** No new token is needed; use a non-white
  existing surface token for day cells and match the register's elevated surface.
- **D4 — Capitalize the month label in `agendaMonthLabel`, not with CSS.** This avoids
  Spanish title-casing errors such as capitalizing the article “de”.

## Constraints

- **Strict TDD ON.** Runner: `cd web && npm test`. RED must be observed before GREEN.
- No linter, formatter, or standalone type checker. The only type check is
  `cd web && npm run build` (`tsc -b`).
- CSS contract tests read the stylesheet with `readFileSync`; precedent:
  `web/src/components/pages/Dashboard.test.tsx:99-105`.
- Every day cell has equal height in month and week views regardless of content.
- Visit counts remain text; `aria-current` and `aria-pressed` remain present.
- Day background cannot be pure white. Prefer an existing token.
- Do not change specs, `openspec/`, backend files, or files outside this scope.
- Operator-facing UI copy is Spanish; code, identifiers, comments, tests, docs, and
  commit messages are English.
- Visual proof: real page in application shell via Storybook on a non-6006 port and
  Chromium geometry; scripts only in `/tmp/opencode/`; remove temporary stories.

## Graph check

`graphify query "AgendaPage calendar styles agendaTime PageFrame actions data region"`
consulted `AgendaPage()`, `AgendaCalendar()`, `agendaTime.ts`, `PageFrame()`,
`.data-region shared surface`, and the AgendaPage community. `graphify query
"AgendaCalendar day cells today selected month label stylesheet data-region"`
consulted `AgendaCalendar()`, `agendaMonthLabel()`, `agendaTime.test.ts`,
`AgendaCalendar.test.tsx`, `AgendaPage.tsx`, and `.data-region shared surface`.
Path `AgendaCalendar` ↔ `AgendaPage` showed the import edge; `agendaMonthLabel` ↔
`agendaTime.test.ts` showed the unit-test edge. `GRAPH_REPORT.md` identifies
`AgendaPage.tsx` as a community hub.

## Tasks

| ID | Task | Route |
|----|------|-------|
| T1 | RED: add tests for action placement, combined marker/accessibility, month capitalization, and CSS contracts; observe failure. | direct inline |
| T2 | GREEN: implement header placement, bounded cell content, equal cell sizing, contrast, today marker, and sibling surface styling. | direct inline |
| T3 | Storybook + Chromium geometry in shell for header action and representative cell heights in month/week views. | direct inline |
| T4 | Full web suite and build. | direct inline |

## Delivery

One reviewable ODD unit, split into atomic commits by behavior; no push or PR.

## Progress / Evidence

- [x] Initial focused run observed RED: `5 failed | 40 passed (45)` across three files.
  The failures exposed stale lowercase month accessible-name expectations and the
  grouped CSS-rule test extractor returning an empty match.
- [x] Corrections: updated expected table names to `Calendario de Septiembre de 2026`,
  fixed the grouped rule matcher, removed invalid `aria-selected` from the button,
  restored the selected-style selector to `aria-pressed`, removed redundant
  `text-transform: none`, restored day-cell spacing, and corrected JSX indentation.
- [x] Focused GREEN observed: 3 files passed, 45 tests passed.
- [x] First visual review found the count was visibly ellipsized despite equal-height
  cells. The fix removed truncation from `.agenda-calendar__count`, allowed its text to
  wrap, reduced day-cell horizontal padding, and widened the table minimum to 320px.
  Fixed cell height remains unchanged.
- [x] Calendar and register surfaces now share 1px solid `var(--corp-border)`,
  `var(--radius-lg)`, `var(--brand-bg-elevated)`, 16px padding, and no shadow. The
  nested Agenda `.data-region` is transparent with no border/shadow to prevent a second
  card inside the aligned register section.
- [x] Second visual proof captured in Chromium via Storybook on port 6012, composing
  `AgendaPage` inside `PanelShell`. Verbatim day-count text from Chromium:
  `0 visitas`, `0 visitas`, `2 visitas`. Month view days 1, 2, 25 (two visits + today),
  30 all measured 94px; week view days 21, 22, 25 (two visits + today), 27 all 94px.
  Header: action rect x=1303.47, y=119.34, w=112.53, h=34.31; header rect x=264,
  y=109, w=1152, h=55; the action is contained by the header.
- [x] Browser-computed surfaces match: calendar rect x=264, y=216, w=481.69,
  h=697.63; register rect x=765.69, y=216, w=650.31, h=341.81. Both computed
  `border: 1px solid rgb(216, 221, 227)`, `border-radius: 12px`, identical elevated
  background `color(srgb 0.921285 0.932861 0.905079 / 0.976471)`, `padding: 16px`,
  and `box-shadow: none`.
  Screenshot: `/tmp/opencode/agenda-u2.png`.
- [x] Full `npm test` passed: 87 test files and 750 tests. Earlier parallel full-suite
  attempts hit 5-second timeouts; the final uncontentended run passed without changing
  any existing timeout or broadening scope.
- [x] `npm run build` passed (`tsc -b` and Vite production build); Vite emitted only its
  existing >500 kB chunk-size advisory.
- [x] Temporary Storybook visual-proof story was deleted after the Chromium capture.

Correction-pass RED/GREEN evidence: initial focused run failed 5 tests (40 passed),
then focused rerun passed all 45 tests. Full suite initially hit timing flakes; final
standard full run passed all 750 tests. Chromium measurement confirms the action is in
the header and representative month/week cells are all exactly 94px tall.

Second correction-pass TDD: the new visual contract assertions first failed (`1 failed,
22 passed`) because `.agenda-calendar__count` had no untruncated wrapping rule. After
the CSS fix, focused tests passed (`3 files passed`, `45 tests passed`). The final
standard `npm test` run passed all 87 files / 750 tests; earlier attempts hit existing
5-second suite-contention timeouts. `npm run build` passed, with only Vite's large-chunk
advisory.

## Next step

Second visual correction is measured and captured. Run full suite and build, refresh
Engram, and create one correction commit. Review the header-action precedent for list
pages as a separate future unit.
