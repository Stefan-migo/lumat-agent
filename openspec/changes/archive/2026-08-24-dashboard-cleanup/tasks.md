# Tasks: Dashboard and story cleanup (slice-3)

> Change: `2026-08-24-dashboard-cleanup` · Project: lumat-agent · 2026-08-24

## Review Workload Forecast

Decision needed before apply: No (auto-chain; chain_strategy=stacked-to-main cached)
Chained PRs recommended: No — single stacked PR (base main; diff narrows as #47/#52 merge)
400-line budget risk: Medium (~440 diff lines incl. adoption of the chained-out rework; ~60 lines are new edits)
Chain strategy: stacked-to-main

## Phase 1 — R3 fixes

- [x] **1.1** R3-001: PanelEntry.stories.tsx docs — accurate shell description (brand dark green --corp-primary; header white --corp-surface; same height). [DS-STORY-2 scenario]
- [x] **1.2** R3-002: Dashboard.stories.tsx — remove inline `fontVariantNumeric: "tabular-nums"` from KPI values (primitives `.kpi__value` provides var(--corp-value)); `.dashboard-activity__time` → `var(--corp-value)`. [DS-DASH-1]
- [x] **1.3** R3-004: mockData/dashboard.ts — add `Kpi` interface + `kpis` export; Dashboard.stories.tsx renders KPI cards from `kpis`. [DS-DASH-2]
- [x] **1.4** R3-003/004: Dashboard.stories.test.tsx — strengthen `initials()` lockstep comment (R3-003 accepted); derive KPI assertions from `kpis` (scoped via closest(".kpi")). [DS-DASH-2]

## Phase 2 — Gates + adoption

- [x] **2.1** `cd web && npx tsc -b` exit 0 (closest<HTMLElement> type fix) and `cd web && npm test` 304+ green. [DS-DASH-1/2]
- [x] **2.2** Adopt chained-out files (PanelEntry.stories.*, PageFrame.*) as-is (already aligned). [DS-STORY-2]

## Delivery Plan

Work-unit commits: `fix(web): correct PanelEntry shell docs (R3-001)` → `fix(web): route dashboard data roles through var(--corp-value) (R3-002)` → `test(web): derive KPI assertions from mock data (R3-003/004)` → `docs(openspec): archive dashboard-cleanup slice-3`.

## Deferred (follow-ups)

- KbList.stories.tsx literal tabular-nums (same DS-TKN-11 class).
- Remaining Corporate components; optional count-up/fade-content.