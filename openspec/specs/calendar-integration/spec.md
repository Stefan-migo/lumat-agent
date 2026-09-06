# Calendar Integration Specification

## Purpose

Provide a narrow, non-authoritative calendar boundary for local bookings.

## Requirements

### Requirement: CI-1 — Stable Calendar Identity

The system MUST export or synchronize a local appointment through a provider boundary with a stable UID, idempotency key, timezone, and cancellation state. Local scheduling MUST remain authoritative.

#### Scenario: Repeat synchronization
- GIVEN an unchanged appointment is synchronized twice
- WHEN both requests are processed
- THEN one external calendar identity is retained and no duplicate event is created

#### Scenario: Cancellation export
- GIVEN a locally cancelled appointment
- WHEN its calendar representation is synchronized
- THEN the external event is cancelled or marked cancelled

### Requirement: CI-2 — Visible Partial Failure

The system MUST retain the local appointment when an external calendar operation fails, record a visible pending/failed status, and permit retry or reconciliation.

#### Scenario: Provider unavailable
- GIVEN a valid local appointment and an unavailable provider
- WHEN synchronization runs
- THEN booking remains intact and failure is auditable and retryable

### Requirement: CI-3 — Bounded Agenda Range Read

The authenticated API MUST read an inclusive `from`/`to` date range in a valid IANA timezone, reject reversed or over-31-day ranges with `invalid_range`, and reject unknown zones with `invalid_timezone`. It MUST order by local start then ID and return customer/case/technician display names, local and UTC times, lifecycle (`booked`, `cancelled`, `completed`, `no_show`), and independent sync (`pending`, `synced`, `failed`), error, and retryability. Cancelled rows remain visible; sync failure never invalidates local scheduling. Existing sync MUST retry pending/failed records while preserving stable identity and lifecycle.

#### Scenario: Valid range
- GIVEN an authenticated user requests a valid zone and bounded range
- WHEN matching appointments exist
- THEN display joins, both time representations, statuses, and stable ordering are returned

#### Scenario: Invalid range
- GIVEN an unknown zone, reversed dates, or a range over 31 days
- WHEN the endpoint is called
- THEN it returns 400 with `invalid_timezone` or `invalid_range` without mutation
