# Admin Panel Specification

## Purpose

Provide the minimal H1 admin panel (served by FastAPI) for authorized users: login with roles (admin/operador), clients list/search, conversation view, cases view, KB manager access, CSV export, and basic KPIs. Ponytail scope: no PWA, no chart library, no advanced dashboards (H2-H4).

## Requirements

### Requirement: AP-1 — Authentication

The system MUST require login for all panel access. Sessions MUST expire and failed login attempts MUST be limited and recorded.

#### Scenario: Authorized login
- GIVEN an authorized user with valid credentials
- WHEN they log in
- THEN they access the panel and the login is audited

#### Scenario: Failed login
- GIVEN a user submits wrong credentials repeatedly
- WHEN the attempts exceed the limit
- THEN access is blocked temporarily and attempts are recorded

### Requirement: AP-2 — Roles and Permissions

The system MUST distinguish `admin` and `operador` roles. `operador` MUST access clients, conversations, cases, and internal notes. `admin` MUST additionally access settings (scope limits, emergency keywords, cost guardrails) and KB management. Role access MUST be enforced server-side.

#### Scenario: Operador permissions
- GIVEN an operador logs in
- WHEN they navigate the panel
- THEN they see clients, conversations, cases, and notes but not settings or KB management

#### Scenario: Admin permissions
- GIVEN an admin logs in
- WHEN they navigate the panel
- THEN they additionally see settings, cost guardrails, and KB management

### Requirement: AP-3 — Clients List and Search

The system MUST list customers with their state and MUST support searching by name and phone number.

#### Scenario: Search customer
- GIVEN the clients view is open
- WHEN the user searches by name or phone
- THEN matching customer records are returned

### Requirement: AP-4 — Conversation View

The system MUST display conversation threads with messages and linked files (evidence) for a customer, read-only in H1.

#### Scenario: View conversation
- GIVEN a customer record is selected
- WHEN the user opens the conversation view
- THEN messages and linked files are displayed in order

### Requirement: AP-5 — Cases View

The system MUST list cases (pending/escalated) and MUST allow authorized users to change case state and assign a responsible person (LumatRequest §1.11).

#### Scenario: Assign and update case
- GIVEN a case in the pending view
- WHEN the user assigns a responsible and changes its state
- THEN the case updates and the change is audited

### Requirement: AP-6 — KB Manager Access

The panel MUST expose the KB manager (add/edit/disable documents) for admin users, delegating to the knowledge-base spec mechanics (KB-3).

#### Scenario: Admin opens KB manager
- GIVEN an admin user
- WHEN they open the KB manager view
- THEN they can add, edit, or disable documents

### Requirement: AP-7 — CSV/Excel Export

The system MUST export clients and requests (cases) to CSV or Excel with the fields visible in the panel, keeping data under Lumat's control.

#### Scenario: Export clients
- GIVEN the clients view is open
- WHEN the user exports
- THEN a CSV/Excel file with client data is downloaded

### Requirement: AP-8 — Basic KPIs

The panel MUST show basic indicators: contacts received, reasons (motivos), derived cases, and visit requests. KPIs MUST be simple counters/time-window aggregates — no chart library, no advanced reporting (H4).

#### Scenario: KPIs rendered
- GIVEN the panel home is open
- WHEN indicators are computed
- THEN contacts, motivos, derived cases, and visit requests are shown for the configured period

### Requirement: AP-9 — Conversations List Endpoint

The system MUST expose `GET /panel/api/conversations` returning `{"conversations": [...]}` with state, persisted assignee, latest customer inbound timestamp, and delivery/window summary; it MUST support state and assignee filters. Rows MUST be ordered by most recent activity (`last_message_at` DESC NULLS LAST, then `id` DESC). JSON 401/no redirects apply. (Previously: read-only rows without assignee, filters, or mutation contract.)

#### Scenario: List returns serialized conversations

- GIVEN an authenticated user
- WHEN they request `GET /panel/api/conversations`
- THEN the response is 200 with `{"conversations": [...]}` and every item matches the `to_conversation_dict` shape (snake_case, ISO dates, nullable timestamps)

#### Scenario: Production fields and commands

- GIVEN a serialized list response
- WHEN it is inspected
- THEN assignment/window/delivery fields are present and command endpoints are available separately

#### Scenario: Most recent first

- GIVEN conversations with different `last_message_at` values
- WHEN the list is requested
- THEN conversations with the most recent activity sort first (nulls last, `id` tiebreak)

#### Scenario: Anonymous rejected

- GIVEN no session cookie
- WHEN the endpoint is requested
- THEN it returns JSON 401 `{"detail": ...}` with no redirect

#### Scenario: Backend contract coverage

- GIVEN the applied change
- WHEN `pytest` runs against the functional suite
- THEN tests cover the response shape, ordering, and the 401 case

### Requirement: AP-10 — Authorized H3 Operations

The panel/API MUST expose authenticated scheduling, availability, notification, template, and calendar actions. Server-side permissions MUST prevent unauthorized reads and mutations; all mutations MUST be audited.

#### Scenario: Operator books visit
- GIVEN an authenticated operator and an available slot
- WHEN they submit a valid booking
- THEN the appointment is created and its audit entry is visible

#### Scenario: Unauthorized mutation
- GIVEN an unauthenticated or insufficiently privileged user
- WHEN they request an H3 mutation
- THEN the server returns an authorization error and changes nothing

### Requirement: AP-11 — Operational Failure Visibility

The panel MUST show appointment conflicts, failed/pending synchronization, failed notifications, and template-policy errors with actionable status. Authenticated operators/admins MUST see cancellation for booked appointments and retry for pending/failed sync. Lifecycle and sync failures MUST remain separate.
(Previously: cancellation visibility and lifecycle/sync separation were unspecified.)

#### Scenario: Failed integration visible
- GIVEN a calendar synchronization has failed
- WHEN an authorized user views the appointment
- THEN its failure status and retry action are shown

#### Scenario: Booked cancellation visible
- GIVEN an authorized user views a booked appointment
- WHEN the agenda row renders
- THEN the cancellation action is available and requires confirmation before mutation

## Non-Goals

- Assignee/responsible column on conversations; reply/state mutation endpoints (HH-5); pagination; migration of existing conversation rows.
