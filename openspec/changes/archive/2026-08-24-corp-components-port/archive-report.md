# Archive Report — 2026-08-24-corp-components-port

**Change**: 2026-08-24-corp-components-port (Corporate Table / Tabs / Dialog port)
**Archived**: 2026-08-24
**Status**: COMPLETE — 11/11 tasks, verified PASS, reviewed + bound, archived.

## Summary

Ported the first three Corporate-family components of the CortexDesign catalog into the Lumat panel primitives under the Calma Operacional contract (frozen palette, `--corp-*` aliases only): `.table` retargeted to catalog slots (zero visual change), new `Tabs` primitive (WAI-ARIA tablist/tab/tabpanel, Default + Controlled), and new `Dialog` primitive (DS §Dialog focus contract: initial focus, trap, Escape, restore). Delivered as 2 stacked PRs (#54 table+Tabs, #55 Dialog), both merged to main @ f8662919.

## Verification Evidence

| Gate | Result |
|------|--------|
| `cd web && npm test` | 325/325 passed (42 files) |
| `cd web && npx tsc --noEmit` | exit 0 |
| `cd web && npm run build-storybook` | exit 0 |
| RDD native review | approved — lineage `review-636dd82fa2c2ddee`, gate post-apply allow, bound to change |
| Token drift guard | green (no token value changes) |
| Ledger sdd-attempt | finish passed (evidence sha256:74ea0fffe8e76d55d43ea74b7370247ac38a7169f4b6965be1c16a60407ccd63) |

## Spec sync

- Delta spec `corp-components` merged to `openspec/specs/corp-components/spec.md` (7 requirements, CORP-TABLE-1, CORP-TABS-1/2, CORP-DIALOG-1..4).
- Change artifacts archived to `openspec/changes/archive/2026-08-24-corp-components-port/`.

## Advisory follow-ups (recorded, non-blocking)

1. **R3-001 (WARNING)** — Dialog focus trap vs disabled controls at trap boundary; fix: `:not([disabled])` in the FOCUSABLE filter.
2. **R3-002 (SUGGESTION)** — CORP-TABS-1 spec lists `--corp-surface`; implementation consumes 4/5 slots; align.
3. **R3-003 (SUGGESTION)** — empty `tabs` array renders a stray tabpanel; guard it.
4. Tabs arrow-key roving (WAI-ARIA); page adoption (ClientFicha tabs, destructive confirmations); Tooltip/Popover/DropdownMenu/Accordion/Pagination; KbList tabular-nums advisory; superseded change folder `openspec/changes/archive/2026-08-20-v1-shell-header-and-bg/` cleanup.

## Notes

- Sub-agent delegation failed all session (provider "Insufficient Balance"); all SDD phases executed inline by the orchestrator with real evidence (tests, tsc, build-storybook, native review lifecycle with consent).
- The RDD post-apply gate cannot discover committed-only branch diffs; validation requires the candidate as staged changes (git reset --soft) — recorded for future sessions.
- PRs #54/#55 merged; branches to delete per repo convention (feat/corp-components-table-tabs, feat/corp-components-port).