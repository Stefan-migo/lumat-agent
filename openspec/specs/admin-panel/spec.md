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

The system MUST expose `GET /panel/api/conversations` returning `{"conversations": [...]}` where each item is `to_conversation_dict(conversation)` — read-only (no assignee/responsible field, no reply/state mutation, no migration of existing conversations), following the JSON API router conventions in `app/panel/api/routes/conversations.py` (`require_user_json`, JSON 401/403, same-origin cookie, no redirects, no CORS). Rows MUST be ordered by most recent activity first (`last_message_at` DESC NULLS LAST, then `id` DESC). No pagination in this change (ponytail: add a cap only if the inbox grows).

#### Scenario: List returns serialized conversations

- GIVEN an authenticated user
- WHEN they request `GET /panel/api/conversations`
- THEN the response is 200 with `{"conversations": [...]}` and every item matches the `to_conversation_dict` shape (snake_case, ISO dates, nullable timestamps)

#### Scenario: Read-only, no assignee

- GIVEN the response payload
- WHEN it is inspected
- THEN no assignee/responsible field appears and no mutation endpoint is added

#### Scenario: Most recent first

- GIVEN conversations with different `last_message_at` values
- WHEN the list is requested
- THEN conversations with the most recent activity sort first (nulls last, `id` tiebreak)

#### Scenario: Anonymous rejected

- GIVEN no session cookie
- WHEN the endpoint is requested
- THEN it returns JSON 401 `{"detail": ...}` with no redirect

#### Scenario: Backend tests cover the endpoint

- GIVEN the applied change
- WHEN `pytest` runs against the functional suite
- THEN tests cover the response shape, ordering, and the 401 case

## Non-Goals

- Assignee/responsible column on conversations; reply/state mutation endpoints (HH-5); pagination; migration of existing conversation rows.
