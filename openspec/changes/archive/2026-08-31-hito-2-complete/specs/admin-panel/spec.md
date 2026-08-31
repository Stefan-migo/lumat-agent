# Delta for admin-panel

## MODIFIED Requirements

### Requirement: AP-9 — Conversations List Endpoint

The system MUST expose authenticated `GET /panel/api/conversations` returning `{"conversations": [...]}` with state, persisted assignee, latest customer inbound timestamp, and delivery/window summary; it MUST support state and assignee filters. Rows MUST be ordered by most recent activity (`last_message_at` DESC NULLS LAST, then `id` DESC). JSON 401/no redirects apply. (Previously: read-only rows without assignee, filters, or mutation contract.)

#### Scenario: Authorized filtered list
- GIVEN an authenticated operator and conversations in multiple states
- WHEN state/assignee filters are requested
- THEN only matching rows and the production contract are returned

#### Scenario: Production fields and commands
- GIVEN a serialized list response
- WHEN it is inspected
- THEN assignment/window/delivery fields are present and command endpoints are available separately

#### Scenario: Most recent first
- GIVEN conversations with different activity timestamps
- WHEN the list is requested
- THEN newest activity sorts first, with nulls last and `id` as tiebreaker

#### Scenario: Anonymous rejected
- GIVEN no session cookie
- WHEN the endpoint is requested
- THEN JSON 401 is returned and no redirect occurs

#### Scenario: Backend contract coverage
- GIVEN the applied change
- WHEN the functional suite runs
- THEN response shape, filters, ordering, and 401 behavior are covered

## ADDED Requirements

### Requirement: AP-10 — Ownership and legal commands

Authenticated panel users MUST be able to take (`bot→human`, assign self), return (`human→bot`, clear/retain assignment per contract), and close (`human→closed`) conversations. Illegal transitions and assigning inactive/nonexistent users MUST return a conflict/validation error; successful and rejected commands MUST be audited and concurrency-safe.

#### Scenario: Take, return, close
- GIVEN an authorized operator and a valid current state
- WHEN one legal command is submitted
- THEN state/assignment persist with actor and cause

#### Scenario: Stale command
- GIVEN another request changed the conversation first
- WHEN a stale command arrives
- THEN it is rejected without overwriting state and is audited
