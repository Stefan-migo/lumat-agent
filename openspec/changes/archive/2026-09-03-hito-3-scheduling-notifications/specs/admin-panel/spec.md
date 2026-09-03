# Delta for Admin Panel

## ADDED Requirements

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

The panel MUST show appointment conflicts, failed/pending calendar synchronization, failed notifications, and template-policy errors with actionable status.

#### Scenario: Failed integration visible
- GIVEN a calendar synchronization has failed
- WHEN an authorized user views the appointment
- THEN its failure status and retry action are shown
