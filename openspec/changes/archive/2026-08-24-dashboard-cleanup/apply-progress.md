# Apply Progress — Dashboard and story cleanup (slice-3)

> Change: `2026-08-24-dashboard-cleanup` · Project: lumat-agent · 2026-08-24
> Mode: Strict TDD (vitest + RTL) · Delivery: stacked-to-main PR
> Status: **4/4 tasks complete** — Ready for verify

## Completed Tasks

| ID | Task | Result | Evidence |
|----|------|--------|----------|
| 1.1 | R3-001 PanelEntry docs copy | ✅ | PanelEntry.stories.tsx:13 — brand dark green (--corp-primary), header white (--corp-surface), same height |
| 1.2 | R3-002 var(--corp-value) on data roles | ✅ | Inline tabular-nums removed (182/187/192); `.dashboard-activity__time` → var(--corp-value) (:123); zero literal tabular-nums in slice files |
| 1.3 | R3-004 kpis mock + story render | ✅ | mockData/dashboard.ts: `Kpi` interface + `kpis` export; Dashboard.stories.tsx renders from `kpis` |
| 1.4 | R3-003/004 test derive from kpis | ✅ | initials() lockstep comment; KPI assertions from `kpis` via closest(".kpi") |
| 2.1 | Gates green | ✅ | `npx tsc -b` exit 0 (closest<HTMLElement> fix); `npm test` 304/304 (39 files) |
| 2.2 | Adopt chained-out files | ✅ | PanelEntry.stories.*, PageFrame.* adopted as-is (already aligned) |

## Verification Evidence

| Gate | Result |
|------|--------|
| `cd web && npm test` | 304/304 passed (39 files) |
| `cd web && npx tsc -b` | exit 0 |
| Hex scan (slice files) | zero hex |
| Literal tabular-nums (slice files) | zero remaining (only var(--corp-value)) |

## Deviations

- R3-003 (initials helper) accepted as-is with strengthened comment (ponytail: no export surface for a test-only mirror).
- KbList.stories.tsx literal tabular-nums noted as follow-up (out of scope — different page, not in the chained-out set).

## Commits (work units)

To be created at PR time: fix(web) R3-001 → fix(web) R3-002 → test(web) R3-003/004 → docs(openspec) archive.

## Graph Nodes Consulted

Dashboard.stories.tsx, PanelEntry.stories.tsx, PageFrame.tsx, mockData/dashboard.ts, primitives.css (.kpi__value), tokens.css (--corp-value).