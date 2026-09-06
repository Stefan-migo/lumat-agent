# Delta for calendar-integration

## ADDED Requirements

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
