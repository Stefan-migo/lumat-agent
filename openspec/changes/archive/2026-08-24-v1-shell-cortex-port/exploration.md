# Exploration — 2026-08-24-v1-shell-cortex-port

Port the v1 shell design decisions to the CortexDesign (DC-004 Corporate) contract, and fix the two reported sidebar bugs (collapse-toggle sizing/placement; hover overflow past sidebar bounds).

## Current State

- `web/src/components/domain/PanelShell.tsx` holds the whole shell as one component with an inline `PANEL_SHELL_STYLES` string: dark-green sidebar (`--primary-800`), inline stroke SVG icons (no icon library), session-only collapse toggle (`aria-expanded`, class `panel-shell--collapsed`), a text-only panel header row, brand block, and UserContext avatar block. It also contains the mobile drawer.
- Slice-1 (archived) shipped the `--corp-*` alias layer (17 slots in `tokens.css`) and re-targeted `primitives.css` to consume only `--corp-*` slots (CST-PRIM-1 hex-free, CST-ALIAS-3 no twins). The shell does NOT consume `--corp-*` yet — it uses raw `--primary-800`, `--surface`, `--brand-lime`, etc. directly.
- The `web/.storybook/component-catalog.json` (DC-004 v1.2.0) declares Corporate components (Button/Badge/Card/Avatar/etc.) **as the catalog contract**. The `storyFile` paths point at `../src/components/Corporate/...`, which DO NOT exist in this repo — the catalog is the vendored contract reference, and the real, shipped implementation is `web/src/components/primitives/*` re-targeted to `--corp-*`. This is the operative reading: "port to the catalog contract" = "consume `--corp-*` slots + reuse the primitives that already map to the contract," not "import missing Corporate component files."
- Working tree has uncommitted v1-shell work (~850 changed lines) incl. Dashboard "friendly" layout and PanelEntry/PageFrame stories.

### Bug 1 — collapse toggle "does not look good, too big, placed without sense"

**Root cause (confirmed in CSS):** shared control rule (~PanelShell.tsx:248-252) sets `min-height: calc(var(--space-8) + var(--space-3))` = **44px** on `.panel-shell__collapse-button`. The dedicated rule (:295-305) sets `width/height: 2.5rem` running (40px) — but `min-height` **overrides** `height`, so the button renders **40 × 44px**. It floats between Brand and Navigation with `margin: 0 var(--space-3) var(--space-3)` (12px bottom), ghost background, no vertical anchoring — an off-center 44px-tall square icon button visually unmoored in the dark-green sidebar. Collapsed state centers it but keeps 44px min-height.

### Bug 2 — hover background exceeds sidebar width

**Root cause (candidate → likely confirmed):** desktop sidebar column is a fixed track `calc(var(--space-8) * 6)` = 192px (96px collapsed). The flex column chain `.panel-shell__sidebar` [has `min-width:0`] → `.panel-shell__sidebar-inner` [**no `min-width:0`**] → `.panel-shell__navigation` [**no `min-width:0`**] → `.panel-shell__navigation-button` [width:100%] lets the button's min-content width force the inner wider than the fixed column; `.sidebar-inner`/`.navigation` default `min-width: auto` prevents shrinking below content. Result: hover `background: var(--primary-700)` (and `aria-current` background) paints wider than the 192px sidebar, spilling past the right border. The label truncates inside, but the button's box (and its hover paint) bleeds. Verify in Storybook at 390/640/768/1024/1280px × expanded/collapsed before/after.

## Affected Areas

- `web/src/components/domain/PanelShell.tsx` — collapse-button sizing/placement (Bug 1) + flex min-width chain (Bug 2) + re-target every value to `--corp-*` slots (CST-PRIM-1).
- `web/src/components/domain/AppShell.tsx` — placeholder `<p>` consumes `--text-*`; stays, no contract change needed.
- `web/src/components/domain/AppShell.test.tsx` — fix TS6133 (:110 unused `s`) + TS2345 (:118 `navButtonByLabel` returns `HTMLButtonElement | undefined`; type the finder or assert non-null).
- `web/src/stories/domain/AppShell.stories.tsx` + `.test.tsx` — port docs copy/assertions that reference hardcoded V1 values; DS-STORY-2 description mentions `--primary-800` brand — update to `--corp-primary` or keep (brand block stays token-based).
- `web/src/stories/pages/Dashboard.stories.tsx` / PanelEntry / PageFrame — already consume primitives/`--corp-*`; only overlap is Dashboard's inline `.dashboard-activity__time` using literal `tabular-nums` instead of `var(--corp-value)` (CST-ALIAS-5).
- `web/src/tokens/tokens.css` — confirm the D7 touch block does NOT set min-height on `.panel-shell__collapse-button` (it only targets `.btn, .field__control`) — safe; but the shell's own 44px min-height must be revisited.
- `openspec/changes/2026-08-20-v1-shell-header-and-bg/proposal.md` — STALE (describes continuous green bar); superseded by this port; do not edit, it stays archived as abandoned.

## Approaches

1. **Port by re-targeting CSS to `--corp-*` + fix both bugs, reusing existing primitives where they map.**
   - Navigation stays hand-rolled (no catalog component for sidebar nav); re-point every color/space to `--corp-*` slots (e.g. sidebar bg `--corp-primary`, nav hover `--corp-surface-hover`... note hover on green needs the shell's dark language — see conflict note).
   - User block avatar → reuse `Avatar` primitive (`web/src/components/primitives/Avatar`); statusBadge slot → `Badge` primitive; brand block stays token-based (no catalog brand component).
   - Bug 1: drop the shared 44px min-height from `.panel-shell__collapse-button` (or set explicit `min-height:0`), size 32–36px (`--space-8`), anchor consistently (align with nav items' right edge / same vertical rhythm as brand), keep lime focus ring + `primary-700` hover language.
   - Bug 2: add `min-width: 0` to `.panel-shell__sidebar-inner` and `.panel-shell__navigation`; verify `overflow: hidden` on the sidebar as a safety net.
   - Pros: smallest surface; directly fixes both user-reported bugs; keeps the shell's proven architecture; aligns with slice-1 contract.
   - Cons: `--corp-*` has no dark-surface slot that mirrors `--primary-700` sidebar hover — `--corp-surface-hover` resolves to `--table-head-bg` (light); the dark sidebar needs its own hover token or a deliberate local rule. Effort: Medium.

2. **Full component rewrite to catalog primitives (compose PanelShell from Button/Badge/Avatar/Card).**
   - Pros: maximal catalog fidelity.
   - Cons: over-engineering (ponytail): nav has no catalog component, so it's a partial rewrite that buys little; large diff vs 400-line budget; risk to the 300 green tests. Effort: High.

3. **Supersede by committing the working tree as-is + only patch the two CSS bugs.**
   - Pros: fastest.
   - Cons: leaves the shell off-contract (still raw `--primary-*`), fails the CST-PRIM-1 port intent, ~850-line review blast. Effort: Low (but wrong scope).

## Recommendation

Approach 1. It satisfies "port the v1-shell design decisions to the CortexDesign contract" while keeping the diff reviewable (fix both bugs + re-target the shell CSS to `--corp-*` + fix the two pre-existing tsc errors in AppShell.test.tsx + update the affected story/test assertions). The D7 touch block in primitives.css targets only `.btn`/`.field__control`, so the shell's collapse button is free to adopt a smaller touch target via its own explicit `min-height` — but the collapse icon is a primary interaction, so keep ≥40px hit target (40×40px) and rely on the desktop sidebar hover language, not the 44px shared rule.

## Risks

- `--corp-*` provides no dark-hover mapping for the sidebar's `--primary-700` (`--corp-surface-hover` is light). The port must either scope a shell-local hover (`var(--primary-700)`) with a ponytail note, or the proposal must accept a shell-specific identity that references raw brand scale tokens (still hex-free).
- The working-tree diff (~850 lines) must NOT be resurrected wholesale; the port re-author is against the contract. Chained slices may be needed: (a) bug fixes + contract re-target of PanelShell; (b) Dashboard/story updates (remove `tabular-nums` literals → `--corp-value`; align AppShell.stories docs).
- Stale `2026-08-20` proposal must be explicitly declared superseded in the new proposal to avoid confusion.
- Bug 2 must be verified in a real Storybook render at the stated viewports; jsdom cannot exercise the media-query/CSS overflow (the css overflow assumption is structural, not covered by the current tests).

## Ready for Proposal

Yes. Root causes for both sidebar bugs are confirmed by static CSS analysis; the contract mapping is clear; the slice fit is Medium risk to the 400-line budget and may warrant a chain (shell port slice + dashboard/story cleanup slice).

## Graph Nodes Consulted

`PanelShell.tsx` (community AppShell.tsx), `AppShell.tsx`, `AppShell.test.tsx` (community AppShell.stories.tsx), `AppShell.stories.tsx`, `PanelEntry.stories.tsx`, `Dashboard.stories.tsx`, `PageFrame.tsx`, `primitives.css`, `Avatar.tsx`, `Badge.tsx`, `tokens.css`, `component-catalog.json` (DC-004), `catalog-query.js` (CA-001). Default BFS depth=2, 75 nodes (community hubs: AppShell.tsx, AppShell.stories.tsx, Dashboard.stories.tsx, PanelEntry.stories.tsx, types.ts). Graph is stale vs working tree (built @ d8f26896; PENDING refresh at session close per graphify policy).
