# Delta for panel-app

## ADDED Requirements

### Requirement: PNL-APP-1 — D7 URL Routing Without a Router (Slice 1)

The SPA MUST use a small typed native History API route table in AppShell, MUST NOT add a router dependency, and MUST synchronize the nine top-level views plus `/panel/app/clients/:id` and `/panel/app/conversations/:id`. Navigation MUST use clean links or equivalent controls with `aria-current="page"`; hash navigation MUST NOT be used.
(Previously: AppShell used state-only routing, drill-down callbacks, and treated URL shareability as a non-goal.)

#### Scenario: View navigation updates URL
- GIVEN an authenticated user at `/panel/app/`
- WHEN they activate Clients
- THEN the Clients view renders and the URL is `/panel/app/clients`
- AND its navigation item has `aria-current="page"`

#### Scenario: Deep link and refresh
- GIVEN a valid client or conversation drill-down URL
- WHEN the SPA loads or refreshes at that URL
- THEN the authenticated shell renders the matching detail view

#### Scenario: Back, forward, and unknown paths
- GIVEN navigation has produced multiple valid history entries
- WHEN the user uses browser back/forward or opens an unknown `/panel/app/*` path
- THEN the matching prior view renders, or the unknown path safely falls back to `/panel/app/`

#### Scenario: Role-safe admin deep link
- GIVEN an operador opens a KB or Settings deep link
- WHEN the view loads and the API returns 403
- THEN the permission-denied state renders and the shell does not crash or bypass authorization

### Requirement: PNL-APP-2 — Auth Gate with Real Login

The auth gate MUST replace the inline anon stub in `web/src/app.tsx` with a real LoginForm: on mount it probes `GET /panel/api/me`; `anon` renders the form, which MUST `POST /panel/api/login` via `api.ts`, render loading and error states, preserve the username on failure (DS-UI-LOGIN), and MUST NOT reveal whether a username exists. On success the gate MUST render `AppShell` with the returned role.

#### Scenario: Successful login

- GIVEN valid credentials on the LoginForm
- WHEN the form is submitted
- THEN `POST /panel/api/login` succeeds and the shell renders with the returned role

#### Scenario: Failed login keeps the username

- GIVEN a 401 `invalid credentials` response
- WHEN the form is submitted
- THEN an inline non-destructive error renders and the username persists

#### Scenario: Account locked

- GIVEN a 401 `account locked` response
- WHEN the form is submitted
- THEN the lock message renders without leaking whether the account exists

### Requirement: PNL-APP-3 — Logout

The shell MUST expose logout from the PanelShell user block: it MUST `POST /panel/api/logout`, and on success the gate MUST return to the LoginForm.

#### Scenario: Logout returns to login

- GIVEN an authenticated user in the shell
- WHEN logout is triggered
- THEN `POST /panel/api/logout` succeeds and the gate renders the LoginForm

### Requirement: PNL-APP-4 — Page Extraction Preserves Story Exports (R7)

The designed page components MUST be extracted from `web/src/stories/pages/*.stories.tsx` into `web/src/components/pages/` (DashboardOverview, LoginAuth, ClientesListView, ClientFichaView, ConversationsListView, ConversationThreadView, CasesListView, KbListView, SettingsView), and each story file MUST become a thin wrapper re-importing the extracted component, keeping the existing named exports and their props so story tests stay green.

#### Scenario: Story tests still resolve exports

- GIVEN a story test importing e.g. `DashboardOverview` from `Dashboard.stories`
- WHEN the extraction is applied
- THEN the same export name resolves with unchanged props

#### Scenario: Wrappers render the extracted component

- GIVEN a story state variant (loading/empty/error)
- WHEN it renders through the wrapper
- THEN it matches the pre-extraction rendering

### Requirement: PNL-APP-5 — Pages Consume the Real API

Extracted pages MUST consume the live JSON API through `api.ts` (`apiFetch`/`ApiError`) instead of `mockData`, and MUST render loading, empty, stale, and error states through the `StateMessage`/`DataTable` patterns from `stories/pages/_shared`; `mockData` remains story-only.

#### Scenario: Loading and error states

- GIVEN a list page with a pending or failed fetch
- WHEN it renders
- THEN the StateMessage loading / fatal-error states appear

#### Scenario: Empty state

- GIVEN a 200 response with an empty collection
- WHEN the list renders
- THEN the DataTable empty state shows "No hay registros"

### Requirement: PNL-APP-6 — 403 Handling on Admin-Only Views

The kb and settings views MUST handle an `ApiError` with status 403 by rendering a permission-denied state (StateMessage) for operadores; they MUST NOT crash or render a fatal error. Nav already hides them via PanelShell `adminOnly`, but the active view state MUST be safe.

#### Scenario: Operador sees denied state

- GIVEN an operador session with kb or settings as the active view
- WHEN the page fetch returns 403
- THEN a permission-denied state renders, not a fatal error

### Requirement: PNL-APP-7 — Production conversations

`ConversationsListView` MUST consume the filtered production list, show state/assignee/window and refresh after commands; each row MUST open a thread that loads current messages and outbound delivery states. (Previously: unfiltered read-only list and thread.)

#### Scenario: List and thread

- GIVEN the conversations endpoint returns serialized conversations
- WHEN the view loads
- THEN production fields and chronological current messages render

#### Scenario: Refresh after command

- GIVEN a conversation row
- WHEN the command completes
- THEN list and thread refresh, while loading/error states remain actionable

### Requirement: PNL-APP-9 — Composer and permissions

The SPA MUST expose take/return/close and a text composer with typed API contracts; it MUST show loading, disabled, policy, failed-delivery/retry, 401, 403, and conflict states without optimistic state corruption. Archived Storybook UI remains a dependency, not reimplementation.

#### Scenario: Window and permission states

- GIVEN stale-window, anonymous, or forbidden responses
- WHEN the thread renders or submits
- THEN the composer is disabled or a specific permission/policy state is shown

### Requirement: PNL-APP-8 — Dashboard Renders Real KPIs

DashboardOverview MUST render the real `compute_kpis` counts (contacts, motivos, derived, visit_requests, window caption) on the designed StatCards, and MUST NOT render fabricated deltas, autonomy %, response time, or the activity feed (R1 — designed metrics are a follow-up).

#### Scenario: Real counts on designed cards

- GIVEN `GET /panel/api/kpis`
- WHEN the Dashboard renders
- THEN StatCards show contacts/derived/visit_requests and the motivos list with the window caption from the payload

#### Scenario: No fabricated metrics

- GIVEN the Dashboard
- WHEN it is inspected
- THEN no delta/autonomy/response-time values and no activity feed appear

### Requirement: PNL-APP-10 — Agent-App Shell Grammar

`PanelShell` and `AppShell` MUST present the panel as an agent application: a forest rail, brand, role-safe `NAVIGATION`, active-thread region, and compact/expanded rail states. Existing native History routing, `aria-current="page"`, drawer focus behavior, and operator filtering MUST remain unchanged.

#### Scenario: Role-safe compact rail
- GIVEN an operador renders `AppShell`
- WHEN `PanelShell` is compact
- THEN navigation remains keyboard reachable with labels/tooltips and admin-only `NAVIGATION` entries are absent

#### Scenario: History contract survives shell change
- GIVEN a user navigates through `AppShell` using `panelRoutes.ts`
- WHEN browser back, forward, deep-link, or an unknown path is exercised
- THEN the existing route and accessibility outcomes of PNL-APP-1 remain unchanged

### Requirement: PNL-APP-11 — Truthful Active-Thread Chrome

`PanelShell` MAY accept an optional `activeThreads` contract with explicit loading, empty, error, and placeholder states, but MUST NOT fetch conversations, call `listConversations()`, or fabricate customer/thread data. The structural region MUST be labeled `Conversaciones activas` when expanded and MAY be hidden in compact mode.

#### Scenario: No supplied data
- GIVEN `PanelShell` receives no active-thread data
- WHEN the expanded shell renders
- THEN a labeled truthful empty/placeholder state appears and no conversation request is made

#### Scenario: Supplied state matrix
- GIVEN the optional contract is loading, empty, or failed
- WHEN the rail renders
- THEN the matching visible state and `status`/`alert` semantics appear without shell-owned retry/fetch behavior

### Requirement: PNL-APP-12 — Conditional Conversation and Dense-Page Surfaces

Conversation routes MUST render `ConversationThread` and `ConversationsList` with directional bubbles/avatars, approved owner-status labels, handoff and reply-window presentation, retry/error affordances, and an optional inspector slot only when context exists. Dashboard, `ClientesList`, `ClientFicha` history, `CasesList`, `AgendaPage`, `AutomationRulesPage`, `Settings`, and `KbList` MUST retain their `DataTable`, KPI, `Badge`, filter, and `StateMessage` control-room primitives.

#### Scenario: Conversation detail states
- GIVEN `/panel/app/conversations/:id` renders a loaded thread
- WHEN messages, handoff, delivery failure, or a closed reply window are present
- THEN the DOM exposes direction, owner/status, handoff, retry, and disabled-reason semantics around the existing mutation behavior

#### Scenario: Inspector is conditional
- GIVEN a non-conversation dense page or a conversation without inspector context
- WHEN the page renders
- THEN no empty inspector column is reserved and dense control-room primitives remain present

#### Scenario: List chrome alignment
- GIVEN `ConversationsList` renders loading, empty, error, or rows
- WHEN its page chrome is inspected
- THEN its table/state behavior remains intact while header, filters, and selected-row treatment use the agent-app grammar

### Requirement: PNL-APP-13 — Realtime Conversation Surfaces

The SPA MUST use one authenticated `/panel/ws` client for live conversation list, thread, ficha, activity, and internal-chat token updates. It MUST retain REST POST commands and MUST refetch conversations and the active summary after reconnect before clearing its disconnected state.

#### Scenario: Live conversation update
- GIVEN the conversation list and thread are open with a connected socket
- WHEN a message or state event arrives
- THEN the matching list, thread, and ficha data update without a manual refresh

#### Scenario: Reconnect recovery
- GIVEN the socket disconnects
- WHEN it reconnects
- THEN the SPA refetches authoritative resources and renders recovered data without replaying events

### Requirement: PNL-APP-14 — Active Summary Rail

`PanelShell` MUST feed its `Conversaciones activas` rail from `GET /panel/api/conversations/active`, including customer name and recency, with loading, empty, error, and disconnected states. It MUST NOT compose active truth from the general conversation list.

#### Scenario: Active rail data
- GIVEN the active-summary endpoint returns rows
- WHEN the expanded rail renders
- THEN rows show customer names ordered by server-provided recency

#### Scenario: Active rail failure
- GIVEN the active-summary request fails or the socket is disconnected
- WHEN the rail renders
- THEN an accessible status/error state appears without fabricated rows

### Requirement: PNL-APP-15 — Agent Activity Semantics

Conversation activity and token-streaming states MUST render with existing panel primitives and accessible `role="status"` semantics; errors MUST use `role="alert"`. The UI MUST distinguish persisted activity history from transient connection status.

#### Scenario: Activity announcement
- GIVEN a `classified`, `kb_retrieved`, or `escalation` event arrives
- WHEN the thread renders it
- THEN a visible labeled activity uses `role="status"`

### Requirement: PNL-APP-16 — Client ficha mutations

ClientFicha MUST submit state changes to `POST /panel/api/clients/{id}/state` and notes to `/notes` through the authenticated API contract. Each mutation MUST expose loading, validation/error, and success states, MUST present audit-safe errors without sensitive internals, and MUST refresh the authoritative ficha after completion.

#### Scenario: State change succeeds
- GIVEN an authenticated operator edits a client state
- WHEN the state form is submitted
- THEN the state endpoint succeeds, success feedback is shown, and ficha data refreshes

#### Scenario: Mutation fails safely
- GIVEN the state or note request returns a validation or server error
- WHEN the mutation completes
- THEN an actionable error is shown without sensitive details and existing data remains intact

### Requirement: PNL-APP-17 — Knowledge-base mutations

KbList MUST wire upload, edit, disable, and restore actions to the existing `/panel/api/kb*` endpoints. Validation errors MUST be visible and actionable, and the list MUST refresh from the server after a committed mutation or use an equivalent rollback-safe optimistic update.

#### Scenario: Document lifecycle mutation
- GIVEN an authorized admin submits a valid upload, edit, disable, or restore action
- WHEN the API commits it
- THEN the action feedback is shown and the KB list reflects the committed server state

#### Scenario: Invalid document input
- GIVEN a KB mutation contains invalid input
- WHEN the API returns validation errors
- THEN the field or action error is visible and no stale optimistic state remains

### Requirement: PNL-APP-18 — Authenticated client exports

ClientesList MUST provide real authenticated downloads from `/panel/export/clients.csv` and `/panel/export/cases.csv`. Export controls MUST NOT use placeholder data or data URIs, and authorization failures MUST remain visible without fabricating a download.

#### Scenario: CSV export download
- GIVEN an authenticated user on ClientesList
- WHEN they activate a client or case export
- THEN the browser requests the corresponding `/panel/export/*.csv` endpoint with the session contract

#### Scenario: Export is denied
- GIVEN an unauthenticated or unauthorized export request
- WHEN the export is activated
- THEN no placeholder file is generated and the authentication/error state is preserved

### Requirement: PNL-APP-19 — Reachable advanced dashboard

AdvancedDashboard MUST be a role-protected top-level panel view reachable through `panelRoutes.ts` and rendered by `AppShell`. It MUST consume `/panel/api/dashboard/summary`, `/trend`, and `/drilldown`, preserving loading, empty, error, and authorization states.

#### Scenario: Dashboard navigation and data
- GIVEN an authenticated user selects AdvancedDashboard
- WHEN the route is opened
- THEN AppShell renders it and the three dashboard API resources populate their corresponding views

#### Scenario: Dashboard authorization failure
- GIVEN the dashboard API returns 403
- WHEN AdvancedDashboard renders
- THEN a permission-denied state appears and the shell remains usable

### Requirement: PNL-APP-20 — SPA-only panel runtime

The panel MUST be served and operated through the SPA; server-rendered panel routes, templates, and Jinja-only dependencies MUST be retired. Existing API, WebSocket, CSV export, cookie-authentication, and conversation behavior MUST remain available under their established contracts.

#### Scenario: SPA replaces legacy rendering
- GIVEN a panel view is requested after retirement
- WHEN the panel loads
- THEN the SPA shell is used and no Jinja-rendered view is required

#### Scenario: Backend contracts remain available
- GIVEN an authenticated panel session
- WHEN API, WebSocket, CSV, or login behavior is exercised
- THEN the established backend response and authorization contracts remain intact

## Non-Goals

- react-router / URL shareability (D7 follow-up); `_shared` relocation; token changes; InboxThread composer and state controls; ChatWithAgent; designed dashboard metrics (autonomy %, response time, deltas); activity feed.
