# Apply Progress: UI Base

## Mode

Standard web/Vitest mode. `openspec/config.yaml` enables strict TDD for the
backend Python runner (`pytest`), but this assigned slice has no applicable
pytest surface and is scoped to web/Vitest. The established web-slice
precedent is additive guard extension; new behavior was tested first where
applicable. The pytest `strict-tdd.md` module was not loaded.

## Completed Tasks

- [x] 1.1 Added `web/src/components/dependency-boundary.test.ts`, recursively scanning component `.ts`/`.tsx` files for static and dynamic imports resolving under stories, with the exact two-importer allowlist.
- [x] 1.2 Extended the existing viewport guard to parse `tokens.css`, require `bp-sm`, `bp-md`, and `bp-lg` alignment, and preserve permitted 390px and 768px presets.
- [x] 1.3 Added Vitest quarantine exclusion while retaining the default `node_modules` exclusion; Storybook discovery remains `src/stories/**/*.stories.tsx`.

## Files Changed

| File | Action | Description |
|---|---|---|
| `web/src/components/dependency-boundary.test.ts` | Created | Exact production-to-story import boundary scan. |
| `web/src/stories/pages/PanelEntry.stories.test.tsx` | Modified | Token-to-Storybook viewport drift guard extension. |
| `web/vite.config.ts` | Modified | Excludes quarantine tests and preserves `node_modules` exclusion. |
| `openspec/changes/ui-base/tasks.md` | Modified | Marked Phase 1 tasks complete. |
| `openspec/changes/ui-base/apply-progress.md` | Created | This cumulative work-unit evidence. |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `cd web && npm test -- --run src/components/dependency-boundary.test.ts src/stories/pages/PanelEntry.stories.test.tsx` — passed, 2 files and 17 tests. |
| Runtime harness command/scenario and exact result | `N/A` — this work unit contains source/config guards only; no runtime boundary exists. |
| Rollback boundary | Revert `web/src/components/dependency-boundary.test.ts`, the viewport test addition in `web/src/stories/pages/PanelEntry.stories.test.tsx`, `web/vite.config.ts`, and the Phase 1 task/progress artifacts. |

## Full Verification Evidence

- `cd web && npm test` — passed, 73 files and 525 tests.
- `cd web && npm run build` — passed; TypeScript build and Vite production build completed.
- `git diff --check` — passed.

## Graph Check

- `graphify-out/GRAPH_REPORT.md` read at session start; graph contained 5,753 nodes and 12,213 edges, with `preview.ts`, `PanelShell.tsx`, `package.json`, and the UI Base change artifacts among the relevant nodes.
- Task 1.1 query: `dependency boundary source scan components imports stories exact allowlist`; path `web/src/components` → `web/src/stories` was queried but no directed path was found. Consulted `dependency-boundary.test.ts`, `Requirement: IAC-2 — Context Boundary`, and `Stories _shared Helpers Origin (pre-promotion)`.
- Task 1.2 query: `viewport drift guard preview presets tokens breakpoint values`; path `preview.ts` → `tokens.css` found the direct `references` edge. Consulted `preview.ts`, `tokens.css`, `tokens.test.ts drift guard`, and `DS-STORY-7 — Viewports Aligned to Breakpoints`.
- Task 1.3 query: `Vitest test exclude Storybook quarantine discovery src stories`; path `vite.config.ts` → `main.ts` was queried but no directed path was found. Consulted `vitest`, `storybook`, `package.json`, `preview.ts`, and the UI Base design/spec nodes.

## Ponytail Pre-Apply Review

No plan to cut from this slice. The implementation uses Vitest, Node filesystem/path APIs, and the existing guard test rather than adding dependencies or abstractions.

## Deviations from Design

None — implementation matches the assigned Phase 1 design and task scope.

## Issues Found

- The initial `test.exclude` override removed Vitest's default `node_modules` exclusion, causing dependency test failures. The configuration now explicitly retains `**/node_modules/**` alongside the requested quarantine pattern.
- Existing unrelated React `act(...)` warnings and jsdom navigation warnings remain in the full suite; all tests pass.
- `npm install` reported five moderate dependency audit findings in the existing toolchain; no dependency was added or changed by this slice.

## Remaining Tasks

- [ ] 3.1–3.3 Storybook harness and story ownership/triage.
- [ ] 4.1–4.2 Documentation and final verification.

Delivered: 2.1–2.3 across PRs #187–#191; 2.4 (post-slice touch guard) in PR #192.

## Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain`, `stacked-to-main`).
- Current work unit: PR 1 — foundation and guards.
- Boundary: starts at the unchecked Phase 1 foundation tasks and ends after boundary, viewport-drift, and Vitest quarantine guards plus focused/full verification.
- Estimated review budget impact: 4 authored code/config/task files plus this evidence; well below the 400-line review budget. No Phase 2–4 implementation included.

---

## Work Unit — touch guard (PR #192)

### Status

Delivered as **PR #192**, stacked on `feat/ui-base-radix-menu` (#191). Branch
`feat/ui-base-touch-guard`, commit `24e55b8b`. Registers task **2.4**, which was
added post-slice from the gatekeeper finding.

### What changed

| File | Action | Description |
|---|---|---|
| `web/src/components/primitives/primitives.css` | Modified | `.combobox__option` rejoins the single D7 `@media (hover: none)` block; the block comment now names the test that enforces the one-block rule. |
| `web/src/tokens/tokens.test.ts` | Modified | D7 test rewritten: asserts exactly one `@media (hover: none)` block plus its required selector set. |
| `openspec/changes/ui-base/tasks.md` | Modified | Registered 2.4 and reconciled the Phase 2 checkboxes. |
| `openspec/changes/ui-base/apply-progress.md` | Modified | This entry. |

### Why this exists

The same defect shipped twice (combobox, then menu): each slice added its own
parallel `@media (hover: none)` block instead of extending the central one. The
rule lived only in a comment, and the D7 test used a non-global regex, so
`.match()` returned the first block and a second one passed green. The test could
not fail on the regression it was meant to guard.

The correction was also asymmetric: `.menu__item` was moved into the block, but
`.combobox__option` was not, so listbox options sat below the 44px touch target.
The combobox input stays covered by `.field__control`.

### Evidence

| Evidence | Result |
|---|---|
| Focused test | `cd web && npm test -- tokens` — passed, 2 files and 20 tests. |
| Negative check | Injecting a second `@media (hover: none)` block fails with `touch sizing must live in exactly one @media (hover: none) block: expected 2 to be 1`; the injected block was removed afterwards. |
| Full suite | `cd web && npm test` — passed, 79 files and 550 tests. |
| Typecheck | `cd web && npx tsc -b` — clean. |
| Rollback boundary | Revert the two source files. No dependency, config, or spec change. |

### Spec Check

No spec change. `CST-PRIM-3 — Control Height and Touch Target`
(`openspec/specs/corp-primitives/spec.md`) already requires the 44px touch target;
this slice makes the existing requirement executable.

### RDD

Review was explicitly declined for this candidate: `action: "declined"`,
`consent: "declined_this_candidate"`, no review record created; delivery proceeds
under ordinary repository policy. Note: RDD derived the candidate with
`--base-ref=main`, so the offered candidate spanned the whole stack (17 files /
1588 changed lines), not this 2-file slice.

---

## Work Unit — slice 3A: shell harness and shared closure (PR #193)

### Status

Delivered as **PR #193**, stacked on `feat/ui-base-touch-guard` (#192). Branch
`feat/ui-base-harness`. Registers tasks **3.1** and **3.3**.

### What changed

| File | Action | Description |
|---|---|---|
| `web/.storybook/preview.ts` | Modified | Global `primitives.css` import; outer `withPanelShell` wrapping each story in the production `PanelShell` with a deterministic fixture user; `withPanelSurface` kept as the inner wrapper (DS-SHELL-7). |
| `web/src/stories/pages/PanelEntry.stories.tsx` | Modified | Declares `parameters.panelShell = false` (its component IS `PanelShell`). |
| `web/src/stories/domain/AppShell.stories.tsx` | Modified | Declares `parameters.panelShell = false` (`AppShell` renders `PanelShell`). |
| `web/src/stories/pages/_shared/StateMessage.tsx` | Modified | Drops the duplicate rationale comment from the story re-export. |

### Gatekeeper finding (caught before commit)

The first pass applied `withPanelShell` to every story literally. That nested a
second shell around the two stories that already own one — `PanelEntry`
(`component: PanelShell`) and `AppShell` (`AppShell.tsx` returns `<PanelShell>`).
No test could catch it: jsdom has no layout. Resolved by an explicit opt-out
parameter read by the decorator, chosen by the maintainer.

### Evidence

| Evidence | Result |
|---|---|
| Full suite | `cd web && npm test` — passed, 79 files and 550 tests. |
| Typecheck | `cd web && npx tsc -b` — clean. |
| `git diff --check` | Clean. |
| Rollback boundary | Revert `preview.ts` and the two `parameters.panelShell` lines; the removed comment is not load-bearing. |

### Notes

- The removed rationale comment was partly stale: it described a `.dashboard-shell`
  scope that no longer exists in the codebase. The remaining contract is recorded
  by `DS-UI-FRAME` in the spec.
- Task 3.2 remains open (slice 3B).
- RDD review was not re-run: the native route derives `--base-ref=main`, so the
  candidate would be the whole stack rather than this slice.
