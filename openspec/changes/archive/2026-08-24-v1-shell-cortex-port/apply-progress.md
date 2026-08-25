# Apply Progress — V1 shell port to CortexDesign contract + sidebar bug fixes (slice-2)

> Change: `2026-08-24-v1-shell-cortex-port` · Project: lumat-agent · 2026-08-24
> Mode: **Strict TDD** (vitest + RTL) · Delivery: single PR ~380 lines (auto-chain resolved: no chaining)
> Status: **11/11 tasks complete** — Ready for verify

## Execution Context

- `applyState`: ready → success (full change implemented in one batch).
- Artifact store: `both` (openspec change dir + engram topic `sdd/2026-08-24-v1-shell-cortex-port/apply-progress`).
- Workload forecast resolved: `auto-chain` → ~380 changed lines, `400-line budget risk: Low`, `Chained PRs: No`, no `size:exception` needed.
- Graph check (5-Step Gate): queried `graphify query "PanelShell sidebar"` + `graphify path`. Graph is stale @ d8f26896 (2026-08-20, per design notes) but structurally valid for the touched files.

## Completed Tasks

| ID | Task | Result | Evidence |
|----|------|--------|----------|
| 1.1 | Collapse toggle: `min-height: 2.25rem` escapes 44px shared rule, keep 2.5rem box ≥40px hit | ✅ | `.panel-shell__collapse-button { min-height:2.25rem; width/height:2.5rem }` + RED story test → GREEN |
| 1.2 | `min-width: 0` on `.sidebar-inner` + `.navigation`; `overflow: hidden` on `.sidebar` | ✅ | CONTAINED in real Storybook at all widths |
| 2.1 | Retarget PANEL_SHELL_STYLES to `--corp-*` | ✅ | hex=0, `--surface`=0, `--primary-8xx`=0 |
| 2.2 | Dark-hover `--primary-700` exception + ponytail note | ✅ | ponytail note at `.sidebar .navigation-button:hover` |
| 2.3 | Reuse Badge + Avatar; drop `.panel-shell__avatar` CSS | ✅ | imports + slot/avatar JSX; CSS removed |
| 3.1 | Fix TS6133 + TS2345 in AppShell.test.tsx | ✅ | `npx tsc -b` exit 0 |
| 3.2 | AppShell.stories.test.tsx re-target + new guards | ✅ | tracked; 13 tests pass |
| 3.3 | AppShell.stories.tsx DS-STORY-2 copy re-target | ✅ | `--corp-primary` copy |
| 3.4 | tsc green + npm test ≥300 incl hex walk | ✅ | 304 passed |
| 4.1 | Real Storybook manual gate (Bug 2 containment) | ✅ | computed-style + screenshot evidence |
| 4.2 | Supersession docs(openspec) commit | ✅ | `4d47257e` |

## TDD Cycle Evidence (Strict TDD)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `AppShell.stories.test.tsx` | Story/source (RTL+regex) | ✅ 300 baseline | ✅ Written first (min-height/width/height asserts) | ✅ Passed | ✅ Bug1 sizing + anchoring + Bug2 → multiple asserts | ➖ None needed |
| 1.2 | `AppShell.stories.test.tsx` | Story/source | ✅ | ✅ Written first (min-width ×2 + overflow) | ✅ Passed | ✅ Bug 2 containment + mobile N/A | ➖ None needed |
| 2.1-2.2 | `AppShell.stories.test.tsx` | Story/source | ✅ | ✅ DS-SHELL-3 (hex-free, no `--surface`/`--primary-8xx`) RED → brand-bg `--corp-primary` RED | ✅ Passed (2→0 RED) | ✅ header-title assertion lockstep | ➖ None needed |
| 2.3 | `AppShell.test.tsx` (existing, unchanged behavior) + story | — | ✅ | Test by story render (Badge/Avatar in DOM) | ✅ Passed | ✅ N/A (structural slot swap) | ✅ removed hand-rolled CSS |
| 3.1 | `AppShell.test.tsx` | Unit (RTL) | ✅ 5/5 | RED = `npx tsc -b` (TS6133/2345 present) | ✅ `tsc -b` exit 0 | ✅ 5 tests still pass | ✅ |
| 3.2 | `AppShell.stories.test.tsx` | Story | ✅ | inherent in 1.1/1.2/2.x RED | ✅ 13 tests pass | ✅ | ✅ |

> Note: Bug 1/Bug 2/contract assertions are raw-source regex guards in the stories test (project pattern — the strict-tdd "no CSS class assertions" rule governs behavioral assertions; these are deliberate source-contract guards matching the existing DS-V1-SHELL pattern). jsdom cannot measure layout, so Bug 2's overflow is proven in the real Storybook render (task 4.1).

## Work Unit Evidence

| Evidence | Value |
|----------|-------|
| Focused test cmd + result | `cd web && npx vitest run src/stories/domain/AppShell.stories.test.tsx` → 13 pass; `src/components/domain/AppShell.test.tsx` → 5 pass |
| Runtime harness cmd + result | `npm run build-storybook` exit 0; Selenium headless Chrome over live Storybook `domain/AppShell` at 390/640/768/1024/1280px × expanded/collapsed → containment PASS |
| Rollback boundary | `git revert` the 3 code/test commits (`5b2d4992`, `9e4b7aa9`, `124e0962`) → PanelShell + AppShell.test + stories diff; token layer untouched (tokens.css unchanged), clean file-level revert |

## Real Storybook verification (task 4.1 — NOT skippable)

`npm run build-storybook` exit 0. Driven the live Storybook `domain/AppShell` (Admin story) in headless Chrome at every reference width × expanded/collapsed:

| Width | State | Sidebar display | Grid column (fixed) | Sidebar clientW | overflow | Result |
|-------|-------|-----------------|---------------------|-----------------|----------|--------|
| 390 | exp+coll | none (drawer) | — | — | — | PASS (no desktop sidebar to spill) |
| 640 | exp+coll | none (drawer) | — | — | — | PASS |
| 768 | exp+coll | none (drawer) | — | — | — | PASS |
| 1024 | expanded | block | `192px` | 191px (≤192) | hidden | PASS |
| 1024 | collapsed | block | `96px` | 95px (≤96) | hidden | PASS |
| 1280 | expanded | block | `192px` | 191px (≤192) | hidden | PASS |
| 1280 | collapsed | block | `96px` | 95px (≤96) | hidden | PASS |

- Grid column stays exactly `calc(--space-8 * 6)`=192px / `calc(--space-8 * 3)`=96px; the sidebar box never exceeds its fixed track.
- `min-width: 0` confirmed on `.sidebar-inner`/`.navigation` (computed `0px`).
- `overflow: hidden` clips the nav button's residual intrinsic min-content (209px vs 191px box) exactly at the sidebar edge → hover / `aria-current` paint CANNOT spill past the sidebar edge.
- Screenshots: `/tmp/opencode/shell-1280-expanded.png`, `shell-1280-collapsed.png`, `shell-1024.png`, `shell-390.png`.
- Collapse toggle computed 2.5rem × 2.5rem (40px) box, ≥40px hit target; escaped 44px shared min-height via `min-height:2.25rem`.

## Files Changed (this apply)

| File | Action | What Was Done |
|------|--------|----------------|
| `web/src/components/domain/PanelShell.tsx` | Modified | Bug 1 (`min-height:2.25rem`), Bug 2 (`min-width:0` ×2 + `overflow:hidden`), `--corp-*` re-target, Badge/Avatar reuse, ponytail dark-hover note, `.avatar` CSS dropped |
| `web/src/components/domain/AppShell.test.tsx` | Modified | TS6133 (unused `s`) removed, TS2345 (`clientesBtn!` non-null) fixed |
| `web/src/stories/domain/AppShell.stories.test.tsx` | Added (tracked) | Re-target brand-bg/header-title to `--corp-*`; new DS-SHELL-1/2/3 guards (toggle size, min-width chain + overflow, hex-free no-leak) |
| `web/src/stories/domain/AppShell.stories.tsx` | Modified | DS-STORY-2 docs re-target to `--corp-primary`/`--corp-*` |
| `openspec/changes/2026-08-24-v1-shell-cortex-port/supersedes-2026-08-20.md` | Added | Supersession record (task 4.2) |
| `openspec/changes/2026-08-24-v1-shell-cortex-port/tasks.md` | Modified | 11/11 tasks `[x]` |
| `web/src/tokens/tokens.css` | — | Unchanged (verified no D7 touch) |

## Commits

| Hash | Subject |
|------|---------|
| `5b2d4992` | fix(web): size sidebar collapse toggle and contain hover overflow |
| `9e4b7aa9` | feat(web): port shell to --corp-* contract and reuse Badge/Avatar |
| `124e0962` | test(web): fix AppShell tsc errors and re-align story assertions |
| `4d47257e` | docs(openspec): record 2026-08-20-v1-shell-header-and-bg as superseded |
| `1cfbdd7b` | fix(web): remove duplicate view label from AppShell |

> **Commit-candidate consistency note (corrective):** the earlier verification evidence and gates
> (npm test 304, `tsc -b` exit 0, build-storybook exit 0) were collected against the **working tree**,
> which at that point still carried an uncommitted `AppShell.tsx` `<h2>`-removal (duplicate view label)
> that the committed candidate lacked. That drift is now **committed** in `1cfbdd7b`, so the committed
> candidate is self-consistent. All three gates have been re-run against the committed candidate and
> remain green: `npx tsc -b` exit 0, `npm test` 304 passed, `npm run build-storybook` exit 0.
> Working-tree drift is limited to the chained-out dashboard/story slice; no implementation file of
> this change is uncommitted.

## Graph Nodes Consulted

`PanelShell.tsx` (root), `AppShell.tsx`, `AppShell.test.tsx`, `AppShell.stories.tsx`, `AppShell.stories.test.tsx`, `Badge.tsx`, `Avatar.tsx`, `primitives.css`, `tokens.css` (`--corp-*`). Communities: `AppShell.tsx`, `AppShell.stories.tsx`. (Graph stale @ d8f26896; structural nodes valid per design; Avatar/Badge shipped post-graph, read from source.)

## Deviations from Design

1. **Commit count (Bug 1 + Bug 2 merged)**: delivery plan listed `fix(web)` ×2 (one per bug). The two CSS fixes land in the same `PanelShell.tsx` working diff (the whole v1-shell re-author is uncommitted), so they were staged and committed together as one `fix(web)` commit (`5b2d4992`) instead of two. Same reviewable story, fewer fragile interactive-staging splits.
2. **`:269` base nav color → `--corp-fg`, not `--corp-primary-fg`**: design.md:32 lists `:269` under "white/nav text → --corp-primary-fg", but in the current working tree `:269` is the *base* `.panel-shell__navigation-button { color: var(--text) }` which also serves the cream drawer. Re-targeting it to `--corp-primary-fg` (white) would make drawer nav text invisible on cream. Converted to `--corp-fg` (== `--text`, contract-resolving, still dark) instead; the white sidebar text stays via the `.sidebar` override → `--corp-primary-fg`.
3. **Base nav hover `--table-head-bg` → `--corp-surface-hover`** (semantically identical; the light drawer hover), keeping the `--corp-*`-only read while the dark sidebar hover stays `--primary-700`.
4. `AppShell.stories.tsx` was committed inside the `feat` commit (it's docs-owned-by-contract, DS-STORY-2) rather than the separate `test(web)` commit — docs traveled with the contract port per work-unit-commits.

## Issues Found

- None blocking. The residual nav-button intrinsic width (18px clipped) in expanded state is the intended `overflow:hidden` safety-net behavior; the grid column and sidebar box both stay fixed (verified). Screenshots confirm no visible spill.

## Next Steps

- `sdd-verify` (independent verification of all 11 tasks + gates).
- `sdd-archive` — merges the `panel-design-system` delta spec into `openspec/specs/`, moves the change dir to `changes/archive/`, and (per the supersedes record) marks `2026-08-20-v1-shell-header-and-bg` abandoned.
- Follow-up slice (chained D8): dashboard/story cleanup (hero, KPI/activity polish, `--corp-value` in `.dashboard-activity__time`, PageFrame overlap), remaining Corporate components.

## Final Gates (committed candidate, re-verified after `1cfbdd7b`)

- `cd web && npx tsc -b` → **exit 0** ✅
- `cd web && npm test` → **304 passed** (39 files, ≥300) ✅
- `cd web && npm run build-storybook` → **exit 0** ✅
- Hex walk / no-leak: PanelShell has 0 hex, 0 `--surface`, 0 `--primary-8xx` ✅
- Commit-candidate consistency: `git show HEAD:web/src/components/domain/AppShell.tsx` has 0 `<h2>`; `git status` clean for all implementation files ✅
