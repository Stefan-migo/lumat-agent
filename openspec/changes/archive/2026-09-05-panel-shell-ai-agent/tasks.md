# Tasks: Panel Shell AI-Agent Infrastructure

## Review Workload Forecast
Estimated changed lines: 900–1,300. Split: PR1 routes; PR2–3 helpers; PR4 links; PR5–7 CSS. Delivery: auto-chain; chain: stacked-to-main.
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units
- 1 / PR1 Routes — `cd web && npm test -- AppShell.test.tsx`; jsdom; rollback route.
- 2 / PR2 Helpers — `cd web && npm test -- helpers.test.tsx`; stories; rollback wrappers.
- 3 / PR3 Closure — `cd web && npm test -- PageFrame.test.tsx`; fixtures; rollback closure.
- 4 / PR4 Links — `cd web && npm test -- src/components/pages`; auth/403; rollback links.
- 5 / PR5 Base CSS — `cd web && npm test -- AppShell.stories.test.tsx`; desktop; rollback base.
- 6 / PR6 Nav CSS — `cd web && npm test -- PanelEntry.stories.test.tsx`; mobile; rollback nav.
- 7 / PR7 Cleanup — `cd web && npm run build && npm test`; DOM guards; rollback CSS.

## Phase 1: Slice 1
- [x] 1.1 **RED** Objective: test routes, IDs, fallback, cleanup. **Files:** `panelRoutes.test.ts`, `AppShell.test.tsx`. **Done:** threat tests fail. **Verify:** `npm test -- panelRoutes.test.ts AppShell.test.tsx`.
- [x] 1.2 **GREEN** Objective: add typed History routes. **Files:** `panelRoutes.ts`, `AppShell.tsx`. **Done:** views/drill-downs/history pass. **Verify:** `npm test -- panelRoutes.test.ts AppShell.test.tsx`.

## Phase 2: Slice 2
- [x] 2.1 **RED** Objective: test component imports/story compatibility. **Files:** boundary/story tests. **Done:** scan fails. **Verify:** `npm test -- helpers.test.tsx`.
- [x] 2.2 **GREEN** Objective: promote four core helpers and wrappers. **Files:** `web/src/components/shared/`, `web/src/stories/pages/_shared/`. **Done:** contracts pass. **Verify:** `npm test -- helpers.test.tsx`.

## Phase 3: Slice 3
- [x] 3.1 **RED** Objective: detect remaining story dependencies. **Files:** boundary/helper tests. **Done:** `closure.test.tsx` failed before promoted modules existed. **Verify:** `npm test -- --run src/components/shared/closure.test.tsx`.
- [x] 3.2 **GREEN** Objective: promote `PageFrame`, `StateMessage`, `toneMaps`. **Files:** `web/src/components/shared/`. **Done:** closure has no production story dependency. **Verify:** focused closure/helper tests pass.

## Phase 4: Slice 4
- [x] 4.1 **RED** Objective: test no story/hash links and 403 safety. **Files:** page/domain tests. **Done:** scans fail. **Verify:** `npm test -- src/components/pages`.
- [x] 4.2 **GREEN** Objective: update imports and drill-down links. **Files:** `web/src/components/pages/*.tsx`, `ClientMemories.tsx`, `StatusBadge.tsx`. **Done:** clean links, safe 403. **Verify:** `npm test -- src/components/pages`.

## Phase 5: Slice 5
- [x] 5.1 **RED** Objective: guard tokenized base layout. **Files:** `AppShell.stories.test.tsx`. **Done:** guard fails. **Verify:** `npm test -- AppShell.stories.test.tsx`.
- [x] 5.2 **GREEN** Objective: move base/layout rules. **Files:** `primitives.css`. **Done:** equivalent layout. **Verify:** `npm test -- AppShell.stories.test.tsx`.

## Phase 6: Slice 6
- [x] 6.1 **RED** Objective: lock nav, focus, collapse, drawer. **Files:** `PanelEntry.stories.test.tsx`. **Done:** regression fails. **Verify:** `npm test -- PanelEntry.stories.test.tsx`.
- [x] 6.2 **GREEN** Objective: migrate nav/drawer/focus rules. **Files:** `primitives.css`, `PanelShell.tsx`. **Done:** keyboard/responsive pass. **Verify:** `npm test -- PanelEntry.stories.test.tsx`.

## Phase 7: Slice 7
- [x] 7.1 **RED** Objective: guard no injection/hex and reduced motion. **Files:** shell tests. **Done:** guards fail. **Verify:** `npm test -- AppShell.stories.test.tsx`.
- [x] 7.2 **GREEN** Objective: migrate remainder; remove `PANEL_SHELL_STYLES`. **Files:** `PanelShell.tsx`, `primitives.css`. **Done:** build/tests pass. **Verify:** `cd web && npm run build && npm test`.

## Graph Nodes Consulted
Nodes: `AppShell.tsx`, `PanelShell.tsx`, page/helper nodes, `primitives.css`; edge AppShell→PanelShell.
