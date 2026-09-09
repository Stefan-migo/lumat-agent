# Delta for advanced-dashboards

## MODIFIED Requirements

### Requirement: AD-1 — Operational Metrics

The panel MUST expose a bounded, authenticated dashboard projection for admin and operador users. It MUST use the request timezone for the local-day HOY window and a seven-day period for KPI metrics. The seven-day response MUST include contacts, derived cases, visit requests, and customers created in-window.
(Previously: metrics covered a selected bounded period without the approved HOY projection or new-customer KPI.)

#### Scenario: Seven-day metrics (pytest)
- GIVEN an authenticated admin or operador requests a valid dashboard period
- WHEN the seven-day metrics are computed
- THEN the response contains the four KPIs, period metadata, and customers created within that window

#### Scenario: Timezone-aware HOY projection (pytest)
- GIVEN a request timezone whose local date differs from UTC
- WHEN the dashboard projection is requested
- THEN appointments are limited to that local date and the response is bounded

#### Scenario: Invalid period (pytest)
- GIVEN a period outside the allowed seven-day dashboard window
- WHEN metrics are requested
- THEN the server returns a validation error without an unbounded query

### Requirement: AD-2 — Trends and Drill-Down

The dashboard MUST retain bounded trend and drill-down behavior and MUST render the seven-day trend as a compact mini trend. Motivos MUST be represented as one-line chips rather than full-width bars.
(Previously: trend and motivos presentation were unspecified for the operational dashboard.)

#### Scenario: Seven-day trend (pytest/vitest)
- GIVEN a valid seven-day window with contact or case events
- WHEN the trend is requested and rendered
- THEN daily bounded buckets appear in the compact mini trend

#### Scenario: Empty trend (pytest/vitest)
- GIVEN a valid window with no matching events
- WHEN the dashboard renders
- THEN zero-valued buckets and an explicit empty state appear

## ADDED Requirements

### Requirement: AD-HOY-1 — Operational HOY Projection

One authenticated endpoint MUST return bounded projections for today’s appointments, active unanswered conversations, and open urgent cases. Unanswered MUST mean at least one inbound message and no outbound message after the latest inbound. Urgent MUST mean `escalated_at` is set or `emergency` is true, with `closed_at` null.

#### Scenario: Three projections (pytest)
- GIVEN an authenticated admin or operador
- WHEN the HOY endpoint is requested
- THEN it returns the three named bounded collections with stable serialized fields

#### Scenario: Row navigation (vitest)
- GIVEN a loaded HOY row
- WHEN the user activates it
- THEN appointments navigate to Agenda, conversations to Conversaciones, and cases to Casos

#### Scenario: No results (pytest/vitest)
- GIVEN no appointments, unanswered conversations, or urgent cases
- WHEN the endpoint and dashboard render
- THEN each collection is empty and each section shows a truthful empty state

### Requirement: AD-HOY-2 — Failure and Authentication States

The dashboard MUST show loading and recoverable error states. Anonymous requests MUST receive the existing JSON 401 contract; insufficient role access MUST receive JSON 403 and a permission state.

#### Scenario: Request failure (vitest)
- GIVEN the HOY request fails after authentication
- WHEN the dashboard renders
- THEN an accessible error state is shown without fabricated rows

#### Scenario: Anonymous request (pytest)
- GIVEN no valid panel session
- WHEN the HOY endpoint is requested
- THEN it returns JSON 401 without redirecting to HTML
