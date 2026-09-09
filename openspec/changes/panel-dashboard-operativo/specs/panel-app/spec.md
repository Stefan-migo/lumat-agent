# Delta for panel-app

## MODIFIED Requirements

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

## ADDED Requirements

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
