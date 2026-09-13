# Delta for panel-app

## ADDED Requirements

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
