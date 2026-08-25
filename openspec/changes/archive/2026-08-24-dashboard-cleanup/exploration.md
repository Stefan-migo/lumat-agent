# Exploration — 2026-08-24-dashboard-cleanup

## Background

Slices 1-2 delivered the Calma Operacional design system (--corp-* aliases, primitives) and the shell port (sidebar bugs fixed, archived, PRs #47/#52). The dashboard/story cleanup was chained out of slice-2 (D8). The native review of slice-2 (lineage review-e81ec386d25c38e3, lens reliability) produced 4 advisory findings (R3-001..004) that define this slice's requirements.

## Working-tree state (adopted by this change)

The chained-out files are uncommitted in the working tree and become this change's scope:
- web/src/stories/pages/Dashboard.stories.tsx — friendly layout (hero, 3 KPI cards, activity card)
- web/src/stories/pages/Dashboard.stories.test.tsx
- web/src/stories/pages/PanelEntry.stories.tsx + .test.tsx
- web/src/stories/pages/_shared/PageFrame.tsx + .test.tsx
- web/src/stories/pages/_shared/mockData/dashboard.ts

## R3 findings plan

- **R3-001 (WARNING, PanelEntry.stories.tsx:13)**: docs claim sidebar brand + panel header form a "continuous top bar at the same height and color" — the header is white (--corp-surface), the brand dark green (--corp-primary): same height, NOT same color. Fix the copy to state both facts accurately.
- **R3-002 (WARNING, Dashboard.stories.tsx:182/187/192 + :123)**: KPI value cells use literal inline `font-variant-numeric: tabular-nums` (overriding the primitives `.kpi__value` rule which already resolves `var(--corp-value)` from slice-1) and `.dashboard-activity__time` uses the literal. Fix: remove the inline styles (the primitives rule applies) and re-target the time rule to `var(--corp-value)`.
- **R3-003 (SUGGESTION, Dashboard.stories.test.tsx:10-18)**: the inline `initials()` helper mirrors Avatar's derivation. Accepted as-is (comment already documents the mirror; exporting from Avatar adds surface — ponytail). Strengthen the comment with the lockstep note.
- **R3-004 (SUGGESTION, Dashboard.stories.test.tsx:31-40)**: KPI assertions hardcode literals. Fix: add a `kpis` export to mockData/dashboard.ts (Kpi interface: label/value/delta/deltaTone); story renders from `kpis`; test derives from `kpis`.

## Extra cleanup found

- KbList.stories.tsx:60-61 has the same literal `fontVariantNumeric: "tabular-nums"` inline style class (DS-TKN-11) — NOT in the chained-out set; noted as follow-up, left out of this slice to keep scope clean.
- PageFrame.tsx/.test.tsx already aligned (text-only titlebar, test renamed) — adopted as-is.

## Gates

- `cd web && npm test` — 304/304 (39 files)
- `cd web && npx tsc -b` — exit 0 (after TS2345 fix in the test: closest<HTMLElement>)
- Zero hex in dashboard files; zero literal tabular-nums remaining in the slice files.

## Ready for Proposal

Yes — small, fully specified slice (~440 diff lines incl. the adopted chained-out rework; ~60 lines are new edits).