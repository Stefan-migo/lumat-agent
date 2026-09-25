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
  Today retains `aria-current="date"`; selection retains `aria-selected`.
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
- Visit counts remain text; `aria-current` and `aria-selected` remain present.
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

- [x] T1 tests authored; focused RED could not be run: `vitest: command not found`
  because this worktree has no `web/node_modules`.
- [x] T2 implementation completed. GREEN is **not verified** for the same missing
  dependency reason; no result is claimed.
- [ ] T3 visual proof unavailable: Storybook dependencies and Chromium harness cannot
  run without installed web dependencies; no geometry is fabricated.
- [ ] T4 full suite and build attempted but blocked: `vitest: command not found` and
  `tsc: command not found`.

`git diff --check` passed. No package installation was attempted; fetching dependencies
would transfer remote files, which was not authorized.

## Next step

Install dependencies under explicit authorization, then run focused tests to observe
RED and GREEN, the full suite, build, and shell-aware Chromium measurements. Review the
header-action precedent for list pages as a separate future unit.
