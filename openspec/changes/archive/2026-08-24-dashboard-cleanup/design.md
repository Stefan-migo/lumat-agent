# Design: Dashboard and story cleanup (slice-3)

## Technical Approach

Small, review-driven slice: fix the 4 R3 advisory findings from the slice-2 review and adopt the chained-out dashboard/story files. No new primitives, no new dependencies, no component rewrites.

## Architecture Decisions (D#)

| # | Decision | Options | Chosen |
|---|---|---|---|
| D1 | R3-001 docs copy | Remove "and color" vs full accurate description | **Accurate description**: brand dark green (--corp-primary), header white (--corp-surface), same height — explicit, prevents re-drift |
| D2 | R3-002 data roles | Inline var() vs rely on primitives rule vs stylesheet rule | **Remove the inline overrides** — primitives `.kpi__value` already resolves `var(--corp-value)` (slice-1); `.dashboard-activity__time` re-targets to `var(--corp-value)` directly |
| D3 | R3-003 initials helper | Export from Avatar vs keep local | **Keep local with strengthened comment** (ponytail: no export surface for a test-only mirror) |
| D4 | R3-004 KPI assertions | Hardcode vs mock-derived | **Mock-derived**: `kpis` export (Kpi interface: label/value/delta/deltaTone); story + test read from it; test scopes each card via `.closest(".kpi")` |

## File Changes

| File | Action | Description |
|---|---|---|
| `web/src/stories/pages/PanelEntry.stories.tsx` | Modify | R3-001: accurate shell description |
| `web/src/stories/pages/Dashboard.stories.tsx` | Modify | R3-002: remove inline tabular-nums; `.dashboard-activity__time` → var(--corp-value); R3-004: render KPIs from `kpis` |
| `web/src/stories/pages/_shared/mockData/dashboard.ts` | Modify | Add `Kpi` interface + `kpis` export |
| `web/src/stories/pages/Dashboard.stories.test.tsx` | Modify | R3-003: lockstep comment; R3-004: derive from `kpis` |
| `web/src/stories/pages/PanelEntry.stories.test.tsx` | Adopt | Already aligned (heading regex) |
| `web/src/stories/pages/_shared/PageFrame.tsx/.test.tsx` | Adopt | Already aligned (text-only titlebar) |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit (RTL) | KPI cards derive from mock; activity rows; hero; no CTA | Dashboard.stories.test.tsx (kpis-derived) |
| Typecheck | `npx tsc -b` | exit 0 (closest<HTMLElement> for within()) |
| Gates | `npm test` 304+, hex walk, no literal tabular-nums in slice files | CI |

## Batch/PR Plan

- Work-unit commits: `fix(web): correct PanelEntry shell docs (R3-001)` → `fix(web): route dashboard data roles through var(--corp-value) (R3-002)` → `test(web): derive KPI assertions from mock data (R3-003/004)` → adopt PageFrame/PanelEntry.
- Delivery: stacked-to-main (chain_strategy cached). Slice-3 PR base = main; branch from current HEAD (includes slices 1-2 commits; diff narrows as #47/#52 merge).
- Rollback: `git revert` the slice commits (file-level; no token/schema change).

## Open Questions

- None blocking. (KbList literal tabular-nums noted as follow-up, not in this slice.)