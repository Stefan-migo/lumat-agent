# Apply Progress: Design System "Calma Operacional" — Slice-1 Catalog Adaptation

Change: `2026-08-24-design-system-calma-operacional`
Slice: **Slice-1 (B1–B4)** — single stacked-slice delivery, `auto-chain` resolved with no decision gate (Review Workload Forecast: ~330 lines, Chained PRs No, 400-line budget risk Low).
Mode: **Strict TDD** (web), artifact store: **hybrid** (OpenSpec + Engram)
Status: **Slice-1 complete — all 16 tasks (T1.1–T4.6) done**

## Completed Tasks

### Phase 1 — B1 Alias layer + hex-guard extension
- [x] **T1.1** Appended 17-slot `--corp-*` block to `tokens.css` `:root`. 13 mapped color/spacing slots resolve to `var(--*)`; `--corp-value: tabular-nums` behavioral (D3); `--corp-size/-w/-h` unresolved → component default with documented fallback warning (D2). Zero hex in the alias layer.
- [x] **T1.2** Test-first `tokens.test.ts`: new `corp-* alias layer` describe with 4 tests — 17 slots declared (14 resolvable, size/w/h unmatched fallbacks), every resolved slot maps to a declared `var(--*)` token, zero hex in the layer, spot-checks primary/bg/surface/value, fallback documented, pre-existing declarations byte-identical (CST-ALIAS-1/2/3/4 · DS-TKN-10).
- [x] **T1.3** Verified no hex literal in alias block; no existing token-test assertion removed (all prior 11 tests preserved).

### Phase 2 — B2 Primitives re-target + touch + states
- [x] **T2.1** `primitives.css` re-targeted slice-1 primitives to `--corp-*`: Button (`--corp-primary`, `--corp-primary-fg`, hover `--primary-700`), Card/SearchInput/field controls (`--corp-border`, `--corp-surface`, `--corp-text`, `--corp-fg-muted`, `--corp-radius`, `--corp-gap`), Badge tones (extra semantic pairs keep existing tokens), flash-message/pagination (D1/D4). Non-aliased tokens (`--border-strong`, `--danger-*`, `--success-*`, `--warning-*`, `--focus-ring*`) keep existing token references per CST-PRIM-1.
- [x] **T2.2** D7 touch block: one `@media (hover: none)` block setting `min-height: 44px` on `.btn` and `.field__control` (comma-grouped selector, no `::before`). Desktop keeps 40px.
- [x] **T2.3** D8 complete-states: documented shipped variants + CSS-only pairings in primitives.css header comment (Button disabled retains label+opacity; fields use `.field--disabled` muted bg+text; Badge/Card/StateMessage variants). **Button loading/empty explicitly deferred** (new props + spinner, no consumer — budget).
- [x] **T2.4** `StateMessage.tsx`: confirmed `STATE_TONES` already tokenized (`var(--*)` accent + tint) and `role="status"|"alert"` prop; added minimal Alert-compat comment (D5), no full BEM refactor this slice.
- [x] **T2.5** `StatusBadge`: confirmed already maps to `<Badge tone>` with `conversationLabel`; no `.tsx`/CSS change — covered by existing `StatusBadge.test.tsx` (tone map + approved Spanish labels + never raw status).

### Phase 3 — B3 Micro-changes
- [x] **T3.1** `StatCard.tsx` + `DataTable.tsx` + `primitives.css`: applied `font-variant-numeric: var(--corp-value)` on data roles — KPI value (StatCard `.kpi__value` + `.kpi__value` CSS), `tabularNum()` numeric cells, timestamps/IDs via the same helper. Decorative labels unaffected. Test-first: updated `DataTable.test.tsx` + `Settings.stories.test.tsx` to assert `var(--corp-value)` (RED against `tabular-nums`, GREEN after), plus `primitives.css` `.kpi__value` already resolved via `--corp-value` (CST-ALIAS-5 · DS-TKN-11).
- [x] **T3.2** `DESIGN_SYSTEM.md` line 120 Canvas row: `--bg` `#F4F5F7` → `#F1F1E8` (doc-only; executable token wins, DS-TKN-12). Verified no stale `#F4F5F7` remains in the doc.

### Phase 4 — B4 Tests + Storybook verification
- [x] **T4.1** `primitives*.test.tsx`: extended Button + Input with hex-free source scan of `primitives.css` and disabled-pairing semantics (native `disabled` + retained label; anchor `aria-disabled` + retained label) (CST-PRIM-1/4).
- [x] **T4.2** `tokens.test.ts`: alias spot-checks assert slots resolve to existing tokens; fallback size/w/h documented, never hardcoded (added in B1, verified).
- [x] **T4.3** `.btn`/`.field__control` ≥44px under `(hover:none)` — CSS media-check test added to `tokens.test.ts` reading `primitives.css` (CST-PRIM-3 · D7).
- [x] **T4.4** StateMessage state-matrix RTL: danger→`role=alert`, loading→`role=status` with visible Spanish label + tone accent/tint pairing (CST-PRIM-5).
- [x] **T4.5** `npm run build-storybook` green (exit 0, ~16s). Viewport presets verified in `.storybook/preview.ts` at 390/640/768/1024/1280px (mobile-compact/bp-sm/tablet-compact/bp-md/bp-lg). D7 touch block is `(hover:none)` only → does not activate under desktop Storybook viewport emulation, so the textarea is NOT undesirably rescaled (keeps `min-height: var(--space-8)` 32px + `resize: vertical` at hover-capable viewports).
- [x] **T4.6** Hex-free audit of newly changed files: `primitives.css`, `StateMessage.tsx`, `StatCard.tsx`, `DataTable.tsx` → zero hex. `tokens.css` → hex only in the legitimate `:root` token-source definitions (allowed by DS-TKN-1), none in the `--corp-*` alias block. `tokens.test.ts` hex only in literal expected-assertions (test source is excluded from the walk).

## TDD Cycle Evidence (Strict TDD)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tokens.test.ts` (corp-* alias describe) | Unit (CSS guard) | ✅ 287/287 | ✅ Written (failing: missing slots / 13 resolve) | ✅ Passed | ✅ 4 cases (slots, var-resolution, hex, fallback) | ➖ None (additive append) |
| 1.2 | `tokens.test.ts` | Unit | ✅ 287/287 | ✅ Written first (RED) | ✅ Passed 4/4 | ✅ spot-checks + byte-identical | ➖ None |
| 1.3 | `tokens.test.ts` (hex guard) | Unit | ✅ 287/287 | ✅ Written | ✅ Passed | ➖ Single | ➖ None |
| 2.1 | `tokens.test.ts` hex guard | N/A (CSS) | ✅ 287/287 | ➖ No runtime boundary (token-equivalent) | ✅ Passed | ➖ Single set | ➖ None |
| 2.2 | `tokens.test.ts` D7 media-check | N/A (CSS) | ✅ 287/287 | ➖ CSS media; verified in B4 (T4.3) | ✅ Passed (T4.3) | ➖ Single | ➖ None |
| 2.3 | D8 documentation + existing tests | N/A (docs/CSS) | ✅ 287/287 | ➖ No behavior change (deferred props) | ✅ Passed | ➖ Single | ➖ None |
| 2.4 | `StateMessage.test.tsx` (existing) | Unit (RTL) | ✅ 287/287 | ➖ Already tokenized (comment-only) | ✅ Passed | ➖ Single | ➖ None |
| 2.5 | `StatusBadge.test.tsx` (existing) | Unit (RTL) | ✅ 287/287 | ➖ No change (confirmed mapping) | ✅ Passed | ➖ Single | ➖ None |
| 3.1 | `DataTable.test.tsx` + `Settings.stories.test.tsx` | Unit (RTL) | ✅ 293/293 | ✅ Written (expect `var(--corp-value)`, RED vs `tabular-nums`) | ✅ Passed | ✅ 2 files (helper + cell) | ➖ None |
| 3.2 | DESIGN_SYSTEM.md (doc) | N/A (doc) | ✅ 293/293 | ➖ Doc-only | ✅ grep no stale | ➖ Single | ➖ None |
| 4.1 | `Button.test.tsx` + `Input.test.tsx` | Unit (RTL) | ✅ 293/293 | ✅ Written (hex scan + disabled pairing) | ✅ Passed | ✅ 3 cases | ➖ None |
| 4.2 | `tokens.test.ts` | Unit | ✅ 293/293 | ✅ Written (B1) | ✅ Passed | ➖ Covered in B1 | ➖ None |
| 4.3 | `tokens.test.ts` D7 media-check | Unit (CSS scan) | ✅ 293/293 | ✅ Written | ✅ Passed | ➖ Single | ➖ None |
| 4.4 | `StateMessage.test.tsx` | Unit (RTL) | ✅ 293/293 | ✅ Written | ✅ Passed | ✅ danger+loading | ➖ None |
| 4.5 | Storybook viewport | E2E (build) | ✅ 293/293 | ➖ No E2E harness installed | ✅ build-green | ➖ 5 viewports via presets | ➖ None |
| 4.6 | Hex-free audit | Unit guard | ✅ 293/293 | ✅ Written | ✅ Passed | ➖ Single | ➖ None |

**RED rationale (CSS-only tasks 2.1–2.3)**: token-equivalent CSS swaps with no testable runtime boundary; per strict-tdd Assertion Quality Rules, CSS-class/style assertions are banned and jsdom cannot compute stylesheet values. Verification carried by the `tokens.test.ts` hex-guard walk (already covers all of `web/src`) + the explicit B4 scans.

## Test Summary

- **Total tests passing**: 300/300 (39 files) — baseline was 287, +13 new slice tests (6 alias+guard in B1, 2 tabular in B3, Button/Input/StateMessage/D7 in B4).
- **Layers used**: Unit (behavioral RTL + CSS guard/source scans); Storybook build as integration harness.
- **Approval tests**: N/A — refactors are token-source/contract changes, not behavior-carrying functions.

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command + result | `cd web && npm test` → **300/300 passed** (39 files, 293 → 300 after +13). Includes token drift guard (17 tests) proving aliases resolve to tokens and pre-existing declarations are byte-identical. |
| Type check | `cd web && npx tsc -b` → **pre-existing failures ONLY in `web/src/components/domain/AppShell.test.tsx` (2 errors, TS6133 + TS2345)** from the uncommitted v1-shell working-tree change — outside slice-1 scope. All slice-1 files tsc-clean (no errors in any `tokens.*`, `primitives.*`, `_shared/*`, `DESIGN_SYSTEM`). |
| Runtime/integration harness + result | `cd web && npm run build-storybook` → **exit 0**, `storybook-static` produced (~16s). Viewport presets 390/640/768/1024/1280px present in `.storybook/preview.ts`; D7 block is `(hover:none)`-only so textarea not rescaled in desktop emulation. |
| Rollback boundary | B1: delete `--corp-*` block from `tokens.css` + revert `tokens.test.ts`. B2: `git revert` `primitives.css` + `_shared/StateMessage.tsx` (primitives fall back to prior token-only BEM). B3: revert `DESIGN_SYSTEM.md` line 120 + the `var(--corp-value)` rules. B4: revert added test cases only. Each batch independently revertible. |

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `web/src/tokens/tokens.css` | Modified | Appended 17-slot `--corp-*` alias layer (13 `var(--*)` maps + `--corp-value: tabular-nums` + documented size/w/h fallback block). Zero hex in aliases. |
| `web/src/tokens/tokens.test.ts` | Modified | Added `corp-* alias layer` describe (4 tests) + `primitives.css slice-1 catalog contract` describe (2 tests: hex-free, D7 media-check). Total 17 tests. |
| `web/src/components/primitives/primitives.css` | Modified | Re-targeted slice-1 primitives to `--corp-*`; added D7 `@media (hover:none)` 44px touch block; `.kpi__value` uses `--corp-value`; D8 complete-states doc comment. |
| `web/src/components/primitives/Button.test.tsx` | Modified | +3 tests: hex-free source scan, disabled label+semantic pairing, anchor `aria-disabled` pairing. |
| `web/src/components/primitives/Input.test.tsx` | Modified | +1 test: disabled pairing retains visible label with muted control. |
| `web/src/stories/pages/_shared/StateMessage.tsx` | Modified | Minimal Alert-compat comment (STATE_TONES already tokenized; `role` prop confirmed). No BEM refactor. |
| `web/src/stories/pages/_shared/StateMessage.test.tsx` | Modified | +1 test: state-matrix pairing (danger→alert, loading→status with spinner). |
| `web/src/stories/pages/_shared/StatCard.tsx` | Modified | KPI value resolved via `var(--corp-value)` (was inline `tabular-nums`). |
| `web/src/stories/pages/_shared/DataTable.tsx` | Modified | `tabularNum()` resolves via `var(--corp-value)`. |
| `web/src/stories/pages/_shared/DataTable.test.tsx` | Modified | Updated tabularNum assertion to `var(--corp-value)`. |
| `web/src/stories/pages/Settings.stories.test.tsx` | Modified | Updated 3 numeric-cell assertions to `var(--corp-value)`. |
| `web/DESIGN_SYSTEM.md` | Modified | Line 120 `--bg` `#F4F5F7` → `#F1F1E8` (doc matches executable token). |
| `openspec/changes/…/tasks.md` | Modified | Marked all 16 tasks `[x]`. |
| `openspec/changes/…/apply-progress.md` | Created | This file. |

## Graph Nodes Consulted (Graph Check)

- `Card()` → `web/src/components/primitives/Card.tsx`
- `Button()` → `web/src/components/primitives/Button.tsx`
- `Badge()` → `web/src/components/primitives/Badge.tsx`, `Badge.tsx`
- `StatusBadge.tsx` → `ConversationsList.stories.tsx`
- `StateMessage` community → `Dashboard.stories.tsx`, `_shared/`
- `tokens` node → `web/src/stories/tokens/Tokens.stories.tsx` (+ `Tokens.stories.test.ts`)
- `Tabular` numeric-alignment consumers → `Settings.stories.tsx`, `KbList.stories.tsx` (via `tabularNum`)
- `.graphify_root` = project root; graph freshness vs HEAD: stale from `d8f26896`, structural queries valid (no top-level node reassignment over the slice's files beyond the primitives/`_shared` communities confirmed above).

## Deviations from Design

None that change contract — implementation matches design D1–D8. Noted transparent discrepancies:
1. **v1-shell workspace substrate**: the working tree already carried uncommitted `2026-08-20-v1-shell-header-and-bg` changes (bg `#F1F1E8`, semantic `--*-tint` tokens, StateMessage tint-based minimal Alert mapping, AppShell/PageFrame). Slice-1 built on top. This also explains a **pre-existing `tsc -b` failure in `AppShell.test.tsx`** (2 errors) that is outside slice-1 scope and was not fixed (strict-TDD safety-net rule: report, don't fix unrelated pre-existing failures).
2. **`--corp-value` on timestamps/IDs**: handled via the `tabularNum()` helper contract (the design's stated extension point) rather than forcing every un-formatted cell; callers using `tabularNum()` for numeric/timestamp/ID cells get it uniformly.
3. **`.btn--secondary` border**: `--border-strong` has no `--corp-*` alias; kept the existing token reference (allowed by CST-PRIM-1 "references a `--corp-*` slot **or existing token**"; mapping it to `--corp-border` would change the value).

## Issues Found

- Pre-existing `tsc -b` errors in `web/src/components/domain/AppShell.test.tsx` (from uncommitted v1-shell work) — recorded, not fixed (outside slice). All slice-1 files type-clean.
- Pre-existing Storybook chunk-size warning (>500kB) — non-blocking, not introduced by slice-1.

## Remaining Tasks

None in slice-1. Full 16/16 tasks complete. Remaining catalog components (~30) are chained to later slices per proposal.

## Workload / PR Boundary

- Mode: single stacked slice (B1–B4 work-unit commits), no chaining needed (auto-chain resolved, ~330 forecast lines within 400 budget).
- Boundary: B1 (aliases+guard) → B2 (primitives re-target) → B3 (micro-changes) → B4 (tests+verification). Each `<400` lines, independently revertible.
- Estimated review budget impact: ~327 authored lines across 4 local commits (within the 400-line hard ceiling).

## Status

**16/16 tasks complete. Ready for verify.**
