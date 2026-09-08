# Delta for panel-app

## ADDED Requirements

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
