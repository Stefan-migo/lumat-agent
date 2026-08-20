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

---

# Apply Progress: Storybook Redesign — S2 (Phase 2: Shared frame + label maps)

Change: `2026-08-20-storybook-redesign`
Slice: **S2 / PR 2** (stacked-to-main chain; branch from S1 head, PR targets `main`)
Mode: **Strict TDD** (web), artifact store: **hybrid** (OpenSpec + Engram)

Status: **S2 complete — tasks 2.1–2.7 done**

## Completed Tasks

- [x] **2.1** RED — `toneMaps.test.ts` + `StatusBadge.test.tsx`: every typed `types.ts` state (CustomerState, MessageDirection) + documented conversation/case/KB values resolve to a non-empty approved Spanish label; raw key never leaks. 19 failing tests first.
- [x] **2.2** GREEN — `_shared/toneMaps.ts`: added `conversationLabel`/`customerStateLabel`/`caseStatusLabel`/`kbStatusLabel`/`directionLabel` per the design LABELS table.
- [x] **2.3** GREEN — `primitives/StatusBadge.tsx`: `label` prop + Spanish default map; renders label, never raw state.
- [x] **2.4** GREEN — `SearchInput.tsx` default `aria-label="Buscar"`; `SearchInput.test.tsx` L10 updated.
- [x] **2.5** GREEN — Promoted `_shared/StateMessage.tsx` (tone/role/title/detail/spinner), created `_shared/PageFrame.tsx` (titlebar lime rail + `--primary-100` tint + banner slot + content). Dashboard consumes `StateMessage`; sentinel green. Role-pairing test (DS-UI-FRAME) added.
- [x] **2.6** GREEN — `DataTable.tsx` ES defaults (`No hay registros`/`Acciones` headers prop), `loading`/`stale`, `tabularNum` helper; `StatCard.tsx` tabular-num core. `helpers.test`/`DataTable.test` EN → Spanish.
- [x] **2.7** Primitives stories copy — StatusBadge/SearchInput/Badge/Card EN → neutral Chilean Spanish (DS-UI-COPY).

## TDD Cycle Evidence (Strict TDD)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1/2.2 | `_shared/toneMaps.test.ts` | Unit | 12/12 | ✅ 19 tests | ✅ 27/27 | ✅ 5 label sets + exact-label asserts | ✅ clean |
| 2.3 | `primitives/StatusBadge.test.tsx` | Unit | 2/2 | ✅ 3 new | ✅ 5/5 | ✅ 5 statuses + label prop | ✅ clean |
| 2.4 | `primitives/SearchInput.test.tsx` | Unit | 1/1 | ✅ 1 | ✅ 1/1 | ➖ Single (one default) | ➖ None |
| 2.5 | `_shared/StateMessage.test.tsx` + `PageFrame.test.tsx` | Unit | N/A (new) | ✅ written | ✅ 9/9 | ✅ role-pair, detail, spinner, tone | ✅ clean |
| 2.6 | `_shared/DataTable.test.tsx` + `helpers.test.tsx` | Unit | 14/14 | ✅ 6 new | ✅ 19/19 | ✅ defaults+loading+stale+tabularNum | ✅ clean |
| 2.7 | primitives stories (copy) | N/A (copy) | ✅ 4/4 | ➖ behavioral only | ✅ pass | ➖ single (copy swap) | ➖ None |

## Test Summary

- **Total tests passing**: 241/241 (38 files) — full suite green.
- **New tests written**: 7 in toneMaps.test (label suites incl. per-set triangulates), 3 in StatusBadge.test, 9 in StateMessage/PageFrame, +19 net DataTable/helpers.
- **Safety Net**: 38/38 on the touched files before edits; 9/9 on ConversationsList (confirmed broken ONLY by the S2 StatusBadge label change, not pre-existing).

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command + result | `cd web && npx vitest run ...(task files)` → each unit GREEN; full `cd web && npm test` → **241/241 (38 files)** |
| Type check | `cd web && npx tsc --noEmit` → **exit 0** |
| Runtime/integration harness | `cd web && npm run build-storybook` → **built OK** (exit 0). Dashboard sentinel: `Dashboard.stories.test.tsx` 9/9 green; rendered output identical (promoted StateMessage emits the same `dashboard-state` classes styled by unchanged `DASHBOARD_STYLES`). |
| Rollback boundary | Revert the 20 S2 web files (16 modified + 4 new). Page stories (production) untouched; Dashboard only adopted the promoted StateMessage (same markup). The SDD planning folder is NOT part of S2 (it ships on S1). |

## Deviations from Design

1. **Cross-slice dependency (flagged)**: `StatusBadge` now renders Spanish by default (design D4, S2 scope), immediately invalidating the `ConversationsList.stories.test.tsx` raw-state badge assertions (scheduled for S4 task 4.4). To keep the green gate, I updated only those 2 badge assertions to the approved Spanish labels (test-only, no page story change) and documented it in the PR body. This is a design-sequencing miss worth revisiting if a future slice re-orders the StatusBadge work.
2. **`tabularNum` signature**: design contract listed it inside `DataTableProps` as `(row, cell) => ReactNode`; I exported it as a standalone `tabularNum(cell)` column helper (D6 "column helper" intent), cleaner for use inside a column's `render`. No consumer exists yet.
3. **`pending` label**: the design LABELS `conversation` map only named bot/human/closed, but `StatusBadge` supports 5 statuses; I added `pending → "En espera"` (and reused `escalated → "Escalado"`) so the badge never renders a raw state. Spec-compliant (DS-UI-COPY/LABELS).
4. **Dependency direction**: `StatusBadge` (primitives) imports `conversationLabel` from `stories/pages/_shared/toneMaps` (app layer) per design D1. Acceptable (pure leaf util) but an inversion noted for a future move if `primitives` must stay dependency-free.

## Issues Found

- The S2 changed-line count (**703** = 575+/128−) exceeds both the ~350 slice forecast and the 400-line budget, due to strict-TDD triangulation coverage and the cross-slice ConversationsList fix. Review budget noted in PR body; orchestrator may elect a further split.

## Files Changed (S2)

| File | Action | What Was Done |
|------|--------|---------------|
| `web/src/stories/pages/_shared/toneMaps.ts` + `.test.ts` | Modified | +5 label maps + tests (task 2.1–2.3) |
| `web/src/components/primitives/StatusBadge.tsx` + `.test.tsx` | Modified | label prop + ES default map (task 2.3) |
| `web/src/components/primitives/SearchInput.tsx` + `.test.tsx` | Modified | default aria-label `Buscar` (task 2.4) |
| `web/src/stories/pages/_shared/StateMessage.tsx` + `.test.tsx` | Created | promoted banner + role-pairing tests (task 2.5) |
| `web/src/stories/pages/_shared/PageFrame.tsx` + `.test.tsx` | Created | shared page shell + tests (task 2.5) |
| `web/src/stories/pages/Dashboard.stories.tsx` | Modified | consume promoted StateMessage (sentinel) (task 2.5) |
| `web/src/stories/pages/_shared/DataTable.tsx` + `.test.tsx` | Modified | ES defaults, loading/stale, tabularNum (task 2.6) |
| `web/src/stories/pages/_shared/StatCard.tsx` | Modified | tabular-nums value core (task 2.6) |
| `web/src/stories/pages/_shared/helpers.test.tsx` | Modified | EN → Spanish assertions (task 2.6) |
| `web/src/stories/pages/ConversationsList.stories.test.tsx` | Modified | badge assertions → Spanish labels (cross-slice, flagged) |
| `web/src/stories/primitives/{StatusBadge,SearchInput,Badge,Card}.stories.tsx` | Modified | copy → neutral Chilean Spanish (task 2.7) |
| `openspec/.../tasks.md` + `apply-progress.md` | Modified | 2.1–2.7 `[x]`, S2 progress appended |

## Delivery / Branch / Commit / PR

- Chain strategy: `stacked-to-main`. PR 2 = S2 only.
- Branch: `feat/storybook-redesign-s2` (branched from S1 chain head `feat/storybook-redesign-s1`).
- Commits (5 work-unit, conventional, no AI attribution): `5b943792` (labels+StatusBadge), `8118eab9` (SearchInput aria), `28c37962` (StateMessage+PageFrame+Dashboard), `fd9919de` (DataTable/StatCard/helpers), `29a7f50b` (primitives copy).
- PR: **https://github.com/Stefan-migo/lumat-agent/pull/33** targeting `main` (position 2/6).

## Graph Record

Graph Check passed (mandatory gate). Queried `graphify query "shared frame page shell statemessage datatable statusbadge tonemaps label"` → BFS depth=2, 278 nodes. Nodes consulted: `StateMessage()`, `DataTable()`, `StatusBadge()`, `PageHeader.tsx`, `toneMaps.ts`, `types.ts`, `CustomerState/MessageDirection/Conversation/Case`, `Dashboard.stories.tsx`, `ConversationsList.stories.tsx`, `helpers.test.tsx`, `DataTable.test.tsx`, `StatusBadge.test.tsx`, `toneMaps.test.ts`, page story communities. Graph present at `graphify-out/` (refreshed at session close, not per-batch).
