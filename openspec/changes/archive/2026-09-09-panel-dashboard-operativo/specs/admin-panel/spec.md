# Delta for admin-panel

## MODIFIED Requirements

### Requirement: AP-2 — Roles and Permissions

The system MUST distinguish `admin`, `operador`, and `tecnico`. Admin and operador MUST access the operational dashboard. Tecnico MUST NOT access admin/chat/realtime surfaces; role boundaries MUST be enforced server-side.
(Previously: only admin and operador existed, and operador access covered general panel areas.)

#### Scenario: Admin and operator dashboard (pytest)
- GIVEN an authenticated admin or operador
- WHEN the dashboard endpoint is requested
- THEN it returns the authorized operational projection

#### Scenario: Operator general permissions (pytest)
- GIVEN an authenticated operador
- WHEN they navigate the panel
- THEN clients, conversations, cases, and notes remain available

#### Scenario: Admin general permissions (pytest)
- GIVEN an authenticated admin
- WHEN they navigate the panel
- THEN settings, cost guardrails, and KB management remain available

#### Scenario: Technician boundary (pytest)
- GIVEN an authenticated tecnico
- WHEN an admin, chat, or realtime surface is requested
- THEN the server returns JSON 403 without exposing data

### Requirement: AP-8 — Basic KPIs

The panel MUST show contacts, motivos, derived cases, visit requests, and new customers for a bounded seven-day window. Each KPI MUST expose the approved colored top accent, including Contactos.
(Previously: basic counters covered contacts, motivos, derived cases, and visit requests for a configured period.)

#### Scenario: Seven-day KPI row (vitest)
- GIVEN a loaded dashboard response
- WHEN the KPI row renders
- THEN all four KPIs appear, including new customers, and each has a top accent

## MODIFIED Requirements

### Requirement: AP-12 — Automation Rule Role Access

The panel MUST expose automation-rule reads and mutations only to authenticated admins. Unauthenticated requests MUST receive JSON 401 and operador requests, including GET list/detail, MUST receive JSON 403 without changing state. Existing backend admin guards MUST remain effective.
(Previously: authenticated operadores could read automation rules while only admin mutations were allowed.)

#### Scenario: Operator read denied (pytest)
- GIVEN an authenticated operador
- WHEN the automation list or detail is requested
- THEN the API returns JSON 403

#### Scenario: Admin reads rules (pytest)
- GIVEN an authenticated admin
- WHEN the automation list is requested
- THEN the API returns the authorized rule data

#### Scenario: Operator mutation remains forbidden (pytest)
- GIVEN an authenticated operador
- WHEN they submit an automation mutation
- THEN the API returns JSON 403 and the rule is unchanged

#### Scenario: Anonymous rejected (pytest)
- GIVEN no valid session
- WHEN the automation API is requested
- THEN it returns JSON 401 without an HTML redirect

## ADDED Requirements

### Requirement: AP-DASH-1 — Dashboard Authentication Contract

All dashboard projections MUST use the existing panel JSON authentication semantics: 401 for absent sessions, 403 for insufficient roles, and no redirects.

#### Scenario: Consistent denial (pytest)
- GIVEN an absent or insufficient session
- WHEN any new dashboard projection is requested
- THEN the corresponding JSON 401 or 403 response is returned
