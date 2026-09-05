## Exploration: panel-shell-ai-agent

### Current State
The authenticated React SPA enters through `web/src/main.tsx` → `web/src/app.tsx`, which probes `/panel/api/me` and mounts `AppShell` after authentication. `AppShell` currently owns a `useState<PanelView>` switch and drill-down IDs; `PanelShell` owns the navigation vocabulary, role filtering, responsive sidebar/drawer, collapse state, focus handling, and header. There is no router and no URL synchronization: navigation does not update the address bar, browser history, or deep-link state. Existing customer links still emit inert `#/clientes/:id` hashes when no callback handles them.

`PanelShell.tsx` is 880 lines. Its `PANEL_SHELL_STYLES` block spans lines 120–641 (522 lines), covering tokenized layout, sidebar/mobile drawer, navigation controls, user/logout context, header/content regions, responsive breakpoints, animations, and reduced-motion behavior. It has no hex literals and deliberately uses inline SVG icons, avoiding an icon dependency. Some shell duplication is intentional for desktop sidebar versus mobile drawer; it should be retained only where the responsive interaction differs, not copied into a new abstraction.

The nine top-level views are `dashboard`, `clients`, `conversations`, `cases`, `notifications`, `push`, `chat`, `kb`, and `settings`. `ClientFicha` and `ConversationThread` are drill-downs mounted conditionally inside the clients/conversations branches. All production pages are already under `web/src/components/pages/`, but 10 of them still import production-used helpers from `web/src/stories/pages/_shared/`. The helpers requested for promotion are `EmptyState`, `DataTable`, `PageHeader`, and `StatCard`; `PageFrame`, `StateMessage`, and `toneMaps` are also production dependencies and must be handled explicitly or the boundary will remain split.

Graph Check consulted `AppShell()`, `PanelShell()`, `AppShell.tsx`, `PanelShell.tsx`, `app.tsx`, all page nodes, the shared helper nodes, `Button.tsx`, `Card.tsx`, `api.ts`, `types.ts`, and `DESIGN_SYSTEM.md`. The graph report identifies `AppShell.tsx`, `PanelShell.tsx`, `api.ts`, `types.ts`, `ClientFicha.tsx`, `ConversationsList.tsx`, `CasesList.tsx`, and `KbList.tsx` as relevant hubs/communities. The path query found: `AppShell() <--contains-- AppShell.tsx --imports--> PanelShell()` (2 hops, undirected); no directed path existed in the requested order.

### Affected Areas
- `web/src/components/domain/AppShell.tsx` — replace state-only view selection with URL-derived routing/history synchronization while preserving drill-down behavior and role-safe rendering.
- `web/src/components/domain/PanelShell.tsx` — migrate the 522-line injected stylesheet, preserve responsive/a11y behavior, and expose navigation as URL-aware links or controls.
- `web/src/app.tsx` — remain the auth boundary; verify refresh/deep-link behavior below `/panel/app/` does not bypass authentication or break the shell.
- `web/src/components/pages/*.tsx` — nine top-level views mount here; clients and conversations additionally mount `ClientFicha` and `ConversationThread`. Replace shared-helper imports and repair hash/link navigation.
- `web/src/stories/pages/_shared/{EmptyState,DataTable,PageHeader,StatCard}.tsx` — promote stable production helpers into `web/src/components/`; retain thin story compatibility wrappers only if existing story tests require them.
- `web/src/stories/pages/_shared/{PageFrame,StateMessage,toneMaps}.tsx` — not named in the four-helper promotion list, but currently imported by production pages and therefore a boundary decision for this change.
- `web/src/components/primitives/primitives.css` and/or a shell stylesheet — destination for reusable tokenized styles; avoid another component-local `<style>` injection and keep all values token-based.
- `web/src/tokens/tokens.css`, `web/DESIGN_SYSTEM.md` — existing token and shell grammar authority; no new palette, font, icon pack, or CSS framework is indicated.
- `web/src/components/domain/AppShell.test.tsx`, `web/src/app.test.tsx`, page tests, and Storybook shell tests — cover navigation, deep links, back/forward, refresh, permissions, drill-down URLs, responsive shell behavior, and preserved exports.
- `web/package.json` — validate that native History API is sufficient before considering a router dependency; current runtime dependencies are only React and React DOM.
- `openspec/specs/{spa-delivery,panel-app,panel-design-system}/spec.md` — current specs lock D7 no-router/state routing and separately define SPA deep-link serving; this change must supersede the former routing requirement deliberately.

### Approaches
1. **Native History API with a small route table** — define the finite view/path mapping in `AppShell`, parse `window.location` on mount, call `history.pushState` for navigation, listen to `popstate`, and use explicit path patterns for customer/conversation drill-downs.
   - Pros: no dependency; directly satisfies clean URLs, deep links, back/forward, and refresh; keeps route behavior close to the existing nine-view switch; smallest review surface.
   - Cons: requires careful path normalization, unknown-route fallback, and test setup for `popstate`/`pushState`; nested route growth must remain bounded.
   - Effort: Medium

2. **Add a router library** — introduce a mature React router and model top-level and drill-down routes declaratively.
   - Pros: standardized matching, navigation, nested routes, and future route growth; less bespoke parsing.
   - Cons: new runtime dependency and migration of the current state contract; unnecessary abstraction for nine finite views; must still validate the `/panel/app/` base path and backend route boundary; increases bundle and review scope.
   - Effort: Medium

### Recommendation
Use the native History API plus a small typed route table. The graph shows a direct `AppShell` → `PanelShell` relationship and all views already converge in `AppShell`, so routing can be added at that seam without a new architectural layer. Promote the four requested helpers, and either promote `PageFrame`/`StateMessage`/`toneMaps` in the same boundary change or document them as an intentional temporary exception; leaving production pages dependent on story infrastructure undermines the stated migration. Move the shell CSS to the existing tokenized stylesheet boundary (prefer the smallest dedicated shell stylesheet or the existing primitives stylesheet based on current test guards), delete the injected `PANEL_SHELL_STYLES` block, and preserve the existing inline SVG icons rather than adding an icon package.

The shell should use clean `/panel/app/` paths, with explicit drill-down paths such as `/panel/app/clients/:id` and `/panel/app/conversations/:id`, and fall back safely to `/panel/app/` for unknown paths. Navigation controls should be real links where possible, with `aria-current="page"`; command/global action scope should stay minimal and only be added if a concrete current job exists.

### Risks
- Existing `openspec/specs/panel-app/spec.md` explicitly requires state routing without a router and lists URL shareability as a non-goal; the proposal/spec phase must update this contract rather than silently contradict it.
- Vite/nginx base-path behavior must be verified for `/panel/app/` deep links and refreshes; backend `/panel/api/` and `/panel/export/` routes must remain outside SPA fallback.
- Browser globals and history events are awkward in current jsdom tests; route parsing, push/replace semantics, back/forward, unknown paths, and cleanup need focused tests.
- Role-filtered navigation must not make an operator deep link into admin-only KB/settings appear as a fatal error; the existing 403 permission state remains required.
- Moving only four helpers leaves `PageFrame`, `StateMessage`, and `toneMaps` imported from `stories/`; either promote the complete production helper closure or accept and test a temporary split.
- Hash links and callback-based drill-downs currently coexist. Partial migration can create duplicate navigation or stale state unless all customer/conversation entry points are made URL-aware together.
- The shell contains responsive duplicate markup and focus management; deleting the whole mobile drawer or collapse behavior would regress accessibility. Delete only the obsolete style injection and any genuinely unused props/branches after tests prove they are unused.

### Ready for Proposal
Yes. The proposal should commit to native History API routing, define the bounded `/panel/app/` route table including drill-downs and role fallback, decide the helper-closure boundary (`PageFrame`/`StateMessage`/`toneMaps`), and split implementation into reviewable slices under the 400-line budget. Router installation is not justified by the current dependency graph or finite route surface.
