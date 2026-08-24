# Tasks: V1 shell port to CortexDesign contract + sidebar bug fixes (slice-2)

> Change: `2026-08-24-v1-shell-cortex-port` · Project: lumat-agent · 2026-08-24

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

Single PR, ~380 lines, under 400; `auto-chain` has no trigger. Dashboard/story cleanup (D8) is chained to a later slice.

### Suggested Work Units

| Unit | Goal | PR | Focused test | Runtime harness | Rollback boundary |
|------|------|------|--------------|-----------------|-------------------|
| U1 | Bugs + `--corp-*` + primitives + tsc/stories + docs | PR 1 | `cd web && npx tsc -b && npm test` | `storybook` `domain/AppShell`, 390/640/768/1024/1280px × expanded/collapsed (Bug 2) | `git revert` the PanelShell + test/story re-author commit; tokens untouched |

## Phase 1 — Bug fixes (D1/D2 Bug 1, D4 Bug 2)

- [x] **1.1** `.panel-shell__collapse-button`: `min-height: 2.25rem` (escapes shared 44px `:252`), keep `width/height: 2.5rem` ≥40px hit; expanded `margin: 0 var(--space-3) var(--space-3)`, collapsed `align-self: center` (D2). [DS-SHELL-1]
- [x] **1.2** `PanelShell.tsx` `.panel-shell__sidebar-inner` + `.navigation`: add `min-width: 0`; `overflow: hidden` on `.panel-shell__sidebar` (safety). [DS-SHELL-2]

## Phase 2 — Contract re-target + primitives (D5/D3, D6)

- [x] **2.1** `PANEL_SHELL_STYLES` retarget (design.md:32): sidebar bg →`--corp-primary` (:151,186,195); white/nav text →`--corp-primary-fg` (:122,152,209,218,229,269,304); hairline `color-mix` →`--corp-primary-fg` (:185,228); role `--brand-aqua` stays (:168,233); drawer `--primary-900` stays (:423); header bg →`--corp-surface` (:382). [DS-SHELL-3]
- [x] **2.2** Dark-hover `:212-213` `--primary-700` hover + `--brand-lime` focus stay brand-scale, add `ponytail:` note on light `--corp-surface-hover` gap; no raw hex. [DS-SHELL-3]
- [x] **2.3** `statusBadge` slot → `<Badge>{statusBadge}</Badge>` in `.panel-shell__header-badge`; sidebar avatar span `:566` → `<Avatar name={user.username}>`; drop `.panel-shell__avatar` CSS; reuse `primitives/Badge` + `primitives/Avatar`. [DS-SHELL-4]

## Phase 3 — Tests / typecheck (D7)

- [x] **3.1** `AppShell.test.tsx`: fix TS6133 (:110) + TS2345 (:118). [DS-SHELL-5]
- [x] **3.2** `AppShell.stories.test.tsx` (untracked, drop in): `:44` brand-bg `--primary-800`→`--corp-primary`; keep lime-rule; add hex-free + `min-width:0`/`overflow:hidden` + `min-height:2.25rem` + no `--primary-8xx`/`--surface` leak in `PANEL_SHELL_STYLES`. RED→GREEN for Bug 1 sizing + Bug 2 containment. [DS-SHELL-5]
- [x] **3.3** `AppShell.stories.tsx`: DS-STORY-2 copy — `var(--primary-800)` (:16)→`--corp-primary`, state shell consumes `--corp-*` slots. [DS-STORY-2]
- [x] **3.4** Gate: `cd web && npx tsc -b` green, `cd web && npm test` ≥300 incl. hex walk. [DS-SHELL-5]

## Phase 4 — Verify + supersede

- [x] **4.1** Manual gate (NOT skippable): real Storybook `domain/AppShell` at 390/640/768/1024/1280px × expanded/collapsed — toggle 32–36px/≥40px hit, no hover/`aria-current` spill. [DS-SHELL-2]
- [x] **4.2** Supersession: `docs(openspec)` records `2026-08-20-v1-shell-header-and-bg` abandoned at archive; dir stays on disk, untouched. [design.md:69-71]

## Delivery Plan

Per-file work-unit commits (tests/docs travel with code):

1. `fix(web): size and anchor sidebar collapse toggle` — 1.1
2. `fix(web): contain sidebar hover overflow with min-width chain` — 1.2
3. `feat(web): port shell to --corp-* contract and reuse Badge/Avatar` — 2.1–2.3
4. `test(web): fix AppShell tsc errors and re-align story assertions` — 3.1–3.3
5. `docs(openspec): mark 2026-08-20-v1-shell-header-and-bg as superseded` — 4.2

Gate after each: `cd web && npx tsc -b && npm test`.

## Deferred (D8, no work this slice)

Dashboard/story cleanup (hero + `.dashboard-activity__time`→`--corp-value` + KPI polish), remaining Corporate components, optional count-up/fade-content.

## Notes

- Threat matrix `N/A` (CSS-only shell re-author; no routing/subprocess/VCS boundary). `tokens.css` untouched (D7 touches `.btn`/`.field__control` only).
