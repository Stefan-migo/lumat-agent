# Archive Report — 2026-08-24-dashboard-cleanup

**Change**: 2026-08-24-dashboard-cleanup (Dashboard and story cleanup, slice-3)
**Archived**: 2026-08-24
**Status**: COMPLETE — 4/4 tasks, verified, reviewed, bound, archived.

## Summary

Adopted the chained-out dashboard/story working-tree files into the CortexDesign/Calma Operacional contract and resolved all 4 advisory findings (R3-001..004) from the slice-2 native review: accurate PanelEntry shell docs (brand dark green / header white, same height), `var(--corp-value)` on all dashboard data roles (KPI values via the primitives rule, activity time explicitly), KPI story/tests derived from the new `kpis` mock export, and the `initials()` helper documented with a lockstep note.

## Verification Evidence

| Gate | Result |
|------|--------|
| `cd web && npm test` | 304/304 passed (39 files) |
| `cd web && npx tsc -b` | exit 0 |
| `cd web && npm run build-storybook` | exit 0 |
| `sdd-verify-validate` | valid: true, verdict pass (3/3 requirements, 5/5 scenarios) |
| Hex walk / literal scan | zero hex; zero literal tabular-nums in slice files |

## Native Review (RDD)

- Lineage: `review-a3149471df2b0ee4` (lens: review-reliability) — state **approved**, receipt created.
- Bound to this change via `gentle-ai review bind-sdd` (binding revision `sha256:28c894cb...`).
- `reviewGate`: **allow** — "explicit bound compact authority exactly matches the current repository".
- **Advisory findings (non-blocking SUGGESTIONs, follow-up notes):**
  - R3-005 — `web/src/stories/pages/Dashboard.stories.tsx:183` — KPI value tabular-nums inherited from the primitives `.kpi__value` rule; no local fallback.
  - R3-006 — `web/src/stories/pages/Dashboard.stories.test.tsx:34` — KPI card scope couples to the `.kpi` class with a non-null assertion.

## R3 Findings Resolution (from slice-2 review)

| Finding | Resolution |
|---------|------------|
| R3-001 WARNING | ✅ Fixed — PanelEntry docs accurate |
| R3-002 WARNING | ✅ Fixed — var(--corp-value) on data roles |
| R3-003 SUGGESTION | ✅ Accepted — lockstep comment on initials() |
| R3-004 SUGGESTION | ✅ Fixed — kpis mock-derived assertions |

## Commits / PR

- Work units: fix(web) R3-001 · fix(web) R3-002 · test(web) R3-003/004 · docs(openspec) archive.
- Delivery: stacked-to-main (chain_strategy cached); slice-3 PR base = main.

## Specs Merged

- `panel-design-system`: DS-DASH-1 + DS-DASH-2 ADDED + DS-STORY-2 scenario extended ("Entry docs match the shell").

## Rollback

`git revert` the slice commits (file-level; no token/schema change).

## Follow-ups

- KbList.stories.tsx literal tabular-nums (same DS-TKN-11 class, different page).
- R3-005/006 advisory suggestions.
- Remaining Corporate catalog components; optional count-up/fade-content.