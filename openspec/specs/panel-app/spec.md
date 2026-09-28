# Delta for panel-app

## ADDED Requirements

### Requirement: PNL-APP-1 — D7 URL Routing Without a Router (Slice 1)

The SPA MUST use the typed native History API route table, MUST NOT add a router dependency, and MUST expose exactly ten navigation destinations: Panel unificado, Asistente Lumat, Conversaciones, Clientes, Agenda, Base de Conocimientos, Automatizaciones, Configuración, Usuarios, and Proyectos. Notifications, push, and advanced-dashboard MUST NOT be visible navigation items. `/panel/app/cases` and `/panel/app/advanced-dashboard` MUST still resolve as compatibility routes.
(Previously: the navigation contract exposed nine destinations (including Usuarios) and had no Proyectos destination.)

#### Scenario: Projects navigation
- GIVEN an authenticated user at `/panel/app/`
- WHEN they activate Proyectos
- THEN the view renders at `/panel/app/projects` with `aria-current="page"`

#### Scenario: Compatibility deep links
- GIVEN a user opens `/panel/app/cases` or `/panel/app/advanced-dashboard`
- WHEN the SPA parses the path or refreshes
- THEN the existing compatible view resolves without a router or data-model migration

#### Scenario: History and authorization remain safe
- GIVEN valid history entries or an operador opening an admin-only deep link
- WHEN back/forward or the API authorization check runs
- THEN the prior view or permission-denied state renders without a crash or bypass

## ADDED Requirements

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

The designed page components MUST be extracted from `web/src/stories/pages/*.stories.tsx` into `web/src/components/pages/` (DashboardOverview, LoginAuth, ClientesListView, ClientFichaView, ConversationsListView, ConversationThreadView, KbListView, SettingsView), and each story file MUST become a thin wrapper re-importing the extracted component, keeping the existing named exports and their props so story tests stay green.

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

### Requirement: PNL-APP-7 — Unified Production Conversations

`ConversationsListView` MUST consume the unified queue contract, show case context, tab counts, priority ordering, search, limit/offset pagination, and applicable `Tomar`/`Reconocer` actions. Selecting a row MUST open a workspace whose thread retains current messages, delivery states, and existing conversation mutations. (Previously: the view showed a filtered production list and thread without unified case context, queue tabs, search, pagination, or queue actions.)

#### Scenario: Queue and workspace

- GIVEN the conversations endpoint returns serialized conversations with optional case context
- WHEN the view loads and a row is selected
- THEN the queue fields render and the workspace loads chronological messages plus the selected case context

#### Scenario: Command refresh

- GIVEN a queue row or open thread
- WHEN a take, acknowledge, state, or message command completes
- THEN authoritative queue and thread data refresh while actionable loading/error states remain visible

### Requirement: PNL-APP-9 — Composer and permissions

The SPA MUST expose take/return/close and a text composer with typed API contracts; it MUST show loading, disabled, policy, failed-delivery/retry, 401, 403, and conflict states without optimistic state corruption. Archived Storybook UI remains a dependency, not reimplementation.

#### Scenario: Window and permission states

- GIVEN stale-window, anonymous, or forbidden responses
- WHEN the thread renders or submits
- THEN the composer is disabled or a specific permission/policy state is shown

### Requirement: PNL-APP-8 — Dashboard Renders Real KPIs

DashboardOverview MUST render the authenticated HOY projection, role-appropriate bento navigation, and real seven-day KPIs: contacts, derived, visit requests, and new customers. It MUST render a compact mini trend and one-line motivos chips, with a colored top accent on every KPI including Contactos.
(Previously: DashboardOverview rendered only contacts, derived, visit requests, motivos, and a window caption.)

#### Scenario: Admin dashboard (vitest)
- GIVEN an authenticated admin with loaded dashboard data
- WHEN the dashboard renders
- THEN HOY appears above the bento grid and seven-day period block, including the Agente Lumat card and Automations card

#### Scenario: Operator dashboard (vitest)
- GIVEN an authenticated operador with loaded dashboard data
- WHEN the dashboard renders
- THEN four equal cards appear without Agente Lumat or Automations

#### Scenario: Period presentation (vitest)
- GIVEN seven-day KPI and trend data
- WHEN the period block renders
- THEN four accented KPIs, a mini trend, and one-line motivos chips appear

### Requirement: PNL-APP-10 — Agent-App Shell Grammar

`PanelShell` and `AppShell` MUST retain the forest rail, brand, role-safe navigation, active-thread region, compact/expanded states, native History routing, `aria-current`, and drawer focus behavior. The header MUST expose notification-bell and avatar affordances; identity/logout MUST remain available from the avatar affordance.
(Previously: the shell grammar had a text-only header and user block in the sidebar.)

#### Scenario: Header actions are usable
- GIVEN an authenticated user renders the shell
- WHEN the header is inspected and keyboard operated
- THEN bell and avatar controls have accessible names, visible focus, and usable destinations/actions.

#### Scenario: Compact rail remains role-safe
- GIVEN an operador renders a compact shell
- WHEN navigation is keyboard traversed
- THEN labels/tooltips remain available and admin-only entries remain absent.

### Requirement: PNL-APP-21 — Unified Cases Compatibility Route

The Conversations destination MUST be the unified operational section; `/panel/app/cases` MUST soft-redirect or resolve to it with the `Casos` tab active. `CasesList` MUST no longer be the rendered owner of that route, while existing case mutation semantics remain available from the unified workspace. (Previously: a `Conversaciones|Casos` segment rendered `CasesList` as a separate surface and the alias preserved that ownership.)

#### Scenario: Bookmarked cases route
- GIVEN an authenticated user opens `/panel/app/cases`
- WHEN the SPA parses the path
- THEN the unified conversations view renders with `Casos` selected and no standalone `CasesList` page is mounted

### Requirement: PNL-APP-22 — Settings Push Composition

Configuración MUST include the existing PushSettings surface as a section without deleting its permission, unsupported, or fallback states; push MUST NOT be a top-level navigation destination.

#### Scenario: Push settings remain functional
- GIVEN an authorized user opens Configuración
- WHEN the push section is rendered
- THEN existing browser permission actions and states remain available.

#### Scenario: PWA boundary preserved
- GIVEN shell routes change
- WHEN PWA registration and cache rules are exercised
- THEN scope remains `/panel/app/` and API/HTML exclusions remain unchanged.

### Requirement: PNL-APP-23 — Skeleton Verification Gates

The skeleton MUST preserve existing page-body, API, data-model, and PWA contracts; acceptance MUST include green backend and web suites.

#### Scenario: Required suites pass
- GIVEN the completed skeleton change
- WHEN `uv run pytest tests/` and `cd web && npx vitest run` execute
- THEN both suites pass without changing page-body or backend contracts.

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

### Requirement: PNL-APP-12 — Conversation Workspace Context

Conversation routes MUST render the thread as the main workspace area and a RIGHT context panel containing a case block, customer block, and collapsible `captured_data` key/value block when data exists. The panel MUST show explicit emergency, acknowledgement, status, and priority state, preserve direction/owner/handoff/reply-window/retry semantics, and MUST NOT reserve an inspector for non-conversation pages. (Previously: conversation routes had only an optional inspector slot and no required case/customer/captured-data workspace.)

#### Scenario: Loaded workspace
- GIVEN a selected conversation with case, customer, and captured data
- WHEN its route renders
- THEN the thread is primary, the context panel is on the right, and all three context blocks are accessible

#### Scenario: Missing optional context
- GIVEN a conversation without a case or captured data
- WHEN the workspace renders
- THEN the customer/thread remain usable, absent blocks show no fabricated data, and no empty inspector is reserved elsewhere

#### Scenario: List chrome alignment
- GIVEN `ConversationsList` renders loading, empty, error, or rows
- WHEN its page chrome is inspected
- THEN queue tabs, search, pagination, and selected-row treatment use the agent-app grammar while state behavior remains actionable

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


### Requirement: PNL-APP-24 — Role Routing and Technician Shell

The SPA MUST branch by the authenticated role. A tecnico MUST render a mobile-friendly agenda shell only; admin and operador MUST retain their existing panel shell and routes. Navigation MUST use `panelRoutes.ts` and `pathForView` without adding a router dependency.

#### Scenario: Technician login (vitest)
- GIVEN login returns role `tecnico`
- WHEN the auth gate completes
- THEN only the technician agenda shell renders

#### Scenario: Dashboard row navigation (vitest)
- GIVEN an admin or operador activates a dashboard row or card
- WHEN navigation runs
- THEN the existing route table resolves Agenda, Conversaciones, Casos, Clientes, or chat as approved
### Requirement: PNL-APP-25 — Technician Privacy Surface

The technician agenda UI MUST display only customer name, address, comuna, phone, appointment service, and brief case summary. It MUST NOT render email, consent, conversation/message history, internal notes, calendar-sync, or operational fields.

#### Scenario: Allowed agenda fields (vitest)
- GIVEN a technician agenda response
- WHEN an appointment renders
- THEN only the allow-listed fields are visible

#### Scenario: Forbidden fields absent (vitest)
- GIVEN an appointment payload containing sensitive fields
- WHEN the technician view renders
- THEN email, consent, history, and internal/operational fields are not present in the DOM
### Requirement: PNL-APP-26 — Shared Dashboard States

Dashboard and technician surfaces MUST represent loading, empty, 401, 403, and recoverable error states using existing panel state primitives.

#### Scenario: State matrix (vitest)
- GIVEN any supported surface is loading, empty, unauthorized, forbidden, or failed
- WHEN it renders
- THEN the matching accessible state appears without fabricated data or a crash

### Requirement: USR-UI-1 — Admin User View and Navigation

The SPA MUST provide an admin-only `Usuarios` view wired through the existing `PanelShell` navigation, `AppShell` view switch, and `panelRoutes` path mapping. Non-admin users MUST NOT see or reach the view.

#### Scenario: Admin navigation (vitest)
- GIVEN an authenticated admin
- WHEN the panel shell renders and `Usuarios` is selected
- THEN the navigation item is visible and the user-management page renders at its mapped panel route

#### Scenario: Non-admin navigation is filtered (vitest)
- GIVEN an authenticated operador or tecnico
- WHEN the panel shell renders or the user route is opened
- THEN `Usuarios` is absent and the view is denied without user data

### Requirement: USR-UI-2 — User List Presentation

The user-management page MUST load and render username, role, and active status for each user, including all supported roles. Role labels MUST be `Administrador`, `Operador`, and `Técnico`; the `tecnico` value MUST never display as an untranslated technical identifier.

#### Scenario: Render roles and status (vitest)
- GIVEN a successful list response containing admin, operador, and tecnico users
- WHEN the page renders
- THEN each username, translated role label, and active/inactive status is visible

#### Scenario: Safe list shape is respected (vitest)
- GIVEN list data without credential or lockout fields
- WHEN the rows render
- THEN the page renders normally and does not require or display sensitive fields

### Requirement: USR-UI-3 — Create User Flow

The page MUST provide username, password, and role controls. It MUST prevent submission of blank usernames or passwords shorter than 8 characters, submit valid data, refresh or update the list on success, and present API validation/conflict errors without losing entered non-password context.

#### Scenario: Successful creation (vitest)
- GIVEN valid username, password of at least 8 characters, and selected role
- WHEN the create form is submitted
- THEN a create request is made and the new safe user row becomes visible

#### Scenario: Client and API validation errors (vitest)
- GIVEN invalid form data or a duplicate username response
- WHEN submission is attempted
- THEN an accessible error is shown and no successful-user state is presented

### Requirement: USR-UI-4 — Active Toggle and Password Reset

The page MUST offer active-status toggling and password reset for other users. Controls for the current admin’s row MUST be disabled. Toggle and reset actions MUST expose pending, success, and error outcomes; reset MUST confirm before submission and MUST NOT display a password.

#### Scenario: Manage another user (vitest)
- GIVEN an admin viewing another user
- WHEN the admin confirms a toggle or password reset
- THEN the corresponding request is sent, pending state is visible, and success updates the row or reports completion

#### Scenario: Self-protection in the UI (vitest)
- GIVEN the current admin appears in the list
- WHEN their row renders
- THEN toggle and reset controls are disabled and cannot initiate a request

### Requirement: USR-UI-5 — User View State Matrix

The view MUST represent loading, empty, API error, and denied states with accessible existing panel state primitives, without fabricated rows. It MUST preserve actionable error messaging when mutations fail.

#### Scenario: List state matrix (vitest)
- GIVEN the list is loading, empty, failed, or forbidden
- WHEN the page renders
- THEN the matching loading, empty, error, or denied state is visible and no user rows are fabricated

### Requirement: PNL-APP-27 — Read-only project SDB browse

The panel MUST provide authenticated read-only list and detail endpoints and UI at `/panel/app/projects`, navigating list → detail. Detail MUST show only typed `sdb:*` artifacts, including cross-thread grouping where applicable, and MUST exclude WhatsApp conversations. The panel MUST NOT expose project CRUD or mutation endpoints.

#### Scenario: Project detail contents
- GIVEN an authorized user selects a project
- WHEN the detail view loads
- THEN only its typed SDB artifacts are shown, grouped by entity, with no WhatsApp conversation rows

#### Scenario: Read-only boundary
- GIVEN a user attempts project create, rename, archive, or merge through panel routes
- WHEN the request is made
- THEN no CRUD endpoint exists and no registry mutation occurs

### Requirement: PNL-APP-28 — Planning sessions navigation and read surface

The authenticated SPA MUST add a “Sesiones de planning” destination with list and detail views. It MUST consume authenticated read-only list/detail endpoints, show thread identity, status, decisions, and report, and provide a reopen action that opens the associated thread and reactivates its session.

#### Scenario: List and detail navigation

- GIVEN an authenticated administrator and available planning sessions
- WHEN they select “Sesiones de planning” and a row
- THEN the list and detail views render status, decisions, report, and thread identity

#### Scenario: Reopen

- GIVEN a closed session belonging to an accessible thread
- WHEN the administrator activates Reopen
- THEN the thread opens with Cortex active and its indicator is visible

#### Scenario: Unauthorized or failed read

- GIVEN an unauthenticated or unauthorized request, or a failed endpoint
- WHEN the planning view loads
- THEN an accessible authentication/permission/error state renders with no fabricated sessions

### Requirement: PNL-APP-29 — Explicit Cortex controls and indicator

The chat UI MUST provide open/close controls and literal command support for `/planning <topic>` and `/planning close`. It MUST show a persistent visible active-session indicator and MUST NOT activate planning from free text.

#### Scenario: Active indicator

- GIVEN a valid active Cortex thread
- WHEN the chat renders
- THEN the indicator and Close session control are visible

#### Scenario: Free text is inert

- GIVEN an inactive thread
- WHEN a message mentions planning without the literal command
- THEN the session remains inactive

## Non-Goals

- react-router / URL shareability (D7 follow-up); `_shared` relocation; token changes; InboxThread composer and state controls; ChatWithAgent; designed dashboard metrics (autonomy %, response time, deltas); activity feed.
