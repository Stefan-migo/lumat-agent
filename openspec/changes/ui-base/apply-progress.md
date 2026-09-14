# Apply Progress: UI Base — PR 1 Foundation and Guards

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

- [ ] 2.1 Native popover/tooltip/dropdown mechanics and tests.
- [ ] 2.2 Native dialog and combobox-class control and tests.
- [ ] 2.3 CSS-only rail/skeleton and narrow Radix menu.
- [ ] 3.1–3.3 Storybook harness and story ownership/triage.
- [ ] 4.1–4.2 Documentation and final verification.

## Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain`, `stacked-to-main`).
- Current work unit: PR 1 — foundation and guards.
- Boundary: starts at the unchecked Phase 1 foundation tasks and ends after boundary, viewport-drift, and Vitest quarantine guards plus focused/full verification.
- Estimated review budget impact: 4 authored code/config/task files plus this evidence; well below the 400-line review budget. No Phase 2–4 implementation included.
