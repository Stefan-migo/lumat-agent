# ODD — panel-header-menus

Base: `a0a53310` (main). Worktree: `../lumat-agent-odd-panel-header-menus`, branch `odd/panel-header-menus`.
Source: owner brief 2026-10-01 (header back button, dashboard breadcrumb, notifications/user-menu bug, and two
redesigns with reference images: account menu + notifications popover).
References: `refs/Diseño Lumat/LUMATProfilePopoverwithLogout.png` (account menu) and the owner's notification
popover images. `refs/` is gitignored — read from the primary worktree only.

Graph nodes consulted: `PanelShell()`, `AccountControl()`, `UserContext()`, `Menu()`,
`parsePanelPath()`, `PanelShell.tsx`, `AppShell.tsx`, `panelRoutes.ts`, `PanelShell.test.tsx`,
`AppShell.test.tsx`.

## Objective

Fix the header navigation chrome (back-button visibility, breadcrumb) and redesign the account menu and the
notifications popover to the owner's designs — without touching the palette.

## Problem

1. **Back button** is rendered unconditionally (`PanelShell.tsx:481-483`) and always calls
   `window.history.back()`. It shows on Dashboard, where there is nothing to go back to.
2. **Breadcrumb** is built from the `currentView` prop + the `NAVIGATION` map (`PanelShell.tsx:484-490`), not
   from the URL. On Dashboard it renders the literal "Panel unificado", which is
   `NAVIGATION.dashboard.label` (`:43`) — the same map the **sidebar** uses.
3. **Bug:** opening the notifications popover unmounts the account control. `PanelShell.tsx:507-510` renders
   `AccountControl` only when `!notificationsOpen`. The bug is codified by `AppShell.test.tsx:476`.
4. **Account menu** (`AccountControl`, `:77-91`; `UserContext`, `:112-202`) is a bare text line + a plain
   logout button. `AccountControl` has **no** outside-click and **no** Escape close.
5. **Notifications popover** (`:498-505`) has no tabs, no icon tiles, a weak empty state.

## Decisions (owner-confirmed 2026-10-01)

| # | Decision |
| --- | --- |
| D1 | The back button is visible **only** on detail routes (a route whose drill-down param is set). Its click navigates **explicitly to the parent list route** — not `window.history.back()`. |
| D2 | The breadcrumb reads `Panel / <Section>`. The Dashboard segment label is "Dashboard". The **sidebar keeps** "Panel unificado" — `NAVIGATION` is not changed; a separate breadcrumb label map is used. |
| D3 | The account control must **never unmount** when the notifications popover opens. At most one popover is open at a time and both triggers stay visible. The test that enshrines the old behaviour is updated. |
| D4 | The redesign reuses existing tokens: `--danger`/`--danger-bg` (logout row), `--success-bg`/`--teal-500` (avatar/role), `--lime-500` (the "N nuevas" pill). **No palette change.** |
| D5 | Mobile behaviour is unchanged: the mobile bell still navigates to the notification centre. The mobile account menu gets the same visual treatment. |
| D6 | The detail-level (third) breadcrumb segment is **deferred**: the entity name is not known in the shell (`AppShell` has only the id; pages fetch the entity). Pages keep their own `PageHeader` title; the breadcrumb stays at section level on detail routes. Recorded, not silent. |

## Scope

**In:** back-button visibility + behaviour; breadcrumb format; the account control unmount bug; the
`AccountControl` and `UserContext` redesign (+ outside-click/Escape on `AccountControl`); the notifications
popover redesign; their tests and stories.

**Out:** the palette/tokens; the sidebar labels; the mobile bell behaviour; the `NotificationCenter` page
(unchanged); any new route or destination.

## Constraints

- Authorized files: `web/src/components/domain/PanelShell.tsx`, `web/src/components/domain/AppShell.tsx`,
  `web/src/components/domain/panelRoutes.ts` (only if needed), `web/src/components/primitives/primitives.css`,
  `web/src/components/domain/PanelShell.test.tsx`, `web/src/components/domain/AppShell.test.tsx`, affected
  `web/src/stories/**`.
- No new dependency, no new route, no palette change.
- **Strict TDD is active** (`openspec/config.yaml`): RED first, then GREEN, then REFACTOR.
- Artifacts and code comments in English; UI copy in neutral Chilean Spanish.
- One work-unit commit per task, tests alongside the behaviour, conventional commits, **no AI attribution**.

## Tasks

### Slice 1 — navigation chrome + the popover bug (behaviour)

- [x] **H1 — conditional back button.** `AppShell` passes the shell a back affordance only for detail routes:
  a route with `clientId` / `conversationId` / `automationRuleId` / `kbDocId` / `appointmentId` / `projectSlug` /
  `planningSessionSlug` (and `threadId` for chat). The click navigates to the parent list route (`pathForView`),
  not `window.history.back()`.
- [x] **H2 — breadcrumb.** Render `Panel / <Section>`; add a breadcrumb-label map with `dashboard: "Dashboard"`
  and labels for the compatibility views; keep `NAVIGATION` untouched for the sidebar. "Panel" links to the
  dashboard except on the dashboard itself.
- [x] **H3 — popover bug.** Stop unmounting `AccountControl` when the notifications popover is open. Opening one
  popover closes the other; both triggers remain visible. Update `AppShell.test.tsx:476` (it asserts the bug).
- [x] **H4 — tests for H1–H3:** back hidden on dashboard and list views, present on a detail route, and it
  navigates to the parent; breadcrumb text; both controls visible with notifications open.

### Slice 2 — the two redesigns (visual)

- [ ] **M1 — `AccountControl` redesign.** Identity block (square avatar + username + role in teal), a divider,
  and "Cerrar sesión" as a full-width destructive row (`--danger-bg` background, `--danger` text/icon). Add
  outside-click and Escape close.
- [ ] **M2 — `UserContext` redesign.** Same visual grammar as M1; keep the existing valuable behaviour
  (outside-click, Escape, focus return). The kebab trigger already exists.
- [ ] **M3 — notifications popover redesign.** Header with a "N nuevas" pill and close button; tabs
  "Todas" / "No leídas" (with a count); "Marcar todas como leídas" with an icon; rows with an icon tile per
  `source`, an unread dot, title, body, relative time and a chevron; a "Ver todas las notificaciones" footer;
  and the empty state (bell + check, "No tienes notificaciones" + subtitle).
- [ ] **M4 — tests + story.** Tests for the redesign behaviour; a Storybook story for the account menu and/or
  the notifications popover.

## Acceptance criteria

- The back button appears only on detail routes and returns to the parent section list.
- The breadcrumb reads `Panel / Dashboard` on the dashboard and `Panel / <Section>` elsewhere; the sidebar
  label is unchanged.
- Opening the notifications popover leaves the account trigger visible; opening one popover closes the other.
- The account menu (header + sidebar) matches the reference: identity block, divider, destructive logout row.
- The notifications popover matches the reference: pill, tabs, icon tiles, footer, empty state.
- `npm run build` passes; the affected tests pass; the full suite passes once per slice.

## Route decisions

| Task | Route | Trigger evidence |
| --- | --- | --- |
| H1+H2+H3 | delegated writer | 2 non-trivial files (`PanelShell.tsx` + `AppShell.tsx`) + tests; mapping done by the orchestrator |
| H4 | delegated writer | tests ship with H1–H3 |
| M1+M2 | delegated writer | `PanelShell.tsx` + `primitives.css` |
| M3 | delegated writer | `PanelShell.tsx` + `primitives.css` |
| M4 | delegated writer | tests + story |

## Progress and evidence

**Slice 1 (navigation chrome + the popover bug) — code complete and verified.**

- Commits: `87e3c15b` (`isDetailRoute`), `7270acec` (back, breadcrumb, popover fix).
- **H1**: `isDetailRoute()` added to `panelRoutes.ts` (gates each drill-down param by its view, mirroring
  `pathForRoute`); `PanelShell` gains an `onBack` prop and renders the back button only when supplied;
  `AppShell` passes a parent-route navigation (`navigateToRoute({ view, … })`), not `window.history.back()`.
- **H2**: `PanelShell` gains a `breadcrumbView` prop (needed because `shellView` remaps projects/planning to
  chat) plus `BREADCRUMB_OVERRIDES`; the breadcrumb reads `Panel / Dashboard` on the dashboard (`Panel`
  unlinked there) and `Panel / <Section>` elsewhere. `NAVIGATION` is untouched, so the sidebar keeps
  "Panel unificado".
- **H3**: the account control is always rendered (the `!notificationsOpen` wrapper is gone); opening one
  popover closes the other; both triggers stay visible. The `AppShell.test.tsx` assertion that the account
  trigger DISAPPEARS was replaced by one asserting it stays visible.
- **H4**: `panelRoutes.test.ts` covers `isDetailRoute` (list false; each detail param true; chat query params
  false; projects/planning slugs true); `PanelShell.test.tsx` covers back visibility/callback and the
  breadcrumb labels; `AppShell.test.tsx` covers the parent navigation, both triggers visible, and closing the
  account menu.
- Checks (re-run by the orchestrator, independent of the writer): `npm run build` → `tsc -b` + Vite OK
  (pre-existing chunk warning only); affected vitests → **3 files / 73 tests passed**. The writer reported RED
  (6 failures) before GREEN.
- Native RDD: `review assess --base-ref a0a53310 --committed-only` → risk **medium**
  (`executable_change`), `review_due: false`, `review_due_reason: under_budget` (242 changed lines, 7 paths).

**Slice 2 (the two redesigns) — pending.**

## Verification

- `cd web && npm run build` — the **only** type check (`tsc -b` runs inside it; a green Vitest run does NOT
  prove the tree type-checks).
- `cd web && npx vitest run <affected files>` per task; full `npm test` once per slice.
- Rendered pass over the header, both account menus and the notifications popover at the reference breakpoints.
