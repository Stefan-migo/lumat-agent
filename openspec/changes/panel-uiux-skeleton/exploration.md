## Exploration: panel-uiux-skeleton

### Current State

The production React entry is `/panel/app/`: `main.tsx:3-7` loads tokens, the global primitive stylesheet, `App`, and PWA registration; `vite.config.ts:7-10` fixes the same base path. `app.tsx:23-70` probes `/panel/api/me`, then mounts `AppShell` or `LoginAuth`.

The shell is already implemented, but its navigation is an engineering inventory. `PanelShell.tsx:8` defines 12 `PanelView` values and `PanelShell.tsx:116-129` maps all of them 1:1 into `NAVIGATION`, including `notifications`, `push`, and `advanced-dashboard`. `AppShell.tsx:114-125` dispatches the same routes and mounts `CasesList`, `NotificationCenter`, `PushSettings`, and `AdvancedDashboard` as separate destinations. The shell has desktop sidebar, collapsed rail, and mobile drawer markup (`PanelShell.tsx:298-380`), with focus return, Escape handling, and a basic focus trap (`PanelShell.tsx:258-290`).

Routing is native History API and bounded to explicit path mappings (`panelRoutes.ts:10-25`, `61-80`). Drill-down IDs exist for clients, conversations, and automation rules only. The shell header currently contains collapse control, current route title, and optional status badge (`PanelShell.tsx:354-375`); there is no notification bell, unread badge, or avatar menu. User identity and logout remain in the sidebar/footer (`PanelShell.tsx:170-199`), not a header menu.

Login is functionally complete but visually unframed: `LoginAuth.tsx:27-59` renders a bare `main`, an inline-centered wrapper, a `Card className="card--auth"`, inline form styles, and a typographic brand block. `card--auth` has no definition in `primitives.css`; the existing reusable page frame is `PageFrame` (`components/shared/PageFrame.tsx:35-45`) and is not used by login. `PageHeader.tsx:10-18` and several pages (for example `CasesList.tsx:57-87`) still use inline layout styles.

Responsive tokens exist (`tokens.css:120-123`), but are reference-only. The shell consumes only `@media (min-width: 40rem)` and `@media (min-width: 64rem)` (`primitives.css:606-631`, `872-925`): mobile is a modal drawer below 1024px, while the design-system target distinguishes `<640`, `640–1023`, `1024–1279`, and `>=1280`. The drawer has good basic keyboard behavior, but there is no explicit body scroll lock, inert background handling, resize reconciliation, or touch-specific shell target rule. `@media (hover: none)` raises primitive buttons/fields to 44px (`primitives.css:112-121`), but shell buttons use their own sizing (`primitives.css:701-712`) and need direct review.

Notifications and push functionality already have separate page/API contracts: `NotificationCenter.tsx:9-18` lists and marks notifications read; `PushSettings.tsx:5-12` requests browser permission; `api.ts:86-88` exposes notification list/read calls. `Settings.tsx:75-84` has no push section, so moving push under Settings requires a new composition/navigation state, not deletion. `pwa.ts:1-28` registers `/panel/app/sw.js` with scope `/panel/app/` and excludes API/HTML from cache; shell route changes must preserve this boundary.

The current visual review surface is useful but incomplete for the new skeleton. `stories/pages/PanelEntry.stories.tsx:22-58` covers admin/operator desktop and tablet/mobile drawer-open states; `stories/pages/Login.stories.tsx:5-63` explicitly documents the old centered login; `stories/domain/AppShell.stories.tsx:13-17` documents role-gated navigation and a text-only header. Page stories exist for Dashboard, clients/ficha, conversations/thread, cases, KB, settings, agenda, automation rules/detail, chat, and login; there is no dedicated notification-header or push-under-settings story.

### Decision Validation

| Decision | Result | Evidence and required adjustment |
|---|---|---|
| Sidebar IA: eight user destinations | **Feasible with adjustment** | `NAVIGATION` and `AppShell` are centralized, so the change has a clean seam. Remove `notifications`, `push`, and `advanced-dashboard` from visible navigation; add/retain the eight approved destinations. Preserve role filtering, but confirm whether `Asistente Lumat` remains admin-only: it is currently `adminOnly` at `PanelShell.tsx:123`. |
| Conversaciones with Conversaciones\|Casos segment | **Needs adjustment** | Current cases is a fully separate `cases` route/page (`AppShell.tsx:120`, `panelRoutes.ts:16`). Mounting `CasesList` as a segment under the conversations destination is feasible, but `/panel/app/cases` must remain a compatibility alias or redirect to protect deep links/bookmarks. Keep the existing cases API and semantics; do not merge data models in this skeleton. |
| Notificaciones in header; push in Settings | **Feasible** | Notification fetch/read behavior is isolated in `NotificationCenter.tsx` and `api.ts`. Add a header bell/badge driven by a defined unread source, retain a reachable notification center route or overlay, and compose `PushSettings` inside Settings. The unread state source/refresh behavior is not currently present and must be specified without inventing realtime semantics. |
| `advanced-dashboard` disappears as a menu item | **Needs adjustment** | `AdvancedDashboard` uses a distinct endpoint/data model (`AdvancedDashboard.tsx:10-35`), while `Dashboard` renders the current KPI/motives contract (`Dashboard.tsx:79-125`). Hide the item now, but preserve `/panel/app/advanced-dashboard` as a compatibility route until Panel content is decided. Do not silently discard advanced metrics; either alias it to Panel or retain a non-menu deep link in a later Panel sweep. |
| Login split responsive | **Feasible** | `LoginAuth` is isolated and has no route coupling. Replace the wrapper with a two-region responsive frame, stack below the mobile breakpoint, preserve username/error/loading behavior (`LoginAuth.tsx:13-25`, `38-55`), and use the existing brand asset conventions from `PanelShell.tsx:131-165`. Add a real login story at narrow and desktop widths. |
| Mobile-first shell | **Feasible with adjustment** | Existing drawer/focus behavior is reusable (`PanelShell.tsx:252-351`), but CSS jumps from mobile drawer to persistent sidebar at 1024px and lacks the design-system 640px/1024px distinctions. Review drawer scroll containment, background interaction, resize transitions, shell touch targets, content padding, table overflow, and the inspector behavior. |
| Icon coherence | **Feasible** | `PanelShell.tsx:50-52` reuses `ChatIcon` for conversations, notifications, push, and chat; automation uses `GearIcon` (`127`). The new eight-item map needs distinct semantic choices without adding an icon dependency; retain inline SVGs unless a real gap is demonstrated. |
| Cleanup: phantom class, inline styles, page frame | **Feasible, bounded** | `card--auth` is referenced only by login and absent from primitive styles. Login and `PageHeader` have inline styles (`LoginAuth.tsx:29-54`, `PageHeader.tsx:12-17`). Use existing tokenized primitives/shared frame for skeleton surfaces, but defer broad page-by-page inline-style cleanup to the later section sweeps. |

### Affected Areas

- `web/src/components/domain/PanelShell.tsx` — replace the 12-item navigation map, add header actions (bell/badge and avatar menu), define active route/segment semantics, and preserve drawer/rail accessibility.
- `web/src/components/domain/AppShell.tsx` — compose the new header contracts, route Conversations/Cases segments, preserve compatibility routes, and keep existing page data ownership.
- `web/src/components/domain/panelRoutes.ts` — add bounded segment/alias parsing and canonical path policy for `/cases` and `/advanced-dashboard`; do not introduce a router dependency.
- `web/src/components/pages/LoginAuth.tsx` — responsive split frame, production brand treatment, removal of inline style block and `card--auth` dependency.
- `web/src/app.tsx` — verify auth gate, login error persistence, and refresh/deep-link behavior after shell/header changes.
- `web/src/components/pages/Settings.tsx` and `PushSettings.tsx` — mount push settings as a settings section without removing its browser permission states.
- `web/src/components/pages/NotificationCenter.tsx`, `web/src/api.ts`, `web/src/types.ts` — define the header unread/badge contract and preserve full notification-center behavior.
- `web/src/components/pages/Dashboard.tsx`, `AdvancedDashboard.tsx` — establish only the shell-level route fate; defer metric/content unification to the Panel sweep.
- `web/src/components/pages/ConversationsList.tsx`, `CasesList.tsx` — provide the internal segment surface while preserving independent serializers, filters, actions, emergency semantics, and tests.
- `web/src/components/primitives/primitives.css`, `tokens/tokens.css`, `components/shared/PageHeader.tsx` — implement tokenized shell/login/header styles and responsive rules; tokens already contain reference breakpoints but no layout consumers.
- `web/src/stories/pages/PanelEntry.stories.tsx`, `Login.stories.tsx`, `stories/domain/AppShell.stories.tsx` plus page stories/tests — add desktop/tablet/mobile shell, header menu/badge, login split, segment, route-alias, and role-state review surfaces. Existing stories cover most page bodies but not the new header/settings composition.
- `web/src/pwa.ts`, `web/index.html`, `web/vite.config.ts` — verify base path, manifest, service-worker scope/cache rules, and history fallback assumptions; no production delivery change is indicated by this exploration.

### Scope Boundary

Include in this skeleton: shell IA/chrome, responsive drawer/rail behavior, header notification/avatar affordances, route compatibility/segment wiring, login split, tokenized frame cleanup, and Storybook review states. Preserve all existing APIs and page behavior.

Defer to later section sweeps: dashboard metric/content reconciliation, full AdvancedDashboard redesign, conversation/cases data or visual redesign, notification center redesign, automation UX, broad inline-style removal, new unread/realtime backend semantics, dark mode, new icon/font/router dependencies, and PWA architecture changes.

### Graphify Consultation

Graphify report: `graphify-out/GRAPH_REPORT.md` (4213 nodes, 8665 edges; report built from `eb990dcf`, older than current local work). Queried before source inspection:

- `PanelShell`, `NAVIGATION`, `AppShell`, drawer/rail: resolved `PanelShell.tsx:L116`, `PanelShell():L239`, `AppShell():L39`, and `panelRoutes.ts:pathForRoute`.
- `LoginAuth`, auth gate, page frame: resolved `LoginAuth():L13`, `App():L23`, `Card`, `PageFrame`, `Login.stories.tsx`.
- `panelRoutes`, notifications, push, settings, advanced dashboard, cases/conversations: resolved `AdvancedDashboard.tsx`, `CasesList.tsx`, `PushSettings.tsx`, `Settings.tsx`, `NotificationCenter` and `AppShell.tsx`.
- `PanelShell.tsx` → `LoginAuth.tsx` directed path: none found; this confirms the login/shell relationship is composition through `app.tsx`, not a direct module edge. The graph’s `AppShell.tsx` community contains the route table, shell, auth gate, and page dispatch.

### Risks

- Removing or relocating routes can break production deep links, bookmarks, browser history, and Storybook route assumptions; retain aliases and test canonicalization.
- Advanced dashboard data is not a visual alias of the basic dashboard; hiding its menu item without a route/content policy can lose discoverability or functionality.
- Header unread badges require a truthful source and refresh policy; do not fabricate counts or silently couple the shell to a new fetch/realtime loop.
- Moving push settings can regress browser permission, PWA scope, or operator/admin visibility if Settings composition is not role-aware.
- Drawer behavior at intermediate widths may regress focus, scroll, or touch usability; verify narrow/medium/desktop and keyboard/reduced-motion states.
- Existing inline styles and story-local page patterns can expand the change beyond the 400-line review budget; keep this change to shared skeleton/chrome contracts.

### Approaches

1. **Evolve the existing shell seam** — modify `AppShell`/`PanelShell` and the native route table, keeping pages/API contracts intact.
   - Pros: smallest risk, preserves recent shell/routing work, no dependency.
   - Cons: route aliases and header state need explicit tests.
   - Effort: Medium

2. **Introduce a new shell/router architecture** — replace the current seam with a new global frame and routing dependency.
   - Pros: more future abstraction.
   - Cons: unnecessary churn, deep-link/PWA risk, conflicts with recent decisions and design-system no-new-library constraint.
   - Effort: High

### Recommendation

Use Approach 1. Treat this as a shared shell and entry-frame change, not a redesign of every page. Implement the approved IA and login/mobile frame, preserve compatibility paths for `cases` and `advanced-dashboard`, and make the unread badge/Settings push placement explicit in the proposal/spec before implementation. Keep dashboard, cases, conversations, notification-center, automation, and settings content sweeps separate.

### Ready for Proposal

Yes, with two decisions made explicit in the proposal: the compatibility policy for `/panel/app/cases` and `/panel/app/advanced-dashboard`, and the truthful unread-count source/refresh contract for the header bell. The implementation surface is concrete and the remaining uncertainty is product behavior, not code discovery.
