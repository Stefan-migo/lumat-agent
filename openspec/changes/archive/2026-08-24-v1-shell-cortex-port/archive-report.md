# Archive Report — 2026-08-24-v1-shell-cortex-port

**Change**: 2026-08-24-v1-shell-cortex-port (V1 shell port to CortexDesign contract + sidebar bug fixes, slice-2)
**Archived**: 2026-08-24
**Status**: COMPLETE — 11/11 tasks, verified, reviewed, bound, archived.

## Summary

The v1 shell design decisions (dark green sidebar, white text-only panel header, collapsible icon-only sidebar) were ported onto the delivered CortexDesign/Calma Operacional contract: `PANEL_SHELL_STYLES` now consumes `--corp-*` slots / existing tokens only (hex-free), the header badge and user avatar reuse the `Badge`/`Avatar` primitives, and both user-reported sidebar bugs were fixed (collapse toggle escaping the shared 44px min-height; hover overflow contained via the `min-width:0` flex chain + `overflow:hidden` safety net). The stale `2026-08-20-v1-shell-header-and-bg` change is superseded (see `supersedes-2026-08-20.md`).

## Verification Evidence

| Gate | Result |
|------|--------|
| `cd web && npm test` | 304/304 passed (39 files) |
| `cd web && npx tsc -b` | exit 0 (both pre-existing AppShell.test.tsx errors TS6133/TS2345 fixed) |
| `cd web && npm run build-storybook` | exit 0 |
| `sdd-verify-validate` | valid: true, verdict pass (6/6 requirements, 12/12 scenarios) |
| Bug 2 real Storybook render | containment confirmed at 390/640/768/1024/1280px × expanded/collapsed (headless Chrome) |

## Native Review (RDD)

- Lineage: `review-e81ec386d25c38e3` (lens: review-reliability) — state **approved**, receipt created.
- Bound to this change via `gentle-ai review bind-sdd` (binding revision `sha256:da89568d...`, receipt hash `sha256:c804f474...`).
- `reviewGate`: **allow** — "explicit bound compact authority exactly matches the current repository".
- `gentle-ai review validate --gate post-apply`: **allow**.
- **Advisory findings (non-blocking, informational — follow-up work for the dashboard/story cleanup slice):**
  - R3-001 WARNING — `web/src/stories/pages/PanelEntry.stories.tsx:13` — docs claim sidebar brand + panel header form a "continuous top bar at the same height and color"; the header is white, the brand dark green: same height, NOT same color.
  - R3-002 WARNING — `web/src/stories/pages/Dashboard.stories.tsx:182-192` (+ :123) — data roles use literal `font-variant-numeric: tabular-nums` instead of `var(--corp-value)` (DS-TKN-11/CST-ALIAS-5 deviation re-introduced by the rewrite).
  - R3-003 SUGGESTION — `web/src/stories/pages/Dashboard.stories.test.tsx:10-18` — `initials()` helper duplicates the Avatar derivation; silent divergence risk.
  - R3-004 SUGGESTION — `web/src/stories/pages/Dashboard.stories.test.tsx:31-40` — hardcoded mock values; brittle to mock changes.

## Deviations (documented)

1. Bug 1 + Bug 2 merged into one `fix(web)` commit (`5b2d4992`) — the two CSS fixes land in the same uncommitted PanelShell re-author diff; interactive splitting was fragile.
2. Base nav color → `--corp-fg` (not `--corp-primary-fg`) — the base rule also serves the cream drawer; white text stays via the sidebar override.
3. 18px residual nav-button intrinsic overflow in expanded state is clipped by the intended `overflow:hidden` safety net; grid column stays fixed (192/96px).
4. Base nav hover → `--corp-surface-hover` (semantically identical to the old `--table-head-bg`); dark sidebar hover stays `--primary-700` (documented shell-scoped exception, ponytail note).

## Commits

| Hash | Subject |
|------|---------|
| `5b2d4992` | fix(web): size sidebar collapse toggle and contain hover overflow |
| `9e4b7aa9` | feat(web): port shell to --corp-* contract and reuse Badge/Avatar |
| `124e0962` | test(web): fix AppShell tsc errors and re-align story assertions |
| `4d47257e` | docs(openspec): record 2026-08-20-v1-shell-header-and-bg as superseded |
| `1cfbdd7b` | fix(web): remove duplicate view label from AppShell |

## Specs Merged

- `panel-design-system`: DS-SHELL-1..5 ADDED + DS-STORY-2 MODIFIED (new "Shell docs reference the contract" scenario) merged into `openspec/specs/panel-design-system/spec.md`.

## Rollback

`git revert` the 5 commits (file-level revert; tokens.css untouched, shell architecture unchanged). No schema/backend/API change.

## Follow-ups (chained D8 slice)

- Dashboard/story cleanup: hero, KPI/activity polish, `--corp-value` in `.dashboard-activity__time`, PageFrame overlap, and the R3-001..004 advisory findings.
- Remaining Corporate catalog components (Table, Tabs, Dialog, Tooltip, Popover, DropdownMenu, Accordion, Pagination).
- Optional count-up/fade-content.
- The working tree still holds the uncommitted chained-out files (`Dashboard.stories.*`, `PanelEntry.stories.*`, `PageFrame.*`, `mockData/dashboard.ts`) — they belong to the follow-up slice, not this change.

## Supersession

`openspec/changes/2026-08-20-v1-shell-header-and-bg/` (stale continuous-green-bar proposal) is **superseded** by this change: recorded, not deleted, archived abandoned. Its dir stays on disk untouched (see `supersedes-2026-08-20.md`).