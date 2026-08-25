# Proposal: V1 shell port to CortexDesign contract + sidebar bug fixes (slice-2)

## Intent

Re-author the v1 shell (dark green sidebar, text-only panel header, collapsible icon-only sidebar, friendly dashboard direction) onto the delivered CortexDesign/Calama Operacional system: consume only `--corp-*` slots, reuse existing primitives, and fix two user-reported sidebar bugs — the oversized/misplaced collapse toggle and the hover background that spills past the sidebar width.

## Current-State Gap

- `PanelShell.tsx` uses raw `--primary-800`/`--surface`/`--brand-*`; NOT on `--corp-*` (CST-PRIM-1 discipline extends to shell).
- Bug 1: shared 44px `min-height` on `.panel-shell__collapse-button` overrides the 40px `height` → renders 40×44px, unanchored between brand and nav.
- Bug 2: flex chain `.sidebar-inner`/`.navigation` lack `min-width:0` → button min-content widens past the fixed 192/96px column; hover `--primary-700` paints past the right edge.
- Pre-existing tsc errors in `AppShell.test.tsx` (TS6133 :110, TS2345 :118).
- Stale `2026-08-20-v1-shell-header-and-bg/proposal.md` (continuous green bar no longer implemented) must be superseded.

## Scope

### In Scope
1. Bug 1: drop shared 44px min-height on collapse button (`min-height:0`), size 32–36px (`--space-8`), consistent sidebar anchoring; keep lime focus + `--primary-700` hover + ≥40px hit target.
2. Bug 2: add `min-width:0` to `.sidebar-inner` + `.navigation`; `overflow:hidden` safety on `.sidebar`; verify in Storybook at 390/640/768/1024/1280px × expanded/collapsed.
3. Re-target every `PANEL_SHELL_STYLES` color/space to `--corp-*` slots or existing tokens (hex-free); resolve dark-hover slot conflict with a shell-local branded reference + ponytail note.
4. Reuse primitives: header statusBadge → `Badge`; user avatar → `Avatar`; brand/nav/collapse stay hand-rolled but token-only.
5. Fix tsc errors in `AppShell.test.tsx`; update untracked `AppShell.stories.test.tsx` assertions in lockstep.
6. Supersede `2026-08-20-v1-shell-header-and-bg` change (stale).

### Out of Scope
- Dashboard/story cleanup (friendly hero, KPI/activity polish, `--corp-value` in `.dashboard-activity__time`), remaining catalog components (Table/Tabs/Dialog/Tooltip/Popover/DropdownMenu/Accordion/Pagination), icon library, persisted collapse state (session-only stays), dark mode, Jinja migration.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `corp-primitives`: shell reuses Badge (statusBadge) and Avatar primitives; shell joins the `--corp-*`-only consumption discipline (extends CST-PRIM-1 scenario scope to `PanelShell`).
- `corp-token-aliases`: document dark-hover gap — `--corp-surface-hover` resolves light (`--table-head-bg`); shell keeps a scoped branded dark hover (CST-ALIAS-3 note).

## Approach

Fix bugs → re-target CSS to `--corp-*` → reuse primitives → fix tests → verify in real Storybook render at all reference widths + collapsed/expanded → supersede stale change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `web/src/components/domain/PanelShell.tsx` | Modified | Both bugs + `--corp-*` re-target |
| `web/src/components/domain/AppShell.test.tsx` | Modified | Fix TS6133/TS2345 |
| `web/src/stories/domain/AppShell.stories.test.tsx` | Modified | Re-align assertions to `--corp-*` |
| `web/src/stories/domain/AppShell.stories.tsx` | Modified | Docs re-target (DS-STORY-2) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Dark-hover slot conflict | High | Shell-local `--primary-700` reference (still hex-free) + ponytail note |
| jsdom can't verify media-query/Bug 2 overflow | Med | Real Storybook render at reference widths |
| 400-line budget | Med | Chained slice: panel + dashboard/story cleanup deferred |
| `--corp-*`-only breaks shell hover language | Med | Verify real render expanded/collapsed |

## Rollback Plan

Revert the single `PanelShell.tsx` + test/story diff (one commit). Shell architecture is unchanged, so rollback is a clean file-level revert; no token changes.

## Dependencies

None. Slice-1 (`corp-primitives`, `corp-token-aliases`) already archived.

## Success Criteria

- [ ] Both sidebar bugs fixed and verified in Storybook (no hover spill; toggle sized 32–36px, anchored, ≥40px hit).
- [ ] `PANEL_SHELL_STYLES` hex-free, all values via `--corp-*` or existing tokens.
- [ ] `AppShell.test.tsx` + `AppShell.stories.test.tsx` green; `npm test` 300+ pass; `tsc -b` clean.
- [ ] Stale `2026-08-20-v1-shell-header-and-bg` declared superseded.
