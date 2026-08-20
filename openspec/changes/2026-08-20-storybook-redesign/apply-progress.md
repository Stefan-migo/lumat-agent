# Apply Progress: Storybook Redesign — S1 (Phase 1: `primitives.css` token swaps)

Change: `2026-08-20-storybook-redesign`
Slice: **S1 / PR 1** (stacked-to-main chain; PR targets `main`)
Mode: **Strict TDD** (web), artifact store: **hybrid** (OpenSpec + Engram)

Status: **S1 complete — tasks 1.1–1.4 done**

## Completed Tasks

- [x] **1.1** RED/assert-nothing — Confirmed no test asserts focus/motion values.
- [x] **1.2** `.btn` transition → `var(--duration-base)` / `var(--ease-out)`.
- [x] **1.3** `.btn:focus-visible`, `.field__control:focus`, `.search-input:focus-within` → `--focus-ring-width` / `--focus-ring` / `--focus-ring-offset` (outline width/color/offset; border-color → `--focus-ring`).
- [x] **1.4** `.spinner__indicator` border-top-color → `var(--info)`, `animation: spin var(--duration-slow) linear infinite`, added `prefers-reduced-motion: reduce` block disabling the spin.

## TDD Cycle Evidence (Strict TDD)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `web/src/components/primitives/*.test.tsx` + `web/src/tokens/tokens.test.ts` | Unit (grep audit) | ✅ 209/209 | ✅ Written (confirmation audit) | ✅ Passed | ➖ Single (assert-nothing task) | ➖ None needed |
| 1.2 | `web/src/tokens/tokens.test.ts` (drift guard) | N/A (CSS) | ✅ 209/209 | ➖ No testable runtime behavior | ✅ Passed (209/209 + guard) | ➖ Single (one declaration) | ➖ None needed |
| 1.3 | `web/src/tokens/tokens.test.ts` (drift guard) | N/A (CSS) | ✅ 209/209 | ➖ No testable runtime behavior | ✅ Passed (209/209 + guard) | ➖ Single set (3 rules, one spec scenario) | ➖ None needed |
| 1.4 | `web/src/tokens/tokens.test.ts` (drift guard) | N/A (CSS) | ✅ 209/209 | ➖ No testable runtime behavior | ✅ Passed (209/209 + guard) | ➖ Single (one declaration + media block) | ➖ None needed |

**RED rationale (tasks 1.2–1.4)**: These are token-equivalent CSS declarations with no testable runtime boundary. Per the strict-tdd module's Assertion Quality Rules, CSS-class and style assertions (e.g. `expect(el.style.color)`) are **banned patterns** ("CSS class assertions are NEVER valid test assertions"), and jsdom cannot compute outline/transition/animation from the stylesheet. Task 1.1 explicitly confirms no test asserts focus/motion values, and the orchestrator stated no test change is needed for this slice. Writing a RED test for a CSS declaration would itself violate the module, so RED is recorded as not-applicable with the drift guard (`tokens.test.ts` hex scan) carrying the verification: no new hex/magic values.

## Test Summary

- **Total tests passing**: 209/209 (36 files) — unchanged from baseline after all S1 edits.
- **Layers used**: Unit (behavioral primitives + guards); no new tests written (CSS-only slice).
- **Approval tests**: N/A — refactor is token-normalization, no behavior-bearing function exists for CSS.

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command + result | `cd web && npm test` → 36 files, **209/209 passed** (25.45s). Includes token drift guard (9/9) proving no new hex/magic values. |
| Type check | `cd web && npx tsc --noEmit` → **exit 0**. |
| Runtime/integration harness + result | `cd web && npm run build-storybook` → **built OK** (exit 0, `storybook-static` produced). CSS integrates into the rendered story bundle. |
| Rollback boundary | Revert `web/src/components/primitives/primitives.css` alone; no other file was modified (SDD pipeline artifacts `tasks.md`/`apply-progress.md` are additive and non-code). |

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `web/src/components/primitives/primitives.css` | Modified | Token-correct focus + motion swaps (tasks 1.2–1.4); +prefers-reduced-motion block. Token-equivalent, no behavior change. |
| `openspec/changes/2026-08-20-storybook-redesign/tasks.md` | Modified | Marked tasks 1.1–1.4 `[x]`. |
| `openspec/changes/2026-08-20-storybook-redesign/apply-progress.md` | Created (this file) | S1 apply progress. |

## Deviations from Design

None — implementation matches design D7 (`primitives.css` token swaps + reduced-motion block). One transparent note: `.field__control:focus` and `.search-input:focus-within` had `outline-offset: 1px`; replacing with `var(--focus-ring-offset)` normalizes it to `2px`. This is exactly what spec DS-UI-PRIMS mandates (`--focus-ring-width`/`--focus-ring`/`--focus-ring-offset`), so it is spec-compliant, but it is a real 1px→2px offset change on those two focus states.

## Issues Found

None. The spec/design resolve cleanly against existing tokens (`--duration-base`, `--ease-out`, `--focus-ring*`, `--info`, `--duration-slow` — all present in `tokens.css`, confirmed by `tokens.test.ts`).

## Remaining Tasks (not this slice)

Phase 2+ (S2–S6) remain. See `tasks.md`.

## Workload / PR Boundary

- Mode: **chained PR slice (stacked-to-main)** — PR 1.
- Current work unit: S1 — primitives.css focus/motion tokens.
- Boundary: starts from `main`, ends with PR 1 (CSS-only slice). Subsequent slices (S2–S6) land in later PRs targeting `main`.
- Review budget impact: ~28 changed lines (17 insertions, 11 deletions) — well under the 400-line budget.

## Delivery / Branch / Commit

- Chain strategy: `stacked-to-main` (each PR targets `main`, merged in order). PR 1 = S1 only.
- Branch: `feat/storybook-redesign-s1` (created from `main`).
- Commit: work-unit commit for S1 (conventional, no AI attribution).
- PR: targeting `main`, scoped to S1.

## Graph Record

Graph Check passed (mandatory gate). Queried: `graphify query "primitives css button spinner focus motion"` → BFS depth=2, 179 nodes; nodes consulted: `Button()`, `Button.tsx`, `Badge.tsx`, `StatusBadge.tsx`, `tokens.test.ts` (via drift guard), primitives test files. `graphify path "primitives.css" "tokens.css"` → no directed edge (CSS file not in node graph); verified token linkage directly via `tokens.css` + `tokens.test.ts`. Graph present at `graphify-out/` (refreshed at session close, not per-batch).
