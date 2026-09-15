# Proposal: UI Base

## Intent

Establish the production-owned UI foundation required by the Command Center. Storybook lacks the real shell and global primitive styles, permits production-to-story imports, and contains stale page copies. Restore one-way ownership and reusable interaction primitives.

## Scope

### In Scope
- Add the Storybook `withPanelShell` decorator, global `primitives.css` import, and token-aligned viewport presets in `web/.storybook/preview.ts`.
- Add a Vitest dependency-boundary test rejecting `web/src/components/**` imports from `web/src/stories/**`.
- Triage: delete `concept/AiAgentGrammar`, quarantine `pages/ChatWithAgent`, resolve `pages/InboxThread`, and enforce existing boundary with test-file policy.
- Use native `popover`, CSS anchors, and `<dialog>` for popover, tooltip, dropdown presentation/dismissal/focus, and modal dialogs; use individual Radix packages only for `menu` and combobox ARIA composites.
- First slice: native popover/tooltip/dropdown/modal; CSS-only sidebar rail/skeleton; Radix menu/combobox. Defer resizable panels and uncertain primitives to the Command Center SDD/design.

### Out of Scope
- Command Center product layout, visual direction, data/API behavior, mobile/PWA decisions, and shell redesign.
- Backend changes, broad catalog completion, non-first-slice primitives, visual regression, and Playwright unless a later design phase adds them.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `panel-design-system`: Storybook shell harness, viewport alignment, story ownership/triage, boundary enforcement, and platform-first primitive policy and its narrow, documented Radix adoption.
- `corp-primitives`: Extend the existing primitive contract to own the first-slice interaction set, split by ownership (native platform, CSS-only, and narrow Radix ARIA composites).

## Approach

Keep production components authoritative and stories thin. Centralize Storybook setup, enforce boundary with Vitest, promote shared behavior into `components/`, and prefer platform features. Radix covers ARIA composites via existing tokens. `corp-primitives` owns these contracts; `panel-design-system` owns harness integration. Resolve `InboxThread` in specs/design.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `web/.storybook/preview.ts` | Modified | Shell, CSS, viewports |
| `web/src/components/**`, `web/src/stories/**` | Modified/Removed | Boundary and story triage |
| `web/src/components/primitives/` | New/Modified | First-slice interaction set (native / CSS-only / narrow Radix) |
| `web/DESIGN_SYSTEM.md` | Modified | Platform-first policy and narrow Radix adoption |
| `web/package.json` | Modified | Radix dependencies |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Radix scope expands into catalog rewrite | Med | Implement only required primitives; preserve tokens |
| Triage deletes useful exploratory intent | Med | Quarantine ChatWithAgent; document InboxThread |

## Rollback Plan

Revert UI commits, restoring stories, imports, harness, and docs. No backend/data rollback.

## Dependencies

- Vitest/Storybook, frozen tokens, native support, Radix ARIA packages.

## Success Criteria

- [ ] `npm test` and Storybook build pass; boundary test fails on production-to-story imports.
- [ ] Stories render in the shell with primitives and platform-first viewports.
- [ ] Required interaction primitives have accessible, token-mapped contracts and no duplicated story ownership.
