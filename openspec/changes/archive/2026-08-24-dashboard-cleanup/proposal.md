# Proposal: Dashboard and story cleanup — resolve R3 advisory findings (slice-3)

## Intent

Adopt the chained-out dashboard/story working-tree files into the delivered CortexDesign/Calma Operacional contract and resolve the 4 advisory findings (R3-001..004) from the slice-2 native review (lineage review-e81ec386d25c38e3): accurate shell docs, `var(--corp-value)` on all data roles, and mock-derived KPI assertions.

## Current-State Gap

- PanelEntry.stories.tsx docs misdescribe the shell ("same height and color" — the header is white, the brand dark green).
- Dashboard KPI values and activity times use literal `tabular-nums` instead of `var(--corp-value)` (DS-TKN-11/CST-ALIAS-5).
- Dashboard tests hardcode KPI literals and duplicate the Avatar initials rule without a lockstep note.
- The chained-out working-tree files (Dashboard/PanelEntry/PageFrame/mockData) are not yet committed.

## Scope

### In Scope
1. R3-001: PanelEntry.stories.tsx docs — accurate shell description (same height; brand dark green, header white).
2. R3-002: Dashboard.stories.tsx — remove inline tabular-nums overrides (primitives `.kpi__value` provides `var(--corp-value)`); `.dashboard-activity__time` → `var(--corp-value)`.
3. R3-003: Dashboard.stories.test.tsx — keep `initials()` helper with strengthened lockstep comment (accepted SUGGESTION).
4. R3-004: mockData/dashboard.ts gains `kpis` export (Kpi interface); story renders from `kpis`; test derives from `kpis`.
5. Adopt the chained-out files into the change (committed with work-unit commits).
6. Gates: `npm test` 304+, `npx tsc -b` exit 0, zero hex, zero literal tabular-nums in slice files.

### Out of Scope
- KbList.stories.tsx literal tabular-nums (same class, different page — noted follow-up).
- Remaining Corporate catalog components; optional count-up/fade-content; icon library; dark mode; Jinja migration.

## Approach

Fix docs copy → re-target data roles to var(--corp-value) → add kpis mock + derive story/test → gates → review → archive → PR (stacked-to-main).

## Risks

| Risk | Mitigation |
|------|------------|
| tsc strictness on closest/within types | Fixed with closest<HTMLElement> |
| Review budget ~440 diff lines (adoption of chained-out rework) | auto-chain + stacked-to-main (chain_strategy cached) |
| Literal values elsewhere (KbList) | Noted follow-up, out of scope |

## Success Criteria

- [ ] R3-001..004 resolved (docs accurate; var(--corp-value) on data roles; KPI assertions mock-derived).
- [ ] `npm test` 304+, `npx tsc -b` exit 0, zero hex, zero literal tabular-nums in slice files.
- [ ] Chained-out files committed; stacked-to-main PR created.