# Delta for panel-design-system

## ADDED Requirements

### Requirement: DS-SHELL-1 — Collapse Toggle Sizing and Placement

The desktop sidebar collapse toggle MUST render 32–36px (`--space-8`), MUST escape the shared 44px control `min-height` while keeping a ≥40px hit target by its own sizing, MUST anchor consistently in the sidebar rhythm (expanded and collapsed), and MUST keep lime focus-visible + `--primary-700` hover in both states.

#### Scenario: Shared rule overridden

- GIVEN the desktop sidebar expanded
- WHEN the toggle renders
- THEN it measures 32–36px (own `min-height` beats 44px), ≥40px hit target

#### Scenario: Anchored in both states

- GIVEN expanded and collapsed
- WHEN placement is inspected
- THEN it stays anchored, keeps lime focus + `--primary-700` hover

### Requirement: DS-SHELL-2 — Sidebar Hover Containment

The desktop sidebar MUST NOT widen beyond its fixed grid column (192px expanded, 96px collapsed). `.sidebar-inner` and `.navigation` MUST set `min-width: 0`; `.sidebar` MUST set `overflow: hidden` as a safety net, so hover/`aria-current` paint stays inside.

#### Scenario: Hover never spills

- GIVEN a nav item in the desktop sidebar
- WHEN hovered or marked `aria-current`
- THEN paint stays within the fixed column, verified at 390/640/768/1024/1280px × expanded/collapsed in a real Storybook render (jsdom cannot test media-query overflow)

### Requirement: DS-SHELL-3 — Shell Consumes the Contract (Hex-Free)

Every color/spacing in `PANEL_SHELL_STYLES` MUST resolve through `--corp-*` slots or existing tokens; no hex literal MAY appear (extends `DS-TKN-1`/`CST-PRIM-1` to `PanelShell`). The dark-hover conflict MUST be a documented shell-scoped exception: `--corp-surface-hover` resolves light (`--table-head-bg`), so the local hover references the brand scale (`--primary-700`) with a ponytail note.

#### Scenario: Hex-free re-target

- GIVEN `PANEL_SHELL_STYLES`
- WHEN scanned
- THEN every color/spacing is a `--corp-*`/existing token and no hex literal appears

#### Scenario: Dark-hover exception documented

- GIVEN the shell-local dark hover rule
- WHEN reviewed
- THEN it references a brand-scale token (hex-free) with a ponytail note on the light `--corp-surface-hover` gap

### Requirement: DS-SHELL-4 — Primitive Reuse

The panel header `statusBadge` slot MUST reuse `Badge`; the user avatar MUST reuse `Avatar`. No new primitive in this slice.

#### Scenario: Badge and avatar reuse primitives

- GIVEN the header badge and sidebar avatar render
- WHEN inspected
- THEN they resolve to `primitives/Badge` / `primitives/Avatar`, no new primitive added

### Requirement: DS-SHELL-5 — Tests and Typecheck Green

The two pre-existing tsc errors in `AppShell.test.tsx` MUST be fixed (TS6133 unused `s` ~:110; TS2345 `HTMLButtonElement | undefined` → `Element` ~:118). `AppShell.stories.test.tsx` (untracked) assertions MUST update in lockstep with the re-target. `npx tsc -b` and `npm test` MUST stay green (incl. hex walk).

#### Scenario: tsc clean

- GIVEN the applied diff
- WHEN `npx tsc -b` runs in `web/`
- THEN it passes with no TS6133/TS2345 in `AppShell.test.tsx`

#### Scenario: Suite green incl. hex guard

- GIVEN the applied diff
- WHEN `npm test` runs in `web/`
- THEN all tests pass incl. the hex walk and updated story assertions

## MODIFIED Requirements

### Requirement: DS-STORY-2 — Description and Usage Guidance

Each of the 10 docs pages MUST include a terse component description and usage guidance stating when the component should and should not be used.
(Previously: `AppShell.stories.tsx` described hardcoded v1 values like `--primary-800`; the port re-targets this copy to `--corp-*`.)

#### Scenario: Guidance visible

- GIVEN a docs page
- WHEN read
- THEN it states purpose and usage guidance

#### Scenario: Shell docs reference the contract

- GIVEN the `AppShell` docs after the port
- WHEN brand/styling references are read
- THEN they describe the shell as consuming `--corp-*` slots, no hardcoded v1 token values

## Modifications

- REMOVED: none. RENAMED: none.

## Non-Goals (explicit)

- Dashboard/story cleanup (hero, KPI/activity polish, `--corp-value` in `.dashboard-activity__time`) — chained later.
- Remaining Corporate components (Table/Tabs/Dialog/Tooltip/Popover/DropdownMenu/Accordion/Pagination) and icon library.
- Persisted collapse state — session-only stays
- Dark mode; Jinja migration.

## Supersession Note

The stale `2026-08-20-v1-shell-header-and-bg` proposal (continuous green bar) is superseded here; recorded, not deleted, archived abandoned.
