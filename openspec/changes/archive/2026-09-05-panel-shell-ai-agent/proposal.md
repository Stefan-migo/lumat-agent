# Proposal: Panel Shell AI-Agent Infrastructure

## Intent

Prepare the React panel for AI-agent work without visual redesign. State-only navigation, hash links, injected CSS, and production imports from `stories/` block a stable production boundary.

## Scope

### In Scope
- Add a typed native History API table in `AppShell` for nine views and two drill-downs; support popstate, refresh, fallback, and role-safe links.
- Promote four helpers plus `PageFrame`, `StateMessage`, and `toneMaps` into `web/src/components/`; retain required story wrappers.
- Move the 522-line style injection to the tokenized stylesheet boundary without visual change.
- Make navigation and entry points URL-aware with `aria-current="page"`, preserving responsive, focus, drawer, collapse, and 403 behavior.

### Out of Scope
- ChatGPT/OpenWebUI redesign, agenda/calendar, automations, WebSocket, Jinja removal, or global commands.
- Router libraries, icon packs, CSS frameworks, new palette tokens, or speculative abstractions.

## Capabilities

### New Capabilities
- None. This is an infrastructure evolution of existing panel behavior.

### Modified Capabilities
- `panel-app`: supersede stale D7. Dependency-free routing MUST synchronize `/panel/app/` URLs, deep links, refresh, back/forward, and safe fallback. URL shareability is now in scope; hash navigation is removed.
- `panel-design-system`: shell styles/navigation MUST consume the token boundary while preserving accessibility contracts.

## Approach

Keep routing at the `AppShell` → `PanelShell` seam with normalized paths, `pushState`/`popstate`, and explicit drill-down patterns. Relocate helpers, update imports/wrappers, and extract CSS unchanged. Ponytail: native APIs and inline SVGs suffice.

Graph: `AppShell.tsx`, `PanelShell.tsx`, `app.tsx`, page/helper nodes, `api.ts`, `types.ts`; edge `AppShell.tsx --imports_from--> PanelShell.tsx`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `web/src/components/domain/` | Modified | Routing, links, shell styles |
| `web/src/components/pages/` | Modified | Helper imports and drill-down links |
| `web/src/components/`, `web/src/stories/pages/_shared/` | New/Modified | Helper closure and wrappers |
| `web/src/**`, `openspec/specs/` | Modified | Regression tests and contract deltas |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Deep-link/base-path or role regression | Med | Focused route, refresh, popstate, and 403 tests; preserve `/panel/app/` boundary |
| CSS/helper migration breaks stories | Med | Move closure atomically and keep thin wrappers where tests require |

## Rollback

Revert slices in reverse order: restore styles, imports, and state/hash navigation. API and delivery remain unchanged.

## Dependencies

- Change A’s `/panel/app/` delivery and fallback must remain deployed.

## Success Criteria

- [ ] Nine views and both drill-downs have clean, refreshable URLs with working back/forward and safe fallback.
- [ ] `cd web && npm test` and `npm run build` pass; responsive/a11y and operator 403 behavior remain intact.
- [ ] Production pages no longer import the helper closure from `stories/` except wrappers.
- [ ] Forecast: ~900–1,300 authored changed lines (High, above 400); use chained slices for routing, helpers, and stylesheet/tests.
