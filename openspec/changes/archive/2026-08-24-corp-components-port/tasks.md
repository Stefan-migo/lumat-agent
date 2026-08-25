# Tasks — Corporate Components Port (Table / Tabs / Dialog)

> Change: `2026-08-24-corp-components-port` · Project: LumatAgent · Phase: sdd-tasks
> Mode: hybrid · Date: 2026-08-24 · Branch: `feat/corp-components-port`
> Preflight: auto | both | auto-chain (stacked-to-main) | review budget 400

## Review Workload Forecast

- Slice-1 (PR-A): ~250 changed lines → **under 400** → no review-budget risk.
- Slice-2 (PR-B): ~220 changed lines → **under 400** → no review-budget risk.
- Chained PRs recommended: **No** (slices fit the budget); delivery proceeds with the planned 2 stacked PRs (auto-chain, stacked-to-main) for review focus.
- Decision needed before apply: **No**.

## Slice-1 — Table contract + Tabs primitive (PR-A)

- [ ] T1. **RED**: Write `web/src/components/primitives/Tabs.test.tsx` (strict TDD): tablist/tab/tabpanel roles, first tab `aria-selected="true"`, click swaps selection + panel, controlled variant honors `activeTab` and fires `onTabChange`. Run and see it fail.
- [ ] T2. **GREEN**: Implement `web/src/components/primitives/Tabs.tsx` per design D2 (uncontrolled + controlled, `role="tablist"`/`tab`/`tabpanel`, `aria-controls`, panel ids `tabs-<id>-panel`).
- [ ] T3. Retarget `.table` block in `web/src/components/primitives/primitives.css`: `color: var(--text)` → `var(--corp-text)`; `border-bottom: 1px solid var(--border)` → `var(--corp-border)`. No other changes (DataTable.tsx untouched).
- [ ] T4. Add `.tabs`, `.tabs__tab`, `.tabs__tab[aria-selected="true"]`, `.tabs__panel` CSS per design D4 (accent underline, `--corp-muted` inactive, `focus-visible` outline).
- [ ] T5. Add `web/src/stories/primitives/Tabs.stories.tsx` (Default + Controlled stories, CSF3, Spanish copy).
- [ ] T6. Full gate: `npm test` (318 existing + new), `npx tsc --noEmit` 0, `npm run build-storybook` OK. Commit as work units (tests + component + story), conventional commits, no AI attribution.

## Slice-2 — Dialog primitive (PR-B)

- [ ] T7. **RED**: Write `web/src/components/primitives/Dialog.test.tsx` (strict TDD): `role="dialog"` + `aria-modal="true"`, close button `Cerrar`, Escape fires `onClose`, focus moves to first focusable on open, Tab trap wraps (assert `document.activeElement`), focus restored to trigger on close. Run and see it fail.
- [ ] T8. **GREEN**: Implement `web/src/components/primitives/Dialog.tsx` per design D3 (open/onClose/title/children/closeLabel; focus capture, trap, Escape, restore; overlay click does NOT close).
- [ ] T9. Add `.dialog-overlay` (scrim via `color-mix` over `--corp-bg`), `.dialog` (`--shadow-3`, `--corp-radius`, `--corp-surface`), header/title/close/body CSS per design D4.
- [ ] T10. Add `web/src/stories/primitives/Dialog.stories.tsx` (trigger + open dialog, confirm/cancel body, Spanish copy).
- [ ] T11. Full gate: `npm test`, `npx tsc --noEmit` 0, `npm run build-storybook` OK. Commit as work units, conventional commits.

## Delivery

- Stack: PR-A (slice-1) → PR-B (slice-2), stacked-to-main, per `chained-pr` skill (registry: `gentle-ai-chained-pr`).
- Each PR: native RDD review (global RDD ON — consent per candidate) approved + bound before merge; `gentle-ai review bind-sdd` after approval.
- After both merge: verify + archive change (delta specs merge to `openspec/specs/corp-components/`).

## Follow-ups (out of scope)

- Tabs arrow-key roving; page adoption (ClientFicha tabs, destructive confirmations); Tooltip/Popover/DropdownMenu/Accordion/Pagination; KbList tabular-nums advisory.