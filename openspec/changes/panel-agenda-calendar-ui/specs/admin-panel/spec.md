# Delta for admin-panel

## MODIFIED Requirements

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
