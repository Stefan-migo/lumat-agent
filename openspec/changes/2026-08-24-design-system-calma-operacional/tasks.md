# Tasks: Design System "Calma Operacional" — Slice-1 Catalog Adaptation

> Change: `2026-08-24-design-system-calma-operacional` · Project: lumat-agent · Date: 2026-08-24
> Additive token-alias layer + existing-primitive re-target. Zero color/font/icon change. Alias layer → hex-guard test → primitives re-target → micro-changes → story/test updates. Strict TDD where tests exist. Numbering `T1.x`=B1, `T2.x`=B2, `T3.x`=B3, `T4.x`=B4. All CSS/tsx in `web/`.

## Review Workload Forecast

Estimated changed lines: ~330 (B1 ~90 · B2 ~155 · B3 ~25 · B4 ~60)

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

Slice-1 batches B1–B4 sum ~330 lines, under the 400-line budget; each batch <400 and independently revertible. **No chaining needed for slice-1** — single stacked-slice delivery, `auto-chain` resolves with no decision gate.

### Suggested Work Units

| Unit | PR | Focused test command | Runtime harness | Rollback boundary |
|------|----|---------------------|-----------------|-------------------|
| B1 aliases+guard | (B1) | `cd web && npm test` | N/A — token-source CSS; no runtime surface, verified by unit hex-guard walk | Delete `--corp-*` block from tokens.css + revert tokens.test.ts aliases/guard |
| B2 primitives re-target | (B2) | `cd web && npm test && npx tsc -b` | `npm run storybook` → Button/Badge/Card/Input/Select/Textarea stories | `git revert` primitives.css + _shared edits; falls back to prior token-only BEM |
| B3 micro-changes | (B3) | `cd web && npm test` | `DESIGN_SYSTEM.md` Canvas row reads `#F1F1E8` | Revert DESIGN_SYSTEM.md line 120 + `--corp-value`/`.kpi__value` rule |
| B4 tests+deps | (B4) | `cd web && npm test` | `npm run build-storybook` + viewport review 390/640/768/1024/1280px | Revert added test cases + storybook viewport checks |

## Phase 1 — B1 Alias layer + hex-guard extension (PR 1)

Gate: `cd web && npm test` green; aliases resolve to `var(--*)`, zero hex.

- [x] **T1.1** Append 17-slot `--corp-*` block to `:root` in `web/src/tokens/tokens.css`: primary→`--primary-800`, primary-fg→`--surface`, accent→`--info`, border→`--border`, fg→`--text`, fg-muted→`--text-muted`, text→`--text`, muted→`--text-muted`, surface→`--surface`, surface-hover→`--table-head-bg`, bg→`--bg`, radius→`--radius-sm`, gap→`--space-3`; add `--corp-value: tabular-nums` (D3); leave size/w/h unresolved (D2) with a build-warning comment. [CST-ALIAS-1,2,3 · DS-TKN-10/1]
- [x] **T1.2** Test-first `web/src/tokens/tokens.test.ts`: extend drift walk to assert every `--corp-*` slot maps to a `var(--*)` and pre-existing `--*` declarations stay byte-identical (CST-ALIAS-2); add spot-checks for primary/bg/surface/value slot targets (DS-TKN-10). [CST-ALIAS-1,2 · DS-TKN-10]
- [x] **T1.3** Verify no hex literal in alias block; no existing token test assertion removed (DS-TKN-10, CS-PRIM-1). [DS-TKN-10]

## Phase 2 — B2 Primitives re-target + touch + states (PR 2)

Gate: `cd web && npm test && npx tsc -b`; no new hex; all slice-1 colors via `--corp-*`.

- [ ] **T2.1** `web/src/components/primitives/primitives.css`: re-target Button (`--primary-800`→`--corp-primary`, hover `--primary-700`; fg `--surface`→`--corp-primary-fg`), Card/SearchInput/field controls (border→`--corp-border`, surface→`--corp-surface`, text→`--corp-text`, muted→`--corp-fg-muted`, radius→`--corp-radius`, gap→`--corp-gap`), Badge tones, flash-message/pagination (D1,D4). [CST-PRIM-1 · DS-TKN-1]
- [ ] **T2.2** D7 touch-target block in `primitives.css`: `@media (hover: none)` `min-height: 44px` on `.btn` and `.field__control` (40px desktop preserved) — one CSS block, no `::before`. [CST-PRIM-3 · D7]
- [ ] **T2.3** D8 complete-states: document-first, CSS-only additions; disabled Button/field keep label+opacity (never `--text-muted` alone); verify Badge neutral/warning/success/danger + Card EmptyState/StateMessage map. Mark **Button loading/empty explicitly deferred** (needs new props+spinner, no consumer — budget). [CST-PRIM-4 · D8]
- [ ] **T2.4** `web/src/stories/pages/_shared/StateMessage.tsx`: confirm `STATE_TONES` tokenized + `role="status"|"alert"` (D5); add minimal Alert-compat comment, **no full BEM refactor** this slice. [CST-PRIM-5 · D5]
- [ ] **T2.5** StatusBadge: confirm maps to `<Badge tone>` with `conversationLabel`; **no `.tsx`/CSS change** — covered by existing test. [CST-PRIM-5]

## Phase 3 — B3 Micro-changes (PR 3)

Gate: `cd web && npm test`; doc matches token source.

- [ ] **T3.1** `web/src/stories/pages/_shared/StatCard.tsx` + `DataTable.tsx` + `web/src/components/primitives/primitives.css`: apply `font-variant-numeric: tabular-nums` via `--corp-value` on numeric data roles (KPI value, numeric/`tabularNum()` cells, timestamps, IDs); decorative labels unaffected (CST-ALIAS-5, DS-TKN-11). [CST-ALIAS-5 · DS-TKN-11]
- [ ] **T3.2** `web/DESIGN_SYSTEM.md` line 120 Canvas row: `--bg` `#F4F5F7` → `#F1F1E8` (executable token wins; DS-TKN-12). [DS-TKN-12]

## Phase 4 — B4 Tests + Storybook verification (PR 4)

Gate: `cd web && npm test && npm run build-storybook`; viewports 390/640/768/1024/1280px.

- [ ] **T4.1** `primitives*.test.tsx` — extend per-component smoke: renders, hex-free source scan, disabled pairing dims+`aria-disabled`/label. [CST-PRIM-1,4]
- [ ] **T4.2** `tokens.test.ts` — alias spot-check asserts slots resolve to existing tokens (fallback size/w/h documented, never hardcoded). [CST-ALIAS-4,1]
- [ ] **T4.3** `.btn`/`.field__control` ≥44px under `(hover:none)` — CSS media-check test (D7). [CST-PRIM-3]
- [ ] **T4.4** StateMessage RTL: `role=` + visible Spanish label + tone (danger→`role=alert`, loading→`role=status`). [CST-PRIM-5]
- [ ] **T4.5** Storybook: `build-storybook` + viewport review slice-1 primitives (Button/Badge/Card/Input/Select/Textarea) at 390/640/768/1024/1280px; record results. [CST-PRIM-6; success-criteria]
- [ ] **T4.6** Hex-free audit: no raw hex in newly changed files under `web/src`. [CST-PRIM-1 · DS-TKN-10]

## Delivery Plan (work-unit commits, stacked-to-main)

| Task(s) | Commit message | Unit / rollback |
|---|---|---|
| T1.1–T1.3 | `feat(web): add corp-* token alias layer and hex-guard extension` | B1 (revert tokens.css alias block + test) |
| T2.1–T2.5 | `feat(web): retarget slice-1 primitives to corp-* contract` | B2 (revert primitives.css + StateMessage) |
| T3.1–T3.2 | `fix(web): apply tabular-nums to data roles and fix DESIGN_SYSTEM --bg` | B3 (revert DESIGN_SYSTEM line 120 + kpi rule) |
| T4.1–T4.6 | `test(web): cover alias guard, touch targets, states, viewport checks` | B4 (revert test additions only) |

Stacked-to-main in order B1→B4; each PR <400 lines, independently revertible (rollback table above). No AI attribution; tests+docs travel with their unit.
